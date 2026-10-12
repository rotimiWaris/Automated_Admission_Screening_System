"""Bounded, single-page PDF/image OCR; independent of any web framework."""
from dataclasses import dataclass
from io import BytesIO
import math
from threading import RLock
import warnings

from PIL import Image, ImageOps
import pypdfium2 as pdfium
from .service import OCRConfig, OCRError, OCRResult, extract_image

# PDFium is not thread-safe. Protect all PDFium calls, even on separate documents.
_pdf_lock = RLock()

@dataclass(frozen=True)
class DocumentPage:
    result: OCRResult
    page_number: int
    page_count: int
    preview_png: bytes


def extract_document(raw: bytes, config: OCRConfig | None = None, max_pages: int = 10):
    """Yield every page in order, keeping only one rendered page in memory.

    Callers can report progress using page_number/page_count. An error raises
    OCRError rather than silently presenting an incomplete document as complete.
    """
    first = extract_page(raw, config=config, max_pages=max_pages)
    yield first
    for number in range(2, first.page_count + 1):
        yield extract_page(raw, number, config, max_pages)

def extract_page(raw: bytes, page_number: int = 1, config: OCRConfig | None = None,
                 max_pages: int = 10) -> DocumentPage:
    """Render and OCR one selected page. PDFs are rendered at up to 300 DPI.

    Returned boxes are relative to the OCR image dimensions in result, while the
    preview is a downscaled copy. Source documents are never persisted here.
    """
    config = config or OCRConfig(timeout_seconds=45)
    if not isinstance(raw, bytes) or not raw or len(raw) > config.max_bytes:
        raise OCRError('Document is empty or exceeds the 10 MB upload limit.')
    if type(page_number) is not int or not 1 <= page_number <= max_pages:
        raise OCRError(f'Choose a page from 1 to {max_pages}.')
    page_count = 1
    if raw.lstrip().startswith(b'%PDF-'):
        try:
            with _pdf_lock:
                with pdfium.PdfDocument(raw) as document:
                    page_count = len(document)
                    if page_count > max_pages:
                        raise OCRError(f'PDFs may contain at most {max_pages} pages. Split this document first.')
                    if page_number > page_count:
                        raise OCRError(f'This PDF has only {page_count} page(s).')
                    page = document[page_number - 1]
                    try:
                        width, height = page.get_size()
                        if not all(math.isfinite(v) and 0 < v <= 14400 for v in (width, height)):
                            raise OCRError('Unsupported PDF page dimensions.')
                        scale = min(config.pdf_dpi / 72, math.sqrt(config.max_pixels * 0.9 / (width * height)))
                        bitmap = page.render(scale=scale)
                        try:
                            image = bitmap.to_pil().convert('RGB').copy()
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
        except OCRError:
            raise
        except (pdfium.PdfiumError, ValueError, RuntimeError) as exc:
            raise OCRError('Cannot open this PDF. Use an unencrypted, valid PDF.') from exc
    else:
        if page_number != 1:
            raise OCRError('Images have one page. Choose page 1.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as original:
                    if original.format not in {'PNG', 'JPEG'}:
                        raise OCRError('Upload a PNG, JPG/JPEG or PDF document.')
                    if original.width * original.height > config.max_pixels:
                        raise OCRError('Image exceeds the 20 megapixel limit.')
                    if getattr(original, 'n_frames', 1) != 1:
                        raise OCRError('Animated images are not supported.')
                    oriented = ImageOps.exif_transpose(original).convert('RGBA')
                    image = Image.new('RGBA', oriented.size, 'white')
                    image.alpha_composite(oriented)
                    image = image.convert('RGB')
                    # Bring small scans closer to print resolution without exceeding
                    # the memory budget. Never reduce a larger source image.
                    scale = min(2, 2480 / min(image.size), math.sqrt(config.max_pixels * .9 / (image.width * image.height)))
                    if scale > 1.05:
                        resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
                        image.close()
                        image = resized
        except OCRError:
            raise
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise OCRError('Cannot read this image. Upload a valid PNG or JPEG.') from exc
    try:
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        # The decoded page has already passed pixel checks. Rendered PNG bytes
        # can exceed the original upload limit without being an oversized upload.
        from dataclasses import replace
        result = extract_image(buffer.getvalue(), replace(config, max_bytes=max(config.max_bytes, buffer.tell())))
        image.thumbnail((1100, 1500))
        preview = BytesIO()
        image.save(preview, format='PNG')
        return DocumentPage(result, page_number, page_count, preview.getvalue())
    finally:
        image.close()
