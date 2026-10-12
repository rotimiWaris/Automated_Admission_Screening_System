# Reusable image and PDF OCR

Standalone Python package, independent of Django and admission rules. Supports single-frame images decoded by Pillow (including PNG, JPEG and TIFF). Returns text, word confidence, line identifiers and bounding boxes. Does not parse student records or verify authenticity.

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ./packages/result_ocr
```

Install the native Tesseract OCR engine separately, with English language data, and put its executable on PATH. Installation guidance: https://tesseract-ocr.github.io/tessdoc/Installation.html . `pip install` alone does not install the engine. If needed, set `pytesseract.pytesseract.tesseract_cmd` once at process startup to the installed executable; never change this global per request.

```python
from result_ocr import OCRConfig, extract_image

result = extract_image("result.png", OCRConfig(language="eng"))
print(result.text)
print(result.to_dict())
```

CLI:

```powershell
.venv\Scripts\result-ocr result.png --psm 3
.venv\Scripts\python -m unittest discover -s packages/result_ocr/tests -v
```

For another project, install this folder with pip or build a wheel. A Django view should validate the upload, read at most `config.max_bytes + 1` bytes, call `extract_image(bytes, config)`, and handle `OCRError`. Do not pass arbitrary client paths. Use a bounded background job queue for batches; the timeout applies per image. Nothing is saved or sent over a network by this package.

The caller must review extracted fields. Confidence is not a probability, and missing/low-confidence grades must not be guessed. Coordinates use the EXIF-corrected image. Grayscale is optional; automatic thresholding is intentionally not applied to every scan. PSM 3 is the default; test PSM 6 only for a known single text block.

## PDF and upload adapter

`extract_page` accepts PNG/JPEG or PDF bytes and returns OCR output plus a preview of one selected page:

```python
from pathlib import Path
from result_ocr.documents import extract_page

page = extract_page(Path("application.pdf").read_bytes(), page_number=1)
print(page.result.text)
print(page.page_number, page.page_count)
```

The adapter enforces a 10 MB upload limit, at most 10 PDF pages and a 20 megapixel image limit by default. It renders the selected PDF page at up to 300 DPI (configurable with `OCRConfig(pdf_dpi=200)` for another pass) and runs Tesseract with a 45-second timeout. PDFium calls are protected by a lock because the library is not thread-safe. All PDFs, including those with embedded text, currently use the rendered-page OCR path. DOCX, animated images and encrypted PDFs are not supported by the OCR adapter. CSV/XLSX files use the separate `read_table` adapter below.

Word coordinates refer to the OCR image dimensions, not the smaller preview. The package handles documents only; student parsing and admission rules remain in Django's separate `screening/result_parser.py` and `screening/domain.py` modules. No source documents are retained by the package.

Unit tests mock recognition to verify data handling, PDF page selection, limits and failures. Real-engine testing on representative institutional documents is also needed; synthetic layouts do not establish accuracy on all result slips.


For the higher-accuracy English LSTM model, install official `tessdata_best` data and set `TESSDATA_PREFIX` to the containing directory before recognition. The application's `scripts/install_ocr_model.py` downloads a checksum-verified model; `ocr-data/README.md` documents its license and setup. This configuration is also usable in another project. Standard installed language data remains a fallback when no custom directory is configured.

The document adapter enlarges small images (at most 2x) within the pixel budget. It preserves engine-recognised text and confidence; the admission adapter decides whether to retry a page and handles ambiguous grades separately. Confidence is not an accuracy percentage. See [Tesseract quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) and [official accuracy models](https://github.com/tesseract-ocr/tessdata_best).


To process a whole PDF in another project without keeping every rendered page in memory:

```python
from pathlib import Path
from result_ocr.documents import extract_document

for page in extract_document(Path("applications.pdf").read_bytes()):
    print(f"Page {page.page_number} of {page.page_count}")
    print(page.result.text)
```

The iterator raises `OCRError` on a failed page. Keep any earlier results labelled incomplete until iteration finishes. The website uses individual page requests instead so it can show progress between pages.


## What carries over to another project

Installing the current package includes bounded image enlargement, configurable PDF resolution, page-by-page and whole-document extraction, word coordinates, genuine confidence scores and resource limits. Use `extract_page` or `extract_document` for the enhanced document preprocessing; `extract_image` remains the lower-level image recognizer.

The native Tesseract executable and English `tessdata_best` model are external dependencies. Set `TESSERACT_CMD` through your application's configuration (or configure `pytesseract.pytesseract.tesseract_cmd`) and `TESSDATA_PREFIX` as documented above. The model binary is not bundled in the Python package. Copying only this package therefore does not automatically reproduce the screening site's full pipeline.

Automatic retry selection currently lives in `backend/screening/ocr_views.py`, while student/grade parsing and eligibility decisions live in the screening application. Another project can use the package's configuration options for its own retry policy, without importing admission rules.

CSV/Excel import is now available through `result_ocr.tables.read_table`. Files are read as structured rows and cells without OCR. Application-specific column mapping remains in `backend/screening/table_import.py`.


## Reusable CSV and Excel reader

```python
from pathlib import Path
from result_ocr.tables import read_table

for row in read_table(Path("students.xlsx").read_bytes(), "students.xlsx"):
    print(row.sheet, row.number, row.values)
```

CSV must use UTF-8 (with or without BOM); comma, semicolon and tab delimiters are supported. Excel uses `.xlsx`; convert legacy `.xls` files first. The first nonblank row of each worksheet contains unique headers. All worksheets are read, with source sheet and row numbers preserved. Text identifiers retain leading zeros; format registration cells as Text in Excel before entering data.

No native OCR engine is needed for table imports, and no OCR confidence is invented. Formulas are rejected: paste their calculated values before importing. Defaults limit files to 10 MB, 10 worksheets, 80 columns, 1,000 data rows, 2,000 characters per cell, and 30 MB of uncompressed workbook content. Errors raise `OCRError`; oversized data is rejected rather than silently truncated. The screening application applies a smaller 200-row / 100-student limit.

Dependencies include openpyxl and defusedxml. [openpyxl reader documentation](https://openpyxl.readthedocs.io/en/3.1/api/openpyxl.reader.excel.html).
