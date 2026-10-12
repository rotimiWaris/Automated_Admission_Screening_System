"""Read explicitly supplied UTME subjects, never infer them from O'level."""
import re
from .domain import SUBJECTS


def parse_subjects(value):
    aliases = {name.casefold(): name for name in SUBJECTS}
    aliases.update({'english': 'English Language', 'use of english': 'English Language',
                    'use of english language': 'English Language', 'maths': 'Mathematics',
                    'principles of accounts': 'Financial Accounting', 'accounts': 'Financial Accounting',
                    'accounting': 'Financial Accounting', 'fine art': 'Fine Arts',
                    'crs': 'Christian Religious Studies', 'crk': 'Christian Religious Studies',
                    'irs': 'Islamic Religious Studies', 'irk': 'Islamic Religious Studies'})
    aliases.update({'lit. in english': 'Literature in English', 'christian rel. know': 'Christian Religious Studies',
                    'princ. of account': 'Financial Accounting', 'islamic studies': 'Islamic Religious Studies'})
    if not value.strip():
        return []
    parts = re.split(r'[,;|\n]+', value)
    parts = [re.sub(r'\s*-\s*\[\d+\](?:\s*\[[?\u2713\u00d7]\])?\s*$', '', part).strip() for part in parts if part.strip()]
    subjects = [aliases.get(part.casefold()) for part in parts]
    if len(subjects) != 4 or None in subjects or len(set(subjects)) != 4:
        raise ValueError('Supply four distinct JAMB subject names separated by commas, semicolons or |.')
    return subjects


def labelled_subjects(text):
    match = re.search(r'(?im)^\s*(?:JAMB|UTME)\s+SUBJECTS?\s*:\s*([^\n]+)', text)
    if not match:
        return []
    return parse_subjects(match.group(1))
