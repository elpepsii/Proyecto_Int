"""
admin.py — Administración de tiendaApp.

Como en el taller del cine: el admin es la "bodega de datos" del proyecto.
Desde aquí se cargan productos (con imagen), stock, preferencias,
proveedores, y se auditan ventas y pagos.

Extras usados (todos estándar de Django):
  - list_display / list_filter / search_fields: qué mostrar y filtrar.
  - TabularInline: editar los DetalleVenta DENTRO de su Venta.
  - StackedInline: editar el Stock DENTRO de su Producto.
  - filter_horizontal: widget cómodo para M2M (alergias, favoritos).
  - readonly_fields: datos de auditoría que nadie debe editar a mano.
"""

from django.contrib import admin

from .models import (Alergia, Administrador, Cliente, DetalleVenta, Entrega,
                     Ficha, Informe, Pago, Preferencia, Producto, Proveedor,
                     Stock, Vendedor, Venta)


# ------------------------------------------------------------------ Inventario
class StockInline(admin.StackedInline):
    """El stock se administra EN la ficha del producto (A-01: el umbral
    mínimo se define junto al producto)."""
    model = Stock
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('sku', 'nombre', 'precio', 'costo', 'margen_ganancia',
                    'tipo_producto', 'animal', 'activo')
    list_filter = ('activo', 'tipo_producto', 'animal', 'edad_producto')
    search_fields = ('sku', 'nombre')
    filter_horizontal = ('alergenos_contenidos',)
    inlines = [StockInline]
    # A-02 / RF-13: el admin ve el precio sugerido al editar costo y margen.
    readonly_fields = ('precio_sugerido',)

    # El botón "desactivar" en vez de borrar (baja lógica del modelo).
    actions = ['desactivar_productos']

    @admin.action(description='Desactivar productos seleccionados (baja lógica)')
    def desactivar_productos(self, request, queryset):
        queryset.update(activo=False)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    # RNF-23: run_empresa unique en el modelo ya impide duplicados.
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
    # subtotal lo calcula DetalleVenta.save(); total lo recalcula el método
    # oficial de Venta. (Sugerencia: crear la venta y usar "agregar_producto"
    # desde el shell o la vista de POS.)


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'origen', 'cliente', 'total', 'estado',
                    'fecha_venta')
    list_filter = ('estado', 'origen', 'fecha_venta')
    search_fields = ('id', 'cliente__apellido', 'cliente__usuario_auth__username')
    date_hierarchy = 'fecha_venta'
    inlines = [DetalleVentaInline]
    readonly_fields = ('total',)   # editable=False en el modelo; nadie lo escribe a mano


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


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ('fecha_informe', 'periodo_inicio', 'periodo_fin',
                    'cantidad_ventas', 'monto_total_ventas')
