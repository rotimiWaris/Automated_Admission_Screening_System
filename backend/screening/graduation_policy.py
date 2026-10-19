"""Configured HND graduation waiting periods (not verification of IT)."""
import calendar
import re
from datetime import date, datetime
from django.utils import timezone


def graduation_check(value, years, today=None):
    today = today or timezone.localdate()
    raw = str(value or '').strip()
    label = 'ND graduation waiting period'
    def check(state, detail):
        return {'label': label, 'status': state, 'detail': detail}
    if not raw:
        return check('failed', 'ND graduation date/year is required.')
    if re.fullmatch(r'\d{4}', raw):
        year = int(raw)
        if not 1900 <= year <= today.year:
            return check('pending', 'Graduation year is invalid or in the future.')
        elapsed = today.year - year
        return check('passed' if elapsed >= years else 'pending',
            f'{elapsed} calendar year(s) since graduation; {years} required. Processing date: {today.isoformat()}. '
            + ('Year-only assessment.' if elapsed >= years else 'Supply a full graduation date to assess the two-month allowance.'))
    graduated = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S'):
        try:
            graduated = datetime.strptime(raw, fmt).date()
            break
        except ValueError:
            pass
    if graduated is None or graduated > today or graduated.year < 1900:
        return check('pending', 'Invalid or future graduation date. Supply YYYY-MM-DD or DD/MM/YYYY.')
    anniversary = date(graduated.year+years, graduated.month,
                       min(graduated.day, calendar.monthrange(graduated.year+years, graduated.month)[1]))
    month_index = anniversary.year*12 + anniversary.month-1-2
    year, month = divmod(month_index, 12)
    month += 1
    earliest = date(year, month, min(anniversary.day, calendar.monthrange(year, month)[1]))
    state = 'passed' if today >= earliest else 'pending'
    return check(state, f'{years}-year anniversary: {anniversary.isoformat()}; two-month allowance begins {earliest.isoformat()}; processing date: {today.isoformat()}. '
                 + ('Waiting period met.' if today >= anniversary else 'Within the two-month allowance.' if state == 'passed' else 'More than two months remain; review required.'))
