from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

# Create your models here.

#0.- Choices reutilizables/compartidos
#--------------------------------------------

class Especie(models.TextChoices):
    """Especie del animal. La usa Ficha.especie y Producto.animal"""
    PERRO = 'perro', 'Perro'
    GATO = 'gato', 'Gato'
    ESPECIAL = 'especial', 'Especial / Exótico'  # conejos, hámsters, aves, etc.

class TamanoGrano(models.TextChoices):
    PEQUENO = 'pequeno', 'Grano pequeño'
    MEDIANO = 'mediano', 'Grano mediano'
    GRANDE = 'grande', 'Grano grande'

class OrigenVenta(models.TextChoices):
    WEB = 'web', 'Web (E-commerce)'
    POS = 'pos', 'POS (Tienda física)'

class EstadoVenta(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente de Pago'
    COMPLETADA = 'completada', 'Completada'
    ANULADA = 'anulada', 'Anulada'

class MedioPago(models.TextChoices):
    EFECTIVO = 'efectivo', 'Efectivo'
    DEBITO = 'debito', 'Tarjeta de Débito (POS)'
    CREDITO = 'credito', 'Tarjeta de Crédito (POS)'
    WEBPAY = 'webpay', 'WebPay (Transbank)'


class EstadoPago(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    AUTORIZADO = 'autorizado', 'Autorizado (Pagado)'
    FALLIDO = 'fallido', 'Fallido'
    ANULADO = 'anulado', 'Anulado'

class TimeStamped(models.Model):
    """Clase para auditabilidad básica,'¿Cuándo se creó?' y '¿Cuándo se modificó por última vez?'."""
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

#--------------------------------------------
#1.-USUARIOS
#--------------------------------------------
class Cliente(models.Model):
    usuario_auth = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='cliente_perfil'
        )
    apellido=models.CharField(max_length=40)
    correo=models.EmailField(unique=True)
    telefono=models.CharField(max_length=20, blank=True, null=True)
    direccion= models.CharField(max_length=250)

    class Meta:
        ordering = ['apellido']

    def __str__(self):
        # f-string incrusta variables, ej: "Carlos Soto (Cliente)"
        return f"{self.usuario_auth.first_name} {self.apellido} (Cliente)"

class Vendedor(models.Model):
    usuario_auth = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='vendedor_perfil'
        )
    sueldo = models.PositiveIntegerField()
    cargo = models.CharField(max_length=50)
    horario = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return f"Vendedor: {self.usuario_auth.first_name} - {self.cargo}"

class Administrador(models.Model):
    usuario_auth = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_perfil')

    def __str__(self):
        return f"Admin: {self.usuario_auth.username}"

    
#--------------------------------------------
#2.- FICHA MASCOTAS
#--------------------------------------------

class Alergia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Preferencia(models.Model):
    """Catálogo de preferencias. Se agregarán desde admin, sin código."""
    class Categoria(models.TextChoices):
        TIPO_ALIMENTO = 'tipo', 'Tipo de alimento'
        PROTEINA = 'proteina', 'Proteína' #sabor (ave, vacuno, cordero queseyo chabal)

    nombre = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)

    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = 'Preferencia'
        verbose_name_plural = 'Preferencias'

    def __str__(self):
        return self.nombre

class Ficha(TimeStamped):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name='fichas_mascotas'
        )
    nombre = models.CharField(max_length=40)
    edad = models.PositiveIntegerField()
    especie = models.CharField(max_length=30, choices=Especie.choices, default=Especie.PERRO)
    alergias = models.ManyToManyField(Alergia, blank=True, related_name='mascotas_alergicas')
    favoritos = models.ManyToManyField(Preferencia, blank=True, related_name='fichas')
    tamano_grano_preferido = models.CharField(max_length=20, choices=TamanoGrano.choices, blank=True, null=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Ficha de mascota'
        verbose_name_plural = 'Fichas de mascotas'

    def __str__(self):
        return f"{self.nombre} ({self.get_especie_display()})"


#--------------------------------------------
#3.- INVENTARIO
#--------------------------------------------

class Producto(models.Model):
    #tienen opciones duplicadas, una para la base de datos y otra para ser visible al usuario
    class TipoProducto(models.TextChoices):
        ALIMENTO = 'alimento', 'Alimento'
        HIGIENE = 'higiene', 'Higiene y Cuidado'
        JUGUETE = 'juguete', 'Juguetes'
        ACCESORIO = 'accesorio', 'Accesorios'

    class EtapaVida(models.TextChoices):
        CACHORRO = 'cachorro', 'Cachorro / Junior'
        ADULTO = 'adulto', 'Adulto'
        SENIOR = 'senior', 'Senior'
        TODAS = 'todas', 'Todas las edades'

    class TamanoRaza(models.TextChoices):
        PEQUENA = 'pequena', 'Raza Pequeña'
        MEDIANA = 'mediana', 'Raza Mediana'
        GRANDE = 'grande', 'Raza Grande'
        TODAS = 'todas', 'Todas las razas'

    sku = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    precio = models.PositiveIntegerField()
    # PROMOCIONES: si se le asigna un precio de oferta (desde el admin), el
    # producto aparece en la sección "En promoción" del home y en el catálogo
    # se muestra el precio anterior tachado. Vacío = precio normal.
    precio_oferta = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Precio de oferta (CLP)')
    # Un producto puede contener varios ingredientes alérgenos
    # Un producto puede contener varios ingredientes alérgenos (typo corregido)
    alergenos_contenidos = models.ManyToManyField(
        Alergia, blank=True, related_name='productos_afectados'
    )
    animal = models.CharField(max_length=30, choices=Especie.choices, default=Especie.PERRO)  # el más común
    tipo_producto = models.CharField(max_length=30, choices=TipoProducto.choices)
    edad_producto = models.CharField(max_length=30, choices=EtapaVida.choices, default=EtapaVida.TODAS)
    tamano_raza = models.CharField(max_length=30, choices=TamanoRaza.choices, default=TamanoRaza.TODAS)
    tamano_grano = models.CharField(max_length=20, choices=TamanoGrano.choices, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    # Fotografía del producto (se sube desde el admin). Si está vacía, los
    # templates muestran un placeholder automático. Requiere Pillow.
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True,
                               verbose_name='Imagen del producto')

    # BAJA LÓGICA: como DetalleVenta.producto usa PROTECT, un producto con historial de ventas NO se puede borrar de la BD; se desactiva con esto.
    activo = models.BooleanField(default=True)

    @property
    def en_oferta(self):
        """True si el admin le asignó precio de oferta al producto."""
        return self.precio_oferta is not None

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} [{self.sku}]"

class Stock(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='stock')
    stock_sala = models.PositiveIntegerField(default=0)
    stock_bodega = models.PositiveIntegerField(default=0)
    # Umbral para alertas de reposición según als H.U
    stock_minimo = models.PositiveIntegerField(default=5)

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'

    @property
    def stock_total(self):
        return self.stock_sala + self.stock_bodega

    def __str__(self):
        return f"Stock de {self.producto.nombre} [Sala: {self.stock_sala} | Bodega: {self.stock_bodega}]"

class Proveedor(models.Model):
    # Null en true; proveedores extranjeros no tendrían cómo registrarse.
    run_empresa = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='RUT de la empresa')
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    fono = models.CharField(max_length=20)
    productos = models.ManyToManyField(Producto, related_name='proveedores', blank=True)

    class Meta:
        ordering = ['nombre']
        # Sin esto Django pluralizaría "Proveedor" como "Proveedors"
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre

    
#--------------------------------------------
#4.- MÓDULO DE VENTAS
#--------------------------------------------

class Venta(models.Model):
    class TipoDocumento(models.TextChoices):
        BOLETA = 'boleta', 'Boleta'
        FACTURA = 'factura', 'Factura'

    origen = models.CharField(max_length=10, choices=OrigenVenta.choices)

    # Si es venta web, el vendedor es nulo. Si es por POS, se registra.
    vendedor = models.ForeignKey(Vendedor, on_delete=models.SET_NULL, null=True, blank=True,related_name='ventas')

    # cliente se elimina, la venta DEBE sobrevivir (SET_NULL, ya nullable).
    cliente = models.ForeignKey(Cliente,on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas') 

    fecha_venta = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

   # editable=False: ningún formulario puede escribirlo a mano.
    total = models.PositiveIntegerField(default=0, editable=False)
    estado = models.CharField(max_length=30, choices=EstadoVenta.choices, default=EstadoVenta.PENDIENTE)

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.BOLETA)
    rut_factura = models.CharField(max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=100, blank=True, null=True)

    productos = models.ManyToManyField(Producto, through='DetalleVenta', related_name='ventas')

    class Meta:
        ordering = ['-fecha_venta']
        indexes = [
            # Reporte típico: filtrar por estado en un rango de fechas
            models.Index(fields=['estado', 'fecha_venta']),
        ]

    #Propiedades de las reglas de negocio

    @property
    def pago_autorizado(self):
        """El pago autorizado de esta venta (None si aún no existe)."""
        return self.pagos.filter(estado_pago=EstadoPago.AUTORIZADO).first()

    @property
    def monto_neto(self):
        """Los precios al público en Chile INCLUYEN IVA (19%): neto = total / 1.19."""
        return round(self.total / 1.19)

    @property
    def monto_iva(self):
        return self.total - self.monto_neto

    #  única forma oficial de manipular el total y los detalles

    def calcular_total(self):
        """Total real según los subtotales de los detalles. No persiste nada."""
        return self.detalles.aggregate(total=Sum('subtotal'))['total'] or 0

    def recalcular_total(self):
        """Persiste el total calculado. Llamar tras crear/editar detalles
        (Venta.agregar_producto() ya lo hace automáticamente)."""
        self.total = self.calcular_total()
        self.save(update_fields=['total', 'fecha_actualizacion'])

    def agregar_producto(self, producto, cantidad=1):
        """Agrega/actualiza una línea usando el precio VIGENTE del producto
        (snapshot en DetalleVenta.precio_unitario) y recalcula el total.
        Si el producto ya está en la venta, acumula la cantidad."""
        if not producto.activo:
            raise ValueError(
                f"El producto {producto.sku} está inactivo y no puede venderse."
            )
        detalle, creado = self.detalles.get_or_create(
            producto=producto,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio},
        )
        if not creado:
            detalle.cantidad += cantidad
            detalle.save()
        self.recalcular_total()
        return detalle

    # NUEVO (RF-18): descuento de inventario al concretarse la venta
    def descontar_stock(self):
        """Descuenta del inventario las unidades vendidas en esta venta.

        NO se llama a mano: la invoca Pago.save() EXACTAMENTE cuando un pago
        pasa a AUTORIZADO (POS o WebPay). Como esa rama solo corre en la
        transición pendiente->completada, el stock nunca se descuenta dos veces.
        Descuenta primero de sala y, si no alcanza, completa desde bodega.
        """
        for detalle in self.detalles.select_related('producto'):
            stock = Stock.objects.filter(producto=detalle.producto).first()
            if stock is None:
                continue  # producto sin fila de Stock: nada que descontar
            pendiente = detalle.cantidad
            de_sala = min(stock.stock_sala, pendiente)
            stock.stock_sala -= de_sala
            pendiente -= de_sala
            stock.stock_bodega = max(0, stock.stock_bodega - pendiente)
            stock.save(update_fields=['stock_sala', 'stock_bodega'])

    def __str__(self):
        return (f"Venta #{self.id} [{self.get_origen_display()}] "
                f"- ${self.total} ({self.get_estado_display()})")

    
class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='detalles'
    )
    # CORREGIDO (era CASCADE): borrar un producto destruiría el historial de
    # ventas. PROTECT bloquea el borrado; para dar de baja usar activo=False.
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='lineas_venta'
    )
    cantidad = models.PositiveIntegerField(default=1)
    # Snapshot del precio AL MOMENTO DE LA VENTA (inmune a cambios futuros)
    precio_unitario = models.PositiveIntegerField(
        verbose_name='Precio unitario cobrado'
    )
    # Precio de lista ANTES de descuentos; null = no hubo descuento
    precio_lista = models.PositiveIntegerField(null=True, blank=True)
    # Calculado automáticamente en save(); nunca se escribe a mano
    subtotal = models.PositiveIntegerField(editable=False)

    class Meta:
        constraints = [
            # Una línea por producto por venta: las cantidades se acumulan
            # (lo garantiza Venta.agregar_producto())
            models.UniqueConstraint(
                fields=['venta', 'producto'],
                name='unique_detalle_venta_producto',
            ),
        ]

    def save(self, *args, **kwargs):
        # Regla central del módulo: subtotal = cantidad * precio_unitario.
        # Nota: QuerySet.update() NO pasa por save(); evitarlo con detalles.
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        # venta_id evita una consulta extra a la BD por cada línea listada
        return f"{self.cantidad}x {self.producto.nombre} (Venta #{self.venta_id})"


class Pago(models.Model):
    """
    Pago GENÉRICO: un solo modelo cubre el POS (efectivo / débito /
    crédito por terminal físico) y la Web (WebPay). Los campos WebPay solo se
    usan cuando medio_pago == 'webpay'; en el POS quedan nulos.
    """
    # CORREGIDO: era OneToOne + CASCADE. Ahora ForeignKey + PROTECT: el pago
    # es registro de auditoría (sobrevive a todo) y una venta puede tener
    # VARIOS intentos (rechazos/reintentos), con la regla de negocio de que
    # solo UNO de ellos puede quedar autorizado (ver constraints).
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='pagos',
    )
    # CORREGIDO (era obligatorio + CASCADE): la venta anónima de POS
    # (cliente null) necesita igualmente registrar su cobro.
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos',
    )
    # Cobro registrado por el vendedor del POS (si aplica)
    vendedor = models.ForeignKey(
        Vendedor,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cobros',
    )
    medio_pago = models.CharField(max_length=20, choices=MedioPago.choices)
    monto = models.PositiveIntegerField()

    # ---------------- CAMPOS ESPECÍFICOS DE WEBPAY (Transbank) ----------
    # Transbank exige buy_order ÚNICO y de MÁXIMO 26 caracteres alfanuméricos
    # (el generador de órdenes debe respetarlo aunque la BD admita 50).
    # Nullable: los pagos de POS no tienen orden de compra.
    buy_order = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        verbose_name='Orden de Compra',
    )
    session_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='ID de Sesión'
    )
    token_ws = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Token WebPay'
    )

    # Datos de respuesta entregados por Transbank tras la confirmación
    codigo_autorizacion = models.CharField(max_length=20, blank=True, null=True)

    codigo_respuesta = models.IntegerField(null=True, blank=True)
    # VD (débito), VN (crédito sin cuotas), VC/SI/S2/NC (con cuotas)
    tipo_pago = models.CharField(max_length=10, blank=True, null=True)
    cuotas = models.PositiveIntegerField(default=0)
    # Nuevos, para conciliación con Transbank (card_detail + transaction_date)
    card_last4 = models.CharField(
        max_length=4, blank=True, null=True,
        verbose_name='Últimos 4 dígitos de la tarjeta',
    )
    fecha_transaccion = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha según Transbank'
    )
    vci = models.CharField(max_length=10, blank=True, null=True)

    estado_pago = models.CharField(
        max_length=30,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)  # se fija al autorizar/anular

    class Meta:
        ordering = ['-fecha_creacion']
        constraints = [
            # Regla de negocio: máximo UN pago AUTORIZADO por venta.
            # Permite N intentos fallidos, pero solo un cobro efectivo.
            models.UniqueConstraint(
                fields=['venta'],
                condition=models.Q(estado_pago=EstadoPago.AUTORIZADO),
                name='unique_pago_autorizado_por_venta',
            ),
        ]

    def save(self, *args, **kwargs):
        # Fijar la fecha de confirmación la primera vez que se autoriza/anula
        if (self.estado_pago in (EstadoPago.AUTORIZADO, EstadoPago.ANULADO)
                and self.fecha_confirmacion is None):
            self.fecha_confirmacion = timezone.now()
        super().save(*args, **kwargs)
        # MÁQUINA DE ESTADOS DEL MÓDULO: el PAGO manda sobre la VENTA.
        #   autorizado -> venta completada
        #   anulado    -> venta anulada   (aquí la lógica de stock debe devolver)
        #   fallido / pendiente -> la venta no cambia (permite reintento)
        # Nota: QuerySet.update() NO pasa por save().
        if (self.estado_pago == EstadoPago.AUTORIZADO
                and self.venta.estado != EstadoVenta.COMPLETADA):
            self.venta.estado = EstadoVenta.COMPLETADA
            # NUEVO (RF-18): el stock se descuenta aquí, en el MISMO instante
            # en que la venta queda completada (sirve para POS y para WebPay).
            self.venta.descontar_stock()
            self.venta.save(update_fields=['estado', 'fecha_actualizacion'])
        elif (self.estado_pago == EstadoPago.ANULADO
                and self.venta.estado != EstadoVenta.ANULADA):
            self.venta.estado = EstadoVenta.ANULADA
            self.venta.save(update_fields=['estado', 'fecha_actualizacion'])

    def __str__(self):
        return (f"Pago #{self.id} [Orden: {self.buy_order or 'N/A'}] "
                f"- {self.get_medio_pago_display()} - "
                f"{self.get_estado_pago_display()} (${self.monto})")


#--------------------------------------------
# 5.- MÓDULO ENTREGAS E INFORMES
#--------------------------------------------

class Entrega(models.Model):
    # choices EXCLUSIVAS de Entrega
    class TipoEntrega(models.TextChoices):
        DESPACHO = 'despacho', 'Despacho a domicilio'
        RETIRO = 'retiro', 'Retiro en tienda'

    class EstadoEntrega(models.TextChoices):
        PREPARANDO = 'preparando', 'Preparando'
        EN_DESPACHO = 'en_despacho', 'En despacho'
        LISTO_RETIRO = 'listo_retiro', 'Listo para retiro'
        ENTREGADO = 'entregado', 'Entregado'
        FALLIDO = 'fallido', 'Fallido / Reprogramar'

    #la entrega SIEMPRE nace de una venta (retiro en tienda incluido).

    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name='entrega',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoEntrega.choices,
        default=TipoEntrega.DESPACHO,
    )
    estado = models.CharField(
        max_length=30,
        choices=EstadoEntrega.choices,
        default=EstadoEntrega.PREPARANDO,
    )
    # SNAPSHOT de la dirección al momento del despacho: la dirección del
    # cliente puede cambiar después, el registro de la entrega no.
    direccion_entrega = models.CharField(max_length=250, blank=True)
    fecha_estimada = models.DateField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de entrega real'
    )

    @property
    def cliente(self):
        """Cliente de la entrega (None si la venta fue anónima en POS)."""
        return self.venta.cliente

    class Meta:
        ordering = ['-venta__fecha_venta']
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'

    def __str__(self):
        cliente = self.venta.cliente
        nombre = cliente.usuario_auth.first_name if cliente else 'Consumidor final'
        return f"Entrega #{self.id} para {nombre} - {self.get_estado_display()}"


class Informe(models.Model):
    administrador = models.ForeignKey(
        Administrador,
        on_delete=models.SET_NULL, null=True,
        related_name='informes',
    )
    fecha_informe = models.DateField(auto_now_add=True)
    # Período que cubre el informe
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)

    monto_total_ventas = models.PositiveBigIntegerField(default=0)  #CLP
    cantidad_ventas = models.PositiveIntegerField(default=0)       # n° de ventas
    cantidad_productos_vendidos = models.PositiveIntegerField(default=0)  #unidades

    class Meta:
        ordering = ['-fecha_informe']

    def __str__(self):
        admin_name = (
            self.administrador.usuario_auth.username
            if self.administrador else 'N/A'
        )
        return f"Informe del {self.fecha_informe} (Admin: {admin_name})"


#--------------------------------------------
# 6.- MÓDULO JORNADAS LABORALES (NUEVO: RF-12 / RF-24)
#--------------------------------------------

class JornadaLaboral(models.Model):
    """Jornada (turno) de trabajo de un vendedor.

    Se ABRE al empezar el turno y se CIERRA al terminarlo. Al cerrar,
    resumen_turno() entrega el desglose de las ventas del turno (RF-24:
    resumen de cierre con el total recaudado por medio de pago).
    """
    vendedor = models.ForeignKey(
        Vendedor, on_delete=models.CASCADE, related_name='jornadas'
    )
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)
    notas_cierre = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'Jornada laboral'
        verbose_name_plural = 'Jornadas laborales'

    @property
    def activa(self):
        """True si el vendedor sigue dentro de esta jornada (sin cerrar)."""
        return self.fin is None

    @property
    def fin_efectivo(self):
        """Fin real de la jornada; si sigue abierta, 'ahora' (sirve para
        ver el resumen en vivo antes de cerrar)."""
        return self.fin or timezone.now()

    @property
    def duracion_minutos(self):
        return int((self.fin_efectivo - self.inicio).total_seconds() // 60)

    def ventas_del_turno(self):
        """Ventas POS de este vendedor dentro de la jornada."""
        return (Venta.objects
                .filter(origen=OrigenVenta.POS,
                        vendedor=self.vendedor,
                        fecha_venta__gte=self.inicio,
                        fecha_venta__lte=self.fin_efectivo)
                .prefetch_related('pagos', 'detalles__producto'))

    def resumen_turno(self):
        """RF-24: desglose de las ventas del turno. Devuelve un dict con la
        cantidad de ventas, el total recaudado y el desglose por medio de
        pago: [(nombre_medio, monto, n_pagos), ...]."""
        ventas = self.ventas_del_turno().filter(estado=EstadoVenta.COMPLETADA)
        pagos = Pago.objects.filter(venta__in=ventas,
                                    estado_pago=EstadoPago.AUTORIZADO)
        por_medio = {}
        for pago in pagos:
            monto, n = por_medio.get(pago.medio_pago, (0, 0))
            por_medio[pago.medio_pago] = (monto + pago.monto, n + 1)
        return {
            'cantidad': ventas.count(),
            'total': sum(p.monto for p in pagos),
            'por_medio': [
                (MedioPago(medio).label, monto, n)
                for medio, (monto, n) in sorted(por_medio.items())
            ],
        }

    @classmethod
    def abrir(cls, vendedor):
        """Abre la jornada del vendedor. Si ya tenía una abierta, devuelve
        esa misma (nunca hay dos jornadas activas a la vez)."""
        return (cls.objects.filter(vendedor=vendedor, fin__isnull=True).first()
                or cls.objects.create(vendedor=vendedor))

    def cerrar(self, notas=''):
        self.fin = timezone.now()
        self.notas_cierre = notas or ''
        self.save(update_fields=['fin', 'notas_cierre'])

    def __str__(self):
        return (f"Jornada #{self.id} de {self.vendedor.usuario_auth.username} "
                f"({'activa' if self.activa else 'cerrada'})")
