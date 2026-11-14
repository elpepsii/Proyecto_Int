from itertools import count
from unicodedata import combining, normalize

from django.db import migrations

# Archivo de imagen, unidades en sala, unidades en bodega y tipo de alimento.
PRODUCTOS_NUEVOS = (
    ('000000000000508438-UN-01.webp', 5, 10, 'seco'),
    ('Champion_Dog_Carne_15kg.png', 4, 8, 'seco'),
    ('Master-Dog-Adulto-18KG-1.jpg', 6, 9, 'seco'),
    ('Purina_Cat_Chow.jpg', 4, 7, 'seco'),
    ('arena_para_gatos.jpg', 5, 9, ''),
    ('fit_formula.jpg', 3, 6, 'seco'),
    ('jugete_kong.jpg', 3, 5, ''),
    ('novopet.jpg', 4, 7, 'seco'),
    ('novopet_ninfas.jpg', 3, 6, 'seco'),
    ('novopet_periquitos.jpg', 5, 8, 'seco'),
    ('wiskas.webp', 6, 10, 'seco'),
)

FORMATOS = {
    'seco': ('Alimento seco', {'seco', 'secos', 'alimento seco', 'alimentos secos', 'comida seca'}),
    'humedo': (
        'Alimento húmedo',
        {'humedo', 'humedos', 'alimento humedo', 'alimentos humedos', 'comida humeda'},
    ),
}


def texto_normalizado(texto):
    sin_tildes = ''.join(letra for letra in normalize('NFD', texto) if not combining(letra))
    return ' '.join(sin_tildes.lower().split())


def vincular_preferencias(apps, schema_editor):
    Preferencia = apps.get_model('tiendaApp', 'Preferencia')
    todas = Preferencia.objects.using(schema_editor.connection.alias)
    tipos = todas.filter(categoria='tipo')
    nombres_ocupados = set(todas.values_list('nombre', flat=True))
    for tipo, (nombre, equivalentes) in FORMATOS.items():
        ids = [
            preferencia.pk
            for preferencia in tipos.filter(tipo_alimento='')
            if texto_normalizado(preferencia.nombre) in equivalentes
        ]
        tipos.filter(pk__in=ids).update(tipo_alimento=tipo)
        if tipos.filter(tipo_alimento=tipo).exists():
            continue
        nombre_disponible = nombre
        for sufijo in count(2):
            if nombre_disponible not in nombres_ocupados:
                break
            nombre_disponible = f'{nombre} ({sufijo})'
        tipos.create(nombre=nombre_disponible, categoria='tipo', tipo_alimento=tipo)


def iniciar_stock_de_productos(apps, schema_editor):
    Producto = apps.get_model('tiendaApp', 'Producto')
    Stock = apps.get_model('tiendaApp', 'Stock')
    base = schema_editor.connection.alias
    productos = Producto.objects.using(base).filter(activo=True)
    stocks = Stock.objects.using(base)
    for imagen, sala, bodega, tipo_alimento in PRODUCTOS_NUEVOS:
        asociados = productos.filter(imagen=f'productos/{imagen}')
        if tipo_alimento:
            asociados.filter(tipo_producto='alimento', tipo_alimento='').update(
                tipo_alimento=tipo_alimento
            )
        for producto_id in asociados.values_list('pk', flat=True):
            stock, creado = stocks.get_or_create(
                producto_id=producto_id, defaults={'stock_sala': sala, 'stock_bodega': bodega}
            )
            if not creado:
                stocks.filter(pk=stock.pk, stock_sala=0, stock_bodega=0).update(
                    stock_sala=sala, stock_bodega=bodega
                )


class Migration(migrations.Migration):
    dependencies = [
        ('tiendaApp', '0004_tipo_alimento'),
    ]

    operations = [
        migrations.RunPython(vincular_preferencias, migrations.RunPython.noop),
        migrations.RunPython(iniciar_stock_de_productos, migrations.RunPython.noop),
    ]
