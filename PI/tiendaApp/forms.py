"""
forms.py — Formularios de tiendaApp.

ModelForm: Django genera los campos a partir del modelo. Solo declaramos
CUÁLES campos y CÓMO se muestran (widgets). La validación de choices,
longitudes y nulos la hace gratis el modelo.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Cliente, Ficha


# ----------------------------------------------------------- Ficha mascota
class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'nombre',
            'edad',
            'especie',
            'alergias',
            'favoritos',
            'tamano_grano_preferido',
        ]
        widgets = {
            # LAS CASILLAS: cada Preferencia del catálogo (cargada desde el
            # admin) aparece como checkbox para marcar varias a la vez.
            'favoritos': forms.CheckboxSelectMultiple,
            'alergias': forms.CheckboxSelectMultiple,
        }
        labels = {
            'favoritos': 'Preferencias de alimentación',
            'tamano_grano_preferido': 'Tamaño de grano preferido (opcional)',
        }


# ------------------------------------------------- Registro de clientes (RF-07)
class RegistroForm(UserCreationForm):
    """Registro de cliente: crea el User de Django y, en la vista, su perfil
    Cliente asociado. UserCreationForm ya trae username + password1/password2
    y valida que las contraseñas coincidan y cumplan los validadores del
    settings (RNF-12: Django las guarda hasheadas, nunca en texto plano)."""

    first_name = forms.CharField(label='Nombre')
    apellido = forms.CharField(max_length=40)
    email = forms.EmailField(label='Correo')
    telefono = forms.CharField(max_length=20, required=False)
    direccion = forms.CharField(max_length=250, label='Dirección de despacho')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'email']
