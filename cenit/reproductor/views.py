import json
import datetime
from bson import ObjectId
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from cenit.mongo_client import db

class MongoEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)

def _get_mongo_user(user):
    """Obtiene o crea el perfil de usuario en MongoDB."""
    mongo_user = db["usuarios"].find_one({"email": user.email})
    if not mongo_user:
        # Auto-incrementar el ID del usuario
        max_u = list(db["usuarios"].find().sort("id", -1).limit(1))
        new_id = (max_u[0].get("id", 0) + 1) if max_u else 1
        
        mongo_user = {
            "id": new_id,
            "nombre": user.first_name or user.username,
            "apellido": user.last_name or "",
            "email": user.email,
            "rol": {"id": 3, "nombreRol": "Usuario", "descripcion": "Usuario regular"},
            "fechaRegistro": datetime.datetime.now().isoformat()
        }
        db["usuarios"].insert_one(mongo_user)
    return mongo_user

@login_required(login_url='login_player')
def player_home(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        # 1. Canciones Publicadas
        docs_songs = list(db["Cancion"].find({"estadoPublicacion": "Publicada"}))
        canciones = []
        for d in docs_songs:
            colabs = d.get('colaboradores', [])
            artista_nombre = "Artista Desconocido"
            for c in colabs:
                if c.get('rolArtista') == 'Principal':
                    artista_nombre = c.get('nombreArtista')
                    break
            else:
                if colabs:
                    artista_nombre = colabs[0].get('nombreArtista')

            canciones.append({
                'id': d.get('cancion_id') or str(d.get('_id')),
                'titulo': d.get('tituloCancion') or 'Sin título',
                'duracion': d.get('duracionSeg') or 180,
                'url_portada': d.get('urlPortada') or '',
                'url_audio': d.get('urlSpotifyAPI') or '',
                'artista': artista_nombre,
                'artista_id': colabs[0].get('artista_id') if colabs else None,
                'album_id': d.get('album_id'),
                'esExplicita': d.get('esExplicita', False),
            })

        # 2. Artistas
        docs_artists = list(db["Artista"].find({"estadoActivo": "Vigente"}))
        artistas = []
        for a in docs_artists:
            artistas.append({
                'id': a.get('artista_id'),
                'nombre': a.get('nombreArtistico') or 'Artista',
                'biografia': a.get('biografia') or '',
                'pais': a.get('paisOrigen') or '',
                'url_perfil': a.get('urlPerfil') or '',
            })

        # 3. Álbumes
        docs_albums = list(db["Album"].find())
        albumes = []
        for al in docs_albums:
            albumes.append({
                'id': al.get('album_id'),
                'titulo': al.get('tituloAlbum') or 'Álbum',
                'url_portada': al.get('urlPortada') or '',
                'artista_id': al.get('artista_id'),
            })

        # 4. Playlists del usuario y públicas
        docs_playlists = list(db["playlists"].find({
            "$or": [
                {"idUsuario": user_id},
                {"esPublicada": True}
            ]
        }))
        
        user_playlists = []
        public_playlists = []
        for p in docs_playlists:
            p_data = {
                'id': str(p.get('_id')),
                'idPlaylist': p.get('idPlaylist'),
                'nombre': p.get('nombre') or 'Playlist',
                'descripcion': p.get('descripcion') or '',
                'imagen_portada': p.get('imagenPortada') or '',
                'idUsuario': p.get('idUsuario'),
                'esPublicada': p.get('esPublicada', False),
                'esPrivada': p.get('esPrivada', True),
                'canciones': p.get('canciones', []),
            }
            if p.get('idUsuario') == user_id:
                user_playlists.append(p_data)
            else:
                public_playlists.append(p_data)

        # 5. Canciones favoritas del usuario
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]

        # 6. Artistas seguidos por el usuario
        seg_docs = list(db["seguimientos"].find({"idUsuario": user_id, "activo": 1}))
        seguidos_ids = [s.get("idArtista") for s in seg_docs]

        # Serializar todo el payload de inicio
        player_data = {
            'currentUser': {
                'id': user_id,
                'nombre': mongo_user.get('nombre'),
                'apellido': mongo_user.get('apellido'),
                'email': mongo_user.get('email')
            },
            'canciones': canciones,
            'artistas': artistas,
            'albumes': albumes,
            'userPlaylists': user_playlists,
            'publicPlaylists': public_playlists,
            'favoritasIds': favoritas_ids,
            'seguidosIds': seguidos_ids,
        }
        
        player_data_json = json.dumps(player_data, cls=MongoEncoder)

    except Exception as e:
        print("❌ ERROR EN PLAYER_HOME:", e)
        player_data_json = "{}"

    return render(request, 'reproductor/player.html', {
        'player_data_json': player_data_json,
    })

@login_required(login_url='login_player')
@require_POST
def crear_playlist(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        nombre = data.get("nombre", "").strip()
        descripcion = data.get("descripcion", "").strip()
        
        if not nombre:
            return JsonResponse({"status": "error", "message": "El nombre es obligatorio."}, status=400)
            
        # Generar un ID único autoincremental para la playlist
        max_p = list(db["playlists"].find().sort("idPlaylist", -1).limit(1))
        new_id = (max_p[0].get("idPlaylist", 0) + 1) if max_p else 1
        
        playlist_doc = {
            "idPlaylist": new_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "esPrivada": False,
            "esPublicada": True,
            "imagenPortada": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300",
            "fechaCreacion": datetime.datetime.now().isoformat(),
            "idUsuario": user_id,
            "canciones": []
        }
        
        res = db["playlists"].insert_one(playlist_doc)
        playlist_doc["id"] = str(res.inserted_id)
        
        return JsonResponse({"status": "success", "playlist": playlist_doc}, encoder=MongoEncoder)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def agregar_cancion_playlist(request):
    try:
        data = json.loads(request.body)
        playlist_id = data.get("playlist_id")
        cancion_id = int(data.get("cancion_id"))
        
        playlist = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        if not playlist:
            return JsonResponse({"status": "error", "message": "Playlist no encontrada."}, status=404)
            
        # Validar si ya existe
        existing = any(c.get("idCancion") == cancion_id for c in playlist.get("canciones", []))
        if existing:
            return JsonResponse({"status": "error", "message": "La canción ya está en la playlist."}, status=400)
            
        new_song_entry = {
            "idCancion": cancion_id,
            "fechaAdicion": datetime.datetime.now().isoformat(),
            "orden": len(playlist.get("canciones", [])) + 1
        }
        
        db["playlists"].update_one(
            {"_id": ObjectId(playlist_id)},
            {"$push": {"canciones": new_song_entry}}
        )
        
        return JsonResponse({"status": "success", "entry": new_song_entry})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def quitar_cancion_playlist(request):
    try:
        data = json.loads(request.body)
        playlist_id = data.get("playlist_id")
        cancion_id = int(data.get("cancion_id"))
        
        playlist = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        if not playlist:
            return JsonResponse({"status": "error", "message": "Playlist no encontrada."}, status=404)
            
        # Re-indexar y re-ordenar canciones sin la canción eliminada
        canciones = playlist.get("canciones", [])
        nuevas_canciones = []
        orden = 1
        for c in canciones:
            if c.get("idCancion") != cancion_id:
                c["orden"] = orden
                nuevas_canciones.append(c)
                orden += 1
                
        db["playlists"].update_one(
            {"_id": ObjectId(playlist_id)},
            {"$set": {"canciones": nuevas_canciones}}
        )
        
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def toggle_favorito(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        cancion_id = int(data.get("cancion_id"))
        
        # Buscar la canción para obtener metadatos
        cancion_doc = db["Cancion"].find_one({"cancion_id": cancion_id})
        if not cancion_doc:
            return JsonResponse({"status": "error", "message": "Canción no encontrada."}, status=404)
            
        colabs = cancion_doc.get("colaboradores", [])
        artista_nombre = colabs[0].get("nombreArtista", "Desconocido") if colabs else "Desconocido"
        
        # Buscar el álbum si existe
        album_doc = db["Album"].find_one({"album_id": cancion_doc.get("album_id")})
        album_nombre = album_doc.get("tituloAlbum", "Sencillo") if album_doc else "Sencillo"
        
        existing = db["cancionesFavoritas"].find_one({"idUsuario": user_id, "idCancion": cancion_id})
        
        if existing:
            db["cancionesFavoritas"].delete_one({"_id": existing["_id"]})
            status = "removed"
        else:
            db["cancionesFavoritas"].insert_one({
                "idUsuario": user_id,
                "idCancion": cancion_id,
                "tituloCancion": cancion_doc.get("tituloCancion"),
                "artista": artista_nombre,
                "album": album_nombre,
                "fechaLike": datetime.datetime.now().isoformat()
            })
            status = "added"
            
        return JsonResponse({"status": "success", "action": status})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def toggle_seguimiento(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        artista_id = int(data.get("artista_id"))
        
        artista_doc = db["Artista"].find_one({"artista_id": artista_id})
        if not artista_doc:
            return JsonResponse({"status": "error", "message": "Artista no encontrado."}, status=404)
            
        existing = db["seguimientos"].find_one({"idUsuario": user_id, "idArtista": artista_id})
        
        if existing:
            nuevo_activo = 1 if existing.get("activo", 0) == 0 else 0
            db["seguimientos"].update_one(
                {"_id": existing["_id"]},
                {"$set": {"activo": nuevo_activo, "fechaSeguimiento": datetime.datetime.now().isoformat()}}
            )
            status = "followed" if nuevo_activo == 1 else "unfollowed"
        else:
            db["seguimientos"].insert_one({
                "idUsuario": user_id,
                "idArtista": artista_id,
                "nombreArtista": artista_doc.get("nombreArtistico"),
                "fechaSeguimiento": datetime.datetime.now().isoformat(),
                "activo": 1
            })
            status = "followed"
            
        return JsonResponse({"status": "success", "action": status})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
