from django.urls import path
from . import views

urlpatterns = [
    path('', views.player_home, name='player_home'),
]
