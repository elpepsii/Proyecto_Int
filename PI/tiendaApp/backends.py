from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class CorreoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        correo = username.strip()
        if '@' not in correo:
            return None

        for user in User.objects.filter(email__iexact=correo):
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
