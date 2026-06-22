from django.urls import path
from . import views

urlpatterns = [
    # ── Canciones ──
    path('', views.songs_overview, name='songs_overview'),
    path('canciones/sync/<int:cancion_id>/', views.sync_spotify_track, name='sync_spotify_track'),
    path('api/search-spotify/', views.search_spotify_ajax, name='search_spotify_ajax'),
    path('api/check-existence/', views.check_existence, name='check_existence'),
    path('canciones/add/', views.add_track_ajax, name='add_track'),
    path('canciones/<int:pk>/edit/', views.edit_track, name='edit_track'),
    path('canciones/<int:pk>/', views.read_track, name='read_track'),
    path('canciones/<int:pk>/delete/', views.delete_track, name='delete_track'),

    # ── Artistas ──
    path('artistas/', views.artists_overview, name='artists_overview'),
    path('artistas/add/', views.add_artist, name='add_artist'),
    path('artistas/<int:pk>/', views.read_artist, name='read_artist'),
    path('artistas/<int:pk>/edit/', views.edit_artist, name='edit_artist'),
    path('artistas/<int:pk>/delete/', views.delete_artist, name='delete_artist'),
    path('artistas/add/', views.add_artist, name='artista_add'),
    path('ajax/search-artist/', views.search_artist_spotify_ajax, name='search_artist_spotify_ajax'),

    # ── Álbumes ──
    path('albumes/', views.albums_overview, name='albums_overview'),
    path('albumes/add/', views.add_album, name='add_album'),
    path('albumes/<int:pk>/', views.read_album, name='read_album'),
    path('albumes/<int:pk>/edit/', views.edit_album, name='edit_album'),
    path('albumes/<int:pk>/delete/', views.delete_album, name='delete_album'),
    path('ajax/search-album/', views.search_album_spotify_ajax, name='search_album_spotify_ajax'),

    # ── Géneros ──
    path('generos/', views.genre_overview, name='genre_overview'),
    path('generos/add/', views.add_genre, name='add_genre'),
    path('generos/<int:pk>/', views.read_genre, name='read_genre'),
    path('generos/<int:pk>/edit/', views.edit_genre, name='edit_genre'),
    path('generos/<int:pk>/delete/', views.delete_genre, name='delete_genre'),



    # ── Reportes específicos ──
    path('reportes/top-10/', views.reporte_top_10, name='reporte_top_10'),
    path('reportes/top-10/pdf/', views.exportar_top_10_pdf, name='exportar_top_10_pdf'),
    path('reportes/top-10/correo/', views.enviar_top_10_correo, name='enviar_top_10_correo'),

    path('reportes/auditoria-metadatos/', views.reporte_auditoria_catalogo, name='reporte_auditoria_catalogo'),
    path('reportes/auditoria-metadatos/pdf/', views.exportar_auditoria_pdf, name='exportar_auditoria_pdf'),
    path('reportes/auditoria-metadatos/correo/', views.enviar_auditoria_correo, name='enviar_auditoria_correo'),
]