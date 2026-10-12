import json
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.db import transaction, OperationalError
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .domain import EXAM_BOARDS, EXAMINATIONS, GRADES, PENDING_GRADES, SUBJECTS, evaluate, validate_rules
from .models import RuleSet, Verification
from .identities import registration_key

def api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (ValueError, UnicodeDecodeError) as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except RuleSet.DoesNotExist:
            return JsonResponse({'error': 'Rule set not found.'}, status=404)
        except OperationalError as exc:
            if 'locked' not in str(exc).lower() and 'busy' not in str(exc).lower():
                raise
            response = JsonResponse({'error': 'The database is busy saving another request. Wait a few seconds and try again. Existing screenings will not be duplicated.'}, status=503)
            response['Retry-After'] = '3'
            return response
    return wrapped

def body(request):
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    return data

def user_data(user):
    return {'username': user.username, 'is_staff': user.is_staff} if user.is_authenticated else None

def staff_required(request):
    return request.user.is_authenticated and request.user.is_staff

@require_GET
def session(request):
    return JsonResponse({'csrf': get_token(request), 'user': user_data(request.user)})

@require_POST
@api
def login_view(request):
    data = body(request)
    if not all(isinstance(data.get(k), str) for k in ['username', 'password']):
        raise ValueError('Enter a username and password.')
    user = authenticate(request, username=data['username'], password=data['password'])
    if user is None:
        return JsonResponse({'error': 'Incorrect username or password.'}, status=401)
    login(request, user)
    return JsonResponse({'csrf': get_token(request), 'user': user_data(user)})

@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'csrf': get_token(request), 'user': None})

@require_GET
def catalogue(request):
    return JsonResponse({'subjects': SUBJECTS, 'grades': GRADES + PENDING_GRADES, 'boards': EXAM_BOARDS, 'examinations': EXAMINATIONS})

@require_http_methods(['GET', 'POST'])
@api
def rules(request):
    if request.method == 'GET':
        query = RuleSet.objects.all() if staff_required(request) else RuleSet.objects.filter(active=True)
        return JsonResponse({'rules': [rule.snapshot() for rule in query.order_by('programme', 'id')]})
    if not staff_required(request):
        return JsonResponse({'error': 'Staff sign-in required to edit rules.'}, status=403)
    rule = RuleSet.objects.create(**validate_rules(body(request)))
    return JsonResponse(rule.snapshot(), status=201)

@require_http_methods(['PUT'])
@api
def rule_detail(request, pk):
    if not staff_required(request):
        return JsonResponse({'error': 'Staff sign-in required to edit rules.'}, status=403)
    data = body(request)
    values = validate_rules(data)
    with transaction.atomic():
        # Conditional update prevents a stale browser from overwriting newer rules.
        if type(data.get('revision')) is not int:
            raise ValueError('A valid rule revision is required.')
        updated = RuleSet.objects.filter(pk=pk, revision=data['revision']).update(**values, revision=data['revision'] + 1, updated_at=timezone.now())
        if not updated:
            if not RuleSet.objects.filter(pk=pk).exists():
                raise RuleSet.DoesNotExist
            return JsonResponse({'error': 'These rules changed elsewhere. Reload them before editing.'}, status=409)
        return JsonResponse(RuleSet.objects.get(pk=pk).snapshot())

@require_POST
@api
def screen(request):
    data = body(request)
    if type(data.get('rule_id')) is not int:
        raise ValueError('Select a programme and rule set.')
    if type(data.get('save')) is not bool:
        raise ValueError('Save must be true or false.')
    rule = RuleSet.objects.get(pk=data['rule_id'], active=True)
    if data.get('rule_revision') != rule.revision:
        return JsonResponse({'error': 'The selected rules changed. Reload programmes and screen again.'}, status=409)
    from .age_policy import apply_age_policy
    result = apply_age_policy(evaluate(rule, data), data)
    if request.user.is_authenticated and not data['save']:
        key = registration_key(result['student']['registration_number'])
        previous = Verification.objects.filter(owner=request.user, registration_key=key).first() if key else None
        if previous:
            result['duplicate_notice'] = f'This student is already saved as screening #{previous.id}. Re-screening will not create another history record.'
    if data['save']:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Sign in to save screening history.'}, status=401)
        key = registration_key(result['student']['registration_number'])
        if not key:
            raise ValueError('Enter a valid registration number before saving.')
        record, created = Verification.objects.get_or_create(owner=request.user, registration_key=key, defaults={'result': result})
        if not created:
            return JsonResponse({'error': f'This student is already saved as screening #{record.id}. No duplicate was stored.', 'existing_id': record.id}, status=409)
        result = result | {'id': record.id, 'created_at': record.created_at.isoformat()}
    return JsonResponse(result)

@require_GET
@api
def history(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in to view your history.'}, status=401)
    try:
        number = int(request.GET.get('page', '1'))
    except ValueError:
        raise ValueError('Page must be a positive whole number.')
    if number < 1:
        raise ValueError('Page must be a positive whole number.')
    query = request.GET.get('q', '').strip()[:150]
    records = Verification.objects.filter(owner=request.user)
    if query:
        tag = ' '.join(query.casefold().removeprefix('status:').strip().removeprefix('#').replace('-', ' ').split())
        statuses = {'pending': 'Pending Review', 'pending review': 'Pending Review',
                    'eligible': 'Eligible', 'qualified': 'Eligible',
                    'not eligible': 'Not Eligible', 'unqualified': 'Not Eligible', 'not qualified': 'Not Eligible'}
        if tag in statuses:
            # Exact status matching keeps "eligible" from including "not eligible".
            records = records.filter(result__status=statuses[tag])
        else:
            records = records.filter(Q(result__student__name__icontains=query) | Q(result__student__registration_number__icontains=query) | Q(result__rules__programme__icontains=query))
    paginator = Paginator(records.order_by('-created_at', '-id'), 50)
    page = paginator.get_page(number)
    return JsonResponse({'history': [record.result | {'id': record.id, 'created_at': record.created_at.isoformat()} for record in page],
                         'page': page.number, 'page_size': 50, 'count': paginator.count, 'num_pages': paginator.num_pages})
