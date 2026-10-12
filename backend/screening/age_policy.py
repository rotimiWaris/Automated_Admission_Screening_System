"""Project-configured admission age rule; waiver decisions require review."""
from datetime import date
from django.utils import timezone
from .applicant_data import applicant_metadata


def apply_age_policy(result, data, today=None, admission_type="ND Full-Time"):
    if admission_type not in ["ND Full-Time", "ND Part-Time"]:
        return result
    today = today or timezone.localdate()
    cutoff = date(today.year, 9, 30)
    applicant = data.get('applicant') or {}
    source = data.get('source_record') or {}
    dob = data.get('dob', applicant.get('dob', ''))
    if not dob:
        dob = next((v for k, v in source.items() if ''.join(c for c in k.lower() if c.isalnum()) in ['dob', 'dateofbirth']), '')
    parsed = applicant_metadata({'dob': dob}, today=today)
    valid = parsed.get('age') is not None
    age = None
    if valid:
        born = date.fromisoformat(parsed['dob'])
        age = cutoff.year-born.year-((cutoff.month,cutoff.day)<(born.month,born.day))
    state = 'passed' if age is not None and age >= 16 else 'pending'
    detail = (f'Age {age} on {cutoff.isoformat()}; minimum 16.' if valid else f'Missing or invalid date of birth. DOB is required to verify age 16 by {cutoff.isoformat()}; a supplied age alone is insufficient.')
    if valid and age < 16:
        detail += ' Underage: review evidence of an approved exceptional-candidate waiver. A UTME score alone does not establish waiver approval.'
    result['checks'].append({'label': 'Admission age', 'status': state, 'detail': detail})
    result['age_assessment'] = {'minimum_age':16, 'cutoff_date':cutoff.isoformat(), 'age_at_cutoff':age, 'dob':parsed.get('dob') if valid else None}
    if state == 'pending': result['status'] = 'Pending Review'
    return result
