from django.urls import path
from . import views

urlpatterns = [

    # ══════════════════════════════════════════
    #  TIPOS DE SUSCRIPCIÓN  (PK numérica: tipo_id)
    # ══════════════════════════════════════════
    path('planes/',                 views.plan_list,   name='plan_list'),
    path('planes/nuevo/',           views.plan_add,    name='plan_add'),
    path('planes/<int:pk>/editar/', views.plan_edit,   name='plan_edit'),
    path('planes/<int:pk>/eliminar/', views.plan_delete, name='plan_delete'),

    # ══════════════════════════════════════════
    #  PROMOCIONES  (PK numérica: promo_id)
    # ══════════════════════════════════════════
    path('promociones/',                    views.promocion_list,   name='promocion_list'),
    path('promociones/nueva/',              views.promocion_add,    name='promocion_add'),
    path('promociones/<int:pk>/editar/',    views.promocion_edit,   name='promocion_edit'),
    path('promociones/<int:pk>/eliminar/',  views.promocion_delete, name='promocion_delete'),

    # ══════════════════════════════════════════
    #  SUSCRIPCIONES  (PK: ObjectId string)
    # ══════════════════════════════════════════
    path('suscripciones/',                   views.suscripcion_list,   name='suscripcion_list'),
    path('suscripciones/nueva/',             views.suscripcion_add,    name='suscripcion_add'),
    path('suscripciones/<str:pk>/editar/',   views.suscripcion_edit,   name='suscripcion_edit'),
    path('suscripciones/<str:pk>/eliminar/', views.suscripcion_delete, name='suscripcion_delete'),

    # ══════════════════════════════════════════
    #  NOTIFICACIONES  (PK: ObjectId string)
    # ══════════════════════════════════════════
    path('notificaciones/',                   views.notificacion_list,   name='notificacion_list'),
    path('notificaciones/nueva/',             views.notificacion_add,    name='notificacion_add'),
    path('notificaciones/<str:pk>/eliminar/', views.notificacion_delete, name='notificacion_delete'),

    # ══════════════════════════════════════════
    #  PLAYLISTS  (PK: ObjectId string)
    # ══════════════════════════════════════════
    path('playlists/',                             views.playlist_list,            name='playlist_list'),
    path('playlists/nueva/',                       views.playlist_add,             name='playlist_add'),
    path('playlists/<str:pk>/editar/',             views.playlist_edit,            name='playlist_edit'),
    path('playlists/<str:pk>/eliminar/',           views.playlist_delete,          name='playlist_delete'),
    path('playlists/<str:pk>/canciones/',          views.playlist_canciones,       name='playlist_canciones'),
    path('playlists/<str:pk>/canciones/agregar/',  views.playlist_cancion_agregar, name='playlist_cancion_agregar'),
    path('playlists/<str:pk>/canciones/quitar/',   views.playlist_cancion_quitar,  name='playlist_cancion_quitar'),

    # ══════════════════════════════════════════
    #  ESTADÍSTICAS DIARIAS  (PK: ObjectId string)
    # ══════════════════════════════════════════
    path('estadisticas/',                   views.estadistica_list,   name='estadistica_list'),
    path('estadisticas/nueva/',             views.estadistica_add,    name='estadistica_add'),
    path('estadisticas/<str:pk>/eliminar/', views.estadistica_delete, name='estadistica_delete'),

    # ══════════════════════════════════════════
    #  REPORTES
    # ══════════════════════════════════════════
    path('reportes/vencimientos/',          views.reporte_vencimientos,          name='reporte_vencimientos'),
    path('reportes/promociones-vencidas/',  views.reporte_promociones_vencidas,  name='reporte_promociones_vencidas'),
]