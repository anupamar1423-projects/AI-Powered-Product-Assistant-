"""Header authentication for the private Streamlit merchandising client."""
import hmac
import os
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class StreamlitAPIKeyAuthentication(BaseAuthentication):
    """Validate an app-to-app bearer token and bind it to a named staff user."""
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None
        expected = os.getenv("STREAMLIT_API_TOKEN", "")
        if not expected or not hmac.compare_digest(parts[1], expected):
            raise AuthenticationFailed("Invalid Streamlit service token.")
        username = os.getenv("STREAMLIT_API_USER", "").strip()
        if not username:
            raise AuthenticationFailed("STREAMLIT_API_USER is not configured.")
        User = get_user_model()
        try:
            user = User.objects.get(username=username, is_staff=True, is_active=True)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("The configured Streamlit user must be an active staff account.") from exc
        return (user, None)

    def authenticate_header(self, request):
        return self.keyword
