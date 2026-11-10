from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Especie(models.TextChoices):
    PERRO = 'perro', 'Perro'
    GATO = 'gato', 'Gato'
    ESPECIAL = 'especial', 'Especial / Exótico'


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
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cliente(models.Model):
    usuario_auth = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='cliente_perfil'
    )
    apellido = models.CharField(max_length=40)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=250)

    class Meta:
        ordering = ['apellido']

    def __str__(self):
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


class Alergia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Preferencia(models.Model):
    class Categoria(models.TextChoices):
        TIPO_ALIMENTO = 'tipo', 'Tipo de alimento'
        PROTEINA = 'proteina', 'Proteína'

    nombre = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)

    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = 'Preferencia'
        verbose_name_plural = 'Preferencias'

    def __str__(self):
        return self.nombre


class Ficha(TimeStamped):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='fichas_mascotas')
    nombre = models.CharField(max_length=40)
    edad = models.PositiveIntegerField()
    especie = models.CharField(max_length=30, choices=Especie.choices, default=Especie.PERRO)
    alergias = models.ManyToManyField(Alergia, blank=True, related_name='mascotas_alergicas')
    favoritos = models.ManyToManyField(Preferencia, blank=True, related_name='fichas')
    tamano_grano_preferido = models.CharField(
        max_length=20, choices=TamanoGrano.choices, blank=True, null=True
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Ficha de mascota'
        verbose_name_plural = 'Fichas de mascotas'

    def __str__(self):
        return f"{self.nombre} ({self.get_especie_display()})"


class Producto(models.Model):
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
    precio_oferta = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Precio de oferta (CLP)'
    )
    alergenos_contenidos = models.ManyToManyField(
        Alergia, blank=True, related_name='productos_afectados'
    )
    animal = models.CharField(max_length=30, choices=Especie.choices, default=Especie.PERRO)
    tipo_producto = models.CharField(max_length=30, choices=TipoProducto.choices)
    edad_producto = models.CharField(
        max_length=30, choices=EtapaVida.choices, default=EtapaVida.TODAS
    )
    tamano_raza = models.CharField(
        max_length=30, choices=TamanoRaza.choices, default=TamanoRaza.TODAS
    )
    tamano_grano = models.CharField(
        max_length=20, choices=TamanoGrano.choices, null=True, blank=True
    )
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(
        upload_to='productos/', null=True, blank=True, verbose_name='Imagen del producto'
    )

    activo = models.BooleanField(default=True)

    @property
    def en_oferta(self):
        return self.precio_oferta is not None

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} [{self.sku}]"


class Stock(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='stock')
    stock_sala = models.PositiveIntegerField(default=0)
    stock_bodega = models.PositiveIntegerField(default=0)
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
    run_empresa = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name='RUT de la empresa'
    )
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    fono = models.CharField(max_length=20)
    productos = models.ManyToManyField(Producto, related_name='proveedores', blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    class TipoDocumento(models.TextChoices):
        BOLETA = 'boleta', 'Boleta'
        FACTURA = 'factura', 'Factura'

    origen = models.CharField(max_length=10, choices=OrigenVenta.choices)

    vendedor = models.ForeignKey(
        Vendedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas'
    )

    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas'
    )

    fecha_venta = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    total = models.PositiveIntegerField(default=0, editable=False)
    estado = models.CharField(
        max_length=30, choices=EstadoVenta.choices, default=EstadoVenta.PENDIENTE
    )

    tipo_documento = models.CharField(
        max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.BOLETA
    )
    rut_factura = models.CharField(max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=100, blank=True, null=True)

    productos = models.ManyToManyField(Producto, through='DetalleVenta', related_name='ventas')

    class Meta:
        ordering = ['-fecha_venta']
        indexes = [
            models.Index(fields=['estado', 'fecha_venta']),
        ]

    @property
    def pago_autorizado(self):
        return self.pagos.filter(estado_pago=EstadoPago.AUTORIZADO).first()

    @property
    def monto_neto(self):
        # El total ya incluye el IVA.
        return round(self.total / 1.19)

    @property
    def monto_iva(self):
        return self.total - self.monto_neto

    def calcular_total(self):
        return self.detalles.aggregate(total=Sum('subtotal'))['total'] or 0

    def recalcular_total(self):
        self.total = self.calcular_total()
        self.save(update_fields=['total', 'fecha_actualizacion'])

    def agregar_producto(self, producto, cantidad=1):
        if not producto.activo:
            raise ValueError(f"El producto {producto.sku} está inactivo y no puede venderse.")
        # Las líneas existentes conservan el precio con que se crearon.
        detalle, creado = self.detalles.get_or_create(
            producto=producto,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio},
        )
        if not creado:
            detalle.cantidad += cantidad
            detalle.save()
        self.recalcular_total()
        return detalle

    def descontar_stock(self):
        for producto_id, cantidad in self.detalles.values_list('producto_id', 'cantidad'):
            stock = Stock.objects.filter(producto_id=producto_id).first()
            if stock is None:
                continue
            de_sala = min(stock.stock_sala, cantidad)
            stock.stock_sala -= de_sala
            stock.stock_bodega = max(0, stock.stock_bodega - (cantidad - de_sala))
            stock.save(update_fields=['stock_sala', 'stock_bodega'])

    def __str__(self):
        return (
            f"Venta #{self.id} [{self.get_origen_display()}] "
            f"- ${self.total} ({self.get_estado_display()})"
        )


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lineas_venta')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField(verbose_name='Precio unitario cobrado')
    precio_lista = models.PositiveIntegerField(null=True, blank=True)
    subtotal = models.PositiveIntegerField(editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['venta', 'producto'],
                name='unique_detalle_venta_producto',
            ),
        ]

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} (Venta #{self.venta_id})"


class Pago(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='pagos',
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos',
    )
    vendedor = models.ForeignKey(
        Vendedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cobros',
    )
    medio_pago = models.CharField(max_length=20, choices=MedioPago.choices)
    monto = models.PositiveIntegerField()

    buy_order = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Orden de Compra',
    )
    session_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='ID de Sesión'
    )
    token_ws = models.CharField(max_length=255, blank=True, null=True, verbose_name='Token WebPay')

    codigo_autorizacion = models.CharField(max_length=20, blank=True, null=True)

    codigo_respuesta = models.IntegerField(null=True, blank=True)
    tipo_pago = models.CharField(max_length=10, blank=True, null=True)
    cuotas = models.PositiveIntegerField(default=0)
    card_last4 = models.CharField(
        max_length=4,
        blank=True,
        null=True,
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
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['venta'],
                condition=models.Q(estado_pago=EstadoPago.AUTORIZADO),
                name='unique_pago_autorizado_por_venta',
            ),
        ]

    def save(self, *args, **kwargs):
        if (
            self.estado_pago in (EstadoPago.AUTORIZADO, EstadoPago.ANULADO)
            and self.fecha_confirmacion is None
        ):
            self.fecha_confirmacion = timezone.now()
        super().save(*args, **kwargs)
        # El stock se descuenta al completar la venta, en POS y Webpay.
        if (
            self.estado_pago == EstadoPago.AUTORIZADO
            and self.venta.estado != EstadoVenta.COMPLETADA
        ):
            self.venta.estado = EstadoVenta.COMPLETADA
            self.venta.descontar_stock()
            self.venta.save(update_fields=['estado', 'fecha_actualizacion'])
        elif self.estado_pago == EstadoPago.ANULADO and self.venta.estado != EstadoVenta.ANULADA:
            self.venta.estado = EstadoVenta.ANULADA
            self.venta.save(update_fields=['estado', 'fecha_actualizacion'])

    def __str__(self):
        return (
            f"Pago #{self.id} [Orden: {self.buy_order or 'N/A'}] "
            f"- {self.get_medio_pago_display()} - "
            f"{self.get_estado_pago_display()} (${self.monto})"
        )


class Entrega(models.Model):
    class TipoEntrega(models.TextChoices):
        DESPACHO = 'despacho', 'Despacho a domicilio'
        RETIRO = 'retiro', 'Retiro en tienda'

    class EstadoEntrega(models.TextChoices):
        PREPARANDO = 'preparando', 'Preparando'
        EN_DESPACHO = 'en_despacho', 'En despacho'
        LISTO_RETIRO = 'listo_retiro', 'Listo para retiro'
        ENTREGADO = 'entregado', 'Entregado'
        FALLIDO = 'fallido', 'Fallido / Reprogramar'

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
    direccion_entrega = models.CharField(max_length=250, blank=True)
    fecha_estimada = models.DateField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de entrega real'
    )

    @property
    def cliente(self):
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
        on_delete=models.SET_NULL,
        null=True,
        related_name='informes',
    )
    fecha_informe = models.DateField(auto_now_add=True)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)

    monto_total_ventas = models.PositiveBigIntegerField(default=0)
    cantidad_ventas = models.PositiveIntegerField(default=0)
    cantidad_productos_vendidos = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-fecha_informe']

    def __str__(self):
        admin_name = self.administrador.usuario_auth.username if self.administrador else 'N/A'
        return f"Informe del {self.fecha_informe} (Admin: {admin_name})"


class JornadaLaboral(models.Model):
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name='jornadas')
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)
    notas_cierre = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'Jornada laboral'
        verbose_name_plural = 'Jornadas laborales'

    @property
    def activa(self):
        return self.fin is None

    @property
    def fin_efectivo(self):
        return self.fin or timezone.now()

    @property
    def duracion_minutos(self):
        return int((self.fin_efectivo - self.inicio).total_seconds() // 60)

    def ventas_del_turno(self):
        return Venta.objects.filter(
            origen=OrigenVenta.POS,
            vendedor=self.vendedor,
            fecha_venta__gte=self.inicio,
            fecha_venta__lte=self.fin_efectivo,
        ).prefetch_related('pagos', 'detalles__producto')

    def resumen_turno(self):
        ventas = self.ventas_del_turno().filter(estado=EstadoVenta.COMPLETADA)
        pagos = Pago.objects.filter(venta__in=ventas, estado_pago=EstadoPago.AUTORIZADO)
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
        return cls.objects.filter(
            vendedor=vendedor, fin__isnull=True
        ).first() or cls.objects.create(vendedor=vendedor)

    def cerrar(self, notas=''):
        self.fin = timezone.now()
        self.notas_cierre = notas or ''
        self.save(update_fields=['fin', 'notas_cierre'])

    def __str__(self):
        return (
            f"Jornada #{self.id} de {self.vendedor.usuario_auth.username} "
            f"({'activa' if self.activa else 'cerrada'})"
        )
