import re


def registration_key(value):
    """JAMB identity ignores case, spacing and punctuation, never guesses a name."""
    return re.sub(r'[^A-Z0-9]', '', value.upper()) or None if isinstance(value, str) else None


def names_match(left, right):
    """Ignore case, order, punctuation and split/joined spelling, not letters."""
    import unicodedata
    from functools import lru_cache
    def tokens(value):
        return tuple(sorted(re.findall(r"[^\W\d_]+",unicodedata.normalize('NFKC',str(value or '')).casefold(),re.UNICODE)))
    a,b=tokens(left),tokens(right)
    if not a or not b: return False
    @lru_cache(maxsize=256)
    def match(a,b):
        if a==b:return True
        if not a or not b or sum(map(len,a))!=sum(map(len,b)):return False
        # Consume a longest token using exact prefix pieces on the other side.
        if max(map(len,a))<max(map(len,b)):return match(b,a)
        word=max(a,key=len);remaining=list(a);remaining.remove(word);remaining=tuple(remaining)
        def consume(rest,parts):
            if not rest:return match(remaining,parts)
            for index,part in enumerate(parts):
                if rest.startswith(part) and consume(rest[len(part):],parts[:index]+parts[index+1:]):return True
            return False
        return consume(word,b)
    return match(a,b)


def minor_name_typo(left, right):
    """One long name token, one edit/transposition, with another exact name token."""
    from collections import Counter
    import unicodedata
    def tokens(value):
        return Counter(re.findall(r"[^\W\d_]+",unicodedata.normalize('NFKC',str(value or '')).casefold()))
    a,b=tokens(left),tokens(right)
    shared=a&b
    x,y=list((a-b).elements()),list((b-a).elements())
    if not shared or len(x)!=1 or len(y)!=1:return False
    x,y=x[0],y[0]
    if min(len(x),len(y))<4 or abs(len(x)-len(y))>1:return False
    if len(x)==len(y):
        diff=[i for i in range(len(x)) if x[i]!=y[i]]
        return len(diff)==1 or (len(diff)==2 and diff[1]==diff[0]+1 and x[diff[0]]==y[diff[1]] and x[diff[1]]==y[diff[0]])
    if len(x)>len(y):x,y=y,x
    return any(y[:i]+y[i+1:]==x for i in range(len(y)))


def candidate_name_issues(expected, text, label='Olevel result', jamb_name='', smart_processing=False, warnings=None):
    issues=[]
    for candidate in re.findall(r'(?im)^\s*Candidate Name\s*:\s*([^\n\r]+)',text):
        if not names_match(candidate,expected) and not names_match(candidate,jamb_name):
            detail=f'{label}: candidate name "{candidate.strip()}" does not match applicant name "{expected}"'
            if str(jamb_name or '').strip():detail+=f' or Name on JAMB "{jamb_name}"'
            if smart_processing and (minor_name_typo(candidate,expected) or minor_name_typo(candidate,jamb_name)):
                if warnings is not None:warnings.append('Smart processing accepted a minor name typo. '+detail+'. Original names were retained.')
            else:
                issues.append(detail+'. Check surname, first name and other names.')
    return issues
