from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailAuthBackend(ModelBackend):
    """Authenticate using email instead of username"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username  # Since Django's authenticate() expects 'username' field
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
