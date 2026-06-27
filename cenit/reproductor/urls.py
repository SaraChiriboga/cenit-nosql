from django.urls import path
from . import views

urlpatterns = [
    path('', views.player_home, name='player_home'),
    path('api/playlist/create/', views.crear_playlist, name='player_crear_playlist'),
    path('api/playlist/add/', views.agregar_cancion_playlist, name='player_add_cancion'),
    path('api/playlist/remove/', views.quitar_cancion_playlist, name='player_remove_cancion'),
    path('api/favorite/toggle/', views.toggle_favorito, name='player_toggle_favorito'),
    path('api/follow/toggle/', views.toggle_seguimiento, name='player_toggle_seguimiento'),
]
