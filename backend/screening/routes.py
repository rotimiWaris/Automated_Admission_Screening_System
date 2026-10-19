"""Route-specific register schemas and owner-configured academic screening."""
from decimal import Decimal, InvalidOperation
from result_ocr import OCRError
from result_ocr.tables import TableRow
from .applicant_data import HEADERS
from .mapoly_import import import_register, normal
from .domain import evaluate

ND_PT_HEADERS = ['#','jamb reg','Form number','Surname','First name','Other name','EMAIL','PHONE NO','Date of Birth','Department','Sitting(s)','OLevel Result Sitting 1','OLevel Result Sitting 2','Submit Date','Remark']
HND_HEADERS = ['#','JAMB Number','Form Number','Surname','First name','Other name','E-mail','Phone','ND Institution Name','First Choice','ND Course Of Study','ND Graduation Year','ND Grade','ND CGPA','Sitting(s)','OLevel Result Sitting 1','OLevel Result Sitting 2','Submit Date','Remark']

def headers_for(route):
    return HND_HEADERS if route.startswith('HND') else ND_PT_HEADERS if route == 'ND Part-Time' else HEADERS


def import_route(rows, filename, route, smart_processing=False):
    headers = headers_for(route)
    expected = {normal(h): h for h in headers}
    aliases = {'formnumber':'Form No.', 'jambnumber':'Jamb reg', 'phoneno':'phone', 'dateofbirth':'dob', 'department':'jamb programme', 'ndcourseofstudy':'jamb programme'}
    canonical = {normal(h): h for h in HEADERS}
    drafts=[]
    for row in rows:
        from .register_schema import prepare_register_row
        source=prepare_register_row(row,headers,route,len(drafts)+1)
        values=dict.fromkeys(HEADERS,'')
        for header,value in source.items():
            target=aliases.get(normal(header),canonical.get(normal(header)))
            if target: values[target]=value
        form = source.get('Form Number',source.get('Form number','')).strip()
        values['Jamb reg'] = form
        draft=import_register([TableRow(row.sheet,row.number,values)],filename,require_utme=False,smart_processing=smart_processing)[0]
        draft['identifier_kind'] = 'Form number'
        if not form:
            draft['review_issues'] = [i for i in draft['review_issues'] if i != 'Student name, JAMB registration or programme is missing.']
            draft['review_issues'].append('Form number is required.')
        raw = {normal(k):v for k,v in row.values.items()}
        if raw.get('fullname') and not raw.get('surname') and not raw.get('firstname'):
            from .portal_import import split_name
            _, issue = split_name(raw['fullname'])
            if issue: draft['review_issues'].append(issue)
        draft.update(source_record=source,admission_type=route,applicant={**draft["applicant"],**source},export_headers=headers)
        if route.startswith('HND'):
            draft['applicant']['warnings']=[]
        drafts.append(draft)
    if len(drafts)>10000: raise OCRError('Import at most 10000 students at a time.')
    return drafts


def evaluate_route(rule, draft, route, confirmed):
    result=evaluate(rule,{**draft,'confirmed':confirmed},academic_only=route!='ND Full-Time')
    result['rules']=dict(result['rules'])
    if route!='ND Full-Time':
        result['rules']['academic_baseline_admission_type']=rule.admission_type
        result['rules']['admission_type']=route
        result['rules']['minimum_jamb']=None
    if route.startswith('HND'):
        source=draft.get('source_record',{})
        checks=result['checks']
        def check(label,state,detail): checks.append({'label':label,'status':state,'detail':detail})
        try:
            cgpa=Decimal(str(source.get('ND CGPA','')).strip())
            if not cgpa.is_finite() or not Decimal('0')<=cgpa<=Decimal('4'): raise InvalidOperation
        except (InvalidOperation,ValueError):
            check('ND CGPA','pending','ND CGPA is missing or invalid; enter a value on the 0.00 to 4.00 scale.')
        else:
            state='failed' if cgpa<2 else 'passed'
            check('ND CGPA',state,f'CGPA {cgpa}: ' + ('below 2.00 minimum.' if state=='failed' else 'meets the academic minimum; graduation waiting period assessed separately.'))
            from .graduation_policy import graduation_check
            checks.append(graduation_check(source.get('ND Graduation Year', ''), 2 if cgpa < Decimal('2.50') else 1))
            expected='fail' if cgpa<2 else 'pass' if cgpa<Decimal('2.50') else 'lower credit' if cgpa<3 else 'upper credit' if cgpa<Decimal('3.50') else 'distinction'
            grade=' '.join(str(source.get('ND Grade','')).lower().replace('-',' ').split())
            grade={'lc':'lower credit','uc':'upper credit'}.get(grade,grade)
            check('ND grade consistency','passed' if grade==expected else ('pending' if not grade else 'failed'),f'ND grade {grade or "not supplied"}; CGPA implies {expected}.')
        result['status']='Not Eligible' if any(c['label']=='ND grade consistency' and c['status']=='failed' for c in checks) else 'Pending Review' if any(c['status']=='pending' for c in checks) else 'Not Eligible' if any(c['status']=='failed' for c in checks) else 'Eligible'
    from .age_policy import apply_age_policy
    return apply_age_policy(result, draft, admission_type=route)
