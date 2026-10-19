"""Conservative draft extraction. Never evaluates admission or invents grades.

The labelled single-form and register layouts have spatial adapters. Other
layouts use labelled-text extraction and return unresolved fields for review.
"""
import re
from statistics import median
from functools import lru_cache
from .domain import SUBJECTS, GRADES, PENDING_GRADES
from .jamb_subjects import labelled_subjects
from .applicant_data import applicant_metadata

def lines(words):
    if not words:
        return []
    tolerance = max(4, median(w['height'] for w in words) * 0.6)
    groups = []
    for word in sorted(words, key=lambda w: w['top'] + w['height']/2):
        center = word['top'] + word['height']/2
        if not groups or abs(center - groups[-1][0]) > tolerance:
            groups.append((center, [word]))
        else:
            groups[-1][1].append(word)
    return [{'text': ' '.join(w['text'] for w in sorted(group, key=lambda w: w['left'])),
             'top': min(w['top'] for w in group), 'height': max(w['height'] for w in group),
             'words': sorted(group, key=lambda w: w['left'])} for _, group in groups]

def region(words, left, top, right, bottom):
    return [w for w in words if left <= w['left'] + w['width']/2 < right and top <= w['top'] + w['height']/2 < bottom]

def strip_assessment_marks(text):
    return re.sub(r'\s*\[(?:[?\u2713\u00d7]|[?\u2713\u00d7]\s+[A-F][1-9]\+(?:,\s*[?\u2713\u00d7]\s+[A-F][1-9]\+)*)\]\s*$', '', text)


@lru_cache(maxsize=1)
def subject_patterns():
    aliases = {s: [s] for s in SUBJECTS}
    aliases['English Language'] += ['English', 'Use of English']
    aliases['Mathematics'] += ['Maths', 'General Mathematics']
    aliases['Financial Accounting'] += ['Principles of Accounts', 'Accounting']
    aliases['ICT'] += ['Information & Communications Technology']
    aliases['Yoruba'] += ['Yoruba Language']
    aliases['Islamic Religious Studies'] += ['Islamic Studies', 'IRS', 'IRK']
    aliases['Christian Religious Studies'] += ['CRS', 'CRK']
    for canonical, variants in {
        'Food and Nutrition': ['Foods & Nutrition'],
        'Catering Craft Practice': ['Cathering Craft Practice'],
    }.items():
        if canonical in aliases:
            aliases[canonical] += variants
    return {subject: tuple(re.compile(r'^\s*' + re.escape(name) + r'(?:\s*[:|.\-]\s*|\s+)(?:\[([^\[\]]+)\]|(\S+))\s*$', re.I) for name in sorted(names, key=len, reverse=True)) for subject, names in aliases.items()}


def subject_rows(text):
    rows, seen = [], set()
    for line in text.splitlines():
        line = strip_assessment_marks(line)
        for subject, patterns in subject_patterns().items():
            if subject in seen:
                continue
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    token = (match.group(1) or match.group(2)).strip()
                    token = {'AR': 'Awaiting', 'ABS': 'Absent'}.get(token.upper(), token)
                    grade = token.upper() if token.upper() in GRADES else token.title()
                    if grade not in GRADES + PENDING_GRADES:
                        grade = 'Unreadable'
                    rows.append({'subject': subject, 'grade': grade})
                    seen.add(subject)
                    break
    return rows[:9]


def quality(words, known_layout=True):
    scores = [w.get('confidence', 100) for w in words]
    average = round(sum(scores) / len(scores), 1) if scores else 0
    issues = []
    if not known_layout:
        issues.append('This document layout needs review before a final decision.')
    if average < 85 or any(score < 50 for score in scores):
        issues.append('Some extracted text has low recognition confidence. Compare it with the source.')
    return {'confidence': average, 'review_issues': issues}

def sitting(text):
    text = '\n'.join(line for line in text.splitlines() if not re.match(r'^\s*(?:Exam No|Exam Cent(?:er|re)|Candidate Name)\s*:', line, re.I))
    board = next((b for b in ['WAEC', 'NECO', 'NABTEB'] if re.search(r'\b' + b + r'\b', text, re.I)), '')
    # Do not infer a board from the ambiguous word SSCE or GCE alone.
    if re.search(r'\bWASC\b', text, re.I):
        board, exam_type = 'WAEC', 'WASC'
    # NABTEB Nov/Dec entry guide identifies this as the private-candidate series:
    # https://novdec.nabteb.gov.ng/docs/EntryGuide.pdf
    elif board == 'NABTEB' and re.search(r'(?im)^\s*Exam Type\s*:\s*November\s*/\s*December', text):
        exam_type = 'Private/GCE'
    elif re.search(r'PRIVATE|EXTERNAL|\bGCE\b', text, re.I):
        exam_type = 'Private/GCE'
    elif re.search(r'SCHOOL|INTERNAL|\bINTENAL\b', text, re.I):
        exam_type = 'School'
    else:
        exam_type = ''
    explicit_year = re.search(r'(?im)^\s*Exam Year\s*:\s*((?:19|20)\d{2})\s*$', text)
    year = re.search(r'\b(?:19|20)\d{2}\b', text)
    return {'board': board, 'exam_type': exam_type, 'year': int(explicit_year.group(1)) if explicit_year else int(year.group()) if year else '', 'subjects': subject_rows(text)}

def score(text):
    match = re.search(r'\b(\d{1,3})\s*/\s*400\b', text)
    if not match:
        match = re.search(r'(?:JAMB|UTME)(?:\s+(?:TOTAL|SCORE|RESULT))*\s*[:\-]?\s*(\d{1,3})\b', text, re.I)
    return int(match.group(1)) if match and int(match.group(1)) <= 400 else None

def below(words, pattern, left, right):
    grouped = lines(region(words, left, 0, right, float('inf')))
    for i, line in enumerate(grouped):
        if re.search(pattern, line['text'], re.I) and i + 1 < len(grouped):
            following = grouped[i + 1]
            if following['top'] - line['top'] <= line['height'] * 5:
                return following['text']
    return ''

def parse_single(words, width, height):
    name = below(words, r'^FULL NAME$', 0, width/2)
    registration = below(words, r'JAMB REGISTRATION NUMBER', width/2, width)
    course = below(words, r'PROPOSED COURSE OF STUDY', 0, width)
    jamb = score('JAMB SCORE: ' + below(words, r'(JAMB|UTME).*TOTAL SCORE', 0, width/2))
    sittings = []
    for left, right in [(0, width/2), (width/2, width)]:
        grouped = lines(region(words, left, 0, right, height))
        header = next((line for line in grouped if re.fullmatch(r'SITTING\s*[12]', line['text'], re.I)), None)
        if not header:
            continue
        end = next((line['top'] for line in grouped if line['top'] > header['top'] and 'ADMINISTRATIVE REVIEW' in line['text']), height * .79)
        text = '\n'.join(line['text'] for line in grouped if header['top'] < line['top'] < end)
        if not re.search(r'Not submitted', text, re.I):
            sittings.append(sitting(text))
    return {'student_name': name, 'registration_number': registration, 'course': course,
            'jamb_score': jamb, 'sittings': sittings, **quality(region(words, 0, height * .17, width, height * .79))}

def parse_register(words, width, height):
    grouped = lines(words)
    header = next((line for line in grouped if 'APPLICANT' in line['text'].upper() and 'PROPOSED' in line['text'].upper()), None)
    if not header:
        return []
    header_words = header['words']
    def start(token):
        return next((w['left'] - 8 for w in header_words if w['text'].upper() == token), None)
    olevels = [w['left'] - 8 for w in header_words if re.fullmatch(r'O[-’\']?LEVEL', w['text'], re.I)]
    jamb_left = start('UTME')
    if jamb_left is None:
        # A narrow table heading may disappear while the scores remain legible.
        scores = [w['left'] - 8 for w in words if re.fullmatch(r'\d{1,3}/400', w['text'])]
        jamb_left = min(scores) if scores else None
    borders = [start('APPLICANT'), start('PROPOSED'), jamb_left, *olevels, width]
    if len(borders) != 6 or any(b is None for b in borders):
        return []
    first_column = region(words, borders[0], header['top'] + header['height'], borders[1], height)
    anchors = [line for line in lines(first_column) if re.fullmatch(r'SYN[- ]?\d{3}', line['text'], re.I)]
    records = []
    for i, anchor in enumerate(anchors):
        top = anchor['top'] - 5
        bottom = anchors[i+1]['top'] - 5 if i+1 < len(anchors) else height * .9
        cells = ['\n'.join(line['text'] for line in lines(region(words, borders[col], top, borders[col+1], bottom))) for col in range(5)]
        applicant = cells[0].splitlines()
        registration = next((value for value in applicant if re.search(r'DEMO[- ]?UTME|\d{8,12}[A-Z]{2}', value, re.I)), '')
        names = [value for value in applicant if value != registration and not re.fullmatch(r'SYN[- ]?\d{3}', value, re.I)]
        sittings = [sitting(cell) for cell in cells[3:] if not re.search(r'Not submitted', cell, re.I) and cell.strip()]
        records.append({'student_name': ' '.join(names), 'registration_number': registration,
                        'course': cells[1].replace('\n', ' '), 'jamb_score': score(cells[2]), 'sittings': sittings, **quality(region(words, borders[0], top, width, bottom))})
    return records

def parse_drafts(result, smart_processing=False):
    words, width, height = result['words'], result['width'], result['height']
    text = '\n'.join(line['text'] for line in lines(words))
    if 'SCREENING REGISTER' in text.upper():
        records = parse_register(words, width, height)
        if not records:
            return [], ['Table layout could not be separated safely. Use the extracted text to enter one student manually.']
    elif 'FULL NAME' in text.upper() and 'SITTING' in text.upper():
        records = [parse_single(words, width, height)]
    else:
        registrations = set(re.findall(r'(?:DEMO[- ]UTME[- ]\d+|\b\d{8,12}[A-Z]{2}\b)', text, re.I))
        if len(registrations) > 1:
            return [], ['Multiple students were detected in an unsupported layout. Enter each student separately; results have not been combined.']
        # Separate result slips and unknown layouts: extract only explicit labels.
        def labelled(pattern):
            match = re.search(pattern + r'\s*[:\-]\s*([^\n]+)', text, re.I)
            return match.group(1).strip() if match else ''
        records = [{'student_name': labelled(r'(?:FULL NAME|CANDIDATE NAME|NAME)'),
                    'registration_number': labelled(r'(?:JAMB REGISTRATION NUMBER|REGISTRATION NUMBER)'),
                    'course': labelled(r'(?:COURSE|PROGRAMME)'), 'jamb_score': score(text),
                    'sittings': [sitting(text)] if subject_rows(text) else [], **quality(words, known_layout=False)}]
        if not any(records[0][key] for key in ['student_name', 'registration_number', 'course', 'sittings']) and records[0]['jamb_score'] is None:
            return [], ['No reliable student fields were found. Review the text and enter the result manually.']
    for record in records:
        issues = record.setdefault('review_issues', [])
        record['smart_processing'] = smart_processing
        processing_warnings = record.setdefault('processing_warnings', [])
        # A page-wide label is safe only for a single applicant. Never apply
        # one student's UTME subjects to every row of a multi-student register.
        if len(records) == 1 and 'SCREENING REGISTER' not in text.upper():
            from .identities import candidate_name_issues
            issues.extend(candidate_name_issues(record.get('student_name', ''), text, smart_processing=smart_processing, warnings=processing_warnings))
            metadata = {}
            for field, pattern in [('dob', r'(?:DOB|DATE OF BIRTH)'), ('age', r'AGE'), ('remark', r'REMARK(?:S)?')]:
                match = re.search(r'^\s*' + pattern + r'\s*[:\-]\s*([^\n]+)', text, re.I | re.M)
                if match:
                    metadata[field] = match.group(1).strip()
            record['applicant'] = applicant_metadata(metadata)
            record['original_remark'] = metadata.get('remark', '')
            try:
                record['jamb_subjects'] = labelled_subjects(text)
            except ValueError as exc:
                issues.append(str(exc))
        for key, label in [('student_name', 'Student name'), ('registration_number', 'Registration number'), ('course', 'Course')]:
            if not record.get(key):
                issues.append(f'{label} was not detected.')
        if record['jamb_score'] is None:
            issues.append('JAMB score is missing or awaiting release.')
        if not record['sittings']:
            issues.append('No examination sitting was detected.')
        for exam in record['sittings']:
            if not all(exam.get(k) for k in ['board', 'exam_type', 'year', 'subjects']):
                issues.append('An examination sitting has missing details.')
            if any(row['grade'] == 'Unreadable' for row in exam['subjects']):
                issues.append('A subject grade is unreadable, withheld or awaiting release.')
    return records, ['Recognition confidence is an engine score, not a guarantee. Uncertain records are held for review.']
