# Automated Student Result Screening System for Admission Requirements

An admission screening application for Moshood Abiola Polytechnic (MAPOLY), built with Django, React, SQLite and reusable Tesseract OCR. The supplied shared-admission compendium is implemented for 28 programmes across all sessions, with an editable UTME default of 100 sourced from MAPOLY's 2025/2026 notice. See [compendium notes](research/nd-full-time-compendium.md) for source details and unresolved wording.

## Included

- Student details, programme and academic session selection.
- O-level subject/grade entry for one or two sittings, with explicit WAEC WASSCE/SSCE, WAEC GCE, WASC, NECO Internal/External and NABTEB NBC/NTC options and examination year.
- JAMB threshold and four-subject combination checks, permitted O-level credit selections, additional passes, alternative eligibility paths and sitting-policy evaluation.
- Eligible, Not Eligible or Pending Review outcomes with detailed feedback.
- Staff rule editor: edit admission thresholds, subject selections, pass requirements and clarification notes.
- Optional saved history, private to each user, containing submitted results and the exact rule snapshot used.
- Authentication, CSRF protection, Django administration and protected screening APIs.
- PNG/JPEG and whole-PDF OCR, document previews, confidence feedback and automatic batch screening with review for uncertain records.

## OCR setup and workflow

Run dependency installation from the repository root (the requirements file includes the local reusable OCR package):

```powershell
.venv\Scripts\python -m pip install -r backend/requirements.txt
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
```

Approve the Windows installation prompt when shown. Tesseract needs the English language data installed. Restart Django after installation. The app looks for Tesseract on PATH or in the usual Windows installation directory. For a custom installation, set the executable path before starting Django:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Install the higher-accuracy English model and restart Django (already installed in this workspace):

```powershell
.venv\Scripts\python scripts/install_ocr_model.py
```

1. Choose a PNG/JPEG or PDF under **Import a result document**. Leave **Extract every page automatically** and **Automatically screen students when extraction finishes** enabled, then click **Extract text**.
2. The application reads every PDF page in order and reports progress. This is one user action, implemented as bounded page requests to avoid a single long-running HTTP request. Limits remain 10 MB, 10 PDF pages, and 20 megapixels per source image.
3. All extracted students are automatically screened against exact matching programme names. If a course has no exact match (including legacy generic example course names), choose its rule set once under **Programme matching**, then click **Screen all students**. No student-result retyping is required. Different sessions with the same programme require explicit selection.
4. Read the Eligible, Not Eligible and Pending Review counts and each student's requirement checks. Uncertain text, unknown layouts, missing fields and duplicate registration numbers remain pending. No match means no eligibility decision is invented.
5. Use **Open student for corrections** for an exception, or inspect the document preview and raw text. You can still load O-level-only or JAMB-only drafts into the manual form. Signed-in users may save evaluated batch results to their own history.

Recognition uses the official `tessdata_best` English model, bounded image enlargement and PDF rendering at up to 300 DPI. If a grade is unreadable or the layout cannot be parsed, a second pass uses alternate segmentation for an image or 200 DPI for a PDF. The selected pass's text and genuine confidence are returned; confidence is never artificially increased. Recognised subjects with ambiguous grades are retained as Unreadable instead of silently omitted. An OCR score is not a probability of correctness or proof of document authenticity, and exact transcription cannot be guaranteed for every scan.

The supplied individual forms and register have spatial parsing adapters. Other layouts use conservative labelled-text extraction and require review. Unknown multi-student tables are not merged. PDFs with embedded text currently still use rendered-page OCR. DOCX imports are not implemented. CSV and Excel imports use the structured reader described below.

The reusable package remains separate from admission parsing. Uploaded sources are not stored in the database; Django may use temporary upload files which are cleaned up after the request. Batch screening accepts signed extraction tokens (valid for one hour), validates rule revisions, and keeps page/recognition information with saved results. One OCR operation runs at a time per process; each recognition pass has a 45-second timeout, so an alternate pass can extend a page's processing time. Completed pages remain available if a later page fails, but an incomplete extraction does not trigger automatic screening. Public deployment should use authenticated access, rate controls and a bounded background worker.

Try `samples/synthetic-admissions/individual/SYN-001.pdf`, the two-sitting form `SYN-003.pdf`, or `samples/synthetic-admissions/multiple-students/screening-register.pdf`. Synthetic samples exercise the pipeline; they do not validate all real MAPOLY layouts.

See [SETUP-WINDOWS.md](SETUP-WINDOWS.md) for a fresh-PC installation and handover checklist.

## Run locally on Windows

Requires Python 3.10+ and Node.js 20.19+ or 22.12+. Python 3.14 and Node 24 were used locally. Start from the project root. `npm.cmd` avoids PowerShell execution-policy restrictions; activating the virtual environment is unnecessary.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python backend/manage.py migrate
.venv\Scripts\python backend/manage.py load_compendium
.venv\Scripts\python backend/manage.py createsuperuser
```

Choose your own username and password. No shared/default administrator password is created. The compendium command installs missing programmes and archives demonstration rules. Reruns preserve administrator changes and saved history. The local database has already been migrated and updated; a fresh checkout requires the setup commands above.

Start Django in one terminal:

```powershell
.venv\Scripts\python backend/manage.py runserver 127.0.0.1:8000
```

Start React in another:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. Use the same hostname consistently for session cookies. Vite proxies API and administration requests to Django. Django admin is at **http://127.0.0.1:5173/admin/**.

## Try the workflow

1. Select an ND Full-Time programme, enter the student's O-level grades and four JAMB subjects, review the entries, tick the confirmation checkbox and select **Screen student**.
2. Change JAMB to `99`, confirm again and screen to see a failed score check with the default threshold of 100.
3. Clear the score or select Awaiting to see **Pending Review**.
4. Sign in as your administrator. Open **Admission rules**, edit a threshold and save.
5. Return to **New screening** and screen using the updated requirements.
6. Enable **Save this screening to my history** before submitting. Open **Screening history** to inspect the outcome and its original rules.

All screening requires sign-in. Authenticated users can save and view their own history. Staff can edit rules. Use Django admin to create additional users; grant staff status only to users who should manage requirements.

## Screening semantics

- A1 through C6 count as credits; each distinct subject counts once.
- If combining is allowed, the best known grade per subject across sittings is used. Forbidden sittings are never combined: users must select permitted sittings first.
- Confirmed complete inputs yield Eligible or Not Eligible. Unconfirmed inputs, a missing JAMB score, or any Awaiting/Withheld/Unreadable grade yield Pending Review. Known failures remain visible.
- A missing required subject fails only after the user confirms the entries are complete. Duplicate subjects within a sitting and malformed inputs are validation errors.
- Saved screenings embed the exact rule snapshot and revision. Later edits do not rewrite history. Stale rule edits and screenings are rejected for review.
- These checks evaluate supplied data; they do not authenticate results or connect to JAMB CAPS.

## Validate

```powershell
.venv\Scripts\python backend/manage.py test screening
.venv\Scripts\python backend/manage.py check
cd frontend
npm.cmd test
npm.cmd run build
```

Tests cover screening boundaries, incomplete results, combination policies, input validation, permissions, CSRF, historical snapshots, stale revisions and React interactions.

The initial prototype was verified with 18 backend tests, 3 frontend interaction tests, the production build, live HTTP screening through Vite, and a real Edge browser screening at desktop and mobile widths. Examination-catalogue validation tests were added with the O’level dropdown update.

With both servers running, exercise the real API through Vite using a synthetic record (nothing is saved):

```powershell
.venv\Scripts\python scripts/smoke_http.py http://127.0.0.1:5173
```

On Windows with Microsoft Edge installed, you can also check the real browser workflow and capture screenshots:

```powershell
node scripts/browser_smoke.mjs
```

This uses a separate temporary browser profile and synthetic data. Screenshots are written to the Git-ignored `artifacts/` folder. Both development servers must be running.

## Structure and remaining work

Live recognition is checked against the fictional samples only. The higher-accuracy model resolves the earlier A1/Al confusion and the misspelt sample name; this does not establish perfect accuracy on real institutional documents.

```text
backend/config/          Django settings and routes
backend/screening/       Rule models, evaluation, API, admin and tests
frontend/src/            React screens and interaction tests
packages/result_ocr/     Independent reusable image/PDF OCR package
research/                Document research and public layout sample
```

The subject catalogue is in `backend/screening/domain.py`. Programme requirements are editable through React. Alternative subject groups, UTME subject combinations, approved institutional rules, broader document-layout coverage remain future work. Manual entry remains usable without the native Tesseract engine.

Local settings default to development mode. Deployment requires production settings, HTTPS, a private `DJANGO_SECRET_KEY`, allowed hosts and static-file hosting. Use synthetic records for local review.

## References

- [MAPOLY O’level examination catalogue and source limitations](research/mapoly-olevel-examinations.md)

- [Research findings and source links](research/admission-documents.md)
- [Downloaded blank UTME registration template](research/samples/utme-registration-template.pdf) — layout reference only; does not contain UTME scores.
- [Reusable OCR package, setup and usage](packages/result_ocr/README.md)

- [Django CSRF guidance](https://docs.djangoproject.com/en/5.2/howto/csrf/)
- [Vite development proxy](https://vite.dev/config/server-options#server-proxy)


## OCR verification and interface checks

The updated recognition pipeline was checked against all 20 individual sample PNGs and all five register PDF pages. Names, registration numbers, JAMB scores and subject grades matched the generated records after the two recognition fixes; the opt-in checker also checks course names. This does not mean arbitrary scans will be error-free.

A live CSRF-protected Django upload/batch check extracted all 20 register students and, with explicit mappings to the existing illustrative rules, returned 13 Eligible, 4 Not Eligible and 3 Pending Review. That check did not save history or start application servers.

```powershell
# Native engine check; can take several minutes with the accuracy model.
.venv\Scripts\python scripts/check_sample_ocr.py
# Offline browser layout check after npm.cmd run build (Windows/Edge).
node scripts/browser_layout.mjs
```

The offline layout check uses mocked API data and closes its temporary browser. Desktop and 390px phone layouts were checked without horizontal overflow; screenshots are in `artifacts/desktop-redesign.png` and `artifacts/mobile-redesign.png`. Body text is 16px, input text 15px and form labels 14px. Logo provenance is documented in `frontend/public/ASSETS.md`.


## Responsive navigation

On desktop and tablet widths above 768px, use **Collapse sidebar** to switch to an icon rail. The browser remembers the setting locally. Collapsed navigation has keyboard-accessible labels and hover/focus tooltips; the main content expands to use the remaining space. Student entries remain intact when navigating between workspace sections.

At 768px and below, navigation becomes a fixed bottom bar with Screening, Admission rules and History. The top header contains the MAPOLY crest and account action. Content padding and safe-area insets keep the bar clear of the final form controls and footer. The layout check covers 1440px desktop (expanded and collapsed), 1024/820px tablet, and 768/390/320px mobile widths, using mocked API data without starting development servers. Screenshots are written under `artifacts/`.


Saved history now uses `/api/history/?page=1&q=...` with 50 records per page and no total-record cap. The API returns `history`, `count`, `page`, `page_size` and `num_pages`. Search applies to the signed-in user's complete history before pagination. Records are ordered newest first, with ID as a tie-breaker. Click a row to open its saved result and rule snapshot in a scrollable modal; Close details or Escape dismisses it and restores focus to the row.


## CSV / Excel imports and duplicate history

Upload CSV or Excel `.xlsx` using **Import a result document**, then choose **Import records**. Download a template from that section; replace the fictional example before submitting your own data. Matching programme rules are used by automatic batch screening, as with PDF imports. CSV/Excel imports do not require Tesseract.

Required columns: `student_name`, `registration_number`, `course`, `jamb_score`, `sitting`, `board`, `exam_type`, `year`, plus subject-name columns such as `English Language` and `Mathematics`. Use `School`, `Private/GCE` or `WASC` for exam type, and the appropriate WAEC/NECO/NABTEB board. Blank grades mean the subject was not supplied. Invalid grades or missing details are held for review.

Use one row per student per sitting (`1` or `2`). Repeat matching student details when supplying a second sitting. Distinct sittings are combined into one draft; repeated rows for the same student/sitting are rejected as duplicates. All Excel worksheets should follow this layout. Limits are 1,000 students / 2,000 rows per file. Use UTF-8 CSV, convert old `.xls` files to `.xlsx`, and paste formula results as values.

Sample files: `samples/synthetic-admissions/tabular/screening-register.csv` and `.xlsx` (20 fictional students). The portable reader is `packages/result_ocr/src/result_ocr/tables.py`; admission-specific mapping is separate.

History permits one saved record per user and normalized JAMB registration number. Normalization ignores case, spaces and punctuation. Names are not used as unique identifiers. Other users' histories remain private and independent. Repeated manual saves return a clear conflict; batch processing labels repeated students **Duplicate** and skips saving them. Uncertain records already saved also count as existing history. Unsaved manual re-screening remains possible.

Migration `0002_unique_student_history` keeps the newest record per student and adds a database uniqueness constraint. Back up existing databases before applying it. During this workspace update, 20 older duplicates were removed, leaving 20 records; a complete pre-cleanup SQLite backup is in `artifacts/backups/history-before-dedup-20260920-191940.sqlite3`.

## ND Full-Time compendium

All 28 supplied programmes are available under ND Full-Time / All sessions. Expand **Full subject requirements** on a rule card for credit selection paths, additional passes and UTME combinations; expand **Compendium source** to compare the original wording. Staff can edit subject requirements with dropdowns, required counts, alternative choices, additional accepted paths and plain-text notes. The editor checks totals before saving; server validation and revision checks remain in place. Original source text is preserved.

The project owner has resolved the four UTME clarification blocks. Mass Communication and Library Science use the supplied category mapping restricted to JAMB-offered subjects. SLT requires English, Mathematics, Physics and Biology or Agricultural Science. Urban Planning requires English, Geography and two supplied electives; Mathematics remains compulsory at O-level. These amendments are project-owner configuration, not independently verified new MAPOLY publications. Missing or unconfirmed student inputs still yield Pending Review. See [clarification notes](research/nd-clarification-online-check.md).

Structured imports may include the optional `jamb_subjects` column, containing four names separated by semicolons. A single-student OCR document may provide a labelled `JAMB subjects:` line. Missing combinations require review.

## MAPOLY register and Excel reports

The [21-column sample workbook](samples/synthetic-admissions/tabular/mapoly-student-register-sample.xlsx) contains 12 **fictional** ND Full-Time applicants. It uses the supplied column list, including `Form No.`, both packed O’level sittings, DOB, age and remark. Regenerate it with `.venv\Scripts\python scripts/generate_mapoly_register.py`. No real student records are included.

Use one student per row. In each O’level sitting cell, use `WAEC School 2025; English Language: C6; Mathematics: B3; ...`; separate entries with semicolons or line breaks. Specify the board, exam type and year. Separate the four JAMB subjects with semicolons. Leave the second sitting blank when unused. Keep registration numbers and phone numbers as text. DOB accepts Excel dates, `YYYY-MM-DD` or `DD/MM/YYYY`; missing ages are calculated in completed years on the processing date. Supplied ages are preserved and discrepancies flagged. This adapter supports this documented cell format; other real-world packed cell formats may need mapping after inspecting an actual example.

Choose the admission type before importing. ND Full-Time uses its 21-column register and complete compendium rules. ND Part-Time uses the 15-column register; both HND routes use the 19-column register. Under the project-owner configuration, these routes use the matched programme Olevel baseline without UTME score/subject checks. The source compendium remains ND Full-Time; this reuse is not a separate official HND/PT compendium. Use a route-specific active rule when one has been configured. Templates are available from the import panel.

Automatic screening downloads one Excel report preserving the route's 21, 15 or 19 columns. The remark is replaced with Qualified or Unqualified, or left blank when review is needed. Comments explain review/failure reasons; a previous-remark entry is added only when a previous value exists. Only a qualifying student's actual selected Olevel subjects are ticked, using one valid credit path and necessary additional passes; unused subjects remain unmarked. When combining sittings, only the chosen occurrence is ticked. JAMB subjects are ticked only for completed ND Full-Time qualification. Existing marks are replaced, not treated as evidence.


SQLite uses immediate write transactions and a 20-second busy timeout to avoid competing read-to-write upgrades during saves. A persistent database lock returns a retryable 503 response instead of an internal-server-error page; a failed batch transaction is rolled back. Restart Django after changing database settings. Do not re-import an annotated report as raw results: its score and grade cells contain assessment marks.

Signed-in users save evaluated students to history by default. Repeated students are reassessed against current inputs and rules for the Excel report, but are not saved again. Storage duplication is not written into the workbook. Records without an applicable rule or sufficient valid input to evaluate require review. History remains one record per user and normalized JAMB registration number. Uploading the same applicant again will not replace an earlier saved assessment.

Spreadsheets are read directly without OCR. For single-student images/PDFs, labelled DOB, age and remarks can be extracted. Tesseract cannot reliably read every handwritten annotation; an unreadable/uncertain remark must be reviewed. Original images are not edited—the ticks and decisions are in the exported workbook. Admission-specific parsing, age calculation and reporting live in Django; the generic reusable `result_ocr` package remains independent of MAPOLY rules.


### Specimen result-cell formats

The MAPOLY register adapter accepts labelled Exam Name/Type/Year/No/Center and
Candidate Name metadata, plus entries such as `GENERAL MATHEMATICS - [B3] [?]`.
Bracketed grades and trailing assessment marks are parsed independently;
previous marks never override grades. Metadata and original grade text remain
in the exported sitting cells. Empty `- []` placeholders are ignored.
JAMB subject lines may include bracketed numbers; these are preserved as source
text but are not summed or substituted for the explicit JAMB Score column.
Subject abbreviations are normalized for matching.

Outstanding, AR/Awaiting, Cancelled and ABS/Absent remain unresolved states.
Non-standard codes such as A2, A3, P7 and P8 are held for review rather than
silently converted. The original codes remain in the source cells. Unlisted
subjects do not automatically become accepted programme alternatives.
NABTEB November/December is mapped to Private/GCE using the official entry guide:
https://novdec.nabteb.gov.ng/docs/EntryGuide.pdf
The observed NECO metadata spelling `Intenal` is recognized as Internal.


Unresolved grades are not counted as credits or passes. If confirmed grades
already meet every requirement, an unrelated Outstanding/Awaiting result does
not block qualification; its warning is retained in history and Excel comments.
An unresolved compulsory subject or required credit/pass combination still
requires review. Unreadable codes and uncertain extraction remain review issues.


### Part-time and HND academic workflow

For ND Part-Time, Department is the intended programme. For HND, ND Course Of
Study is the intended programme by project-owner instruction; First Choice is
only the preferred institution. ND grade and CGPA are checked on a four-point
scale: 2.50 or above meets the baseline; 2.00-2.49 requires consideration; below
2.00 fails. Missing/invalid values or classification conflicts require review.
IT/work experience and accreditation checks are explicitly excluded. Route
workbooks can be corrected and re-imported; the manual correction form currently
supports ND Full-Time only. Import a workbook matching the selected route.

Candidate Name in each sitting is compared with the surname/first/other-name
combination. Case, name order and punctuation are normalized; missing or different
name tokens require review, and the comment identifies both values and the sitting.
Unrecognised optional subjects are retained but never credited or silently mapped.
If recognized grades satisfy all requirements, they do not block qualification.
Otherwise an unresolved subject interpretation that could affect Olevel checks
requires review. Unknown electives do not turn a definite low CGPA into a pass.


Name-check update: each Olevel Candidate Name passes when it matches either
Name on JAMB (when supplied) or the combined surname/first/other names. Order,
case, punctuation and exact split/joined spellings are ignored. Actual letter
changes remain review issues; a match in one sitting does not clear a different
name in another sitting. No fuzzy spelling corrections are applied automatically.


Generated register columns are optional on upload: Remark, Age (where part of
that route), # and Sitting(s). Remarks come from screening, age from DOB when
available, row numbers from sequence, and sitting counts from supplied result
cells. A missing second-sitting column is accepted as empty; if a supplied
sitting count says two, the missing result still triggers review. Exports restore
the route's full column layout. Missing input fields such as JAMB Score or ND
CGPA are named explicitly in import errors rather than silently invented.


Repeat uploads show fresh Eligible/Not Eligible/Pending Review outcomes and
requirement checks on the dashboard, just like first-time screening. A separate
storage note identifies records already in history; they are neither saved again
nor used to overwrite the historical decision. Dashboard totals count academic
outcomes, not duplicate-save status. Repeated rows within one upload are also
assessed individually while blocked from duplicate storage.


Smart processing is optional and disabled by default in document imports. It accepts a single-letter edit or adjacent transposition in one name part of at least four letters when another name part matches exactly. Original names remain unchanged; the accepted difference appears in screening warnings and the exported Remark note. Missing names and larger differences still require review. Academic requirements are unaffected. Excel notes wrap long explanations and grow with their content, with review reasons before supporting information; display may vary between spreadsheet applications.

Authentication is required for all screening, document import/OCR, catalogue, rules and history APIs. Only session initialization and login are public. Sign in with an existing Django account; administrator accounts can be created with `python backend/manage.py createsuperuser`. Rule changes continue to require staff privileges.
