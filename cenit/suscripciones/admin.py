from django.contrib import admin
from .models import TipoSuscripcion, Promocion, Suscripcion, Notificacion, Playlist, PlaylistCancion, EstadisticaDiaria

@admin.register(TipoSuscripcion)
class TipoSuscripcionAdmin(admin.ModelAdmin):
    list_display = ['idtipo', 'nombreplan', 'precio', 'moneda', 'duracion']

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ['idpromo', 'descripcion', 'porcentajedesc', 'fechainicio', 'fechaexpira', 'estadoactivo', 'tiposuscripcion']

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ['idsuscripcion', 'fechainicio', 'fechafin', 'estado', 'usuario', 'tiposuscripcion', 'promocion']

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['idnotificacion', 'tiponotif', 'mensaje', 'fechaenvio', 'usuario', 'promocion']

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['idplaylist', 'nombre', 'descripcion', 'esprivada', 'espublicada', 'fechacreacion', 'usuario']

@admin.register(PlaylistCancion)
class PlaylistCancionAdmin(admin.ModelAdmin):
    list_display = ['playlist', 'cancion', 'fechaadicion', 'orden']

@admin.register(EstadisticaDiaria)
class EstadisticaDiariaAdmin(admin.ModelAdmin):
    list_display = ['idestat', 'totalrepros', 'fechareporte', 'cancion']