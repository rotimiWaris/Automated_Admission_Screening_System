# Admission document and OCR research

Research date: 19 September 2026. Historical sources establish document types, not current admission thresholds.

## What is the document called?

The closest individual document is an **admission screening application form**, **Post-UTME application printout**, or **UTME/DE screening assessment form**. Names and layouts vary by institution. It may combine candidate details, UTME score and subject combination, and O-level subjects/grades for one or two sittings. A screening clearance checklist is a different document: it lists credentials checked but may not contain scores or grades.

For multiple candidates, the relevant source is an institution's candidate data downloaded from JAMB CAPS or its admission system. I did not verify a public official combined O-level + UTME bulk export template, extension, or column schema. Do not describe a custom XLSX/CSV format as an official JAMB format.

## Sources and retrieval status

1. JAMB CAPS overview: https://www.jamb.gov.ng/caps . Describes admission officers' roles and processing candidates in batches. Public page read successfully.
2. JAMB 2021 admission guidelines: https://caps.jamb.gov.ng/2021%20Admission%20Guidelinesv1.pdf . Section 5 says officers download candidates' O-level details from CAPS before initiating admission processing. Browser research retrieved the indexed PDF text; direct local download returned HTTP 404. This is historical guidance, not a verified current policy statement.
3. JAMB 2024 policy presentation: https://www.jamb.gov.ng/PDFs/2024/POLICY_2024_Final_18_July_2024.pdf . Indexed slide 115 describes institutions downloading available candidates' O-level results per programme. Browser opening exceeded the tool's document size limit. No local copy retrieved.
4. EKSU 2024 screening instructions: https://eksu.edu.ng/wp-content/uploads/2024/07/corrected-Advert-_Post-UTME-2024-1.pdf . Describes entering JAMB registration details, uploading O-level results from up to two sittings, then printing the completed screening form. Indexed content available; direct download encountered a browser challenge.
5. UNIMAID screening checklist, indexed as 2024/2025: https://admission.unimaid.edu.ng/Admi/e_letter/SCREENING%20FORM.pdf . Search index shows a blank clearance checklist including JAMB result/cutoff/subject combination and O-level certificate. Opening the URL now returned an HTML alumni page, so the original PDF is not verified retrievable. It is not a combined result table.
6. NDU candidate screening application example: https://www.nursinghero.com/study-files/21321405 . Third-party indexed preview shows the relevant structure: JAMB score and subjects, plus a first-sitting O-level subject/grade table. This is not an official university-hosted template; the preview contains a person's data, so it was not copied into the repository. Full direct fetch failed; the preview advertises premium access. Treat as a layout example only.
7. Bingham's official instructions: https://binghamuni.edu.ng/v2/announcements/undergraduate-admission-for-2024-2025-academic-session . Confirms use of a UTME/DE Screening Assessment Form. A blank third-party preview is at https://www.scribd.com/document/939025087/Utme-de-Assessment-Form . Not downloaded and not independently authenticated as the university's current template.
8. Public blank UTME registration template: https://myschool.ng/download/blog_files/NjEQFEvjPSgjq2DiMMYGox2CZhvtIzNoRuFt8vMx.pdf . Successfully downloaded to `samples/utme-registration-template.pdf` (1,060,540 bytes, PDF header verified). Third-party hosted. Indexed page says 2026 while the embedded document title mentions 2024. Includes O-level subject/grade/exam/sitting fields and intended UTME subjects; **does not contain a completed UTME score**. Useful as a layout reference, not the combined admission results file sought. Retain source attribution; public access does not establish redistribution rights.

## Recommended input coverage

| Input | Processing |
| --- | --- |
| Manual result entry | Validate structured fields directly |
| JPEG/PNG or scanned result slips | OCR, then human review |
| Combined screening form in PDF | Extract embedded text; render scanned pages and OCR when necessary |
| Separate JAMB and WAEC/NECO slips | Extract independently and associate after identity review |
| XLSX/CSV containing many candidates | Parse cells with explicit column mapping, never OCR |
| DOCX | Read paragraphs/tables; OCR embedded scan images only if supported |

Keep original extraction separate from confirmed fields. Record examining body, exam type (school/private, including GCE), year, examination number and sitting; GCE alone does not identify the examining body. Never silently select the best of two sittings without the programme's combination policy. Flag awaiting, withheld, cancelled, and unreadable results for review. OCR identifies text, not authenticity.

## Tesseract.js versus pytesseract

Both use the Tesseract recognition engine. Accuracy should be compared with matching engine versions, language data, input images and settings; a Python wrapper is not inherently more accurate.

| Factor | Tesseract.js in browser | Python pytesseract on server |
| --- | --- | --- |
| Django integration | Separate client extraction, followed by API submission | Direct reusable Python service |
| Resources | Uses administrator's device | Central server CPU/memory; bound concurrency |
| Privacy | Can keep source images local if app code does not upload them | Uploads reach your controlled backend |
| Setup | WebAssembly worker and model assets | Native engine and language packs plus Python package |
| Batch jobs | Browser worker lifecycle needs management | Fits background Python job workers |
| PDF | Needs rendering or a separate library | Also needs text extraction/rendering outside pytesseract |
| Future reuse | Best for other JavaScript clients | Installable package usable from Django, scripts or another Python API |

Recommendation: **pytesseract for this project**, primarily because of Django, server-controlled processing, and future reuse. Tesseract.js remains a good choice when keeping scans entirely on the user's device is a central requirement. No speed or accuracy benchmark on actual admission slips has been performed.

Primary technical references:
- https://github.com/madmaze/pytesseract — native engine dependency, confidence/box output, timeouts.
- https://github.com/naptha/tesseract.js — browser/Node support and project scope.
- https://github.com/naptha/tesseract.js/blob/master/docs/faq.md — shared engine and PDF limitations.
- https://pypdf.readthedocs.io/en/stable/user/extract-text.html — native PDF text extraction versus OCR.

## Reuse boundary implemented

`packages/result_ocr` is a standalone installable image OCR package with a CLI, structured results, image limits and a timeout. It has no dependency on Django, React, JAMB subject names or admission rules. Document adapters, student-result parsing, and admission evaluation remain separate layers. A Django/React manual-entry prototype has since been added; see the root README. PDF/DOCX/spreadsheet adapters and OCR integration are still future work.
