import unittest
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from result_ocr import OCRError, OCRConfig
from result_ocr.documents import extract_page, extract_document

def image_bytes(kind='PNG', pages=1):
    buffer = BytesIO()
    image = Image.new('RGB', (100, 100), 'white')
    if kind == 'PDF':
        image.save(buffer, format='PDF', save_all=True, append_images=[image] * (pages - 1))
    else:
        image.save(buffer, format=kind)
    return buffer.getvalue()

class DocumentTests(unittest.TestCase):
    @patch('result_ocr.documents.extract_image')
    def test_whole_document_yields_all_pages_in_order(self, extract):
        pages = list(extract_document(image_bytes('PDF', 3)))
        self.assertEqual([p.page_number for p in pages], [1, 2, 3])
        self.assertTrue(all(p.page_count == 3 for p in pages))
        self.assertEqual(extract.call_count, 3)

    @patch('result_ocr.documents.extract_image', side_effect=[None, OCRError('page failed')])
    def test_whole_document_does_not_hide_later_page_failure(self, extract):
        pages = extract_document(image_bytes('PDF', 2))
        self.assertEqual(next(pages).page_number, 1)
        with self.assertRaisesRegex(OCRError, 'page failed'):
            next(pages)

    @patch('result_ocr.documents.extract_image')
    def test_pdf_page_selection(self, extract):
        page = extract_page(image_bytes('PDF', 2), 2)
        self.assertEqual((page.page_number, page.page_count), (2, 2))
        self.assertTrue(page.preview_png.startswith(b'\x89PNG'))
        extract.assert_called_once()

    def test_invalid_encrypted_or_truncated_input(self):
        for raw in [b'%PDF-1.7 broken', b'not an image', image_bytes('GIF')]:
            with self.subTest(raw=raw[:15]), self.assertRaises(OCRError):
                extract_page(raw)

    def test_page_and_resource_limits(self):
        cases = [(image_bytes('PDF', 2), 3, OCRConfig()), (image_bytes('PDF', 11), 1, OCRConfig()),
                 (image_bytes(), 2, OCRConfig()), (image_bytes(), 1, OCRConfig(max_pixels=50)),
                 (image_bytes(), 1, OCRConfig(max_bytes=2))]
        for raw, page, config in cases:
            with self.subTest(page=page, config=config), self.assertRaises(OCRError):
                extract_page(raw, page, config)
