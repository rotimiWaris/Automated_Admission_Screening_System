"""Screen signed OCR drafts against explicitly matched rule revisions."""
from collections import Counter
import base64
from django.core import signing
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .routes import evaluate_route
from .models import RuleSet, Verification
from .views import api, body
from .identities import registration_key, screening_key
from .applicant_data import ADMISSION_TYPES
from .screening_export import enrich_result, workbook_bytes


@require_POST
@api
def screen_batch(request):
    data = body(request)
    admission_type = data.get('admission_type', 'ND Full-Time')
    if admission_type not in ADMISSION_TYPES:
        raise ValueError('Select a valid admission type.')
    tokens, mappings = data.get('pages'), data.get('course_rules', {})
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= 10 or not all(isinstance(t, str) and len(t) < 8 * 1024 * 1024 for t in tokens):
        raise ValueError('Supply extracted pages from one document (maximum 10).')
    if not isinstance(mappings, dict) or len(mappings) > 100:
        raise ValueError('Supply valid course-to-rule mappings.')
    if type(data.get('save')) is not bool:
        raise ValueError('Save must be true or false.')
    if data['save'] and not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in to save screening history.'}, status=401)
    records, seen_pages, documents = [], set(), set()
    for token in tokens:
        try:
            page = signing.loads(token, salt='ocr-batch', max_age=3600)
        except signing.BadSignature:
            raise ValueError('The extraction expired or changed. Extract the document again.')
        documents.add(page.get('document'))
        if len(documents) > 1:
            raise ValueError('Screen pages from one document at a time.')
        if page['page'] in seen_pages:
            raise ValueError('A PDF page was included more than once.')
        seen_pages.add(page['page'])
        if page.get('admission_type', 'ND Full-Time') != admission_type:
            raise ValueError('Admission type changed. Import the document again for this admission type.')
        records.extend((page['page'], draft) for draft in page['drafts'])
    if not 1 <= len(records) <= 10000:
        raise ValueError('Extract between 1 and 10000 students per batch.')
    registrations = Counter(screening_key(draft, admission_type) for _, draft in records)
    existing = dict(Verification.objects.filter(owner=request.user, registration_key__in=[key for key in registrations if key]).values_list('registration_key', 'id')) if request.user.is_authenticated else {}
    if admission_type != 'ND Full-Time' and request.user.is_authenticated:
        for saved in Verification.objects.filter(owner=request.user, result__admission_type=admission_type).values('id','result'):
            key = screening_key(saved['result'])
            if key: existing.setdefault(key,saved['id'])
    rules = {r.id: r for r in RuleSet.objects.filter(active=True, admission_type__in=[admission_type, 'All Admission Type', 'ND Full-Time'])}
    results = []
    with transaction.atomic():
        for page_number, draft in records:
            issues = list(draft.get('review_issues', []))
            registration = screening_key(draft, admission_type)
            duplicate = bool(registration and (registration in existing or registrations[registration] > 1 or draft.get('duplicate_in_upload')))
            if admission_type != 'ND Full-Time' and draft.get('admission_type') != admission_type:
                issues.append('Import the register using the selected admission type before screening.')
            mapping = mappings.get(draft['course'])
            if mapping is None:
                from .programmes import programme_key
                matches = [r for r in rules.values() if programme_key(r.programme) == programme_key(draft['course'])]
                specific = [r for r in matches if r.admission_type == admission_type]
                matches = specific or matches
                if len(matches) == 1:
                    mapping = {'id': matches[0].id, 'revision': matches[0].revision}

            rule = rules.get(mapping.get('id')) if isinstance(mapping, dict) and type(mapping.get('id')) is int else None
            if admission_type != 'ND Full-Time' and draft.get('admission_type') != admission_type:
                rule = None
            if rule and mapping.get('revision') != rule.revision:
                return JsonResponse({'error': 'Programme rules changed. Reload programmes before screening this batch.'}, status=409)
            outcome = None
            if admission_type != 'ND Full-Time':
                from .entry_assessment import assess_entries
                try:
                    assessment = assess_entries(draft, list(rules.values()), admission_type, not issues)
                    assessment['warnings'].extend(draft.get('optional_warnings', []) + draft.get('processing_warnings', []))
                    assessment['smart_processing'] = draft.get('smart_processing', False)
                    outcome = enrich_result(assessment, draft, admission_type)
                except ValueError as exc:
                    issues.append(str(exc))
            elif not rule:
                issues.append('No active admission rule is matched to this course. Select one and screen again.')
            else:
                try:
                    assessment = evaluate_route(rule, draft, admission_type, not issues)
                    if draft.get('optional_warnings') and any(c['status'] == 'failed' and c['label'] not in ['ND CGPA', 'ND grade consistency', 'JAMB score', 'JAMB subject combination', 'Examination sittings'] for c in assessment['checks']):
                        assessment = evaluate_route(rule, draft, admission_type, False)
                    assessment['warnings'].extend(draft.get('optional_warnings', []) + draft.get('processing_warnings', []))
                    assessment['smart_processing'] = draft.get('smart_processing', False)
                    outcome = enrich_result(assessment, draft, admission_type)
                except ValueError as exc:
                    issues.append(str(exc))
            item = {'page': page_number, 'student_name': draft['student_name'], 'registration_number': draft['registration_number'],
                    'course': draft['course'], 'confidence': draft.get('confidence', 0),
                    'source_format': draft.get('source_format', 'ocr'), 'source_rows': draft.get('source_rows', []),
                    'source_record': draft.get('source_record', {}), 'applicant': draft.get('applicant', {}), 'original_remark': draft.get('original_remark', ''),
                    'status': outcome['status'] if outcome else 'Pending Review', 'issues': list(dict.fromkeys(issues + (outcome.get('warnings', []) if outcome else []))), 'result': outcome}
            results.append(item)
            if duplicate:
                item.update(save_skipped=True, existing_id=existing.get(registration))
                item['storage_notice'] = 'Already in history; not saved again.' if registration in existing else 'Repeated registration in this upload; not saved.'
                # Reassess every row for the report; duplication only blocks saving.
        # Validate the entire batch before saving any rows.
        if data['save']:
            for item in results:
                if item['result'] and not item.get('save_skipped'):
                    origin_key = 'ocr' if item['source_format'] == 'ocr' else 'import_source'
                    result = item['result'] | {origin_key: {'page': item['page'], 'confidence': item['confidence'], 'issues': item['issues'], 'format': item['source_format'], 'rows': item['source_rows']}}
                    key = screening_key(item, admission_type)
                    if not key:
                        item['status'] = 'Pending Review'
                        item['issues'].append('A valid '+('JAMB registration number' if admission_type=='ND Full-Time' else 'form number')+' is required before saving.')
                        continue
                    saved, created = Verification.objects.get_or_create(owner=request.user, registration_key=key, defaults={'result': result})
                    if created:
                        item['result'] = result | {'id': saved.id, 'created_at': saved.created_at.isoformat()}
                    else:
                        item.update(save_skipped=True, existing_id=saved.id, storage_notice='Already in history; not saved again.')
    # Only validated admission registers have the columns required for this report.
    from .register_schema import prepare_register_row
    from .routes import headers_for
    from types import SimpleNamespace
    from result_ocr import OCRError
    exportable = True
    for index, (_, draft) in enumerate(records, 1):
        try:
            prepare_register_row(SimpleNamespace(values=draft.get('source_record', {})), headers_for(admission_type), admission_type, index)
        except OCRError:
            exportable = False
            break
    response = {'results': results, 'summary': dict(Counter(item['status'] for item in results))}
    if exportable:
        report = workbook_bytes(results, admission_type)
        response['excel'] = {'filename': 'screening-results.xlsx', 'base64': base64.b64encode(report).decode('ascii')}
    else:
        response['export_notice'] = 'No Excel file was created: the input does not contain the expected admission register columns. Upload the register for the selected admission type; row number, age, sitting count and Remark may be omitted.'
    return JsonResponse(response)
