import unittest
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from result_ocr import OCRConfig, OCRError, extract_image

def picture():
    buffer = BytesIO()
    Image.new('RGB', (200, 80), 'white').save(buffer, format='PNG')
    return buffer.getvalue()

def engine_data():
    return {'text': ['', 'English', 'C6', 'JAMB', '240'], 'conf': [-1, 95, 62, 96, 98], 'left': [0, 5, 100, 5, 100], 'top': [0, 5, 5, 40, 40], 'width': [0, 80, 20, 70, 30], 'height': [0, 20, 20, 20, 20], 'block_num': [0, 1, 1, 1, 1], 'par_num': [0, 1, 1, 1, 1], 'line_num': [0, 1, 1, 2, 2], 'page_num': [1]*5}

class OCRTests(unittest.TestCase):
    @patch('result_ocr.service.pytesseract.image_to_data', return_value=engine_data())
    def test_lines_boxes_and_review_warning(self, mock):
        result = extract_image(picture())
        self.assertEqual(result.text, 'English C6\nJAMB 240')
        self.assertEqual(result.words[1].left, 100)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(mock.call_args.kwargs['timeout'], 30)

    def test_invalid_bytes(self):
        with self.assertRaises(OCRError):
            extract_image(b'not an image')

    def test_size_limits(self):
        for config in [OCRConfig(max_bytes=2), OCRConfig(max_pixels=1)]:
            with self.subTest(config=config), self.assertRaises(OCRError):
                extract_image(picture(), config)

    @patch('result_ocr.service.pytesseract.image_to_data', side_effect=RuntimeError('timeout'))
    def test_timeout(self, mock):
        with self.assertRaisesRegex(OCRError, 'timed out'):
            extract_image(picture())

    @patch('result_ocr.service.pytesseract.image_to_data', return_value={'text': []})
    def test_empty_ocr_requires_review(self, mock):
        result = extract_image(picture())
        self.assertEqual(result.text, '')
        self.assertIn('No text', result.warnings[0])

    def test_multi_frame_is_not_silently_truncated(self):
        buffer = BytesIO()
        first = Image.new('RGB', (20, 20), 'white')
        first.save(buffer, format='TIFF', save_all=True, append_images=[first])
        with self.assertRaisesRegex(OCRError, 'multi-frame'):
            extract_image(buffer.getvalue())

if __name__ == '__main__':
    unittest.main()
