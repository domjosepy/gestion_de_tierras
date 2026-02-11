import sys


class CSRFDebugMiddleware:
    """Middleware temporal para depurar problemas de CSRF en /login/.

    Imprime en la salida estándar el token enviado en el formulario y la
    cookie `csrftoken` para ayudar a identificar desajustes.
    El archivo puede eliminarse una vez terminado el debugging.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.path == '/login/' and request.method == 'POST':
                post_token = request.POST.get('csrfmiddlewaretoken')
                cookie_token = request.COOKIES.get('csrftoken')
                referer = request.META.get('HTTP_REFERER')
                host = request.META.get('HTTP_HOST')
                print('\n[CSRFDebug] POST to /login/ detected')
                print(f'[CSRFDebug] POST csrfmiddlewaretoken: {post_token}')
                print(f'[CSRFDebug] Cookie csrftoken: {cookie_token}')
                print(f'[CSRFDebug] Referer: {referer} Host: {host}\n')
        except Exception as e:
            print('[CSRFDebug] Error reading request tokens:', e, file=sys.stderr)

        return self.get_response(request)
