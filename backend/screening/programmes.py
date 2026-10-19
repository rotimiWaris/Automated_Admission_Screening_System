"""Programme aliases and conservative, unambiguous typo matching."""
import re


def programme_key(value):
    text = str(value or '').lower().replace('&',' and ').replace('/',' and ')
    text = re.sub(r'[^a-z0-9 ]',' ',text)
    text = re.sub(r'\b(?:higher national diploma|national diploma|full time|part time|fulltime|parttime|nd|hnd)\b',' ',text)
    text = ' '.join(text.split())
    text = re.sub(r'\bengineering technology\b','engineering',text)
    aliases = {
        'accounting':'accountancy',
        'business administration':'business administration and management',
        'electrical electronics engineering':'electrical and electronics engineering',
        'electrical engineering':'electrical and electronics engineering',
        'estate management':'estate management and valuation',
        'surveying and geoinformatics':'surveying and geo informatics',
        'library and information sciences':'library and information science',
    }
    return aliases.get(text,text)


def resolve_programme(value, rules, route):
    from difflib import SequenceMatcher
    key = programme_key(value)
    # A pasted course may occur several times in the same cell.
    words = key.split()
    for size in range(1, len(words) // 2 + 1):
        if len(words) % size == 0 and words == words[:size] * (len(words) // size):
            key = ' '.join(words[:size])
            break
    groups = {}
    for rule in rules:
        groups.setdefault(programme_key(rule.programme), []).append(rule)
    candidates = [key] if key in groups else []
    if not candidates and len(key) >= 6:
        candidates = [name for name in groups if abs(len(name)-len(key)) <= 2
                      and SequenceMatcher(None, key, name).ratio() >= .90]
    if len(candidates) != 1:
        return None, 'ambiguous' if len(candidates) > 1 else 'unmatched'
    matches = groups[candidates[0]]
    specific = [r for r in matches if r.admission_type == route]
    matches = specific or matches
    if len(matches) != 1:
        return None, 'ambiguous'
    return matches[0], 'exact' if programme_key(value) == candidates[0] else 'normalised'
