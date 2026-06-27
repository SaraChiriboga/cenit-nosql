from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from catalogo import views as catalogo_views
from usuarios.views import login_admin_view, login_analista_view, login_player_view

urlpatterns = [
    # Ruta raíz del sitio web


    # Rutas del módulo de catálogo
    path('catalogo/', include('catalogo.urls')),

    # Rutas de autenticación — cada una valida el rol antes de permitir acceso
    path('login/',          login_admin_view,    name='login'),
    path('login/analista/', login_analista_view, name='login_analista'),
    path('login/player/',   login_player_view,   name='login_player'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # El cuarto de máquinas
    path('admin/', admin.site.urls),

    # Conexión a la app de suscripciones
    path('suscripciones/', include('suscripciones.urls')),

    # Conexión a la app de usuarios (¡Esta es la única línea que necesitas aquí!)
    path('usuarios/', include('usuarios.urls')),

    # Conexión a la app de reproductor web
    path('player/', include('reproductor.urls')),

    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
]