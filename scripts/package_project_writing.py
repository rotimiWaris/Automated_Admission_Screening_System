"""Build a source-only archive for reviewing and documenting the implementation."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
files = set()
for folder, extensions in [
    ('backend', {'.py', '.txt'}),
    ('frontend/src', {'.js', '.jsx', '.css'}),
    ('packages/result_ocr', {'.py', '.toml', '.md'}),
]:
    for path in (ROOT / folder).rglob('*'):
        if path.is_file() and path.suffix in extensions and not any(
            part == '__pycache__' or part.endswith('.egg-info') for part in path.parts
        ):
            files.add(path.relative_to(ROOT))
for name in [
    'README.md', 'compendium.txt', 'frontend/package.json',
    'frontend/package-lock.json', 'frontend/index.html', 'frontend/vite.config.js',
    'frontend/public/mapoly-logo.png', 'frontend/public/ASSETS.md',
    'scripts/generate_mapoly_register.py', 'scripts/generate_sample_forms.py',
    'scripts/install_ocr_model.py', 'scripts/package_project_writing.py',
    'research/nd-full-time-compendium.md', 'research/nd-clarification-online-check.md',
]:
    path = ROOT / name
    if path.is_file():
        files.add(Path(name))

guide = '''# Project writing: implementation guide

Automated Student Result Screening System for Admission Requirements

This archive contains the current implementation, configuration, migrations,
tests and relevant rule-source notes. Start here, then inspect the source files
before describing a feature or evaluation result.

## Code map
- backend/screening/models.py: rules, stored screening snapshots and uniqueness.
- backend/screening/domain.py and criteria.py: grades, credits, sittings,
  UTME score/subject combinations and qualification decisions.
- backend/screening/compendium.py and compendium.txt: 28 ND Full-Time programmes.
- backend/screening/ocr_views.py and result_parser.py: OCR integration and
  extraction of applicant fields, with uncertain inputs held for review.
- packages/result_ocr/src/result_ocr/: reusable Tesseract image/PDF OCR and
  direct CSV/XLSX reading. Native Tesseract is an external prerequisite.
- backend/screening/mapoly_import.py and applicant_data.py: 21-column register,
  date-of-birth age calculation, packed O'level results and prior remarks.
- backend/screening/batch_views.py and screening_export.py: batch evaluation,
  history deduplication and a 21-column Excel report with marks and comments.
- backend/screening/views.py: authentication, rules, manual screening and
  private history with pagination and status-tag searches.
- frontend/src/: responsive React interface, OCR upload, batch review,
  form-based rule editing, history and result dialogs.
- Tests alongside the backend/frontend code and in packages/result_ocr/tests/.

## Scope to describe accurately
The four admission routes are selectable; the supplied compendium configures
ND Full-Time only. Other routes require their own configured requirements.
Source notes distinguish supplied compendium wording, online cutoff references
and project-owner clarifications. Do not infer institutional approval or real
student testing from source code alone. Sample generators create fictional data.
OCR confidence is not a measured accuracy percentage and handwriting is not
guaranteed. JAMB upload status is imported data, not live JAMB verification.
Repeated applicants are evaluated for the report without saving duplicate
history. Final Excel remarks are Qualified/Unqualified; incomplete decisions
leave the cell blank and explain the issue in its comment.

## What is excluded
Student databases, history/backups, uploaded documents, generated sample/report
files, virtual environments, node_modules, builds, OCR model binaries, environment
secrets and browser artifacts. Native Tesseract must be installed separately.
No measured research metrics or user-study findings are invented in this archive.

## Reproduction
Use the repository README for installation, running and testing commands.
Run Python dependency installation from the archive root, because the backend
requirements refer to the local packages/result_ocr folder.
Generate fixtures before tests that load sample files:
  python scripts/generate_mapoly_register.py
  python scripts/generate_mapoly_register.py --twenty
Other OCR fixture tests may need scripts/generate_sample_forms.py and its
document-generation prerequisites. Model downloads and native engine setup
are described in packages/result_ocr/README.md.

This archive is a code reference; it does not contain the live database or
constitute evidence that every described scenario has been deployed in practice.
'''

destination = ROOT / 'artifacts/MAPOLY-project-writing-source.zip'
destination.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
    archive.writestr('START_HERE.md', guide)
    for path in sorted(files):
        archive.write(ROOT / path, path.as_posix())
    archive.writestr('SOURCE_MANIFEST.txt', '\n'.join(path.as_posix() for path in sorted(files)))
with ZipFile(destination) as archive:
    assert archive.testzip() is None
    assert not any(name.endswith(('.sqlite3', '.env', '.pyc')) or 'node_modules/' in name for name in archive.namelist())
print(f'{destination}\n{len(files)} source/reference files; {destination.stat().st_size:,} bytes; ZIP integrity checked.')
