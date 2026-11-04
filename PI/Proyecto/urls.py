"""
URL configuration for PI project (PetShop).

CORREGIDO: el original solo tenía /admin/. Se agregan:
  - tiendaApp en la raíz (home, catálogo, fichas, carrito, vendedor)
  - webpay (flujo de pago Transbank)
  - django.contrib.auth.urls -> /cuenta/login y /cuenta/logout (RF-07)
  - servir archivos de media en desarrollo
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tiendaApp.urls')),                    # tienda completa
    path('webpay/', include('webpay.urls')),                # pago Transbank
    path('cuenta/', include('django.contrib.auth.urls')),   # login / logout
]

# En desarrollo, los archivos subidos (media/) se sirven así.
# En producción esto lo hace el servidor web (nginx, etc.).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
