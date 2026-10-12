from django.http import JsonResponse


class AuthenticationRequiredMiddleware:
    """Deny API access by default, including future screening endpoints."""
    public_paths = {'/api/session/', '/api/login/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            if request.path not in self.public_paths and not request.user.is_authenticated:
                response = JsonResponse({'error': 'Sign in to use the screening system.'}, status=401)
            else:
                response = self.get_response(request)
            response['Cache-Control'] = 'no-store'
            return response
        return self.get_response(request)
