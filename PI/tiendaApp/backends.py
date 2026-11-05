"""
backends.py — Backend de autenticación por CORREO (RF-07).

Django, por defecto, solo autentica por 'username'. Este backend permite
entrar escribiendo el CORREO electrónico, que es como se registran los
clientes. Django prueba los backends de AUTHENTICATION_BACKENDS en orden:
el estándar (por username, para admin y demo) primero; si ninguno valida,
prueba este: si lo escrito parece un correo, lo busca por email.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class CorreoBackend(ModelBackend):
    """Autentica por correo electrónico (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        correo = username.strip()
        if '@' not in correo:
            # No parece un correo: lo atiende el backend estándar.
            return None

        for user in User.objects.filter(email__iexact=correo):
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None