import hashlib
import mimetypes
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import uuid4

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage


class ErrorAlmacenamiento(OSError):
    pass


class AlmacenamientoImagenes(FileSystemStorage):
    prefijo = 'lopets/'

    def _url_objeto(self, nombre, publico=False):
        base = settings.SUPABASE_URL
        if not base:
            raise ErrorAlmacenamiento('Configura SUPABASE_URL para usar las imágenes de Lopets.')
        segmento = 'public/' if publico else ''
        bucket = quote(settings.SUPABASE_STORAGE_BUCKET, safe='')
        return f'{base}/storage/v1/object/{segmento}{bucket}/{quote(nombre)}'

    def _solicitud(self, metodo, nombre, *, datos=None, tipo=None, publico=False, upsert=False):
        url = self._url_objeto(nombre, publico)
        headers = {}
        if not publico:
            clave = settings.SUPABASE_STORAGE_KEY
            if not clave:
                raise ErrorAlmacenamiento('Configura SUPABASE_STORAGE_KEY para subir imágenes.')
            headers['apikey'] = clave
            if not clave.startswith('sb_secret_'):
                headers['Authorization'] = f'Bearer {clave}'
        if tipo:
            headers.update({'Content-Type': tipo, 'Cache-Control': 'max-age=3600'})
        if upsert:
            headers['x-upsert'] = 'true'

        try:
            respuesta = requests.request(
                metodo, url, headers=headers,
                data=datos, timeout=(5, 30), allow_redirects=False,
            )
        except requests.RequestException:
            raise ErrorAlmacenamiento('No hubo conexión con Supabase Storage.') from None
        if not 200 <= respuesta.status_code < 300:
            raise ErrorAlmacenamiento(f'Supabase Storage respondió HTTP {respuesta.status_code}.')
        return respuesta

    def _save(self, name, content):
        if not settings.SUPABASE_URL:
            return super()._save(name, content)
        ruta = PurePosixPath(name)
        extension = ruta.suffix.lower()
        tipo = getattr(content, 'content_type', None) or mimetypes.guess_type(name)[0]
        destino = f'{self.prefijo}{ruta.parent.name}/{uuid4().hex}{extension}'
        self._solicitud('POST', destino, datos=content.read(), tipo=tipo)
        return destino

    def url(self, name):
        if settings.SUPABASE_URL and name.startswith(self.prefijo):
            return self._url_objeto(name, publico=True)
        return super().url(name)

    def _open(self, name, mode='rb'):
        if name.startswith(self.prefijo):
            respuesta = self._solicitud('GET', name, publico=True)
            return ContentFile(respuesta.content, name=name)
        return super()._open(name, mode)

    def trasladar(self, ruta, carpeta):
        datos = ruta.read_bytes()
        huella = hashlib.sha256(datos).hexdigest()
        destino = f'{self.prefijo}{carpeta}/{huella}{ruta.suffix.lower()}'
        tipo = mimetypes.guess_type(destino)[0]
        self._solicitud('POST', destino, datos=datos, tipo=tipo, upsert=True)
        return destino
