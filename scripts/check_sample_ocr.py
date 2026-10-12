"""Opt-in native OCR regression check. No JSON answers or student records are saved."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from screening.ocr_views import recognise
from generate_sample_forms import students


def matches(draft, expected):
    return (draft['student_name'] == expected['name']
            and draft['registration_number'] == expected['registration']
            and draft['course'] == expected['course']
            and draft['jamb_score'] == expected['score']
            and [[(row['subject'], row['grade']) for row in sitting['subjects']] for sitting in draft['sittings']]
                == [sitting['rows'] for sitting in expected['sittings']])


if __name__ == '__main__':
    expected = students()
    failures = []
    for record in expected:
        name = record['id'] + '.png'
        _, drafts, _ = recognise((ROOT / 'samples/synthetic-admissions/individual' / name).read_bytes(), 1)
        exact = len(drafts) == 1 and matches(drafts[0], record)
        print(name, 'MATCH' if exact else 'REVIEW', flush=True)
        if not exact:
            failures.append(name)
    raw = (ROOT / 'samples/synthetic-admissions/multiple-students/screening-register.pdf').read_bytes()
    for number in range(1, 6):
        _, drafts, _ = recognise(raw, number)
        exact = len(drafts) == 4 and all(matches(d, e) for d, e in zip(drafts, expected[(number-1)*4:number*4]))
        print(f'Register page {number}', 'MATCH' if exact else 'REVIEW', flush=True)
        if not exact:
            failures.append(f'Register page {number}')
    print(f'{25-len(failures)}/25 pages match for names, registrations, courses, scores and subject grades.')
    print('Synthetic-layout accuracy only; this is not a guarantee for real documents.')
    sys.exit(bool(failures))
