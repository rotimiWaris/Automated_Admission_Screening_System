"""Validate register headings and supply safely derivable output fields."""
import re
from result_ocr import OCRError


def normal(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def prepare_register_row(row, headers, route, number):
    expected={normal(h):h for h in headers}
    optional={normal(h) for h in ['#','Remark','Age','Sitting(s)','OLevel Result Sitting 2']}
    if route != 'ND Full-Time': optional.update(['jambreg','jambnumber'])
    # Accept portal label variants but keep the selected route's canonical schema.
    groups = [('formno','formnumber'), ('jambreg','jambnumber','regno','registrationnumber'),
              ('phone','phoneno'), ('dob','dateofbirth'), ('firstchoice','choice1')]
    if route == 'ND Part-Time': groups.append(('department','jambprogramme'))
    for group in groups:
        target = next((expected[k] for k in group if k in expected), None)
        if target:
            for key in group: expected.setdefault(key,target)
    values = dict(row.values)
    normalized = {normal(k):v for k,v in values.items()}
    if normalized.get('fullname') and not normalized.get('surname') and not normalized.get('firstname'):
        from .portal_import import split_name
        (surname, first, other), _ = split_name(normalized['fullname'])
        values.update({'Surname':surname,'First Name':first,'Other Name':other})
    mapped={};unknown=[]
    for header,value in values.items():
        canonical=expected.get(normal(header))
        if canonical is None:
            unknown.append(header);continue
        if normal(header) != normal(canonical) and normal(canonical) in normalized:
            continue
        if canonical in mapped:
            raise OCRError(f'{route} register: column "{canonical}" appears more than once. Keep one copy.')
        mapped[canonical]=value
    missing=[h for h in headers if h not in mapped and normal(h) not in optional]
    if missing:
        parts=[f'{route} register could not be imported.']
        if missing:parts.append('Missing required columns: '+', '.join(missing)+'.')
        if unknown:parts.append('Unrecognised column names: '+', '.join(unknown)+'. Check their spelling and the selected admission type.')
        parts.append('Remark, age, row number and sitting count can be generated automatically; other missing information must be supplied.')
        raise OCRError(' '.join(parts))
    for h in headers:
        if h in mapped:continue
        if h=='#':mapped[h]=str(number)
        elif normal(h)=='sittings':
            values=[value.strip().casefold() for key,value in mapped.items() if normal(key) in ['olevelresultsitting1','olevelresultsitting2']]
            mapped[h]=str(sum(value not in ['', 'none','n/a','not submitted','-'] for value in values))
        else:mapped[h]=''
    return mapped
