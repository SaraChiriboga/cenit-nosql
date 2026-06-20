from django.contrib import admin
from .models import Usuario, Rol, AuditoriaAcceso, Seguimiento, CancionFavorita


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['idusuario', 'nombre', 'apellido', 'email', 'estadoplan', 'fecharegistro']


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['idrol', 'nombrerol', 'descripcion', 'usuario']


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ['idlog', 'accion', 'iporigen', 'rol']


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'artista', 'fechaseguimiento']


@admin.register(CancionFavorita)
class CancionFavoritaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'cancion', 'fechalike']