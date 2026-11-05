"""
URL configuration for PI project (PetShop).

CORREGIDO: el original solo tenía /admin/. Se agregan:
  - tiendaApp en la raíz (home, catálogo, fichas, carrito, vendedor)
  - webpay (flujo de pago Transbank)
  - login/logout con formulario propio -> /cuenta/login y /cuenta/logout
    (RF-07: el cliente inicia sesión con su CORREO, no con username)
  - servir archivos de media en desarrollo
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from tiendaApp.forms import EntrarForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tiendaApp.urls')),                    # tienda completa
    path('webpay/', include('webpay.urls')),                # pago Transbank

    # Login/logout explícitos (antes: include('django.contrib.auth.urls')).
    # Se usa EntrarForm para que el campo diga "Correo electrónico o usuario"
    # y el mensaje de error salga en español. redirect_authenticated_user
    # evita que alguien ya logueado vuelva a ver el formulario.
    path('cuenta/login/', auth_views.LoginView.as_view(
            template_name='registration/login.html',
            form_class=EntrarForm,
            redirect_authenticated_user=True), name='login'),
    path('cuenta/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# En desarrollo, los archivos subidos (media/) se sirven así.
# En producción esto lo hace el servidor web (nginx, etc.).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
