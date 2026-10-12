from .compendium import NAMES
from .criteria import assess, validate_criteria

GRADES = ['A1', 'B2', 'B3', 'C4', 'C5', 'C6', 'D7', 'E8', 'F9']
PENDING_GRADES = ['Awaiting', 'Withheld', 'Unreadable', 'Outstanding', 'Cancelled', 'Absent']
SUBJECTS = ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Economics', 'Government', 'Literature in English', 'Geography', 'Agricultural Science', 'Commerce', 'Financial Accounting', 'Civic Education', 'Computer Studies', 'Further Mathematics', 'Technical Drawing', 'Christian Religious Studies', 'Islamic Religious Studies', 'Yoruba', 'Igbo', 'Hausa', 'French', 'Marketing', 'Data Processing']
SUBJECTS = list(dict.fromkeys(SUBJECTS + list(NAMES.values()) + ['Livestock Farming', 'Photography', 'Physical Education', 'Computer Craft Studies']))
# Sources and current-policy limitations: research/mapoly-olevel-examinations.md
EXAMINATIONS = [
    {'board': 'WAEC', 'exam_type': 'School', 'label': 'WAEC — WASSCE / SSCE (School)'},
    {'board': 'WAEC', 'exam_type': 'Private/GCE', 'label': 'WAEC — GCE O’level / WASSCE (Private)'},
    {'board': 'WAEC', 'exam_type': 'WASC', 'label': 'WAEC — WASC (Legacy certificate)'},
    {'board': 'NECO', 'exam_type': 'School', 'label': 'NECO — SSCE Internal (School)'},
    {'board': 'NECO', 'exam_type': 'Private/GCE', 'label': 'NECO — SSCE External / GCE (Private)'},
    {'board': 'NABTEB', 'exam_type': 'School', 'label': 'NABTEB — NBC / NTC (School)'},
    {'board': 'NABTEB', 'exam_type': 'Private/GCE', 'label': 'NABTEB — NBC / NTC (Private / GCE)'},
]
EXAM_BOARDS = list(dict.fromkeys(exam['board'] for exam in EXAMINATIONS))
EXAM_COMBINATIONS = {(exam['board'], exam['exam_type']) for exam in EXAMINATIONS}

def integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be a whole number from {minimum} to {maximum}.')
    return value

def text(value, name, maximum=150):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f'{name} is required (maximum {maximum} characters).')
    return value.strip()

def validate_rules(data):
    if not isinstance(data, dict):
        raise ValueError('Supply a rule object.')
    result = {'programme': text(data.get('programme'), 'Programme'), 'academic_session': text(data.get('academic_session'), 'Academic session', 30), 'minimum_jamb': None if data.get('minimum_jamb') is None else integer(data.get('minimum_jamb'), 'Minimum JAMB score', 0, 400), 'minimum_credits': integer(data.get('minimum_credits'), 'Required credits', 1, 9), 'max_sittings': None if data.get('max_sittings') is None else integer(data.get('max_sittings'), 'Maximum sittings', 1, 2)}
    result['admission_type'] = data.get('admission_type', 'ND Full-Time')
    if result['admission_type'] not in ['All Admission Type', 'ND Full-Time', 'ND Part-Time', 'HND Full-Time', 'HND Part-Time']:
        raise ValueError('Select a valid admission type.')
    result['criteria'] = validate_criteria(data.get('criteria', {}), SUBJECTS)
    if result['criteria'] and result['minimum_credits'] != 5:
        raise ValueError('The supplied compendium requires five credits. Edit selection paths consistently before changing this policy.')
    if result['criteria'] and result['admission_type'] not in ['ND Full-Time', 'All Admission Type']:
        raise ValueError('This compendium applies only to ND Full-Time.')
    result['source'] = data.get('source', '')
    if not isinstance(result['source'], str) or len(result['source']) > 250:
        raise ValueError('Source must be text of at most 250 characters.')
    required = data.get('required_subjects')
    if not isinstance(required, list) or not 1 <= len(required) <= 9:
        raise ValueError('Add between 1 and 9 required subjects.')
    seen = set()
    for item in required:
        if not isinstance(item, dict) or item.get('subject') not in SUBJECTS or item.get('minimum_grade') not in GRADES:
            raise ValueError('Each required subject needs a valid subject and minimum grade.')
        if item['subject'] in seen:
            raise ValueError('Required subjects cannot be duplicated.')
        seen.add(item['subject'])
    result['required_subjects'] = [{'subject': r['subject'], 'minimum_grade': r['minimum_grade']} for r in required]
    for key in ['allow_combining', 'active']:
        if type(data.get(key)) is not bool:
            raise ValueError(f'{key} must be true or false.')
        result[key] = data[key]
    if result['max_sittings'] == 1 and result['allow_combining']:
        raise ValueError('Combining results requires a maximum of two sittings.')
    return result

def evaluate(rule, data, academic_only=False):
    student = {'name': text(data.get('student_name'), 'Student name'), 'registration_number': text(data.get('registration_number'), 'JAMB registration number', 80)}
    score = data.get('jamb_score')
    if score is not None:
        integer(score, 'JAMB score', 0, 400)
    if type(data.get('confirmed')) is not bool:
        raise ValueError('Specify whether the entered result is complete and confirmed.')
    sittings = data.get('sittings')
    if not isinstance(sittings, list) or not 1 <= len(sittings) <= 2:
        raise ValueError('Enter one or two examination sittings.')
    normalized = []
    for sitting in sittings:
        if (not isinstance(sitting, dict)
                or not isinstance(sitting.get('board'), str)
                or not isinstance(sitting.get('exam_type'), str)
                or (sitting['board'], sitting['exam_type']) not in EXAM_COMBINATIONS):
            raise ValueError('Select a listed O’level examination for each sitting.')
        year = integer(sitting.get('year'), 'Examination year', 1980, 2100)
        rows = sitting.get('subjects')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 9:
            raise ValueError('Enter 1–9 subjects in each sitting.')
        seen = set()
        clean = []
        for row in rows:
            if not isinstance(row, dict) or row.get('subject') not in SUBJECTS or row.get('grade') not in GRADES + PENDING_GRADES:
                raise ValueError('Choose a valid subject and grade for every row.')
            if row['subject'] in seen:
                raise ValueError(f'Duplicate subject in a sitting: {row["subject"]}.')
            seen.add(row['subject'])
            clean.append({'subject': row['subject'], 'grade': row['grade']})
        normalized.append({'board': sitting['board'], 'exam_type': sitting['exam_type'], 'year': year, 'subjects': clean})
    jamb_subjects = data.get('jamb_subjects', [])
    if not isinstance(jamb_subjects, list) or len(jamb_subjects) > 4 or any(not isinstance(s, str) or s not in SUBJECTS for s in jamb_subjects) or len(set(jamb_subjects)) != len(jamb_subjects):
        raise ValueError('Enter up to four distinct, valid JAMB subjects.')
    if rule.criteria and rule.admission_type not in ['ND Full-Time', 'All Admission Type'] and not academic_only:
        raise ValueError('The supplied compendium only covers ND Full-Time.')
    checks = []
    def check(label, status, detail):
        checks.append({'label': label, 'status': status, 'detail': detail})
    if not academic_only:
        check('JAMB score', 'pending' if score is None or rule.minimum_jamb is None else ('passed' if score >= rule.minimum_jamb else 'failed'), f'{score if score is not None else "Not entered"}; minimum {rule.minimum_jamb if rule.minimum_jamb is not None else "not specified"} / 400.')
    permitted = len(normalized) <= (rule.max_sittings or 2) and (len(normalized) == 1 or rule.allow_combining)
    check('Examination sittings', 'pending' if rule.max_sittings is None else 'passed' if permitted else 'failed', f'{len(normalized)} submitted; maximum {rule.max_sittings if rule.max_sittings is not None else "not specified"}. Combining results is {"allowed" if rule.allow_combining else "not allowed"}.')
    # Never combine forbidden sittings or count the same subject twice.
    best = {}
    unresolved_subjects = set()
    for sitting in normalized:
        for row in sitting['subjects']:
            subject, grade = row['subject'], row['grade']
            if grade in PENDING_GRADES:
                unresolved_subjects.add(subject)
            if subject not in best or (grade in GRADES and (best[subject] not in GRADES or GRADES.index(grade) < GRADES.index(best[subject]))):
                best[subject] = grade
    if permitted:
        credits = sum(g in GRADES[:6] for g in best.values())
        possible_credits = credits + sum(best[s] not in GRADES[:6] for s in unresolved_subjects)
        check('O’level credits', 'passed' if credits >= rule.minimum_credits else ('pending' if possible_credits >= rule.minimum_credits or not data['confirmed'] else 'failed'), f'{credits} distinct subjects at C6 or above; {rule.minimum_credits} required.')
        for required in rule.required_subjects:
            grade = best.get(required['subject'])
            if grade is None:
                status = 'failed' if data['confirmed'] else 'pending'
                detail = f'Missing subject; {required["minimum_grade"]} or above required.'
            elif grade in PENDING_GRADES:
                status, detail = 'pending', f'{grade}; confirm the grade before screening.'
            else:
                status = 'passed' if GRADES.index(grade) <= GRADES.index(required['minimum_grade']) else 'failed'
                if status == 'failed' and required['subject'] in unresolved_subjects:
                    status = 'pending'
                detail = f'{grade} submitted; {required["minimum_grade"]} or above required.'
            check(required['subject'], status, detail)
        if rule.criteria:
            assess(rule.criteria, best, jamb_subjects, data['confirmed'], check, unresolved_subjects, check_utme=not academic_only)
    else:
        check('O’level assessment', 'pending', 'Select permitted sitting(s) before subjects and credits can be evaluated.')
    if not data['confirmed']:
        check('Result confirmation', 'pending', 'Confirm all entered results and resolve awaiting, withheld or unreadable grades.')
    # Incomplete inputs stay pending, even if another check has already failed.
    pending = (score is None and not academic_only) or not data['confirmed'] or any(c['status'] == 'pending' for c in checks if c['label'] != 'O’level assessment')
    status = 'Pending Review' if pending else ('Not Eligible' if any(c['status'] == 'failed' for c in checks) else 'Eligible')
    warnings = [f'{row["subject"]}: {row["grade"]} (sitting {index}). This unresolved grade was not counted as a credit or pass.' for index, sitting in enumerate(normalized, 1) for row in sitting['subjects'] if row['grade'] in PENDING_GRADES]
    return {'warnings': warnings, 'status': status, 'student': student, 'jamb_score': score, 'jamb_subjects': jamb_subjects, 'sittings': normalized, 'confirmed': data['confirmed'], 'checks': checks, 'rules': rule.snapshot()}
