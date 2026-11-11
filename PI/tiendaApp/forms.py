import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Value
from django.db.models.functions import Replace

from .models import Cliente, Entrega, Ficha, MedioPago, Preferencia, Proveedor, Vendedor, Venta


class ProveedorProductoForm(forms.Form):
    producto_id = forms.IntegerField(min_value=1)
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.all(), required=False)


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


def normalizar_rut(valor):
    rut = (valor or '').upper()

    if not re.fullmatch(r'[0-9]{7,8}-[0-9K]', rut):
        raise forms.ValidationError(
            'Ingresa el RUT sin puntos y con guion. Ejemplo: 12345678-5.'
        )

    cuerpo, dv = rut.split('-')
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

    return rut


class RutField(forms.CharField):
    def __init__(self, **kwargs):
        super().__init__(
            strip=False,
            max_length=20,
            help_text='Sin puntos y con guion. Puedes usar K como dígito verificador.',
            widget=forms.TextInput(attrs={'placeholder': 'Ej: 12345678-5'}),
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        return normalizar_rut(value) if value else value


class TelefonoField(forms.CharField):
    def __init__(self, **kwargs):
        super().__init__(
            label='Teléfono',
            strip=False,
            max_length=20,
            help_text='Ingresa +56, un espacio y 9 dígitos.',
            widget=forms.TextInput(attrs={
                'type': 'tel', 'autocomplete': 'tel', 'placeholder': 'Ej: +56 912345678',
            }),
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        if value and not re.fullmatch(r'\+56 [0-9]{9}', value):
            raise forms.ValidationError('Usa el formato +56 912345678.')
        return value


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre')
    apellido = forms.CharField(max_length=40, label='Apellido')
    email = forms.EmailField(label='Correo')
    telefono = TelefonoField(required=False)
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
    telefono = TelefonoField(required=False)
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


def validar_datos_factura(datos):
    if datos.get('tipo_documento') == Venta.TipoDocumento.FACTURA:
        if not datos.get('rut_factura') or not datos.get('razon_social'):
            raise forms.ValidationError('Para factura debes indicar RUT y razón social.')
    return datos


class DocumentoVentaForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        label='Documento',
        choices=Venta.TipoDocumento.choices,
        widget=forms.RadioSelect,
        initial=Venta.TipoDocumento.BOLETA,
    )
    rut_factura = RutField(required=False, label='RUT de facturación')
    razon_social = forms.CharField(max_length=100, required=False, label='Razón social')

    def clean(self):
        return validar_datos_factura(super().clean())


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
    rut_factura = RutField(required=False, label='RUT (solo factura)')
    razon_social = forms.CharField(
        max_length=100, required=False, label='Razón social (solo factura)'
    )
    correo_cliente = forms.EmailField(required=False, label='Correo del cliente (opcional)')


class DatosVendedorForm(forms.ModelForm):
    DIAS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')
    dias_laborales = forms.MultipleChoiceField(
        label='Días laborales',
        choices=[(dia, dia) for dia in DIAS],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dias-laborales'}),
    )

    class Meta:
        model = Vendedor
        fields = ['cargo', 'sueldo', 'dias_laborales', 'telefono']
        labels = {
            'cargo': 'Cargo',
            'sueldo': 'Sueldo (CLP)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        horario = self.instance.horario
        if horario:
            dias = [dia.strip() for dia in horario.split(',')]
            if all(dia in self.DIAS for dia in dias):
                self.initial['dias_laborales'] = dias
            else:
                campo = self.fields['dias_laborales']
                campo.required = False
                campo.help_text = f'Horario anterior: {horario}. Marca los días si quieres actualizarlo.'

    def save(self, commit=True):
        dias = self.cleaned_data['dias_laborales']
        if dias:
            self.instance.horario = ', '.join(dia for dia in self.DIAS if dia in dias)
        return super().save(commit=commit)


class EditarVendedorForm(DatosVendedorForm):
    field_order = ['first_name', 'last_name', 'username', 'password']
    first_name = forms.CharField(label='Nombre', max_length=150, required=False)
    last_name = forms.CharField(label='Apellido', max_length=150, required=False)
    telefono = TelefonoField(required=False)


class VendedorForm(EditarVendedorForm):
    username = forms.CharField(label='Nombre de usuario', max_length=150)
    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellido', max_length=150)
    telefono = TelefonoField()
    password = forms.CharField(label='Contraseña inicial', widget=forms.PasswordInput)


class VendedorAdminForm(DatosVendedorForm):
    class Meta(DatosVendedorForm.Meta):
        fields = ['usuario_auth', *DatosVendedorForm.Meta.fields]


class ProveedorForm(forms.ModelForm):
    run_empresa = RutField(required=False, label='RUT de la empresa')
    fono = TelefonoField()

    class Meta:
        model = Proveedor
        fields = ['nombre', 'run_empresa', 'correo', 'fono']

    def clean_run_empresa(self):
        rut = self.cleaned_data['run_empresa']
        if not rut:
            return None
        proveedores = Proveedor.objects.exclude(pk=self.instance.pk).alias(
            rut_sin_separadores=Replace(Replace('run_empresa', Value('.')), Value('-')),
        )
        if proveedores.filter(rut_sin_separadores__iexact=rut.replace('-', '')).exists():
            raise forms.ValidationError('Ya existe un proveedor con ese RUT.')
        return rut


class ProveedorAdminForm(ProveedorForm):
    class Meta(ProveedorForm.Meta):
        fields = [*ProveedorForm.Meta.fields, 'productos']


class VentaAdminForm(forms.ModelForm):
    rut_factura = RutField(required=False, label='RUT de facturación')

    class Meta:
        model = Venta
        fields = '__all__'

    def clean(self):
        return validar_datos_factura(super().clean())
