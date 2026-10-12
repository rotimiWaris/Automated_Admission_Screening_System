"""Distinct-subject matching for compendium credit and UTME selections."""

def allocation(groups, available):
    """Return one actual distinct-subject selection, or None if unsatisfied."""
    slots=[]
    for index,group in enumerate(groups):
        choices=[(subject,(index,option_index)) for option_index,option in enumerate(group['options']) for subject in option if subject in available]
        slots.extend([choices]*group['count'])
    slots.sort(key=len)
    def assign(index,used,buckets):
        if index==len(slots): return used
        for subject,bucket in slots[index]:
            if subject not in used and bucket not in buckets:
                found=assign(index+1,used|{subject},buckets|{bucket})
                if found is not None: return found
        return None
    return assign(0,set(),set())


def matches(groups, available):
    return allocation(groups,available) is not None


def describe(groups):
    return '; '.join(f'{g["count"]} from [' + ', '.join(' / '.join(o) for o in g['options']) + ']'
                     for g in groups)


def validate_criteria(value, subjects):
    if not isinstance(value, dict):
        raise ValueError('Advanced criteria must be an object.')
    if not value:
        return value
    paths = value.get('credit_paths')
    if not isinstance(paths, list) or not 1 <= len(paths) <= 5:
        raise ValueError('Supply between one and five credit paths.')
    def groups_valid(groups):
        if not isinstance(groups, list) or not 1 <= len(groups) <= 9:
            raise ValueError('Each selection requires 1–9 groups.')
        total = 0
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError('Invalid subject group.')
            count, options = group.get('count'), group.get('options')
            if not isinstance(group.get('label', ''), str) or len(group.get('label', '')) > 250:
                raise ValueError('Group labels must be text of at most 250 characters.')
            if type(count) is not int or not 1 <= count <= 9 or not isinstance(options, list) or not count <= len(options) <= 80:
                raise ValueError('Invalid selection count or subject options.')
            for option in options:
                if not isinstance(option, list) or not 1 <= len(option) <= 10 or any(not isinstance(s, str) or s not in subjects for s in option) or len(set(option)) != len(option):
                    raise ValueError('Invalid subject alternative.')
            total += count
        if total > 9:
            raise ValueError('A selection cannot require more than nine subjects.')
    for path in paths:
        groups_valid(path)
        if sum(g['count'] for g in path) != 5:
            raise ValueError('Compendium credit paths must select five distinct subjects.')
    for key in ['jamb_groups', 'pass_groups']:
        groups = value.get(key)
        if not isinstance(groups, list):
            raise ValueError(f'{key} must be a list.')
        if groups:
            groups_valid(groups)
    for key in ['review_notes', 'advisories']:
        items = value.get(key, [])
        if not isinstance(items, list) or len(items) > 20 or any(not isinstance(s, str) or len(s) > 2000 for s in items):
            raise ValueError(f'Invalid {key}.')
    for key in ['programme', 'school', 'source_text']:
        if not isinstance(value.get(key, ''), str) or len(value.get(key, '')) > 30000:
            raise ValueError(f'Invalid {key}.')
    if 'source_row' in value and (type(value['source_row']) is not int or not 1 <= value['source_row'] <= 28):
        raise ValueError('Source row must be between 1 and 28.')
    if 'cutoff_source' in value:
        source = value['cutoff_source']
        if not isinstance(source, dict) or type(source.get('score')) is not int or not 0 <= source['score'] <= 400 or any(not isinstance(source.get(k), str) for k in ['session', 'url']):
            raise ValueError('Invalid cutoff source.')
        if not source['url'].startswith('https://'):
            raise ValueError('Cutoff source must use an HTTPS URL.')
    utme_count = sum(g['count'] for g in value['jamb_groups'])
    if utme_count > 4 or (utme_count != 4 and not value.get('review_notes')):
        raise ValueError('Specify four UTME subjects or document the unresolved combination.')
    return value


def assess(criteria, best, jamb_subjects, confirmed, check, unresolved_subjects=(), check_utme=True):
    from .domain import GRADES, PENDING_GRADES
    credits = {s for s, grade in best.items() if grade in GRADES[:6]}
    possible = credits | {s for s, grade in best.items() if grade in PENDING_GRADES} | set(unresolved_subjects)
    paths = criteria['credit_paths']
    passed = any(matches(path, credits) for path in paths)
    pending = not confirmed or any(matches(path, possible) for path in paths)
    check('Programme credit combination', 'passed' if passed else 'pending' if pending else 'failed',
          ('Five distinct permitted credits found. ' if passed else 'Required combination not met. ') +
          ' OR '.join(describe(path) for path in paths))
    for group in criteria['pass_groups']:
        passed = matches([group], {s for s, g in best.items() if g in GRADES[:8]})
        pending = not confirmed or matches([group], {s for s, g in best.items() if g in GRADES[:8] + PENDING_GRADES} | set(unresolved_subjects))
        check(group.get('label', 'Additional pass'), 'passed' if passed else 'pending' if pending else 'failed',
              describe([group]) + '; E8 or above required. A credit also satisfies a pass.')
    if check_utme:
        valid = len(jamb_subjects) == 4 and len(set(jamb_subjects)) == 4
        groups = criteria['jamb_groups']
        complete_rule = sum(g['count'] for g in groups) == 4
        status = ('pending' if not valid or not complete_rule else
                  'passed' if matches(groups, set(jamb_subjects)) else 'failed')
        check('JAMB subject combination', status,
              ('Submitted: ' + ', '.join(jamb_subjects) + '. ' if jamb_subjects else 'Enter the four UTME subjects. ') + describe(groups))
    for note in criteria.get('review_notes', []):
        check('Compendium clarification required', 'pending', note)
    for note in criteria.get('advisories', []):
        check('Advisory (not compulsory)', 'passed', note)
