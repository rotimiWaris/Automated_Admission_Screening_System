# Recognition model

This application uses the official English `tessdata_best` LSTM model when
`eng.traineddata` is present in this folder. Install it from the repository root:

```powershell
.venv\Scripts\python scripts/install_ocr_model.py
```

The installer verifies the tested model's SHA-256 before replacing it. The native
Tesseract engine remains a separate requirement. An existing `TESSDATA_PREFIX`
environment variable takes precedence over this folder.

Source: https://github.com/tesseract-ocr/tessdata_best

License: Apache 2.0; see LICENSE. Model binaries are excluded from Git.
