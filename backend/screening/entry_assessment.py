"""Assess aligned ND credentials supplied by HND applicants."""
from copy import deepcopy
from .programmes import resolve_programme
from .routes import evaluate_route
from .result_parser import strip_assessment_marks

FIELDS = ('ND Course Of Study', 'ND Grade', 'ND CGPA', 'ND Institution Name', 'ND Graduation Year')

def lines(value):
    return [strip_assessment_marks(line).strip() for line in str(value or '').splitlines() if line.strip()] or ['']

def unresolved(draft, route, detail, failed=False):
    return {'student': {'name': draft['student_name'], 'registration_number': draft['registration_number']},
            'status': 'Not Eligible' if failed else 'Pending Review', 'confirmed': False,
            'sittings': draft.get('sittings', []), 'jamb_score': None, 'jamb_subjects': [],
            'checks': [{'label': 'Programme / ND entries', 'status': 'failed' if failed else 'pending', 'detail': detail}],
            'warnings': [], 'rules': {'programme': draft['course'], 'academic_session': '', 'revision': None,
            'admission_type': route, 'required_subjects': [], 'criteria': {}, 'minimum_credits': 5,
            'minimum_jamb': None, 'max_sittings': 2}}

def assess_entries(draft, rules, route, confirmed):
    hnd = route.startswith('HND')
    source = draft.get('source_record', {})
    values = {field: lines(source.get(field, '')) for field in FIELDS} if hnd else {'Department': lines(draft['course'])}
    count = max(map(len, values.values()))
    if any(len(parts) not in (1, count) for parts in values.values()):
        return unresolved(draft, route, 'ND entries have different numbers of lines. Align each course, grade and CGPA on the same line before screening.')
    outcomes = []
    for index in range(count):
        selected = {field: parts[index] if len(parts) > 1 else parts[0] for field, parts in values.items()}
        course = selected['ND Course Of Study' if hnd else 'Department']
        rule, match = resolve_programme(course, rules, route)
        if rule is None:
            result = unresolved(draft, route, f'Entry {index+1}: course "{course}" ' + ('has ambiguous programme matches.' if match == 'ambiguous' else 'does not match a configured programme.'), failed=bool(course) and match == 'unmatched')
        else:
            candidate = deepcopy(draft)
            candidate['course'] = rule.programme
            candidate['source_record'] = {**source, **selected}
            result = evaluate_route(rule, candidate, route, confirmed)
            if draft.get('optional_warnings') and any(c['status']=='failed' and c['label'] not in ['ND CGPA', 'ND grade consistency', 'Examination sittings'] for c in result['checks']):
                result = evaluate_route(rule, candidate, route, False)
            if match != 'exact':
                result['warnings'].append(f'Course "{course}" recognised as "{rule.programme}"; original text retained.')
            result['selected_nd_entry'] = {'index': index, 'values': selected,
                'positions': {field: index if len(parts)>1 else 0 for field, parts in values.items()}}
        outcomes.append(result)
    chosen = min(outcomes, key=lambda r: {'Eligible': 0, 'Pending Review': 1, 'Not Eligible': 2}[r['status']])
    if count > 1:
        chosen['warnings'].append(f'Assessed {count} aligned entries; selected entry {outcomes.index(chosen)+1}: {chosen["status"]}.')
        for index, outcome in enumerate(outcomes):
            if outcome is not chosen:
                reasons = '; '.join(c['detail'] for c in outcome['checks'] if c['status'] != 'passed')
                chosen['warnings'].append(f'Entry {index+1}: {outcome["status"]}. {reasons}')
    return chosen
