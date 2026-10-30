"""
URL configuration for PI project (PetShop).

CORREGIDO: el original solo tenía /admin/. Se agregan:
  - tiendaApp en la raíz (home, catálogo, fichas, registro)
  - webpay (flujo de pago Transbank)
  - django.contrib.auth.urls -> /cuenta/login, /cuenta/logout (RF-07)
  - servir archivos de media en desarrollo (imágenes de productos)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tiendaApp.urls')),                    # home, catálogo, fichas
    path('webpay/', include('webpay.urls')),                # pago Transbank
    path('cuenta/', include('django.contrib.auth.urls')),   # login / logout
]

# En desarrollo, las imágenes subidas (media/productos/) se sirven así.
# En producción esto lo hace el servidor web (nginx, etc.).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
