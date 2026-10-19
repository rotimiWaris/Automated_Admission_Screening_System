"""Applicant metadata shared by structured imports and OCR drafts."""
from datetime import date, datetime
from django.utils import timezone

HEADERS = ['#', 'Form No.', 'Jamb reg', 'Name on Jamb', 'Surname', 'First Name',
           'other name', 'email', 'phone', 'dob', 'age', 'first choice',
           'jamb programme', 'jamb subject', 'jamb score', 'sitting(s)',
           'olevel result sitting 1', 'olevel result sitting 2', 'jamb olevel status',
           'submit date', 'remark']
ADMISSION_TYPES = ['ND Full-Time', 'ND Part-Time', 'HND Full-Time', 'HND Part-Time']


def applicant_metadata(values, today=None):
    today = today or timezone.localdate()
    metadata = dict(values)
    metadata['age_as_of'] = today.isoformat()
    warnings = []
    dob = str(values.get('dob', '')).strip()
    parsed = None
    if dob:
        try:
            parsed = datetime.fromisoformat(dob).date()
        except ValueError:
            for fmt in ['%d/%m/%Y', '%d-%m-%Y']:
                try:
                    parsed = datetime.strptime(dob, fmt).date()
                    break
                except ValueError:
                    pass
        if parsed is None or parsed > today:
            warnings.append('Date of birth is invalid. Use YYYY-MM-DD or DD/MM/YYYY.')
            parsed = None
    supplied = str(values.get('age', '')).strip()
    calculated = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day)) if parsed else None
    if supplied:
        if supplied.isdigit() and 0 <= int(supplied) <= 120:
            metadata['age'] = int(supplied)
            metadata['age_source'] = 'Provided'
            if calculated is not None and calculated != int(supplied):
                warnings.append(f'Provided age {supplied} differs from age {calculated} calculated from DOB.')
        else:
            metadata['age'] = None
            warnings.append('Provided age is invalid; review the source.')
    else:
        metadata['age'] = calculated
        metadata['age_source'] = 'Calculated from DOB' if parsed else 'Unavailable'
        if not dob:
            warnings.append('Age could not be calculated because DOB is missing.')
    if parsed:
        metadata['dob'] = parsed.isoformat()
    metadata['warnings'] = warnings
    return metadata


def remark_comparison(original, status):
    text = str(original or '').strip().casefold()
    expected = {'eligible': True, 'qualified': True, 'not eligible': False, 'unqualified': False, 'not qualified': False}.get(text)
    if not text:
        return {'mark': '', 'detail': 'No previous remark'}
    if expected is None or status not in ['Eligible', 'Not Eligible']:
        return {'mark': '?', 'detail': ''}
    agrees = expected == (status == 'Eligible')
    return {'mark': '✓' if agrees else '×', 'detail': 'Previous remark agrees' if agrees else 'Previous remark disagrees'}
