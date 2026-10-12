# Set up on another Windows PC

These instructions run the application on that PC only. They are a local officer evaluation setup, not an internet or shared-office server deployment.

## 1. Copy the source

Copy backend/, frontend/ (including public/ and package-lock.json), packages/, scripts/, compendium.txt and the documentation. Keep frontend/public/templates/: the interface links to these workbooks. Samples and artifacts are not required to run the app; some development tests use samples.

Do not copy .venv, node_modules, frontend/dist, .env, artifacts or your working database into a fresh installation. Gitignore does not exclude files from a manually created ZIP; inspect its contents before sharing. There is no Git repository initialized in the current workspace, so no tracked-file audit was possible.

A fresh database has no users or history. It loads the source compendium, not any later rule edits made in your current database. Compare and apply those edits through Admission rules before officer use. If transferring existing records instead, stop Django and make a protected backup of backend/db.sqlite3; transfer it only when those records and accounts are intended for the destination. Never commit it to Git.

## 2. Install prerequisites

Install Python (3.14 was used in this project) and Node.js (24 was used), with command-line access enabled. Install Tesseract OCR with English language data. On Windows, the installer used by this project is available through:

```powershell
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
```

Reopen PowerShell after installing prerequisites. Internet access is needed for dependency/model installation; Google Fonts also need internet, with system-font fallbacks when offline.

## 3. Install and initialize

In PowerShell, change to the copied project folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe scripts/install_ocr_model.py
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py load_compendium
.\.venv\Scripts\python.exe backend/manage.py createsuperuser
cd frontend
npm.cmd ci
cd ..
```

Choose a unique administrator username and password. The OCR model is intentionally ignored by Git; the install script restores the tested model. For a nonstandard Tesseract installation, set its executable path in the terminal that will run Django:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

The application reads environment variables; it does not automatically load a .env file.

## 4. Start the application

Terminal 1, from the project folder:

```powershell
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173 and sign in. Keep both terminals running. Use that same hostname consistently. Stop each process with Ctrl+C when finished. Repeat only the start commands on later visits.

## 5. Prepare officer accounts and verify

At http://127.0.0.1:5173/admin/ create individual active user accounts. Ordinary users can screen and see their own history. Grant staff access only to officers who should edit admission requirements; reserve superuser access for administrators.

Review all 28 programme rules and the UTME cutoff before use. Try an authorized register, confirm the selected admission type, inspect decisions/comments and the downloaded workbook, and verify history. Test an image/PDF to confirm Tesseract is available. ND age is checked against September 30 of the processing year; HND has no age check. Keep the PC clock correct.

For a shared office server, arrange a production deployment separately: the bundled Django/Vite development servers are not a production hosting configuration. Sharing a folder with another PC does not share databases or history.
