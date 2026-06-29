from django.urls import path
from . import views

urlpatterns = [
    path('', views.users_overview, name='users_overview'),
    path('nuevo/', views.add_user, name='add_user'),

    # ── Roles ──
    path('roles/', views.roles_overview, name='roles_overview'),
    path('roles/<str:idRol>/editar/', views.edit_role, name='edit_role'),
    path('roles/<str:idRol>/', views.read_role, name='read_role'),

    # ══════════════════════════════════════════
    #  AUDITORÍA DE ACCESO
    # ══════════════════════════════════════════
    path('auditoria/',                   views.auditoria_list,   name='auditoria_list'),
    path('auditoria/nuevo/',             views.auditoria_add,    name='auditoria_add'),
    path('auditoria/<str:pk>/eliminar/', views.auditoria_delete, name='auditoria_delete'),

    # ══════════════════════════════════════════
    #  SEGUIMIENTOS
    # ══════════════════════════════════════════
    path('seguimientos/',            views.seguimiento_list,   name='seguimiento_list'),
    path('seguimientos/nuevo/',      views.seguimiento_add,    name='seguimiento_add'),
    path('seguimientos/eliminar/',   views.seguimiento_delete, name='seguimiento_delete'),

    # ══════════════════════════════════════════
    #  CANCIONES FAVORITAS
    # ══════════════════════════════════════════
    path('favoritas/',           views.favorita_list,   name='favorita_list'),
    path('favoritas/nueva/',     views.favorita_add,    name='favorita_add'),
    path('favoritas/eliminar/',  views.favorita_delete, name='favorita_delete'),

    # ── Rutas Dinámicas de Usuarios (Deben ir al final para no atrapar rutas estáticas) ──
    path('<str:idUsuario>/', views.read_user, name='read_user'),
    path('<str:idUsuario>/editar/', views.edit_user, name='edit_user'),
    path('<str:idUsuario>/toggle/', views.toggle_user, name='toggle_user'),
]