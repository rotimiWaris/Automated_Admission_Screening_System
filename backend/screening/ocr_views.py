import base64
import csv
from io import StringIO
from hashlib import sha256
import os
from pathlib import Path
import shutil
from threading import BoundedSemaphore

from django.http import JsonResponse
from django.core import signing
from django.views.decorators.http import require_http_methods
from result_ocr import OCRConfig, OCRError
from result_ocr.documents import extract_page
import pytesseract
from .result_parser import parse_drafts
from .table_import import import_students
from .applicant_data import ADMISSION_TYPES

# Configure the process once; never accept executable paths from an upload.
_command = os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
if not _command:
    for root in [os.getenv('ProgramFiles', 'C:/Program Files'), os.getenv('LOCALAPPDATA', '')]:
        candidate = Path(root) / 'Tesseract-OCR' / 'tesseract.exe'
        if candidate.is_file():
            _command = str(candidate)
            break
if _command:
    pytesseract.pytesseract.tesseract_cmd = _command
_models = Path(__file__).resolve().parents[2] / 'ocr-data'
if (_models / 'eng.traineddata').is_file():
    os.environ.setdefault('TESSDATA_PREFIX', str(_models))
_capacity = BoundedSemaphore(1)

def recognise(raw, page_number, smart_processing=False):
    """Retry ambiguous recognition without substituting or inventing characters."""
    page = extract_page(raw, page_number, OCRConfig(timeout_seconds=45))
    drafts, notices = parse_drafts(page.result.to_dict(), smart_processing)
    def rank(records):
        rows = [row for record in records for sitting in record['sittings'] for row in sitting['subjects']]
        return (len(records), -sum(row['grade'] == 'Unreadable' for row in rows), len(rows))
    if not drafts or rank(drafts)[1] < 0:
        try:
            config = OCRConfig(timeout_seconds=45, pdf_dpi=200) if raw.lstrip().startswith(b'%PDF-') else OCRConfig(timeout_seconds=45, page_segmentation_mode=11)
            alternative = extract_page(raw, page_number, config)
            other_drafts, other_notices = parse_drafts(alternative.result.to_dict(), smart_processing)
            if rank(other_drafts) > rank(drafts):
                page, drafts, notices = alternative, other_drafts, other_notices
                notices.append('A second recognition pass recovered additional fields. Text and confidence come from that pass.')
        except OCRError:
            notices.append('The alternate-resolution check failed; review the first extraction.')
    return page, drafts, notices

@require_http_methods(['GET', 'POST'])
def ocr(request):
    if request.method == 'GET':
        return JsonResponse({'available': bool(_command), 'max_bytes': 10 * 1024 * 1024, 'max_pages': 10})
    upload = request.FILES.get('file')
    smart_value = request.POST.get('smart_processing', 'false')
    if smart_value not in ['true', 'false']:
        return JsonResponse({'error': 'Smart processing must be true or false.'}, status=400)
    smart_processing = smart_value == 'true'
    admission_type = request.POST.get('admission_type', 'ND Full-Time')
    if admission_type not in ADMISSION_TYPES:
        return JsonResponse({'error': 'Select a valid admission type.'}, status=400)
    if upload is None:
        return JsonResponse({'error': 'Choose a PNG, JPEG, PDF, CSV or XLSX file.'}, status=400)
    if upload.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'The document exceeds the 10 MB upload limit.'}, status=413)
    try:
        page_number = int(request.POST.get('page', '1'))
    except ValueError:
        return JsonResponse({'error': 'Choose a valid page number.'}, status=400)
    if upload.name.lower().endswith(('.csv', '.xlsx', '.xls')):
        try:
            if page_number != 1:
                raise OCRError('A spreadsheet is imported in one request. Select page 1.')
            raw = upload.read(10 * 1024 * 1024 + 1)
            drafts, rows = import_students(raw, upload.name, admission_type, smart_processing)
            merge_report = drafts[0].get('merge_report') if drafts else None
            text = StringIO()
            writer = csv.writer(text)
            headers = list(dict.fromkeys(key for row in rows for key in row.values))
            writer.writerow(['Sheet', 'Row', *headers])
            for row in rows[:100]:
                writer.writerow([row.sheet, row.number, *[row.values.get(key, '') for key in headers]])
            token = signing.dumps({'document': sha256(raw).hexdigest(), 'page': 1, 'drafts': drafts, 'admission_type': admission_type}, salt='ocr-batch', compress=True)
            return JsonResponse({'page': 1, 'page_count': 1, 'token': token, 'confidence': None, 'merge_report': merge_report, 'source_format': upload.name.rsplit('.', 1)[-1].lower(),
                                 'text': text.getvalue(), 'drafts': drafts, 'warnings': ['Imported directly from cells; OCR was not used. Invalid or missing values need review.'],
                                 'low_confidence_words': [], 'preview': None, 'table': {'headers': headers, 'rows': [[row.values.get(key, '') for key in headers] for row in rows[:20]], 'count': len(rows)}})
        except OCRError as exc:
            return JsonResponse({'error': str(exc)}, status=422)
    if not _command:
        return JsonResponse({'error': 'Tesseract is not installed or configured. Install the engine, set TESSERACT_CMD if needed, and restart Django.'}, status=503)
    if not _capacity.acquire(blocking=False):
        return JsonResponse({'error': 'Another page is being processed. Try again shortly.'}, status=429)
    try:
        raw = upload.read(10 * 1024 * 1024 + 1)
        page, drafts, notices = recognise(raw, page_number, smart_processing)
        result = page.result.to_dict()
        token = signing.dumps({'document': sha256(raw).hexdigest(), 'page': page.page_number, 'drafts': drafts, 'admission_type': admission_type}, salt='ocr-batch', compress=True)
        return JsonResponse({'page': page.page_number, 'page_count': page.page_count,
                             'token': token,
                             'confidence': round(sum(w['confidence'] for w in result['words']) / len(result['words']), 1) if result['words'] else 0,
                             'text': result['text'], 'drafts': drafts,
                             'warnings': list(result['warnings']) + notices,
                             'low_confidence_words': [w['text'] for w in result['words'] if w['confidence'] < 70],
                             'preview': 'data:image/png;base64,' + base64.b64encode(page.preview_png).decode('ascii')})
    except OCRError as exc:
        return JsonResponse({'error': str(exc)}, status=422)
    finally:
        _capacity.release()
