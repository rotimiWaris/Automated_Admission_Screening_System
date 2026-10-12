"""Exercise the running API through Django directly or the Vite proxy.

Usage: python scripts/smoke_http.py http://127.0.0.1:5173
Uses synthetic input and does not save student records.
"""
import http.cookiejar
import json
import sys
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5173').rstrip('/')
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def request(path, data=None, csrf=None):
    headers = {'Content-Type': 'application/json', 'Origin': base}
    if csrf:
        headers['X-CSRFToken'] = csrf
    req = urllib.request.Request(base + '/api/' + path + '/', data=None if data is None else json.dumps(data).encode(), headers=headers)
    with client.open(req, timeout=15) as response:
        return json.load(response)

session = request('session')
rules = request('rules')['rules']
rule = next(r for r in rules if r['active'])
subjects = list(dict.fromkeys([s['subject'] for s in rule['required_subjects']] + ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Economics', 'Geography', 'Commerce', 'Government']))[:9]
payload = {'rule_id': rule['id'], 'rule_revision': rule['revision'], 'student_name': 'Synthetic HTTP Smoke Test', 'registration_number': 'DEMO-HTTP', 'jamb_score': 400, 'confirmed': True, 'save': False, 'sittings': [{'board': 'WAEC', 'exam_type': 'School', 'year': 2026, 'subjects': [{'subject': s, 'grade': 'A1'} for s in subjects]}]}
result = request('screen', payload, session['csrf'])
assert result['status'] == 'Eligible', result
assert 'id' not in result, 'Smoke test must not save history.'
payload['jamb_score'] = None
result = request('screen', payload, session['csrf'])
assert result['status'] == 'Pending Review', result
print('HTTP smoke passed: session cookie, CSRF, rule retrieval, eligible and pending screening, no saved records.')
