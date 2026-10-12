> Current status: the project owner subsequently supplied and authorized the remaining UTME rules. The earlier unresolved findings below are retained as research history, not current screening blocks. See the amendment at the end of this document.

# ND Full-Time compendium implementation

Source: project owner's `compendium.txt`, supplied 27 September 2026; 28 programmes across five schools. The owner confirmed the compendium applies to **all sessions** and **ND Full-Time only**. It does not establish ND Part-Time or HND requirements.

## UTME score research

The official MAPOLY notice, dated 7 August 2025, sets a score of **100 and above** for the 2025 UTME. Retrieved directly from MAPOLY's WordPress API and checked 27 September 2026:

https://mapoly.edu.ng/mapoly-begins-processing-of-2025-2026-admission-application-forms/

API used: https://mapoly.edu.ng/wp-json/wp/v2/posts?search=admission&per_page=15

The official 2024/2025 notice also specifies 100:
https://mapoly.edu.ng/mapoly-begins-processing-of-2024-2025-application-forms/

Some third-party pages advertise 2026/2027 using 100, but recycled dates/headings are inconsistent. These were not used as proof of a new official notice. **100 is the editable default, not a verified permanent cutoff or a guarantee of admission.** The source session is retained in each rule. No unsupported departmental scores or age threshold were added.

## Encoding decisions

- Credits mean A1–C6; a pass means E8 or better (D7 and credit grades also satisfy it).
- Five distinct credit subjects must satisfy an accepted programme path. Unrelated extra credits cannot replace a listed elective.
- Slash-separated options are treated as alternatives within one selection. Comma-separated options are distinct choices. One subject cannot fill two slots, including a compulsory subject repeated in an elective list.
- SBMS explicitly permits Economics, Commerce and Accounts/Book Keeping as separate selections. Urban Planning explicitly permits separate Physics, Chemistry, Biology and Economics credits. Those exceptions are encoded.
- Estate Management includes both the general path and its alternative science-student path.
- Science Laboratory Technology requires credits in two core science groups and a pass in all three groups, with Biology/Agricultural Science treated as one group.
- Mass Communication needs a Literature pass; Food and Pharmaceutical Technology need a Physics pass. Additional passes may be satisfied by a subject already counted at credit level.
- Architectural Technology's Technical Drawing/Fine Art advantage is advisory, not a rejection condition.
- Principles of Accounts/Accounting maps to Financial Accounting. Book Keeping remains a separate named alternative. Business Methods/Studies/Management and similar source groups retain their separate alternatives.
- The Business Administration wording `store, management` is transcribed as Store Management (the compound named elsewhere in the compendium). Building Technology's `Technical Drawing.Wood Work` is transcribed as two subjects. These punctuation interpretations should be checked against the original document.
- Unusual but explicit UTME combinations (including Leisure and Tourism, Nutrition and Dietetics, and Statistics and Mathematics) are preserved as supplied rather than replaced with typical combinations from other sources.

## Unresolved source wording

Screenings retain Pending Review, with all known passes/failures visible, for:

1. Science Laboratory Technology: the UTME wording does not clearly enumerate four subjects.
2. Electrical/Electronics Engineering: resolved by the project owner on 27 September 2026 as a maximum of two sittings. The transcription, loader and installed rule were corrected; historical snapshots were preserved.
3. Mass Communication and Library and Information Science: UTME categories are specified without a subject membership list. A staff-confirmed list is needed for automatic validation.
4. Urban and Regional Planning: `two other subjects from course requirement` does not explicitly enumerate UTME options.

Staff can resolve criteria and notes in the advanced rule editor once clarified. The original source text stays available for comparison. Missing UTME subjects also stay Pending Review; they are never inferred from O'level grades.

## Operations

Run `python backend/manage.py migrate`, then `python backend/manage.py load_compendium`. The import is transactional and checks all 28 headings. Rerunning it does not duplicate rules or overwrite staff edits. It archives identifiable demonstration rules and preserves their IDs and historical snapshots. `seed_demo` refuses to run after compendium installation.

Before this workspace's migration, SQLite was backed up to `artifacts/backups/before-nd-compendium-20260927.sqlite3`. Backups contain existing application data and should remain local.

The generic CSV/XLSX importer now optionally accepts `jamb_subjects` (four names separated by commas, semicolons or pipes). Single-student OCR accepts an explicit `JAMB subjects:` or `UTME subjects:` line. Existing files without this information require review against these rules. This change does **not** claim support for the school's 21-column workbook layout; that adapter needs its actual cell formats.


## Project-owner amendment

The four remaining clarification blocks have been removed following explicit instructions:

- Mass Communication and Library Science: English plus three subjects from the supplied categories, restricted to JAMB-offered subjects. Biology, Agricultural Science and Computer Studies are included by the owner's category policy. Further Mathematics, Technical Drawing, Marketing and Book Keeping are excluded from this UTME category pool; they remain available for applicable O-level requirements. General Mathematics, ICT, Visual Art and Financial Accounting use the canonical Mathematics, Computer Studies, Fine Arts and Financial Accounting labels.
- SLT: English, Mathematics, Physics and either Biology or Agricultural Science. The source wording was corrected from 'or Physics' to 'and Physics'.
- Urban Planning: English and Geography plus any two options from Physics, Chemistry, Biology/Agricultural Science, Economics, Government, Fine Arts and Technical Drawing. Biology/Agricultural Science is one alternative group, not two elective slots. Mathematics remains compulsory at O-level, not UTME. Technical Drawing is retained here because the owner explicitly included it, despite not being in the researched approved UTME subject list.

Migration 0005 updates only these programme criteria and revisions; history and other requirements stay unchanged. The fresh-install loader uses the same configurations. These are documented project-owner decisions rather than claims of independent institutional verification.
