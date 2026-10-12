"""Validate register headings and supply safely derivable output fields."""
import re
from result_ocr import OCRError


def normal(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def prepare_register_row(row, headers, route, number):
    expected={normal(h):h for h in headers}
    optional={normal(h) for h in ['#','Remark','Age','Sitting(s)','OLevel Result Sitting 2']}
    mapped={};unknown=[]
    for header,value in row.values.items():
        canonical=expected.get(normal(header))
        if canonical is None:
            unknown.append(header);continue
        if canonical in mapped:
            raise OCRError(f'{route} register: column "{canonical}" appears more than once. Keep one copy.')
        mapped[canonical]=value
    missing=[h for h in headers if h not in mapped and normal(h) not in optional]
    if missing or unknown:
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
