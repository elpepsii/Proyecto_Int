"""
forms.py — Formularios de tiendaApp.

ModelForm: Django genera los campos a partir del modelo. Solo declaramos
CUÁLES campos y CÓMO se muestran (widgets). La validación de choices,
longitudes y nulos la hace gratis el modelo.
"""

from django import forms

from .models import Ficha


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'nombre',
            'edad',
            'especie',
            'alergias',
            'favoritos',               # M2M con Preferencia (requiere la corrección del models.py)
            'tamano_grano_preferido',
        ]
        widgets = {
            # LAS CASILLAS que querías: cada Preferencia del catálogo
            # (cargada desde el admin) aparece como checkbox.
            'favoritos': forms.CheckboxSelectMultiple,
            'alergias': forms.CheckboxSelectMultiple,
        }
        labels = {
            'favoritos': 'Preferencias de alimentación',
            'tamano_grano_preferido': 'Tamaño de grano preferido (opcional)',
        }
