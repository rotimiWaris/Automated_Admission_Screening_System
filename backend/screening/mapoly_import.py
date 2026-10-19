"""One-row-per-applicant MAPOLY register adapter; no OCR or grade guessing."""
import re
from result_ocr import OCRError
from .applicant_data import HEADERS, applicant_metadata
from .jamb_subjects import parse_subjects
from .result_parser import sitting, subject_rows
from .domain import EXAM_COMBINATIONS, PENDING_GRADES


def normal(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def import_register(rows, filename, require_utme=True, smart_processing=False):
    if len(rows) > 10000:
        raise OCRError('Import at most 10000 students at a time.')
    expected = {normal(h): h for h in HEADERS}
    drafts = []
    for row in rows:
        from .register_schema import prepare_register_row
        mapped = prepare_register_row(row, HEADERS, 'ND Full-Time', len(drafts)+1)
        issues = []
        optional_warnings = []
        processing_warnings = []
        name = ' '.join(mapped[h].strip() for h in ['Surname', 'First Name', 'other name'] if mapped[h].strip()) or mapped['Name on Jamb']
        draft = {'student_name': name, 'registration_number': mapped['Jamb reg'], 'course': mapped['jamb programme'],
                 'jamb_score': None, 'jamb_subjects': [], 'sittings': [], 'confidence': None,
                 'review_issues': issues, 'optional_warnings': optional_warnings, 'processing_warnings': processing_warnings, 'smart_processing': smart_processing, 'source_rows': [f'{row.sheet}, row {row.number}'],
                 'source_format': filename.rsplit('.', 1)[-1].lower(), 'source_record': mapped,
                 'applicant': applicant_metadata(mapped), 'original_remark': mapped['remark']}
        if not all([name, draft['registration_number'], draft['course']]):
            issues.append('Student name, JAMB registration or programme is missing.')
        if mapped.get('jamb olevel status','').strip().casefold() in ['false','no','0','not uploaded','pending']:
            issues.append('JAMB Olevel status requires review: '+mapped['jamb olevel status'])
        if require_utme:
            score = mapped['jamb score'].strip()
            if score.isdigit() and 0 <= int(score) <= 400:
                draft['jamb_score'] = int(score)
            else:
                issues.append('JAMB score is missing or invalid.')
            try:
                draft['jamb_subjects'] = parse_subjects(mapped['jamb subject'])
            except ValueError as exc:
                issues.append(str(exc))
        for column in ['olevel result sitting 1', 'olevel result sitting 2']:
            content = mapped[column].strip()
            if not content or content.lower() in ['none', 'n/a', 'not submitted', '-']:
                continue
            lines = [s.strip() for s in re.split(r'[;|\n\r]+', content) if s.strip()]
            exam = sitting('\n'.join(lines))
            from .identities import candidate_name_issues
            issues.extend(candidate_name_issues(name, content, column, mapped.get('Name on Jamb', ''), smart_processing, processing_warnings))
            for line in lines:
                if re.match(r'^(?:Exam (?:Name|Type|Year|No|Cent(?:er|re))|Candidate Name)\s*:', line, re.I) or re.fullmatch(r'-\s*\[\s*\](?:\s*\[\?\])?', line):
                    continue
                if re.search(r'\b(?:WAEC|NECO|NABTEB|WASC|19\d{2}|20\d{2})\b', line, re.I):
                    continue
                if not subject_rows(line):
                    optional_warnings.append(f'{column}: unrecognised entry "{line}". Not counted toward requirements.')
            if (exam['board'], exam['exam_type']) not in EXAM_COMBINATIONS or not exam['year']:
                issues.append(f'{column}: specify examination board, School/Private/GCE and year.')
            if not exam['subjects'] or any(s['grade'] == 'Unreadable' for s in exam['subjects']):
                pending = ', '.join(f'{s["subject"]}: {s["grade"]}' for s in exam['subjects'] if s['grade'] in PENDING_GRADES)
                issues.append(f'{column}: grades need review' + (f' ({pending}).' if pending else '.'))
            parsed_rows = [r for line in lines for r in subject_rows(line)]
            if len(parsed_rows) > 9 or len({r['subject'] for r in parsed_rows}) != len(parsed_rows):
                issues.append(f'{column}: duplicate subjects or more than nine subjects.')
            draft['sittings'].append(exam)
        if str(len(draft['sittings'])) != mapped['sitting(s)'].strip() or not draft['sittings']:
            issues.append('Sitting count does not match the results supplied.')
        drafts.append(draft)
    return drafts
