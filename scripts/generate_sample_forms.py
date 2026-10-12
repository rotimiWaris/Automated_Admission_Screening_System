"""Generate fictional admission documents, not answer files or database records."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'samples' / 'synthetic-admissions'
REGULAR = Path('C:/Windows/Fonts/arial.ttf')
BOLD = Path('C:/Windows/Fonts/arialbd.ttf')
GREEN = '#174b3a'
INK = '#26362e'
GREY = '#62736a'
BORDER = '#c9d5cc'
NOTICE = 'SYNTHETIC TEST DATA - NOT AN OFFICIAL MAPOLY DOCUMENT'

def font(size=24, bold=False):
    return ImageFont.truetype(str(BOLD if bold else REGULAR), size)

def write(draw, xy, value, size=24, bold=False, fill=INK):
    draw.text(xy, str(value), font=font(size, bold), fill=fill)

def wrap(draw, value, width, size=23):
    lines, line = [], ''
    for word in str(value).split():
        candidate = f'{line} {word}'.strip()
        if draw.textlength(candidate, font=font(size)) > width:
            if not line:
                raise ValueError(f'Text too wide: {word}')
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + ([line] if line else [])

def banner(draw, width, title, subtitle):
    draw.rectangle((0, 0, width, 82), fill=GREEN)
    write(draw, (45, 25), NOTICE, 25, True, 'white')
    write(draw, (50, 118), title, 38, True)
    write(draw, (50, 174), subtitle, 23, fill=GREY)

def section(draw, y, title, width=1140):
    draw.rectangle((50, y, 50 + width, y + 43), fill='#eaf0e9')
    write(draw, (66, y + 8), title, 23, True)

def field(draw, x, y, label, value):
    write(draw, (x, y), label.upper(), 18, True, GREY)
    write(draw, (x, y + 29), value, 26)

def students():
    names = ['Adeola Akinwale', 'Chinedu Okafor', 'Zainab Bello', 'Temitope Alade',
             'Ifeoma Nwosu', 'Musa Ibrahim', 'Oluwaseyi Dada', 'Amarachi Eze',
             'Aisha Yusuf', 'Tobiloba Adebayo', 'Emeka Obi', 'Fatima Lawal',
             'Damilola Ajayi', 'Ngozi Uche', 'Sulaiman Musa', 'Bolanle Oladipo',
             'Chiamaka Onuoha', 'Maryam Sani', 'Kehinde Bakare', 'Daniel Bassey']
    courses = ['Computer Science', 'Business Administration', 'Science Laboratory Technology',
               'Accountancy', 'Electrical/Electronics Engineering']
    exams = [('WAEC', 'WASSCE / SSCE - School'), ('NECO', 'SSCE Internal'),
             ('WAEC', 'GCE / WASSCE - Private'), ('NABTEB', 'NBC / NTC - School'),
             ('NECO', 'SSCE External / GCE'), ('NABTEB', 'NBC / NTC - Private')]
    science = ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Geography', 'Civic Education']
    business = ['English Language', 'Mathematics', 'Economics', 'Commerce', 'Financial Accounting', 'Government', 'Civic Education']
    grades = ['B3', 'C4', 'C5', 'B2', 'C6', 'A1', 'B3']
    scores = [245, 178, 260, 155, 210, 188, 275, 160, 235, 199, 142, 280, 220, 170, 250, 185, None, 205, 230, 195]
    records = []
    for i, name in enumerate(names):
        course = courses[i % len(courses)]
        subjects = business if i % 5 in [1, 3] else science
        rows = list(zip(subjects, grades))
        if i in [3, 10]:
            rows[1] = ('Mathematics', 'D7')
        if i == 5:
            rows = rows[1:]  # English absent from the submitted record.
        if i == 7:
            rows = [(s, 'E8' if j > 2 else g) for j, (s, g) in enumerate(rows)]
        if i == 12:
            rows[2] = (rows[2][0], 'Awaiting')
        if i == 18:
            rows[3] = (rows[3][0], 'Withheld')
        board, exam = exams[i % len(exams)]
        sittings = [{'board': board, 'exam': exam, 'year': 2025, 'rows': rows}]
        if i in [2, 6, 9, 13, 17, 19]:
            sittings[0]['rows'] = [(s, 'F9' if s == 'Mathematics' else g) for s, g in rows]
            sittings.append({'board': 'NECO', 'exam': 'SSCE External / GCE', 'year': 2026,
                             'rows': [('English Language', 'B2'), ('Mathematics', 'B3'), (subjects[2], 'C4')]})
        records.append({'id': f'SYN-{i+1:03}', 'name': name, 'registration': f'DEMO-UTME-{i+1:04}',
                        'course': course, 'score': scores[i], 'sittings': sittings})
    return records

def individual(record):
    image = Image.new('RGB', (1240, 1754), 'white')
    draw = ImageDraw.Draw(image)
    banner(draw, 1240, 'ADMISSION SCREENING APPLICATION', 'Fictional applicant | MAPOLY project testing | Session: DEMO 2026/2027')
    section(draw, 235, 'A. APPLICANT AND PROGRAMME')
    field(draw, 65, 302, 'Application reference', record['id'])
    field(draw, 650, 302, 'JAMB registration number', record['registration'])
    field(draw, 65, 389, 'Full name', record['name'])
    field(draw, 650, 389, 'Admission route', 'ND Full-Time (test scenario)')
    field(draw, 65, 476, 'Proposed course of study', record['course'])
    field(draw, 65, 563, 'JAMB / UTME total score', 'Awaiting result' if record['score'] is None else f'{record["score"]} / 400')
    field(draw, 650, 563, 'Number of O-level sittings', len(record['sittings']))
    section(draw, 663, 'B. O-LEVEL EXAMINATION RESULTS')
    for index in range(2):
        x = 65 + index * 578
        write(draw, (x, 735), f'SITTING {index + 1}', 24, True)
        if index >= len(record['sittings']):
            write(draw, (x, 785), 'Not submitted', 24, fill=GREY)
            continue
        sitting = record['sittings'][index]
        write(draw, (x, 778), f'{sitting["board"]} | {sitting["year"]}', 24, True)
        write(draw, (x, 816), sitting['exam'], 22)
        draw.rectangle((x, 866, x + 530, 907), fill=GREEN)
        write(draw, (x + 10, 874), 'SUBJECT', 20, True, 'white')
        write(draw, (x + 385, 874), 'GRADE', 20, True, 'white')
        for j, (subject, grade) in enumerate(sitting['rows']):
            y = 907 + 49*j
            if j % 2 == 0:
                draw.rectangle((x, y, x+530, y+49), fill='#f3f6f2')
            write(draw, (x+10, y+13), subject, 21)
            write(draw, (x+385, y+13), grade, 21, True)
            draw.line((x, y+49, x+530, y+49), fill=BORDER)
    section(draw, 1385, 'C. ADMINISTRATIVE REVIEW')
    write(draw, (65, 1450), 'Screening officer: ____________________     Date: ____________________', 23)
    write(draw, (65, 1502), 'Decision: __________________________     Remarks: __________________', 23)
    write(draw, (65, 1585), 'All identities and results are fictional. Course choices are testing scenarios.', 21, fill=GREY)
    write(draw, (65, 1621), 'This layout is invented and is not a reproduction of a MAPOLY application form.', 21, fill=GREY)
    write(draw, (65, 1680), f'{NOTICE} | {record["id"]}', 20, True, GREEN)
    return image

def register_page(records, page, total):
    image = Image.new('RGB', (2480, 1754), 'white')
    draw = ImageDraw.Draw(image)
    banner(draw, 2480, 'MULTI-STUDENT ADMISSION SCREENING REGISTER',
           f'Fictional applicants across different courses | DEMO 2026/2027 | Page {page} of {total}')
    # Two separate sitting columns preserve each subject/grade association.
    columns = [50, 390, 825, 995, 1705, 2430]
    labels = ['APPLICANT', 'PROPOSED COURSE', 'UTME', 'O-LEVEL SITTING 1', 'O-LEVEL SITTING 2']
    draw.rectangle((50, 240, 2430, 293), fill=GREEN)
    for x, label in zip(columns, labels):
        write(draw, (x+14, 255), label, 23, True, 'white')
    for row_index, record in enumerate(records):
        y = 293 + row_index*315
        draw.rectangle((50, y, 2430, y+315), fill='#f2f6f1' if row_index % 2 == 0 else 'white')
        texts = [f'{record["id"]}\n{record["name"]}\n{record["registration"]}', record['course'],
                 'Awaiting' if record['score'] is None else f'{record["score"]} / 400']
        for sitting in record['sittings']:
            texts.append(f'{sitting["board"]} | {sitting["exam"]} | {sitting["year"]}\n' + '\n'.join(f'{s}: {g}' for s, g in sitting['rows']))
        if len(texts) == 4:
            texts.append('Not submitted')
        for col, value in enumerate(texts):
            lines = []
            for paragraph in value.split('\n'):
                lines.extend(wrap(draw, paragraph, columns[col+1]-columns[col]-28, 23))
            if len(lines)*31 > 289:
                raise ValueError(f'Register cell overflows for {record["id"]}')
            for k, line in enumerate(lines):
                write(draw, (columns[col]+14, y+14+k*31), line, 23)
        for x in columns:
            draw.line((x, y, x, y+315), fill=BORDER, width=2)
        draw.line((50, y+315, 2430, y+315), fill=BORDER, width=2)
    write(draw, (50, 1592), 'Invented layout. All identities and results are fictional. No admission decisions are supplied.', 24, fill=GREY)
    write(draw, (50, 1650), f'{NOTICE} | REGISTER PAGE {page}/{total}', 24, True, GREEN)
    return image

def main():
    singles = OUT / 'individual'
    batch = OUT / 'multiple-students'
    singles.mkdir(parents=True, exist_ok=True)
    batch.mkdir(parents=True, exist_ok=True)
    records = students()
    for record in records:
        image = individual(record)
        image.save(singles / f'{record["id"]}.png', dpi=(150, 150))
        image.save(singles / f'{record["id"]}.pdf', 'PDF', resolution=150.0, title=f'Synthetic screening application {record["id"]}')
        image.close()
    pages = [register_page(records[i:i+4], i//4+1, 5) for i in range(0, 20, 4)]
    for i, image in enumerate(pages, 1):
        image.save(batch / f'register-page-{i:02}.png', dpi=(150, 150))
    pages[0].save(batch / 'screening-register.pdf', 'PDF', save_all=True, append_images=pages[1:], resolution=150.0,
                  title='Synthetic multi-student admission screening register')
    for image in pages:
        image.close()
    print('Created 20 individual PDF forms, 20 individual PNGs, a 5-page register PDF and 5 register PNGs.')
    print('No JSON answers, real student data, or admission database records were created.')

if __name__ == '__main__':
    main()
