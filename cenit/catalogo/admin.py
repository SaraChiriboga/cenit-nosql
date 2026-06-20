from django.contrib import admin
from .models import Cancion, Genero, Artista, Album, Colaboracion

@admin.register(Artista)
class ArtistaAdmin(admin.ModelAdmin):
    list_display = ['idartista', 'nombreartistico', 'paisorigen', 'estadoactivo']

@admin.register(Genero)
class GeneroAdmin(admin.ModelAdmin):
    list_display = ['idgenero', 'nombregenero', 'descripcion']

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    # ANTES: 'artista_idartista' -> AHORA: 'artista'
    list_display = ['idalbum', 'tituloalbum', 'fechalanzamiento', 'artista']

@admin.register(Cancion)
class CancionAdmin(admin.ModelAdmin):
    # ANTES: 'album_idalbum' -> AHORA: 'album'
    list_display = ['idcancion', 'titulocancion', 'duracionseg', 'esexplicita', 'estadopublicacion', 'album', 'genero']

@admin.register(Colaboracion)
class ColaboracionAdmin(admin.ModelAdmin):
    # ANTES: 'cancion_idcancion', 'artista_idartista' -> AHORA: 'cancion', 'artista'
    list_display = ['idcolaboracion', 'cancion', 'artista', 'rolartista']