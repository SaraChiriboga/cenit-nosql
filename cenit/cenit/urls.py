from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from catalogo import views as catalogo_views

urlpatterns = [
    # Ruta raíz del sitio web


    # Rutas del módulo de catálogo
    path('catalogo/', include('catalogo.urls')),

    # Rutas de autenticación
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('login/analista/', auth_views.LoginView.as_view(template_name='registration/login_analista.html'), name='login_analista'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # El cuarto de máquinas
    path('admin/', admin.site.urls),

    # Conexión a la app de suscripciones
    path('suscripciones/', include('suscripciones.urls')),

    # Conexión a la app de usuarios (¡Esta es la única línea que necesitas aquí!)
    path('usuarios/', include('usuarios.urls')),

    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
]