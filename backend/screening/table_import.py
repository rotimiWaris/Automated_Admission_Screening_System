"""Admission column mapping, separate from the generic table reader."""
import re
from result_ocr import OCRError
from result_ocr.tables import read_table
from .domain import SUBJECTS, GRADES, PENDING_GRADES, EXAM_COMBINATIONS
from .identities import registration_key
from .jamb_subjects import parse_subjects


def normal(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def import_students(raw, filename, admission_type='ND Full-Time', smart_processing=False):
    rows = read_table(raw, filename, max_rows=2000)
    if admission_type != 'ND Full-Time':
        from .routes import import_route
        return import_route(rows, filename, admission_type, smart_processing), rows
    if 'formno' in {normal(h) for h in rows[0].values}:
        from .mapoly_import import import_register
        return import_register(rows, filename, smart_processing=smart_processing), rows
    aliases = {normal(name): name for name in ['student_name', 'registration_number', 'course', 'jamb_score', 'jamb_subjects', 'sitting', 'board', 'exam_type', 'year'] + SUBJECTS}
    aliases.update({'jambsubject': 'jamb_subjects', 'utmesubjects': 'jamb_subjects'})
    aliases.update({normal(key): value for key, value in {'Full name': 'student_name', 'Student name': 'student_name', 'JAMB registration number': 'registration_number', 'Programme': 'course', 'UTME score': 'jamb_score', 'English': 'English Language', 'Maths': 'Mathematics', 'Accounting': 'Financial Accounting'}.items()})
    groups = {}
    for row in rows:
        values = {}
        for header, value in row.values.items():
            key = aliases.get(normal(header))
            if key is None:
                raise OCRError(f'{row.sheet}: unknown column "{header}". Use the downloadable template.')
            if key in values:
                raise OCRError(f'{row.sheet}: more than one column maps to {key}.')
            values[key] = value
        required = {'student_name', 'registration_number', 'course', 'jamb_score', 'sitting', 'board', 'exam_type', 'year'}
        if not required.issubset(values):
            raise OCRError('Missing columns: ' + ', '.join(sorted(required - values.keys())) + '. Use the template.')
        if not any(subject in values for subject in SUBJECTS):
            raise OCRError('Include subject columns, such as English Language and Mathematics.')
        source = f'{row.sheet}, row {row.number}'
        if values['sitting'] not in ['1', '2']:
            raise OCRError(f'{source}: sitting must be 1 or 2.')
        key = registration_key(values['registration_number']) or f'missing:{row.sheet}:{row.number}'
        score = int(values['jamb_score']) if re.fullmatch(r'\d{1,3}', values['jamb_score']) and int(values['jamb_score']) <= 400 else None
        draft = groups.setdefault(key, {'student_name': values['student_name'], 'registration_number': values['registration_number'], 'course': values['course'], 'jamb_score': score, 'sittings': [], 'confidence': None, 'review_issues': [], 'source_format': filename.rsplit('.', 1)[-1].lower(), 'source_rows': [], '_sitting_numbers': []})
        issues = draft['review_issues']
        try:
            combination = parse_subjects(values.get('jamb_subjects', ''))
            if combination:
                if draft.get('jamb_subjects') and set(draft['jamb_subjects']) != set(combination):
                    issues.append(f'{source}: conflicting JAMB subject combinations across sitting rows.')
                else:
                    draft['jamb_subjects'] = combination
        except ValueError as exc:
            issues.append(f'{source}: {exc}')
        if any(draft[field].strip().casefold() != values[field].strip().casefold() for field in ['student_name', 'course']) or draft['jamb_score'] != score:
            issues.append(f'{source}: conflicting student details across sitting rows.')
        draft['source_rows'].append(source)
        if values['sitting'] in draft['_sitting_numbers']:
            draft['duplicate_in_upload'] = True
            issues.append(f'{source}: this student and sitting occur more than once.')
            continue
        draft['_sitting_numbers'].append(values['sitting'])
        board = values['board'].upper()
        exam_type = {'school': 'School', 'privategce': 'Private/GCE', 'wasc': 'WASC'}.get(normal(values['exam_type']), '')
        year = int(values['year']) if re.fullmatch(r'\d{4}', values['year']) else ''
        subjects = []
        for subject in SUBJECTS:
            value = values.get(subject, '')
            if not value:
                continue
            grade = value.upper() if value.upper() in GRADES else value.title()
            if grade not in GRADES + PENDING_GRADES:
                grade = 'Unreadable'
            subjects.append({'subject': subject, 'grade': grade})
            if grade in PENDING_GRADES:
                issues.append(f'{source}: {subject} needs review ({value}).')
        if not all(values[field] for field in ['student_name', 'registration_number', 'course']) or not registration_key(values['registration_number']):
            issues.append(f'{source}: student details are incomplete.')
        if score is None:
            issues.append(f'{source}: JAMB score is missing or invalid.')
        if (board, exam_type) not in EXAM_COMBINATIONS or not isinstance(year, int) or not 1980 <= year <= 2100:
            issues.append(f'{source}: examination details need correction.')
        if not 1 <= len(subjects) <= 9:
            issues.append(f'{source}: enter between 1 and 9 subject grades.')
        draft['sittings'].append({'board': board, 'exam_type': exam_type, 'year': year, 'subjects': subjects})
    if len(groups) > 1000:
        raise OCRError('Import at most 1000 students at a time.')
    for draft in groups.values():
        draft.pop('_sitting_numbers')
    return list(groups.values()), rows
