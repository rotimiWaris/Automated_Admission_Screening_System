"""Reviewed transcription of the supplied ND Full-Time compendium.

Comma separates distinct credit options; / separates alternatives within one
option. These are selection groups, not aliases. Source wording is retained in
each rule's JSON criteria by the import command. No score/session is inferred.
"""
import re

NAMES = {
    'E': 'English Language', 'M': 'Mathematics', 'P': 'Physics', 'C': 'Chemistry',
    'B': 'Biology', 'A': 'Agricultural Science', 'Ec': 'Economics', 'Co': 'Commerce',
    'Ac': 'Financial Accounting', 'Bk': 'Book Keeping', 'G': 'Geography',
    'Gov': 'Government', 'H': 'History', 'L': 'Literature in English',
    'St': 'Statistics', 'BM': 'Business Methods', 'BS': 'Business Studies',
    'Mgmt': 'Business Management', 'CE': 'Civic Education', 'Ins': 'Insurance',
    'Y': 'Yoruba', 'I': 'Igbo', 'Ha': 'Hausa', 'F': 'French',
    'CR': 'Christian Religious Studies', 'IR': 'Islamic Religious Studies',
    'Mk': 'Marketing', 'SM': 'Store Management', 'Pu': 'Purchasing',
    'FA': 'Fine Arts', 'Ty': 'Typewriting', 'Sh': 'Shorthand', 'OP': 'Office Practice',
    'DP': 'Data Processing', 'Mu': 'Music', 'TD': 'Technical Drawing',
    'MW': 'Metal Work', 'WW': 'Wood Work', 'BE': 'Basic Electricity',
    'EL': 'Basic Electronics', 'FM': 'Further Mathematics', 'HE': 'Home Economics',
    'FN': 'Food and Nutrition', 'AH': 'Animal Husbandry',
    'BCF': 'Basic Catering and Food Services', 'Fi': 'Fisheries',
    'CC': 'Catering Craft Practice', 'HS': 'Health Science', 'TS': 'Tourism Studies',
    'HM': 'Home Management', 'CS': 'Computer Studies', 'ICT': 'ICT',
    'CCP': 'Computer Craft Practice', 'EI': 'Electrical Installation and Maintenance Work',
    'VA': 'Visual Art', 'CCA': 'Cultural and Creative Art', 'Tie': 'Tie Dye and Bleaching',
    'CT': 'Clothing and Textiles', 'GD': 'Graphic Design', 'BC': 'Building Construction',
    'PD': 'Painting and Decoration', 'CJ': 'Carpentry and Joinery',
    'PP': 'Plumbing and Pipe Fitting', 'Brick': 'Bricklaying and Concreting',
    'Su': 'Surveying', 'RT': 'Radio Television and Electrical Work',
    'AR': 'Air Conditioning and Refrigeration', 'AM': 'Auto Mechanics',
    'AE': 'Auto Electrical Work', 'GSM': 'GSM Phone Maintenance and Repair',
    'AB': 'Auto Body Repair and Spray Painting', 'WP': 'Welding and Pipe Fitting',
    'Block': 'Block Laying and Concreting', 'Up': 'Upholstery', 'Fu': 'Furniture Making',
    'Machine': 'Machine Wood Working', 'Arabic': 'Arabic',
}


def group(count, choices, label='Subject selection'):
    return {'count': count, 'options': [[NAMES[s] for s in option.split('/')]
                                      for option in choices.split(',')], 'label': label}


def path(core, count, electives):
    return [group(1, item, 'Required credit: ' + ' / '.join(NAMES[s] for s in item.split('/')))
            for item in core.split(',')] + ([group(count, electives, 'Other permitted credits')] if count else [])


def jamb(core, count=0, electives=''):
    return path(core, count, electives)


BUSINESS = 'Ac/Bk,St,Gov,G,H,BM/BS/Mgmt,L,P,C,B/A,CE,Ins,Y/Ha/I/F,CR/IR'
BUSINESS_JAMB = jamb('E,M', 2, 'G,Co,Gov,Ac,Ec')
# Project-owner category mapping, restricted to JAMB-offered subjects. School
# labels ICT/Visual Art/General Mathematics map to Computer Studies/Art/Maths.
BROAD = jamb('E', 3, 'P,C,B,M,A,CS,Ec,Co,Gov,G,Ac,L,H,Y,I,Ha,F,Arabic,CR,IR,FA,Mu')
CATEGORY_NOTE = 'Subject categories configured from the project owner\'s supplied list, using JAMB-offered subjects; this is a project configuration, not a newly verified MAPOLY subject list.'


def specifications():
    rows = []
    def add(name, core, count, electives, utme, passes=(), notes=(), advisory=(), extra_paths=()):
        rows.append({'programme': name, 'credit_paths': [path(core, count, electives), *extra_paths],
                     'jamb_groups': utme, 'pass_groups': [group(1, p, 'Additional pass: ' + ' / '.join(NAMES[s] for s in p.split('/'))) for p in passes],
                     'review_notes': list(notes), 'advisories': list(advisory)})
    for name, pool in [
        ('Accountancy', BUSINESS),
        ('Business Administration and Management', 'Ac/Bk,L,BM/BS/Mgmt,H,St,SM,G,Mk,Gov,P,C,CE,B/A,Y/Ha/I/F,CR/IR'),
        ('Marketing', 'Ac/Bk,L,BM/BS/Mgmt,St,Gov/H,Pu,P,C,B/A,Y/Ha/I/F,CR/IR,Mk,CE,SM'),
        ('Banking & Finance', BUSINESS),
    ]:
        add(name, 'E,M,Ec/Co', 2, pool + ',Ec,Co',
            jamb('E,M', 2, 'Ec,G,H,Gov,Co,Ac') if name == 'Banking & Finance' else BUSINESS_JAMB)
    add('Mass Communication', 'E,M', 3, 'H,L,Ec/Co,FA,F,Gov,B,P,C,G,Ty,Ac,CR/IR,CE,Y/I/Ha', BROAD, passes=['L'],
        advisory=[CATEGORY_NOTE])
    add('Office Technology and Management', 'E,M', 3, 'Ty,Sh,OP,Ec/Co,L,Ac,BM,H/Gov,G,B/A,P,C,DP,Mk,CE,CR/IR,F', jamb('E',3,'M,Ec/Co,Gov/H,CR,G,Ac'))
    add('Social Development', 'E,M', 3, 'Ec/Co,BM,Ac,L,G,OP,B/A,C,P,H/Gov,Ty,Sh', jamb('E,Gov/H',2,'Ec,Co,G,M'))
    add('Library and Information Science', 'E,M', 3, 'H,CE,Mu,F,Ec/Co,Gov,CR/IR,G,L,P,C,A,B', BROAD,
        advisory=[CATEGORY_NOTE])
    add('Science Laboratory Technology', 'E,M', 1, 'Ec,G,TD,MW/WW,FA,BE/EL,FM,St,Y/I/Ha', jamb('E,M,B/A,P'), passes=['P','C','B/A'])
    rows[-1]['credit_paths'][0].insert(2, group(2, 'P,C,B/A', 'Two core science credits'))
    add('Food Technology', 'E,M,C,B/A', 1, 'Ec,G,FM,P,TD,HE,FN,AH,BCF,Fi,CC', jamb('E,B/A',2,'Ec,C,P,M'), passes=['P'])
    add('Hospitality Management', 'E,M,B/A/FN', 2, 'P,C,M/St,Co/Ec,HS,FN/HE/CC,G,Gov,TD,Y/I/Ha', jamb('E,B/A',2,'P,C,M,Ec'))
    add('Leisure and Tourism Management', 'E,M', 3, 'G,Ec/Co,H,Mk,CE,Gov,Ac,TS,A,B,C,P,FN', jamb('E,M,C,P'))
    add('Nutrition and Dietetics', 'E,M', 3, 'P,C,B/A/HS,HE/HM,FN,Ec/Co,CC,BCF', jamb('E,C,B,A'))
    add('Pharmaceutical Technology', 'E,M,C,B', 1, 'G,Ec,TD,FN,A', jamb('E,M,C,P/B'), passes=['P'])
    add('Computer Science', 'E,M,P/BE/EL', 2, 'C,B/A/FN,CS/DP/ICT,CCP,CE/G,Ec/Co,FM,EI', jamb('E,M',2,'G,P,Ec,C'))
    add('Statistics and Mathematics', 'E,M', 3, 'Ec,G,Gov/H,Bk/Ac,FM,P,C,B/A,Co,St,CR/IR', jamb('E',3,'Ec/Co,H/Gov,CR/IR,M'))
    add('Environmental Science and Management Technology', 'E,M', 3, 'P,C,B,A,G', jamb('E,C,B',1,'P,A,G'))
    add('Art and Industrial Design', 'E,M', 3, 'B/A,FA/VA/CCA,Tie,C,H,Gov,L,CT,G,Ec,Co,CR/IR,TD,HE', jamb('E,FA',2,'M,H,C,B,Y/I/Ha'))
    add('Architectural Technology', 'E,M,P', 2, 'B/A,C,H,FM,G,Ec/Co,TD/GD,BC,PD/FA,WW,EL,CS,CR/IR,CJ', jamb('E,M',2,'P,C,TD'),
        advisory=['A pass in Technical Drawing/Fine Art is an advantage, not a compulsory requirement.'])
    add('Building Technology', 'E,M,P', 2, 'B,C,FM,G,TD,WW,MW,FA,CR/IR,Co/Ec,St,BE,BC,PP,Brick,CS,PD,CJ', jamb('E,M,P,C/FA'))
    add('Estate Management and Valuation', 'E,M,Ec,P/C/B/A', 1, 'G,Gov,TD,Co,FA,Ac,Bk,Y/I/Ha,FN,L,WW,MW', jamb('E,M',2,'Ec,FA,P,C,B'),
        extra_paths=[path('E,M,Ec',2,'P,C,B/A')])
    add('Quantity Surveying', 'E,M,P/C', 2, 'B/A,C,P,FM,G,Ec,FA,TD,MW,WW,CR/IR,CJ,Brick,BC', jamb('E',3,'P,M,G,Ec,B/A'))
    add('Surveying and Geo-Informatics', 'E,M,P', 2, 'B/A,C,St,FM,G,Ec/Co,TD/FA,Su,CR/IR', jamb('E',3,'C,A/B,Ec,M'))
    add('Urban and Regional Planning', 'E,M,P/C/B/Ec', 2, 'A,FM,G,FA,TD,Gov/H,CR/IR,Y/I/Ha,P,C,B,Ec', jamb('E,G',2,'P,C,B/A,Ec,Gov,FA,TD'),
        advisory=['UTME electives configured as explicitly supplied by the project owner, including Technical Drawing. Mathematics remains compulsory at O\'level.'])
    for name, pool in [
        ('Electrical/Electronics Engineering', 'MW,TD,FM,BE/EL,B/A,G,EI,Ec,CS,CE,RT,AR,AM,AE,GSM,DP'),
        ('Computer Engineering', 'MW,TD,AM,FM,BE/EL,B/A,G,Ec/Co,CS,CE,GSM,RT,EI,DP'),
        ('Mechanical Engineering', 'MW,TD,AM,FM,BE/EL,B/A,G,Ec,CS,CE,AB,AR,WP,PP,AE'),
        ('Civil Engineering', 'MW,TD,AM,FM,BE/EL,B/A,G,Ec/Co,CS,CE,Block,Up,Fu,CJ,Machine,PP,BC'),
    ]:
        add(name, 'E,M,P,C', 1, pool, jamb('E,M,P,C'))
    return rows


def from_source(source):
    blocks = re.split(r'(?im)^row\s+\d+\s*$', source)[1:]
    rows = specifications()
    if len(blocks) != len(rows):
        raise ValueError('Expected all 28 compendium rows; refusing a partial import.')
    for index, (row, block) in enumerate(zip(rows, blocks), 1):
        heading = next((line.strip().lstrip('-') for line in block.splitlines()
                        if line.strip() and not re.fullmatch(r'-?\d+', line.strip())), '')
        def normalized(value):
            return re.sub(r'[^a-z0-9]', '', value.casefold().replace('&', 'and'))
        if normalized(heading) != normalized(row['programme']):
            raise ValueError(f'Unexpected programme in row {index}: {heading}. Review the transcription before importing.')
        # Exclude the next school's heading; retain row-specific wording.
        block = re.split(r'(?im)^\s*(?:i{1,3}|iv|v)\.\s+school', block)[0]
        row['source_text'] = block.strip()
        row['source_row'] = index
        row['school'] = ('Business & Management Studies' if index <= 4 else
                         'Communication and Information Technology' if index <= 8 else
                         'Science and Technology' if index <= 17 else
                         'Environmental Studies' if index <= 24 else 'Engineering')
    return rows
