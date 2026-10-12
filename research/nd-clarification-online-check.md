> Current status: the project owner subsequently supplied and authorized the remaining UTME rules. The earlier unresolved findings below are retained as research history, not current screening blocks. See the amendment at the end of this document.

# ND Full-Time clarification check — 27 September 2026

## Confirmed correction

The project owner explicitly confirmed Electrical/Electronics Engineering permits
not more than two sittings. `compendium.txt`, the loader and the installed rule
were updated. Migration 0004 removes only the obsolete sitting-limit note and
increments the rule revision. Saved screening snapshots are not rewritten.

## Primary sources retrieved

- JAMB IBASS: https://ibass.jamb.gov.ng/
- The ND brochure linked in the site's current public JavaScript asset:
  https://ibass.jamb.gov.ng/static/media/ndcourses.fb51edbfa2fec65d0d7f.pdf
  Local copy: `sources/jamb-nd-brochure.pdf` (216 PDF pages).
  This is the document served by IBASS on the retrieval date; it is not evidence
  that every provision was newly revised for 2026/2027.
- MAPOLY requirements page: https://mapoly.edu.ng/admission-requirements/
- Working version of the linked 2023/2024 ND notice:
  https://mapoly.edu.ng/wordpress/wp-content/uploads/2023/07/2023-2024-ND-FULL-TIME-REQUIREMENTS.pdf
  The page's older `/web/wp-content/` link returns 404. The one-page notice lists
  programmes and general application eligibility, not detailed UTME combinations.

## Findings

| Programme | JAMB PDF page / printed page | Finding and remaining issue |
|---|---|---|
| Mass Communication | 129 / 803; 131 / 805 | Three elective UTME subjects from Arts, Social Science or Physical Science. MAPOLY is listed; its Literature pass note concerns O'level. Category wording agrees with the compendium, but no exhaustive category-to-subject mapping is supplied. |
| Library and Information Science | 125–127 / 799–801 | Same three-category UTME rule. MAPOLY appears on PDF page 126. No MAPOLY-specific UTME exception was found in this entry. The named membership list remains unspecified. |
| Science Laboratory Technology | 161 / 835; 165–166 / 839–840 | The UTME list names Mathematics, Biology/Agricultural Science and Physics with awkward selection wording. English + Mathematics + Physics + either Biology or Agricultural Science is a plausible interpretation, not an independently confirmed explicit MAPOLY list. Chemistry exceptions appear for other institutions, which cannot establish acceptance at MAPOLY. |
| Urban and Regional Planning | 188–193 / 862–867 | Geography and two subjects from the course requirements. The general adjacent list and MAPOLY's O'level exception provide context, but differ from the supplied compendium. The MAPOLY exception also permits four O'level credits in one sitting, unlike the owner's five-credit compendium. Do not apply that conflicting waiver without institutional confirmation. |

The English component comes from the supplied compendium. The brochure's UTME
column lists the three elective subjects.

## System decision

Only the explicit Electrical/Electronics correction was applied to admission
logic. The other four clarification flags remain: the online sources confirm
some wording, but do not conclusively resolve all exact automatic-validation
choices. Do not substitute university degree requirements, another polytechnic's
waiver, or the O'level elective list for a verified UTME combination.

To finish the remaining configuration, obtain confirmation of:

1. The accepted named UTME subject lists for the Arts/Social Science/Physical
   Science categories in Mass Communication and Library and Information Science.
2. Whether SLT requires Mathematics + Physics + Biology/Agricultural Science,
   and whether Chemistry is an accepted alternative.
3. The exact two-subject UTME choice pool for Urban and Regional Planning,
   following compulsory English and Geography.


## Project-owner amendment

The four remaining clarification blocks have been removed following explicit instructions:

- Mass Communication and Library Science: English plus three subjects from the supplied categories, restricted to JAMB-offered subjects. Biology, Agricultural Science and Computer Studies are included by the owner's category policy. Further Mathematics, Technical Drawing, Marketing and Book Keeping are excluded from this UTME category pool; they remain available for applicable O-level requirements. General Mathematics, ICT, Visual Art and Financial Accounting use the canonical Mathematics, Computer Studies, Fine Arts and Financial Accounting labels.
- SLT: English, Mathematics, Physics and either Biology or Agricultural Science. The source wording was corrected from 'or Physics' to 'and Physics'.
- Urban Planning: English and Geography plus any two options from Physics, Chemistry, Biology/Agricultural Science, Economics, Government, Fine Arts and Technical Drawing. Biology/Agricultural Science is one alternative group, not two elective slots. Mathematics remains compulsory at O-level, not UTME. Technical Drawing is retained here because the owner explicitly included it, despite not being in the researched approved UTME subject list.

Migration 0005 updates only these programme criteria and revisions; history and other requirements stay unchanged. The fresh-install loader uses the same configurations. These are documented project-owner decisions rather than claims of independent institutional verification.
