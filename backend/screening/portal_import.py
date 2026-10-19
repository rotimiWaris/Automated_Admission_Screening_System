"""Join portal exports by registration identity, never by name or row position."""
from collections import Counter, defaultdict
from result_ocr import OCRError
from result_ocr.tables import TableRow
from .identities import registration_key, names_match, minor_name_typo
from .mapoly_import import normal, import_register
from .routes import headers_for, import_route


def columns(row):
    result = {}
    for heading, value in row.values.items():
        key = normal(heading)
        if key in result:
            raise OCRError(f'{row.sheet}: ambiguous repeated heading {heading}.')
        result[key] = value
    return result


def registration_column(values, sheet):
    explicit = [k for k in values if k in ['jambreg','jambnumber','jambregistrationnumber','regno','registration','registrationno','registrationnumber','regnumber']]
    candidates = explicit or [k for k in values if 'reg' in k]
    if len(candidates) != 1:
        raise OCRError(f'{sheet}: identify one JAMB registration column (for example Jamb reg or REG NO.).')
    return candidates[0]


def split_name(full):
    parts = full.split()
    surname = [i for i, p in enumerate(parts) if p.isupper()]
    if len(surname) == 1 and len(parts) >= 2:
        index = surname[0]
        remaining = parts[:index] + parts[index+1:]
        return (parts[index], remaining[0], ' '.join(remaining[1:])), None
    return ('', full, ''), 'Full Name has no unambiguous single uppercase surname. Full name retained; review surname, first name and other name.'


def merge_portals(rows, filename, route, smart=False):
    sheets = defaultdict(list)
    for row in rows: sheets[row.sheet].append(row)
    school = [name for name, values in sheets.items() if 'olevelresultsitting1' in columns(values[0])]
    jamb = [name for name, values in sheets.items() if 'name' in columns(values[0]) and 'utmesubject' in columns(values[0]) and 'jamb' in columns(values[0])]
    if not jamb: return None
    if len(sheets) != 2 or len(school) != 1 or len(jamb) != 1 or school[0] == jamb[0]:
        raise OCRError('Portal workbook requires exactly two populated sheets: school Olevel results and JAMB Name/UTME Subject/JAMB columns.')
    school_rows, jamb_rows = sheets[school[0]], sheets[jamb[0]]
    if len(school_rows) > 10000:
        raise OCRError('Import at most 10000 school candidates at a time.')
    school_key = registration_column(columns(school_rows[0]), school[0])
    jamb_key = registration_column(columns(jamb_rows[0]), jamb[0])
    index = defaultdict(list)
    for row in jamb_rows:
        key = registration_key(columns(row).get(jamb_key, ''))
        if key: index[key].append(row)
    counts = Counter(registration_key(columns(row).get(school_key, '')) for row in school_rows)
    report = {'school_rows':len(school_rows), 'jamb_rows':len(jamb_rows), 'matched':0, 'excluded_school_rows':[], 'unused_jamb_rows':0, 'ignored_columns':{}}
    school_fields = {'','sn','jambreg','formnumber','formno','fullname','surname','firstname','othername','email','phone','phoneno','dob','dateofbirth','sittings','olevelresultsitting1','olevelresultsitting2','choice1','firstchoice','jambprogramme','department','jambsubject','jambscore','ndinstitutionname','ndgraduationyear','ndcourseofstudy','ndgrade','ndcgpa','submitdate','remark'}
    jamb_fields = {jamb_key,'name','utmesubject','jamb','has5credits'}
    report['ignored_columns'][school[0]] = [h for h in school_rows[0].values if normal(h) not in school_fields | {school_key}]
    report['ignored_columns'][jamb[0]] = [h for h in jamb_rows[0].values if normal(h) not in jamb_fields]
    drafts, merged, used = [], [], set()
    for row in school_rows:
        s = columns(row); reg = s.get(school_key, ''); key = registration_key(reg)
        matches = index.get(key, [])
        reason = ('Missing JAMB registration' if not key else 'Duplicate registration in school sheet' if counts[key] > 1 else 'No matching JAMB registration' if not matches else 'Multiple JAMB rows have this registration' if len(matches)>1 else '')
        if reason:
            report['excluded_school_rows'].append({'sheet_row':row.number,'serial':s.get('',s.get('sn','')),'registration_number':reg,'reason':reason})
            continue
        other = matches[0]; j = columns(other); used.add(key)
        issues, warnings = [], []
        if s.get('surname') and s.get('firstname'):
            surname, first, rest = s['surname'], s['firstname'], s.get('othername','')
            full = ' '.join(p for p in [surname,first,rest] if p)
        else:
            full = s.get('fullname','')
            (surname,first,rest), issue = split_name(full)
            if issue: issues.append(issue)
        jamb_name = j.get('name','')
        if not names_match(full, jamb_name):
            detail = f'School name "{full}" differs from JAMB name "{jamb_name}"; registration matched.'
            if smart and minor_name_typo(full,jamb_name): warnings.append('Smart processing accepted a minor name typo. '+detail)
            else: issues.append(detail)
        status = j.get('has5credits','')
        if status.strip().casefold() not in ['true','yes','1']:
            issues.append('JAMB Has 5 Credits? is false, missing or unrecognised. Verify the JAMB Olevel status before admission.')
        values = dict(s)
        values.update({'':s.get('',s.get('sn',str(row.number-1))), 'jambreg':reg,'jambnumber':reg,
            'formno':s.get('formnumber',s.get('formno','')), 'formnumber':s.get('formnumber',s.get('formno','')),
            'surname':surname,'firstname':first,'othername':rest,'nameonjamb':jamb_name,
            'phone':s.get('phone',s.get('phoneno','')), 'phoneno':s.get('phone',s.get('phoneno','')),
            'dob':s.get('dob',s.get('dateofbirth','')), 'dateofbirth':s.get('dob',s.get('dateofbirth','')),
            'firstchoice':s.get('choice1',s.get('firstchoice','')), 'department':s.get('department',s.get('jambprogramme','')),
            'jambsubject':s.get('jambsubject',s.get('jambsubjects','')), 'jambscore':s.get('jambscore',''), 'jambolevelstatus':status})
        # School portal is authoritative for UTME score and subjects, including blanks.
        headers = headers_for(route)
        output = {h:values.get(normal(h),'') for h in headers if normal(h) in values}
        record = TableRow(row.sheet,row.number,output)
        result = (import_register([record],filename,smart_processing=smart) if route=='ND Full-Time' else import_route([record],filename,route,smart))[0]
        result['review_issues'].extend(issues)
        result['processing_warnings'].extend(warnings)
        result['source_rows'].append(f'{other.sheet}, row {other.number}')
        result['portal_match'] = {'school_name':full,'jamb_name':jamb_name,'jamb_olevel_status':status}
        drafts.append(result); merged.append(record)
    report['matched'] = len(drafts)
    report['unused_jamb_rows'] = sum(1 for row in jamb_rows if registration_key(columns(row).get(jamb_key,'')) not in used)
    if not drafts:
        raise OCRError(f'No unambiguous registration matches. School rows: {len(school_rows)}; JAMB rows: {len(jamb_rows)}. Check registration columns, missing matches and duplicate registrations. No result file was created.')
    drafts[0]['merge_report'] = report
    return drafts, merged
