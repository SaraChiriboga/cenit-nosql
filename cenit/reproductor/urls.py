from django.urls import path
from . import views

urlpatterns = [
    path('', views.player_home, name='player_home'),
    path('api/playlist/create/', views.crear_playlist, name='player_crear_playlist'),
    path('api/playlist/add/', views.agregar_cancion_playlist, name='player_add_cancion'),
    path('api/playlist/remove/', views.quitar_cancion_playlist, name='player_remove_cancion'),
    path('api/favorite/toggle/', views.toggle_favorito, name='player_toggle_favorito'),
    path('api/follow/toggle/', views.toggle_seguimiento, name='player_toggle_seguimiento'),
    path('api/song/<int:cancion_id>/preview/', views.get_song_preview, name='player_song_preview'),
    path('api/playlist/edit/', views.editar_playlist, name='player_editar_playlist'),
    path('api/playlist/delete/', views.eliminar_playlist, name='player_eliminar_playlist'),
    path('api/song/play/', views.registrar_reproduccion, name='player_registrar_reproduccion'),
    
    # Settings view and APIs
    path('view/settings/', views.player_settings_view, name='player_view_settings'),
    path('api/settings/profile/', views.api_settings_profile, name='api_settings_profile'),
    path('api/settings/upgrade/', views.api_settings_upgrade, name='api_settings_upgrade'),
    path('api/settings/cancel/', views.api_settings_cancel, name='api_settings_cancel'),
    path('api/settings/change-sub/', views.api_settings_change_sub, name='api_settings_change_sub'),
    path('api/settings/privacy/', views.api_settings_privacy, name='api_settings_privacy'),
    path('api/settings/unfollow/', views.api_settings_unfollow, name='api_settings_unfollow'),
    path('api/settings/unfavorite/', views.api_settings_unfavorite, name='api_settings_unfavorite'),
    path('api/settings/notif-preference/', views.api_settings_notif_pref, name='api_settings_notif_pref'),
    
    # Template-based sub-views
    path('view/home/', views.player_home_view, name='player_view_home'),
    path('view/search/', views.player_search_view, name='player_view_search'),
    path('view/library/', views.player_library_view, name='player_view_library'),
    path('view/artist/<int:artist_id>/', views.player_artist_view, name='player_view_artist'),
    path('view/playlist/<str:playlist_id>/', views.player_playlist_doc_view, name='player_view_playlist'),
    path('view/album/<int:album_id>/', views.player_album_view, name='player_view_album'),
    path('view/favorites/', views.player_favorites_view, name='player_view_favorites'),
]
