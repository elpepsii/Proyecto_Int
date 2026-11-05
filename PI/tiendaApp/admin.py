"""
admin.py — Administración de tiendaApp.

El admin es la "bodega de datos" del proyecto: aquí el ADMINISTRADOR
carga productos y stock (RF-09, RF-10), el catálogo de alergias y
preferencias para las fichas, los vendedores (RF-12) y audita ventas,
pagos y jornadas.

Extras usados (todos estándar de Django):
  - list_display / list_filter / search_fields: qué mostrar y filtrar.
  - TabularInline: editar los DetalleVenta DENTRO de su Venta.
  - StackedInline: editar el Stock DENTRO de su Producto.
  - filter_horizontal: widget cómodo para M2M (alergias, favoritos).
  - readonly_fields: datos de auditoría que nadie debe editar a mano.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (Alergia, Administrador, Cliente, DetalleVenta, Entrega,
                     Ficha, Informe, JornadaLaboral, Pago, Preferencia,
                     Producto, Proveedor, Stock, Vendedor, Venta)


# ------------------------------------------------------------------ Inventario
class StockInline(admin.StackedInline):
    """El stock se administra EN la ficha del producto (A-01: el umbral
    mínimo se define junto al producto)."""
    model = Stock
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('miniatura', 'sku', 'nombre', 'precio', 'precio_oferta',
                    'tipo_producto', 'animal', 'activo')
    # El precio de oferta se puede editar directo desde el listado:
    # vacío = precio normal; con valor = aparece "En promoción" en el home.
    list_editable = ('precio_oferta', 'activo')
    list_filter = ('activo', 'tipo_producto', 'animal', 'edad_producto')
    search_fields = ('sku', 'nombre')
    filter_horizontal = ('alergenos_contenidos',)
    inlines = [StockInline]

    # Miniatura de la foto en el listado del admin.
    @admin.display(description='Foto')
    def miniatura(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="width:46px;height:46px;'
                'object-fit:cover;border-radius:8px" />', obj.imagen.url)
        return '—'

    # El botón "desactivar" en vez de borrar (baja lógica del modelo).
    actions = ['desactivar_productos']

    @admin.action(description='Desactivar productos seleccionados (baja lógica)')
    def desactivar_productos(self, request, queryset):
        queryset.update(activo=False)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'run_empresa', 'correo', 'fono')
    search_fields = ('nombre', 'run_empresa')
    filter_horizontal = ('productos',)


@admin.register(Alergia)
class AlergiaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(Preferencia)
class PreferenciaAdmin(admin.ModelAdmin):
    """Catálogo de preferencias para las casillas de la ficha de mascota
    (C-04): tipo de alimento y proteínas."""
    list_display = ('nombre', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('nombre',)


# --------------------------------------------------------------- Fichas mascotas
@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cliente', 'especie', 'edad')
    list_filter = ('especie',)
    search_fields = ('nombre', 'cliente__usuario_auth__username',
                     'cliente__apellido')
    filter_horizontal = ('alergias', 'favoritos')


# ------------------------------------------------------------------- Usuarios
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario_auth', 'apellido', 'correo', 'telefono')
    search_fields = ('apellido', 'correo', 'usuario_auth__username')


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    # A-05: los permisos finos se administran en /admin/auth/user/ (grupos);
    # aquí va la información laboral del vendedor.
    list_display = ('usuario_auth', 'cargo', 'horario', 'telefono', 'sueldo')
    search_fields = ('cargo', 'usuario_auth__username')


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('usuario_auth',)


# --------------------------------------------------------------------- Ventas
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    # subtotal lo calcula DetalleVenta.save(); total lo recalcula la venta.
    # (Sugerencia: registrar las ventas por la vista POS de la tienda.)


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'origen', 'cliente', 'vendedor', 'total', 'estado',
                    'fecha_venta')
    list_filter = ('estado', 'origen', 'fecha_venta')
    search_fields = ('id', 'cliente__apellido', 'cliente__usuario_auth__username')
    date_hierarchy = 'fecha_venta'
    inlines = [DetalleVentaInline]
    readonly_fields = ('total',)   # editable=False: nadie lo escribe a mano


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Auditoría de pagos (POS y WebPay). Los datos que devuelve Transbank
    son de solo lectura: se registraron al confirmar y no se tocan."""
    list_display = ('id', 'venta', 'medio_pago', 'estado_pago', 'monto',
                    'buy_order', 'fecha_creacion')
    list_filter = ('medio_pago', 'estado_pago')
    search_fields = ('buy_order', 'token_ws', 'venta__id')
    readonly_fields = ('venta', 'cliente', 'vendedor', 'medio_pago', 'monto',
                       'buy_order', 'session_id', 'token_ws',
                       'codigo_autorizacion', 'codigo_respuesta', 'tipo_pago',
                       'cuotas', 'card_last4', 'fecha_transaccion', 'vci',
                       'fecha_creacion', 'fecha_confirmacion')


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'tipo', 'estado', 'fecha_estimada',
                    'fecha_entrega')
    list_filter = ('tipo', 'estado')
    search_fields = ('venta__id',)


@admin.register(JornadaLaboral)
class JornadaLaboralAdmin(admin.ModelAdmin):
    """Jornadas laborales (RF-12 / RF-24): el admin revisa horarios y
    asistencias de sus vendedores."""
    list_display = ('id', 'vendedor', 'inicio', 'fin', 'duracion_minutos')
    list_filter = ('vendedor',)
    readonly_fields = ('vendedor', 'inicio', 'fin', 'notas_cierre')


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ('fecha_informe', 'periodo_inicio', 'periodo_fin',
                    'cantidad_ventas', 'monto_total_ventas')
