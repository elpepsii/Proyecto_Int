from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.html import format_html

from .almacenamiento import ErrorAlmacenamiento
from .forms import (
    PreferenciaAdminForm,
    ProductoAdminForm,
    ProveedorAdminForm,
    TelefonoField,
    VendedorAdminForm,
    VentaAdminForm,
)
from .models import (
    Administrador,
    Alergia,
    Cliente,
    DetalleVenta,
    Entrega,
    Ficha,
    Informe,
    JornadaLaboral,
    Pago,
    Preferencia,
    Producto,
    Proveedor,
    Stock,
    Vendedor,
    Venta,
)


class StockInline(admin.StackedInline):
    model = Stock
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoAdminForm
    list_display = (
        'miniatura',
        'sku',
        'nombre',
        'precio',
        'precio_oferta',
        'tipo_producto',
        'tipo_alimento',
        'animal',
        'activo',
    )
    list_editable = ('precio_oferta', 'activo')
    list_filter = ('activo', 'tipo_producto', 'tipo_alimento', 'animal', 'edad_producto')
    search_fields = ('sku', 'nombre')
    filter_horizontal = ('alergenos_contenidos',)
    inlines = [StockInline]

    class Media:
        js = ('js/tipo-alimento-admin.js',)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except ErrorAlmacenamiento as error:
            self.message_user(request, str(error), level=messages.ERROR)
            return redirect(request.path)

    @admin.display(description='Foto')
    def miniatura(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="width:46px;height:46px;'
                'object-fit:cover;border-radius:8px" />',
                obj.imagen.url,
            )
        return '—'

    actions = ['desactivar_productos']

    @admin.action(description='Desactivar productos seleccionados (baja lógica)')
    def desactivar_productos(self, request, queryset):
        queryset.update(activo=False)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    form = ProveedorAdminForm
    list_display = ('nombre', 'run_empresa', 'correo', 'fono')
    search_fields = ('nombre', 'run_empresa')
    filter_horizontal = ('productos',)


@admin.register(Alergia)
class AlergiaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(Preferencia)
class PreferenciaAdmin(admin.ModelAdmin):
    form = PreferenciaAdminForm
    list_display = ('nombre', 'categoria', 'tipo_alimento')
    list_filter = ('categoria',)
    search_fields = ('nombre',)


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cliente', 'especie', 'edad')
    list_filter = ('especie',)
    search_fields = ('nombre', 'cliente__usuario_auth__username', 'cliente__apellido')
    filter_horizontal = ('alergias', 'favoritos')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario_auth', 'apellido', 'correo', 'telefono')
    search_fields = ('apellido', 'correo', 'usuario_auth__username')

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'telefono':
            return TelefonoField(required=False)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    form = VendedorAdminForm
    list_display = ('usuario_auth', 'cargo', 'horario', 'telefono', 'sueldo')
    search_fields = ('cargo', 'usuario_auth__username')

    def get_exclude(self, request, obj=None):
        return ('telefono',) if obj is None else super().get_exclude(request, obj)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'telefono':
            return TelefonoField(required=False)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            cliente = getattr(obj.usuario_auth, 'cliente_perfil', None)
            telefono = getattr(cliente, 'telefono', None) or ''
            if len(telefono) == 12 and telefono.startswith('+56'):
                telefono = f'+56 {telefono[3:]}'
            try:
                obj.telefono = TelefonoField(required=False).clean(telefono)
            except ValidationError:
                obj.telefono = ''
        super().save_model(request, obj, form, change)


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('usuario_auth',)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    form = VentaAdminForm
    list_display = ('id', 'origen', 'cliente', 'vendedor', 'total', 'estado', 'fecha_venta')
    list_filter = ('estado', 'origen', 'fecha_venta')
    search_fields = ('id', 'cliente__apellido', 'cliente__usuario_auth__username')
    date_hierarchy = 'fecha_venta'
    inlines = [DetalleVentaInline]
    readonly_fields = ('total',)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'venta',
        'medio_pago',
        'estado_pago',
        'monto',
        'buy_order',
        'fecha_creacion',
    )
    list_filter = ('medio_pago', 'estado_pago')
    search_fields = ('buy_order', 'token_ws', 'venta__id')
    readonly_fields = (
        'venta',
        'cliente',
        'vendedor',
        'medio_pago',
        'monto',
        'buy_order',
        'session_id',
        'token_ws',
        'codigo_autorizacion',
        'codigo_respuesta',
        'tipo_pago',
        'cuotas',
        'card_last4',
        'fecha_transaccion',
        'vci',
        'fecha_creacion',
        'fecha_confirmacion',
    )


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'tipo', 'estado', 'fecha_estimada', 'fecha_entrega')
    list_filter = ('tipo', 'estado')
    search_fields = ('venta__id',)


@admin.register(JornadaLaboral)
class JornadaLaboralAdmin(admin.ModelAdmin):
    list_display = ('id', 'vendedor', 'inicio', 'fin', 'duracion_minutos')
    list_filter = ('vendedor',)
    readonly_fields = ('vendedor', 'inicio', 'fin', 'notas_cierre')


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_informe',
        'periodo_inicio',
        'periodo_fin',
        'cantidad_ventas',
        'monto_total_ventas',
    )
