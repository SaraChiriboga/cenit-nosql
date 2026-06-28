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
    path('reportes/vencimientos/',          views.reporte_vencimientos,           name='reporte_vencimientos'),
    path('reportes/vencimientos/pdf/',      views.exportar_vencimientos_pdf,       name='exportar_vencimientos_pdf'),
    path('reportes/vencimientos/excel/',    views.exportar_vencimientos_excel,     name='exportar_vencimientos_excel'),
    path('reportes/vencimientos/correo/',   views.enviar_vencimientos_correo,      name='enviar_vencimientos_correo'),

    path('reportes/promociones-vencidas/',          views.reporte_promociones_vencidas,          name='reporte_promociones_vencidas'),
    path('reportes/promociones-vencidas/pdf/',      views.exportar_promociones_vencidas_pdf,      name='exportar_promociones_vencidas_pdf'),
    path('reportes/promociones-vencidas/excel/',    views.exportar_promociones_vencidas_excel,    name='exportar_promociones_vencidas_excel'),
    path('reportes/promociones-vencidas/correo/',   views.enviar_promociones_vencidas_correo,   name='enviar_promociones_vencidas_correo'),

    path('reportes/usuarios-premium/',          views.reporte_usuarios_premium,          name='reporte_usuarios_premium'),
    path('reportes/usuarios-premium/pdf/',      views.exportar_usuarios_premium_pdf,      name='exportar_usuarios_premium_pdf'),
    path('reportes/usuarios-premium/excel/',    views.exportar_usuarios_premium_excel,    name='exportar_usuarios_premium_excel'),
    path('reportes/usuarios-premium/correo/',   views.enviar_usuarios_premium_correo,   name='enviar_usuarios_premium_correo'),

    path('reportes/usuarios-free/',          views.reporte_usuarios_free,          name='reporte_usuarios_free'),
    path('reportes/usuarios-free/pdf/',      views.exportar_usuarios_free_pdf,      name='exportar_usuarios_free_pdf'),
    path('reportes/usuarios-free/excel/',    views.exportar_usuarios_free_excel,    name='exportar_usuarios_free_excel'),
    path('reportes/usuarios-free/correo/',   views.enviar_usuarios_free_correo,   name='enviar_usuarios_free_correo'),

    path('reportes/accesos-fallidos/',          views.reporte_accesos_fallidos,          name='reporte_accesos_fallidos'),
    path('reportes/accesos-fallidos/pdf/',      views.exportar_accesos_fallidos_pdf,      name='exportar_accesos_fallidos_pdf'),
    path('reportes/accesos-fallidos/excel/',    views.exportar_accesos_fallidos_excel,    name='exportar_accesos_fallidos_excel'),
    path('reportes/accesos-fallidos/correo/',   views.enviar_accesos_fallidos_correo,   name='enviar_accesos_fallidos_correo'),

    path('reportes/acciones-admin/',          views.reporte_acciones_admin,          name='reporte_acciones_admin'),
    path('reportes/acciones-admin/pdf/',      views.exportar_acciones_admin_pdf,      name='exportar_acciones_admin_pdf'),
    path('reportes/acciones-admin/excel/',    views.exportar_acciones_admin_excel,    name='exportar_acciones_admin_excel'),
    path('reportes/acciones-admin/correo/',   views.enviar_acciones_admin_correo,   name='enviar_acciones_admin_correo'),

    # ── DASHBOARD ANALISTA ──
    path('reportes/dashboard/',      views.analista_dashboard,     name='analista_dashboard'),
    path('reportes/dashboard/data/', views.analista_dashboard_data, name='analista_dashboard_data'),

    # ── REPORTES PERSONALIZADOS ──
    path('reportes/crear/', views.crear_reporte_hub, name='crear_reporte_hub'),
    path('reportes/crear/mongodb/', views.crear_reporte_mongodb, name='crear_reporte_mongodb'),
    path('reportes/crear/powerbi/', views.crear_reporte_powerbi, name='crear_reporte_powerbi'),
    path('reportes/crear/ia/', views.crear_reporte_ia, name='crear_reporte_ia'),
    path('reportes/ver/<str:report_id>/', views.ver_reporte_personalizado, name='ver_reporte_personalizado'),
    
    path('reportes/api/ejecutar-mongo/', views.ejecutar_query_mongo_api, name='ejecutar_query_mongo_api'),
    path('reportes/api/ia-query/', views.ia_generar_query_api, name='ia_generar_query_api'),
    path('reportes/api/guardar/', views.guardar_reporte_api, name='guardar_reporte_api'),
    
    path('reportes/exportar/dinamico/pdf/', views.exportar_reporte_dinamico_pdf, name='exportar_reporte_dinamico_pdf'),
    path('reportes/exportar/dinamico/excel/', views.exportar_reporte_dinamico_excel, name='exportar_reporte_dinamico_excel'),
    path('reportes/exportar/dinamico/correo/', views.enviar_reporte_dinamico_correo, name='enviar_reporte_dinamico_correo'),
    path('reportes/eliminar/<str:report_id>/', views.eliminar_reporte, name='eliminar_reporte'),
]