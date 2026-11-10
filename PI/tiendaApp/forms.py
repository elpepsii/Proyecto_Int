import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Cliente, Entrega, Ficha, MedioPago, Preferencia, Vendedor, Venta


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
            'favoritos': forms.CheckboxSelectMultiple,
            'alergias': forms.CheckboxSelectMultiple,
        }
        labels = {
            'favoritos': 'Preferencias de alimentación',
            'tamano_grano_preferido': 'Tamaño de grano preferido (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campo = self.fields['favoritos']
        titulos = {
            Preferencia.Categoria.TIPO_ALIMENTO: 'Tipo de alimento',
            Preferencia.Categoria.PROTEINA: 'Sabor o proteína',
        }
        grupos = {categoria: [] for categoria in titulos}
        for valor, etiqueta in campo.choices:
            grupos.setdefault(valor.instance.categoria, []).append((valor, etiqueta))
        campo.widget.choices = [
            (titulos.get(categoria, 'Otras preferencias'), opciones)
            for categoria, opciones in grupos.items()
        ]
        campo.widget.template_name = 'tiendaApp/preferencias_checkbox.html'


def generar_username(correo):
    base = re.sub(r'[^a-zA-Z0-9_.+-]', '', correo.split('@')[0].lower()) or 'cliente'
    username = base
    n = 2
    while User.objects.filter(username__iexact=username).exists():
        username = f'{base}{n}'
        n += 1
    return username


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre')
    apellido = forms.CharField(max_length=40, label='Apellido')
    email = forms.EmailField(label='Correo')
    telefono = forms.CharField(max_length=20, required=False, label='Teléfono')
    direccion = forms.CharField(max_length=250, label='Dirección de despacho')

    field_order = [
        'first_name',
        'apellido',
        'email',
        'telefono',
        'direccion',
        'password1',
        'password2',
    ]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)

    def clean_email(self):
        correo = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=correo).exists():
            raise forms.ValidationError(
                'Ya existe una cuenta con ese correo. Inicia sesión o usa otro.'
            )
        return correo

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = generar_username(self.cleaned_data['email'])
        user.last_name = self.cleaned_data['apellido']
        if commit:
            user.save()
        return user


class EntrarForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'No encontramos una cuenta con esos datos. '
        'Revisa tu correo y contraseña e inténtalo de nuevo.',
        'inactive': 'Esta cuenta está desactivada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo electrónico o usuario'


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre')
    email = forms.EmailField(label='Correo')

    field_order = ['first_name', 'apellido', 'email', 'telefono', 'direccion']

    class Meta:
        model = Cliente
        fields = ['apellido', 'telefono', 'direccion']
        labels = {
            'apellido': 'Apellido',
            'telefono': 'Teléfono',
            'direccion': 'Dirección de despacho',
        }

    def clean_email(self):
        correo = self.cleaned_data['email'].strip().lower()
        otras = User.objects.exclude(pk=self.instance.usuario_auth_id)
        if otras.filter(email__iexact=correo).exists():
            raise forms.ValidationError('Ese correo ya está en otra cuenta.')
        return correo


def normalizar_rut(valor):
    rut = (valor or '').strip().upper().replace('.', '').replace('-', '')

    if not re.fullmatch(r'\d{7,8}[\dK]', rut):
        raise forms.ValidationError(
            'RUT inválido. Usa el formato 12.345.678-5 (7 u 8 dígitos más el dígito verificador).'
        )

    cuerpo, dv = rut[:-1], rut[-1]
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    dv_calculado = '0' if resto == 11 else ('K' if resto == 10 else str(resto))
    if dv != dv_calculado:
        raise forms.ValidationError(
            f'El dígito verificador no corresponde: el RUT {cuerpo} '
            f'termina en -{dv_calculado}, no en -{dv}.'
        )

    rev = cuerpo[::-1]
    con_puntos = '.'.join(rev[i : i + 3] for i in range(0, len(rev), 3))[::-1]
    return f'{con_puntos}-{dv}'


class DocumentoVentaForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        label='Documento',
        choices=Venta.TipoDocumento.choices,
        widget=forms.RadioSelect,
        initial=Venta.TipoDocumento.BOLETA,
    )
    rut_factura = forms.CharField(
        max_length=20,
        required=False,
        label='RUT de facturación',
        help_text='Formato: 12.345.678-5 (se valida el dígito verificador).',
    )
    razon_social = forms.CharField(max_length=100, required=False, label='Razón social')

    def clean_rut_factura(self):
        valor = self.cleaned_data['rut_factura']
        return normalizar_rut(valor) if valor else valor

    def clean(self):
        datos = super().clean()
        if datos.get('tipo_documento') == Venta.TipoDocumento.FACTURA:
            if not datos.get('rut_factura') or not datos.get('razon_social'):
                raise forms.ValidationError('Para factura debes indicar RUT y razón social.')
        return datos


class CheckoutForm(DocumentoVentaForm):
    field_order = ['tipo_entrega', 'direccion']

    tipo_entrega = forms.ChoiceField(
        label='Tipo de entrega',
        choices=Entrega.TipoEntrega.choices,
        widget=forms.RadioSelect,
        initial=Entrega.TipoEntrega.DESPACHO,
    )
    direccion = forms.CharField(
        max_length=250,
        label='Dirección de entrega',
        required=False,
        help_text='Se usa solo si eliges despacho.',
    )

    def clean(self):
        datos = super().clean()
        if datos.get('tipo_entrega') == Entrega.TipoEntrega.DESPACHO and not datos.get('direccion'):
            raise forms.ValidationError('Indica la dirección de entrega para el despacho.')
        return datos


class POSVentaForm(DocumentoVentaForm):
    field_order = ['medio_pago']

    medio_pago = forms.ChoiceField(
        label='Medio de pago',
        choices=[
            (MedioPago.EFECTIVO, 'Efectivo'),
            (MedioPago.DEBITO, 'Tarjeta de débito'),
            (MedioPago.CREDITO, 'Tarjeta de crédito'),
        ],
        widget=forms.RadioSelect,
        initial=MedioPago.EFECTIVO,
    )
    rut_factura = forms.CharField(max_length=20, required=False, label='RUT (solo factura)')
    razon_social = forms.CharField(
        max_length=100, required=False, label='Razón social (solo factura)'
    )
    correo_cliente = forms.EmailField(required=False, label='Correo del cliente (opcional)')


class VendedorForm(forms.ModelForm):
    username = forms.CharField(label='Nombre de usuario')
    first_name = forms.CharField(label='Nombre')
    password = forms.CharField(
        label='Contraseña inicial',
        widget=forms.PasswordInput,
        help_text='El vendedor podrá cambiarla luego.',
    )

    class Meta:
        model = Vendedor
        fields = ['cargo', 'sueldo', 'horario', 'telefono']
        labels = {
            'cargo': 'Cargo',
            'sueldo': 'Sueldo (CLP)',
            'horario': 'Horario',
            'telefono': 'Teléfono',
        }
