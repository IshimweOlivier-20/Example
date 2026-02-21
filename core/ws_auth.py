"""
JWT authentication middleware for Channels.
"""
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JwtAuthMiddleware(BaseMiddleware):
    """Populate scope.user from JWT token in query string or header."""

    async def __call__(self, scope, receive, send):
        token = None

        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        if 'token' in query_params:
            token = query_params['token'][0]

        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization')
            if auth_header and auth_header.startswith(b'Bearer '):
                token = auth_header.split(b' ')[1].decode()

        scope['user'] = await get_user_from_token(token)
        return await super().__call__(scope, receive, send)


@database_sync_to_async
def get_user_from_token(token):
    if not token:
        return AnonymousUser()

    try:
        access = AccessToken(token)
        user_id = access.get('user_id')
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


def JwtAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
