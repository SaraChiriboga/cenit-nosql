import json
import datetime
from bson import ObjectId
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from cenit.mongo_client import db
import requests

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
                'url_audio': d.get('urlDeezerPreview') or '',
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
        
        es_publicada = data.get("esPublicada", True)
        es_privada = not es_publicada
        imagen_portada = data.get("imagenPortada", "")

        playlist_doc = {
            "idPlaylist": new_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "esPrivada": es_privada,
            "esPublicada": es_publicada,
            "imagenPortada": imagen_portada,
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

@login_required(login_url='login_player')
def get_song_preview(request, cancion_id):
    try:
        # Find the song in MongoDB
        cancion_doc = db["Cancion"].find_one({"cancion_id": int(cancion_id)})
        if not cancion_doc:
            return JsonResponse({"status": "error", "message": "Canción no encontrada."}, status=404)

        # If we already have a cached Deezer preview URL in the document, use it!
        preview_url = cancion_doc.get("urlDeezerPreview")
        if preview_url:
            return JsonResponse({"status": "success", "preview_url": preview_url})

        # Otherwise, fetch it on the fly from Deezer
        # 1. Get artist name
        colabs = cancion_doc.get("colaboradores", [])
        artista_nombre = "Artista"
        for c in colabs:
            if c.get("rolArtista") == "Principal":
                artista_nombre = c.get("nombreArtista", "Artista")
                break
        else:
            if colabs:
                artista_nombre = colabs[0].get("nombreArtista", "Artista")

        titulo = cancion_doc.get("tituloCancion", "")

        # 2. Query Deezer
        deezer_url = "https://api.deezer.com/search"
        params = {"q": f"{titulo} {artista_nombre}", "limit": 1}
        r = requests.get(deezer_url, params=params, timeout=5)
        deezer_data = r.json().get('data', [])
        
        if deezer_data:
            preview_url = deezer_data[0].get('preview')
            # Cache it in the Mongo document
            db["Cancion"].update_one(
                {"cancion_id": int(cancion_id)},
                {"$set": {"urlDeezerPreview": preview_url}}
            )
            return JsonResponse({"status": "success", "preview_url": preview_url})

        return JsonResponse({"status": "success", "preview_url": None})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

# -------------------------------------------------------------
# TEMPLATE-BASED PARTIAL VIEWS (SPA-AJAX)
# -------------------------------------------------------------
@login_required(login_url='login_player')
def player_home_view(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        # Determine greeting
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting = "Buenos días"
        elif hour < 18:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"

        # Playlists
        playlists_cursor = db["playlists"].find({
            "$or": [
                {"idUsuario": user_id},
                {"esPublicada": True}
            ]
        })
        all_playlists = []
        for p in playlists_cursor:
            all_playlists.append({
                "id": str(p["_id"]),
                "nombre": p.get("nombre", ""),
                "descripcion": p.get("descripcion", ""),
                "imagen_portada": p.get("imagenPortada", ""),
                "canciones": p.get("canciones", []),
            })

        # Artists (Loaded first to map names to albums and avoid N+1 queries)
        artistas_cursor = list(db["Artista"].find({"estadoActivo": "Vigente"}))
        artists_map = {art.get("artista_id"): art.get("nombreArtistico", "Artista") for art in artistas_cursor}
        
        artistas = []
        for art in artistas_cursor:
            artistas.append({
                "id": art.get("artista_id"),
                "nombre": art.get("nombreArtistico", ""),
                "url_perfil": art.get("urlPerfil", ""),
            })

        # Albums
        albums_cursor = db["Album"].find()
        albumes = []
        for al in albums_cursor:
            art_name = artists_map.get(al.get("artista_id"), "Artista")
            albumes.append({
                "id": al.get("album_id"),
                "titulo": al.get("tituloAlbum", ""),
                "url_portada": al.get("urlPortada", ""),
                "artista_id": al.get("artista_id"),
                "artista_name": art_name,
            })

        # New releases (songs)
        songs_cursor = db["Cancion"].find({"estadoPublicacion": "Publicada"}).sort("cancion_id", -1).limit(8)
        new_songs = []
        for s in songs_cursor:
            colabs = s.get("colaboradores", [])
            artist_name = "Artista"
            for c in colabs:
                if c.get("rolArtista") == "Principal":
                    artist_name = c.get("nombreArtista", "Artista")
                    break
            new_songs.append({
                "id": s.get("cancion_id"),
                "titulo": s.get("tituloCancion", ""),
                "url_portada": s.get("urlPortada", ""),
                "artista": artist_name,
            })

        # Quick access items (first 6 combinations of playlists/songs)
        quick_items = []
        for p in all_playlists[:3]:
            quick_items.append({
                "type": "playlist",
                "id": p["id"],
                "title": p["nombre"],
                "cover": p["imagen_portada"]
            })
        for s in new_songs[:3]:
            quick_items.append({
                "type": "song",
                "id": s["id"],
                "title": s["titulo"],
                "cover": s["url_portada"]
            })

        context = {
            "greeting": greeting,
            "quick_items": quick_items,
            "all_playlists": all_playlists,
            "albumes": albumes,
            "artistas": artistas,
            "new_songs": new_songs,
        }
        return render(request, 'reproductor/views/home.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
def player_search_view(request):
    return render(request, 'reproductor/views/search.html')

@login_required(login_url='login_player')
def player_library_view(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        # Favorites
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]
        favoritas = []
        if favoritas_ids:
            songs_cursor = db["Cancion"].find({"cancion_id": {"$in": favoritas_ids}})
            for s in songs_cursor:
                colabs = s.get("colaboradores", [])
                artist_name = "Artista"
                for c in colabs:
                    if c.get("rolArtista") == "Principal":
                        artist_name = c.get("nombreArtista", "Artista")
                        break
                favoritas.append({
                    "id": s.get("cancion_id"),
                    "titulo": s.get("tituloCancion", ""),
                    "url_portada": s.get("urlPortada", ""),
                    "artista": artist_name,
                    "duracion": s.get("duracionSeg", 180),
                })

        # Followed artists
        seguidos_cursor = db["seguimientos"].find({"idUsuario": user_id, "activo": 1})
        seguidos_ids = [s.get("idArtista") for s in seguidos_cursor]
        artistas_seguidos = []
        if seguidos_ids:
            artists_cursor = db["Artista"].find({"artista_id": {"$in": seguidos_ids}})
            for art in artists_cursor:
                artistas_seguidos.append({
                    "id": art.get("artista_id"),
                    "nombre": art.get("nombreArtistico", ""),
                    "url_perfil": art.get("urlPerfil", ""),
                })

        # User Playlists
        playlists_cursor = db["playlists"].find({"idUsuario": user_id})
        user_playlists = []
        for p in playlists_cursor:
            user_playlists.append({
                "id": str(p["_id"]),
                "nombre": p.get("nombre", ""),
                "descripcion": p.get("descripcion", ""),
                "imagen_portada": p.get("imagenPortada", ""),
                "canciones": p.get("canciones", []),
            })

        context = {
            "favoritas": favoritas,
            "artistas_seguidos": artistas_seguidos,
            "user_playlists": user_playlists,
        }
        return render(request, 'reproductor/views/library.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
def player_artist_view(request, artist_id):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        artist = db["Artista"].find_one({"artista_id": int(artist_id)})
        if not artist:
            return HttpResponse("Artista no encontrado", status=404)

        # Check followed
        seg = db["seguimientos"].find_one({"idUsuario": user_id, "idArtista": int(artist_id), "activo": 1})
        is_following = seg is not None

        # Songs
        songs_cursor = db["Cancion"].find({
            "colaboradores.artista_id": int(artist_id),
            "estadoPublicacion": "Publicada"
        }).limit(5)
        popular_tracks = []
        for s in songs_cursor:
            colabs = s.get("colaboradores", [])
            artist_name = "Artista"
            for c in colabs:
                if c.get("rolArtista") == "Principal":
                    artist_name = c.get("nombreArtista", "Artista")
                    break
            
            dur = int(s.get("duracionSeg", 0))
            minutes = dur // 60
            seconds = dur % 60
            dur_formatted = f"{minutes}:{seconds:02d}"

            popular_tracks.append({
                "id": s.get("cancion_id"),
                "titulo": s.get("tituloCancion", ""),
                "url_portada": s.get("urlPortada", ""),
                "artista": artist_name,
                "duracion_formatted": dur_formatted,
            })

        # Albums
        albums_cursor = db["Album"].find({"artista_id": int(artist_id)})
        artist_albums = []
        for al in albums_cursor:
            artist_albums.append({
                "id": al.get("album_id"),
                "titulo": al.get("tituloAlbum", ""),
                "url_portada": al.get("urlPortada", ""),
            })

        # Favorites ids list for user
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]

        # Related artists (Fans also like)
        other_artists_cursor = db["Artista"].find({"artista_id": {"$ne": int(artist_id)}, "estadoActivo": "Vigente"}).limit(3)
        fans_like = []
        for oa in other_artists_cursor:
            fans_like.append({
                "id": oa.get("artista_id"),
                "nombre": oa.get("nombreArtistico", ""),
                "url_perfil": oa.get("urlPerfil", ""),
            })

        context = {
            "artist": {
                "id": artist.get("artista_id"),
                "nombre": artist.get("nombreArtistico"),
                "url_perfil": artist.get("urlPerfil"),
                "pais": artist.get("paisOrigen"),
                "biografia": artist.get("biografia"),
            },
            "is_following": is_following,
            "popular_tracks": popular_tracks,
            "artist_albums": artist_albums,
            "fans_like": fans_like,
            "favoritas_ids": favoritas_ids,
        }
        return render(request, 'reproductor/views/artist_profile.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
def player_playlist_doc_view(request, playlist_id):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        playlist = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        if not playlist:
            return HttpResponse("Playlist no encontrada", status=404)

        is_owner = playlist.get("idUsuario") == user_id

        # Get creator name
        creator = db["usuarios"].find_one({"id": playlist.get("idUsuario")})
        owner_name = f"{creator.get('nombre', 'Usuario')} {creator.get('apellido', '')}" if creator else "Usuario"

        # Songs
        songs_list = []
        total_seconds = 0
        for pe in playlist.get("canciones", []):
            s = db["Cancion"].find_one({"cancion_id": int(pe.get("idCancion"))})
            if s:
                colabs = s.get("colaboradores", [])
                artist_name = "Artista"
                artista_id = 0
                for c in colabs:
                    if c.get("rolArtista") == "Principal":
                        artist_name = c.get("nombreArtista", "Artista")
                        artista_id = c.get("idArtista", 0)
                        break

                dur = int(s.get("duracionSeg", 0))
                total_seconds += dur
                minutes = dur // 60
                seconds = dur % 60
                dur_formatted = f"{minutes}:{seconds:02d}"

                # Find album name
                album = db["Album"].find_one({"album_id": s.get("album_id")})
                album_name = album.get("tituloAlbum", "Sencillo") if album else "Sencillo"

                # Relative date added formatting
                formatted_date_added = "Hace tiempo"
                if pe.get("fechaAdicion"):
                    try:
                        added_date = datetime.datetime.fromisoformat(pe.get("fechaAdicion"))
                        diff = datetime.datetime.now() - added_date
                        if diff.days <= 1:
                            formatted_date_added = "Hoy"
                        elif diff.days == 2:
                            formatted_date_added = "Ayer"
                        elif diff.days < 7:
                            formatted_date_added = f"Hace {diff.days} días"
                        elif diff.days < 30:
                            weeks = diff.days // 7
                            formatted_date_added = f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
                        else:
                            months = diff.days // 30
                            formatted_date_added = f"Hace {months} me{'ses' if months > 1 else 's'}"
                    except Exception:
                        pass

                songs_list.append({
                    "id": s.get("cancion_id"),
                    "titulo": s.get("tituloCancion"),
                    "artista": artist_name,
                    "artista_id": artista_id,
                    "url_portada": s.get("urlPortada"),
                    "album_id": s.get("album_id"),
                    "album_name": album_name,
                    "duracion_formatted": dur_formatted,
                    "formatted_date_added": formatted_date_added,
                })

        # Calculate duration text
        total_min = total_seconds // 60
        total_hr = total_min // 60
        rem_min = total_min % 60
        duration_text = f"{total_hr} h {rem_min} min" if total_hr > 0 else f"{total_min} min"

        # Favorites ids list for user
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]

        context = {
            "playlist": {
                "id": str(playlist["_id"]),
                "nombre": playlist.get("nombre"),
                "descripcion": playlist.get("descripcion"),
                "imagen_portada": playlist.get("imagenPortada"),
                "esPublicada": playlist.get("esPublicada"),
            },
            "is_owner": is_owner,
            "owner_name": owner_name,
            "songs": songs_list,
            "duration_text": duration_text,
            "favoritas_ids": favoritas_ids,
        }
        return render(request, 'reproductor/views/playlist_detail.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
def player_album_view(request, album_id):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        album = db["Album"].find_one({"album_id": int(album_id)})
        if not album:
            return HttpResponse("Álbum no encontrado", status=404)

        # Get artist name
        art = db["Artista"].find_one({"artista_id": album.get("artista_id")})
        artist_name = art.get("nombreArtistico", "Artista") if art else "Artista"

        # Songs
        songs_cursor = db["Cancion"].find({"album_id": int(album_id), "estadoPublicacion": "Publicada"})
        songs_list = []
        for s in songs_cursor:
            colabs = s.get("colaboradores", [])
            artist_name_s = "Artista"
            for c in colabs:
                if c.get("rolArtista") == "Principal":
                    artist_name_s = c.get("nombreArtista", "Artista")
                    break

            dur = int(s.get("duracionSeg", 0))
            minutes = dur // 60
            seconds = dur % 60
            dur_formatted = f"{minutes}:{seconds:02d}"

            songs_list.append({
                "id": s.get("cancion_id"),
                "titulo": s.get("tituloCancion"),
                "artista": artist_name_s,
                "url_portada": s.get("urlPortada"),
                "duracion_formatted": dur_formatted,
            })

        # Favorites ids list for user
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]

        context = {
            "album": {
                "id": album.get("album_id"),
                "titulo": album.get("tituloAlbum"),
                "url_portada": album.get("urlPortada"),
                "artista_id": album.get("artista_id"),
            },
            "artist_name": artist_name,
            "songs": songs_list,
            "favoritas_ids": favoritas_ids,
        }
        return render(request, 'reproductor/views/album_detail.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
def player_favorites_view(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")

        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        favoritas_ids = [f.get("idCancion") for f in fav_docs]
        
        songs_list = []
        if favoritas_ids:
            songs_cursor = db["Cancion"].find({"cancion_id": {"$in": favoritas_ids}})
            for s in songs_cursor:
                colabs = s.get("colaboradores", [])
                artist_name = "Artista"
                artista_id = 0
                for c in colabs:
                    if c.get("rolArtista") == "Principal":
                        artist_name = c.get("nombreArtista", "Artista")
                        artista_id = c.get("idArtista", 0)
                        break

                dur = int(s.get("duracionSeg", 180))
                minutes = dur // 60
                seconds = dur % 60
                dur_formatted = f"{minutes}:{seconds:02d}"

                album = db["Album"].find_one({"album_id": s.get("album_id")})
                album_name = album.get("tituloAlbum", "Sencillo") if album else "Sencillo"

                songs_list.append({
                    "id": s.get("cancion_id"),
                    "titulo": s.get("tituloCancion"),
                    "artista": artist_name,
                    "artista_id": artista_id,
                    "url_portada": s.get("urlPortada"),
                    "album_id": s.get("album_id"),
                    "album_name": album_name,
                    "duracion_formatted": dur_formatted,
                })

        context = {
            "songs": songs_list,
            "favoritas_ids": favoritas_ids,
        }
        return render(request, 'reproductor/views/favorites_detail.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
@require_POST
def editar_playlist(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        playlist_id = data.get("playlist_id")
        nombre = data.get("nombre", "").strip()
        descripcion = data.get("descripcion", "").strip()
        es_publicada = data.get("esPublicada", False)
        imagen_portada = data.get("imagenPortada", "")
        
        if not playlist_id:
            return JsonResponse({"status": "error", "message": "Falta ID de playlist."}, status=400)
            
        if not nombre:
            return JsonResponse({"status": "error", "message": "El nombre no puede estar vacío."}, status=400)
            
        from bson import ObjectId
        playlist_doc = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        if not playlist_doc:
            return JsonResponse({"status": "error", "message": "Playlist no encontrada."}, status=404)
            
        if playlist_doc.get("idUsuario") != user_id:
            return JsonResponse({"status": "error", "message": "No tienes permiso para editar esta playlist."}, status=403)
            
        update_fields = {
            "nombre": nombre,
            "descripcion": descripcion,
            "esPublicada": es_publicada,
            "esPrivada": not es_publicada,
        }
        if imagen_portada:
            update_fields["imagenPortada"] = imagen_portada
            
        db["playlists"].update_one(
            {"_id": ObjectId(playlist_id)},
            {"$set": update_fields}
        )
        
        # Get updated playlist
        updated_doc = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        updated_doc["id"] = str(updated_doc["_id"])
        
        return JsonResponse({"status": "success", "playlist": updated_doc}, encoder=MongoEncoder)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def eliminar_playlist(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        playlist_id = data.get("playlist_id")
        
        if not playlist_id:
            return JsonResponse({"status": "error", "message": "Falta ID de playlist."}, status=400)
            
        from bson import ObjectId
        playlist_doc = db["playlists"].find_one({"_id": ObjectId(playlist_id)})
        if not playlist_doc:
            return JsonResponse({"status": "error", "message": "Playlist no encontrada."}, status=404)
            
        if playlist_doc.get("idUsuario") != user_id:
            return JsonResponse({"status": "error", "message": "No tienes permiso para eliminar esta playlist."}, status=403)
            
        db["playlists"].delete_one({"_id": ObjectId(playlist_id)})
        return JsonResponse({"status": "success", "message": "Playlist eliminada correctamente."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def registrar_reproduccion(request):
    try:
        data = json.loads(request.body)
        cancion_id = data.get("cancion_id")
        if not cancion_id:
            return JsonResponse({"status": "error", "message": "Falta ID de canción."}, status=400)
            
        import datetime
        today_str = datetime.date.today().isoformat()
        
        # Increment play counts in estadisticasDiarias
        db["estadisticasDiarias"].update_one(
            {"idCancion": int(cancion_id), "fechaReporte": today_str},
            {"$inc": {"totalRepros": 1}},
            upsert=True
        )
        
        return JsonResponse({"status": "success", "message": "Reproducción registrada correctamente."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
def player_settings_view(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        # User details
        user_doc = db["usuarios"].find_one({"id": user_id})
        
        # Subscription details
        sub_doc = db["suscripciones"].find_one({"idUsuario": user_id, "estado": {"$in": ["Activa", "Cancelada"]}})
        if sub_doc:
            if "tipoSuscripcion" in sub_doc and isinstance(sub_doc["tipoSuscripcion"], dict):
                sub_doc["tipoSuscripcion"]["id"] = sub_doc["tipoSuscripcion"].get("_id")
            if "promocion" in sub_doc and isinstance(sub_doc["promocion"], dict):
                sub_doc["promocion"]["id"] = sub_doc["promocion"].get("_id")
        
        # Followed artists
        follow_docs = list(db["seguimientos"].find({"idUsuario": user_id, "activo": 1}))
        
        # Favorite songs
        fav_docs = list(db["cancionesFavoritas"].find({"idUsuario": user_id}))
        fav_ids = [f.get("idCancion") for f in fav_docs]
        fav_songs = list(db["Cancion"].find({"cancion_id": {"$in": fav_ids}}))
        
        # Convert fav_songs to format used in UI
        fav_songs_list = []
        for s in fav_songs:
            colabs = s.get("colaboradores", [])
            artist_name = colabs[0].get("nombreArtista", "Artista") if colabs else "Artista"
            fav_songs_list.append({
                "id": s.get("cancion_id"),
                "titulo": s.get("tituloCancion", ""),
                "artista": artist_name
            })
            
        # Notifications
        notif_docs = list(db["notificaciones"].find({"idUsuario": user_id}))
        notif_docs.sort(key=lambda x: x.get("fechaEnvio", ""), reverse=True)
        
        # Auditoria Acceso
        audit_docs = list(db["auditoriaAcceso"].find({"idUsuario": user_id}))
        audit_docs.sort(key=lambda x: x.get("fechaHora", ""), reverse=True)
        audit_docs = audit_docs[:10]
        
        # Available premium plans
        planes = list(db["tipoSuscripciones"].find({"tipo_id": {"$ne": 1}}))
        
        context = {
            "user_profile": user_doc,
            "subscription": sub_doc,
            "followed_artists": follow_docs,
            "favorite_songs": fav_songs_list,
            "notifications": notif_docs,
            "audit_logs": audit_docs,
            "planes": planes,
        }
        return render(request, 'reproductor/views/settings.html', context)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_profile(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        nombre = data.get("nombre", "").strip()
        apellido = data.get("apellido", "").strip()
        email = data.get("email", "").strip()
        new_password = data.get("password", "").strip()
        
        if not nombre or not apellido or not email:
            return JsonResponse({"status": "error", "message": "Nombre, apellido y correo son requeridos."}, status=400)
            
        existing = db["usuarios"].find_one({"email": email, "id": {"$ne": user_id}})
        if existing:
            return JsonResponse({"status": "error", "message": "El correo ya está registrado por otro usuario."}, status=400)
            
        django_user = request.user
        django_user.first_name = nombre
        django_user.last_name = apellido
        django_user.email = email
        if new_password:
            django_user.set_password(new_password)
        django_user.save()
        
        from django.contrib.auth.hashers import make_password
        update_fields = {
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
        }
        if new_password:
            update_fields["contrasena"] = make_password(new_password)
            
        db["usuarios"].update_one(
            {"id": user_id},
            {"$set": update_fields}
        )
        
        if new_password:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, django_user)
            
        return JsonResponse({"status": "success", "message": "Perfil actualizado correctamente."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_upgrade(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        plan_id = int(data.get("plan_id", 2))
        
        existing = db["suscripciones"].find_one({"idUsuario": user_id, "estado": "Activa"})
        if existing:
            return JsonResponse({"status": "error", "message": "Ya tienes una suscripción Premium activa."}, status=400)
            
        import datetime
        today = datetime.date.today()
        fecha_inicio = today.isoformat() + "T00:00:00"
        fecha_fin = (today + datetime.timedelta(days=30)).isoformat() + "T00:00:00"
        
        plan_doc = db["tipoSuscripciones"].find_one({"tipo_id": plan_id})
        if not plan_doc:
            return JsonResponse({"status": "error", "message": "Plan no encontrado."}, status=404)
            
        tipo_embed = {
            '_id': plan_id,
            'nombrePlan': plan_doc['nombrePlan'],
            'precio': plan_doc['precio'],
        }
        
        promo_doc = db["promociones"].find_one({"tipoSuscripcion._id": plan_id, "estadoActivo": True})
        promo_embed = {'_id': None, 'descripcion': None, 'porcentajeDesc': None}
        if promo_doc:
            promo_embed = {
                '_id': promo_doc.get('promo_id'),
                'descripcion': promo_doc.get('descripcion'),
                'porcentajeDesc': promo_doc.get('porcentajeDesc'),
            }
            
        db["usuarios"].update_one(
            {"id": user_id},
            {"$set": {"estadoPlan": "Premium"}}
        )
        
        db["suscripciones"].insert_one({
            'fechaInicio':      fecha_inicio,
            'fechaFin':         fecha_fin,
            'estado':           'Activa',
            'idUsuario':        user_id,
            'tipoSuscripcion':  tipo_embed,
            'promocion':        promo_embed,
        })
        
        return JsonResponse({"status": "success", "message": f"Suscripción al plan {plan_doc['nombrePlan']} activada exitosamente."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_cancel(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        sub = db["suscripciones"].find_one({"idUsuario": user_id, "estado": "Activa"})
        if not sub:
            return JsonResponse({"status": "error", "message": "No tienes una suscripción activa para cancelar."}, status=400)
            
        db["suscripciones"].update_one(
            {"_id": sub["_id"]},
            {"$set": {"estado": "Cancelada"}}
        )
        
        return JsonResponse({"status": "success", "message": "Tu suscripción ha sido cancelada. Mantendrás el acceso Premium hasta el final de tu periodo de facturación actual."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_change_sub(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        new_plan_id = int(data.get("plan_id"))
        
        sub = db["suscripciones"].find_one({"idUsuario": user_id, "estado": "Activa"})
        if not sub:
            return JsonResponse({"status": "error", "message": "No tienes una suscripción activa para modificar."}, status=400)
            
        plan_doc = db["tipoSuscripciones"].find_one({"tipo_id": new_plan_id})
        if not plan_doc:
            return JsonResponse({"status": "error", "message": "Plan no encontrado."}, status=404)
            
        tipo_embed = {
            '_id': new_plan_id,
            'nombrePlan': plan_doc['nombrePlan'],
            'precio': plan_doc['precio'],
        }
        
        promo_doc = db["promociones"].find_one({"tipoSuscripcion._id": new_plan_id, "estadoActivo": True})
        promo_embed = {'_id': None, 'descripcion': None, 'porcentajeDesc': None}
        if promo_doc:
            promo_embed = {
                '_id': promo_doc.get('promo_id'),
                'descripcion': promo_doc.get('descripcion'),
                'porcentajeDesc': promo_doc.get('porcentajeDesc'),
            }
            
        db["suscripciones"].update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "tipoSuscripcion": tipo_embed,
                "promocion": promo_embed
            }}
        )
        
        return JsonResponse({"status": "success", "message": f"Suscripción actualizada exitosamente al plan {plan_doc['nombrePlan']}."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_privacy(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        make_public = data.get("make_public", False)
        
        db["usuarios"].update_one(
            {"id": user_id},
            {"$set": {"defaultPlaylistPrivacy": "public" if make_public else "private"}}
        )
        
        es_publicada = make_public
        es_privada = not make_public
        
        db["playlists"].update_many(
            {"idUsuario": user_id},
            {"$set": {
                "esPublicada": es_publicada,
                "esPrivada": es_privada
            }}
        )
        
        return JsonResponse({"status": "success", "message": "Preferencia de privacidad actualizada y aplicada a todas tus playlists."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_unfollow(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        artista_id = int(data.get("artista_id"))
        
        db["seguimientos"].update_one(
            {"idUsuario": user_id, "idArtista": artista_id},
            {"$set": {"activo": 0}}
        )
        
        return JsonResponse({"status": "success", "message": "Has dejado de seguir al artista."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_unfavorite(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        cancion_id = int(data.get("cancion_id"))
        
        db["cancionesFavoritas"].delete_one({"idUsuario": user_id, "idCancion": cancion_id})
        
        return JsonResponse({"status": "success", "message": "Canción removida de favoritas."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login_player')
@require_POST
def api_settings_notif_pref(request):
    try:
        mongo_user = _get_mongo_user(request.user)
        user_id = mongo_user.get("id")
        
        data = json.loads(request.body)
        pref = {
            "seguridad": data.get("seguridad", True),
            "lanzamientos": data.get("lanzamientos", True),
            "pagos": data.get("pagos", True)
        }
        
        db["usuarios"].update_one(
            {"id": user_id},
            {"$set": {"preferenciasNotificaciones": pref}}
        )
        
        return JsonResponse({"status": "success", "message": "Preferencias de notificaciones guardadas."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


