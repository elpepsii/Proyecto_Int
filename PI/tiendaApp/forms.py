"""
forms.py — Formularios de tiendaApp.

ModelForm: Django genera los campos a partir del modelo. Solo declaramos
CUÁLES campos y CÓMO se muestran (widgets). La validación de choices,
longitudes y nulos la hace gratis el modelo.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Cliente, Ficha, Vendedor


# ----------------------------------------------------------- Ficha mascota
class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            'nombre',
            'edad',
            'especie',
            'alergias',
            'favoritos',               # M2M con Preferencia (catálogo del admin)
            'tamano_grano_preferido',
        ]
        widgets = {
            # LAS CASILLAS que querías: cada Preferencia/Alergia del catálogo
            # aparece como checkbox para marcar varias a la vez.
            'favoritos': forms.CheckboxSelectMultiple,
            'alergias': forms.CheckboxSelectMultiple,
        }
        labels = {
            'favoritos': 'Preferencias de alimentación',
            'tamano_grano_preferido': 'Tamaño de grano preferido (opcional)',
        }


# ------------------------------------------------- Registro de clientes (RF-07)
class RegistroForm(UserCreationForm):
    """Registro SOLO para clientes (RF-07): crea el User de Django y, en la
    vista, su perfil Cliente asociado. Los vendedores NO se registran aquí:
    los crea el administrador (RF-12).

    UserCreationForm ya trae username + password1/password2, valida que las
    contraseñas coincidan y aplica los validadores del settings
    (RNF-12: Django las guarda hasheadas, nunca en texto plano)."""

    first_name = forms.CharField(label='Nombre')
    apellido = forms.CharField(max_length=40)
    email = forms.EmailField(label='Correo')
    telefono = forms.CharField(max_length=20, required=False)
    direccion = forms.CharField(max_length=250, label='Dirección de despacho')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'email']


# ------------------------------------------------------- Perfil del cliente
class PerfilForm(forms.ModelForm):
    """Edición de los datos del cliente: mezcla campos del User (nombre,
    correo) con los del perfil Cliente (apellido, teléfono, dirección)."""

    first_name = forms.CharField(label='Nombre')
    email = forms.EmailField(label='Correo')

    class Meta:
        model = Cliente
        fields = ['apellido', 'telefono', 'direccion']
        labels = {
            'apellido': 'Apellido',
            'telefono': 'Teléfono',
            'direccion': 'Dirección de despacho',
        }


# ------------------------------------------------------ Checkout (RF-06)
class CheckoutForm(forms.Form):
    """Datos de la venta web: entrega y documento. El total NO se pregunta:
    lo calcula Venta.agregar_producto() con el precio vigente."""

    tipo_entrega = forms.ChoiceField(
        label='Tipo de entrega',
        choices=[('despacho', 'Despacho a domicilio'),
                 ('retiro', 'Retiro en tienda')],
        widget=forms.RadioSelect,
        initial='despacho',
    )
    direccion = forms.CharField(
        max_length=250, label='Dirección de entrega', required=False,
        help_text='Se usa solo si eliges despacho.',
    )
    tipo_documento = forms.ChoiceField(
        label='Documento',
        choices=[('boleta', 'Boleta'), ('factura', 'Factura')],
        widget=forms.RadioSelect,
        initial='boleta',
    )
    rut_factura = forms.CharField(
        max_length=20, required=False, label='RUT de facturación')
    razon_social = forms.CharField(
        max_length=100, required=False, label='Razón social')

    def clean(self):
        """Reglas cruzadas: factura exige RUT y razón social; si es retiro,
        la dirección no importa."""
        datos = super().clean()
        if datos.get('tipo_documento') == 'factura':
            if not datos.get('rut_factura') or not datos.get('razon_social'):
                raise forms.ValidationError(
                    'Para factura debes indicar RUT y razón social.')
        if datos.get('tipo_entrega') == 'despacho' and not datos.get('direccion'):
            raise forms.ValidationError(
                'Indica la dirección de entrega para el despacho.')
        return datos


# --------------------------------------------------- Venta POS (RF-18)
class POSVentaForm(forms.Form):
    """Datos de la venta presencial que NO son productos (las cantidades
    llegan como inputs 'cant_<id>' que la vista lee directamente)."""

    MEDIO = [('efectivo', 'Efectivo'),
             ('debito', 'Tarjeta de débito'),
             ('credito', 'Tarjeta de crédito')]

    medio_pago = forms.ChoiceField(label='Medio de pago', choices=MEDIO,
                                   widget=forms.RadioSelect,
                                   initial='efectivo')
    tipo_documento = forms.ChoiceField(
        label='Documento',
        choices=[('boleta', 'Boleta'), ('factura', 'Factura')],
        widget=forms.RadioSelect, initial='boleta')
    rut_factura = forms.CharField(max_length=20, required=False,
                                  label='RUT (solo factura)')
    razon_social = forms.CharField(max_length=100, required=False,
                                   label='Razón social (solo factura)')
    # Cliente opcional: si el comprador tiene cuenta, se asocia la venta
    # (basta el correo con el que se registró). Vacío = consumidor final.
    correo_cliente = forms.EmailField(required=False,
                                      label='Correo del cliente (opcional)')

    def clean(self):
        datos = super().clean()
        if (datos.get('tipo_documento') == 'factura'
                and not datos.get('rut_factura')):
            raise forms.ValidationError(
                'Para factura debes indicar el RUT.')
        return datos


# --------------------------------------- Crear vendedor (RF-12, solo admin)
class VendedorForm(forms.ModelForm):
    """El administrador crea la cuenta del vendedor (RF-12). El User de
    acceso se crea en la vista junto con el perfil Vendedor."""

    username = forms.CharField(label='Nombre de usuario')
    first_name = forms.CharField(label='Nombre')
    password = forms.CharField(
        label='Contraseña inicial', widget=forms.PasswordInput,
        help_text='El vendedor podrá cambiarla luego.')

    class Meta:
        model = Vendedor
        fields = ['cargo', 'sueldo', 'horario', 'telefono']
        labels = {
            'cargo': 'Cargo',
            'sueldo': 'Sueldo (CLP)',
            'horario': 'Horario',
            'telefono': 'Teléfono',
        }
