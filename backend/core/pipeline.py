from rest_framework.authtoken.models import Token


def create_auth_token(user, **kwargs):
    """PSA pipeline step: ensure a DRF token exists for the user."""
    Token.objects.get_or_create(user=user)
