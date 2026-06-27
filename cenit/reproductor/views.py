from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from cenit.mongo_client import db

@login_required(login_url='login_player')
def player_home(request):
    try:
        # Consultamos las canciones publicadas de la base de datos MongoDB
        docs = list(db["Cancion"].find({"estadoPublicacion": "Publicado"}).limit(20))
        canciones = []
        
        for d in docs:
            colabs = d.get('colaboradores', [])
            artista_nombre = "Artista Desconocido"
            
            # Buscar el colaborador principal
            for c in colabs:
                if c.get('rolArtista') == 'Principal':
                    artista_nombre = c.get('nombreArtista')
                    break
            else:
                if colabs:
                    artista_nombre = colabs[0].get('nombreArtista')
            
            # Mapeamos los datos limpios para el reproductor
            canciones.append({
                'id': d.get('cancion_id') or str(d.get('_id')),
                'titulo': d.get('tituloCancion') or 'Sin título',
                'duracion': d.get('duracionSeg') or 180,
                'url_portada': d.get('urlPortada') or 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=150',
                'url_audio': d.get('urlSpotifyAPI') or '',
                'artista': artista_nombre,
            })
            
    except Exception as e:
        print("❌ ERROR EN PLAYER_HOME:", e)
        canciones = []

    return render(request, 'reproductor/player.html', {'canciones': canciones})
