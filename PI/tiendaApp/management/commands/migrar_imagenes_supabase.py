from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tiendaApp.models import BANNERS_PREDETERMINADOS, Banner, Producto


class Command(BaseCommand):
    help = 'Copia las imágenes locales a Supabase y actualiza sus referencias en Django.'

    def handle(self, *args, **options):
        if not settings.SUPABASE_URL or not settings.SUPABASE_STORAGE_KEY:
            raise CommandError('Configura SUPABASE_URL y SUPABASE_STORAGE_KEY antes de continuar.')

        raiz = Path(settings.MEDIA_ROOT)
        prefijo = default_storage.prefijo
        productos = list(
            Producto.objects.exclude(imagen__startswith=prefijo)
            .exclude(imagen__isnull=True).exclude(imagen='').values_list('pk', 'sku', 'imagen')
        )
        banners = list(Banner.objects.exclude(imagen__startswith=prefijo).values_list(
            'posicion', 'imagen',
        ))
        faltantes = [
            f'{sku}: {nombre}' for _, sku, nombre in productos if not (raiz / nombre).is_file()
        ]
        faltantes += [
            f'Banner {posicion}: {nombre}'
            for posicion, nombre in banners if nombre and not (raiz / nombre).is_file()
        ]
        predeterminadas = {
            posicion: settings.BASE_DIR / 'static' / 'img' / f'banner-{posicion}.jpg'
            for posicion in range(1, len(BANNERS_PREDETERMINADOS) + 1)
        }
        faltantes += [ruta.name for ruta in predeterminadas.values() if not ruta.is_file()]
        if faltantes:
            raise CommandError('Recupera estos archivos antes de migrar:\n' + '\n'.join(faltantes))

        rutas_productos = {raiz / nombre for _, _, nombre in productos}
        rutas_productos.update(
            ruta for ruta in (raiz / 'productos').rglob('*')
            if ruta.is_file() and ruta.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif', '.bmp', '.tiff', '.tif', '.ico'}
        )
        rutas_banners = {posicion: raiz / nombre for posicion, nombre in banners if nombre}
        try:
            copias = {
                ruta: default_storage.trasladar(ruta, 'productos') for ruta in sorted(rutas_productos)
            }
            copias_predeterminadas = {
                posicion: default_storage.trasladar(ruta, 'banners')
                for posicion, ruta in predeterminadas.items()
            }
            copias_banners = {
                posicion: default_storage.trasladar(ruta, 'banners')
                for posicion, ruta in rutas_banners.items()
            }
        except OSError as error:
            raise CommandError(str(error)) from error

        actualizados = 0
        with transaction.atomic():
            for pk, _, nombre in productos:
                actualizados += Producto.objects.filter(pk=pk, imagen=nombre).update(
                    imagen=copias[raiz / nombre],
                )
            for posicion, texto in enumerate(BANNERS_PREDETERMINADOS, 1):
                Banner.objects.get_or_create(
                    posicion=posicion,
                    defaults={'imagen': copias_predeterminadas[posicion], 'texto_alternativo': texto},
                )
            for posicion, nombre in banners:
                Banner.objects.filter(posicion=posicion, imagen=nombre).update(
                    imagen=copias_banners.get(posicion, copias_predeterminadas[posicion]),
                )
        self.stdout.write(self.style.SUCCESS(
            f'Imágenes copiadas. Productos actualizados: {actualizados}. Cuatro banners disponibles.'
        ))
