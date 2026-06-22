import datetime
import secrets
import urllib
from io import BytesIO

import requests
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.views.decorators.http import require_POST
from weasyprint import HTML

from django.conf import settings
from django.db import connection
from .models import Cancion, Artista, Album, Genero, Colaboracion
from .spotify_service import SpotifyClient
import pymongo
from bson import ObjectId

# Configuración de MongoDB
MONGODB_URI = getattr(settings, "MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_NAME = getattr(settings, "MONGODB_NAME", "Cenit")

mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_NAME]

def map_genero(doc, cache=None):
    if not doc: return None
    return {
        'idgenero': doc.get('genero_id'),
        'genero_id': doc.get('genero_id'),
        'nombregenero': doc.get('nombreGenero'),
        'descripcion': doc.get('descripcion'),
    }

def map_artista(doc, cache=None):
    if not doc: return None
    return {
        'idartista': doc.get('artista_id'),
        'artista_id': doc.get('artista_id'),
        'nombreartistico': doc.get('nombreArtistico'),
        'biografia': doc.get('biografia'),
        'paisorigen': doc.get('paisOrigen'),
        'estadoactivo': doc.get('estadoActivo'),
        'fecharegistro': doc.get('fechaRegistro'),
        'urlperfil': doc.get('urlPerfil'),
    }

def map_album(doc, cache=None):
    if not doc: return None
    
    album_id = doc.get('album_id')
    if cache and album_id is not None:
        cached_album = cache.get('albumes', {}).get(int(album_id))
        if cached_album:
            return cached_album
            
    artista_data = doc.get('artista')
    if not artista_data and doc.get('artista_id') is not None:
        art_id = int(doc.get('artista_id'))
        if cache and art_id in cache.get('artistas', {}):
            artista_data = cache['artistas'][art_id]
        else:
            art_doc = db["Artista"].find_one({"artista_id": art_id})
            artista_data = map_artista(art_doc, cache)
            if cache:
                if 'artistas' not in cache: cache['artistas'] = {}
                cache['artistas'][art_id] = artista_data
    elif isinstance(artista_data, dict):
        artista_data = map_artista(artista_data, cache)
        
    return {
        'idalbum': doc.get('album_id'),
        'album_id': doc.get('album_id'),
        'tituloalbum': doc.get('tituloAlbum'),
        'fechalanzamiento': doc.get('fechaLanzamiento'),
        'urlportada': doc.get('urlPortada'),
        'artista_id': doc.get('artista_id'),
        'artista': artista_data,
    }

def map_cancion(doc, cache=None):
    if not doc: return None
    
    album_data = doc.get('album')
    if not album_data and doc.get('album_id') is not None:
        alb_id = int(doc.get('album_id'))
        if cache and alb_id in cache.get('albumes', {}):
            album_data = cache['albumes'][alb_id]
        else:
            alb_doc = db["Album"].find_one({"album_id": alb_id})
            album_data = map_album(alb_doc, cache)
            if cache:
                if 'albumes' not in cache: cache['albumes'] = {}
                cache['albumes'][alb_id] = album_data
    elif isinstance(album_data, dict):
        album_data = map_album(album_data, cache)
        
    genero_data = doc.get('genero')
    if not genero_data and doc.get('genero_id') is not None:
        gen_id = int(doc.get('genero_id'))
        if cache and gen_id in cache.get('generos', {}):
            genero_data = cache['generos'][gen_id]
        else:
            gen_doc = db["Genero"].find_one({"genero_id": gen_id})
            genero_data = map_genero(gen_doc, cache)
            if cache:
                if 'generos' not in cache: cache['generos'] = {}
                cache['generos'][gen_id] = genero_data
    elif isinstance(genero_data, dict):
        genero_data = map_genero(genero_data, cache)
        
    return {
        'idcancion': doc.get('cancion_id'),
        'cancion_id': doc.get('cancion_id'),
        'titulocancion': doc.get('tituloCancion'),
        'duracionseg': doc.get('duracionSeg'),
        'esexplicita': doc.get('esExplicita'),
        'estadopublicacion': doc.get('estadoPublicacion'),
        'urlportada': doc.get('urlPortada'),
        'urlspotifyapi': doc.get('urlSpotifyAPI'),
        'album_id': doc.get('album_id'),
        'genero_id': doc.get('genero_id'),
        'album': album_data,
        'genero': genero_data,
        'colaboradores': doc.get('colaboradores', []),
    }

def get_db_cache():
    cache = {
        'artistas': {},
        'generos': {},
        'albumes': {}
    }
    try:
        # Pre-populate in bulk to avoid all further queries
        for doc in db["Artista"].find():
            aid = doc.get("artista_id")
            if aid is not None:
                cache['artistas'][int(aid)] = {
                    'idartista': doc.get('artista_id'),
                    'artista_id': doc.get('artista_id'),
                    'nombreartistico': doc.get('nombreArtistico'),
                    'biografia': doc.get('biografia'),
                    'paisorigen': doc.get('paisOrigen'),
                    'estadoactivo': doc.get('estadoActivo'),
                    'fecharegistro': doc.get('fechaRegistro'),
                    'urlperfil': doc.get('urlPerfil'),
                }
                
        for doc in db["Genero"].find():
            gid = doc.get("genero_id")
            if gid is not None:
                cache['generos'][int(gid)] = {
                    'idgenero': doc.get('genero_id'),
                    'genero_id': doc.get('genero_id'),
                    'nombregenero': doc.get('nombreGenero'),
                    'descripcion': doc.get('descripcion'),
                }
                
        for doc in db["Album"].find():
            alb_id = doc.get("album_id")
            if alb_id is not None:
                cache['albumes'][int(alb_id)] = map_album(doc, cache)
    except Exception as e:
        print(f"Error pre-populating db cache: {e}")
    return cache

def fn_FormatearDuracion(seconds):
    if not seconds:
        return "00:00"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"

ESTADOS_PUBLICACION = ['Borrador', 'Programada', 'Publicada']
# ══════════════════════════════════════════
#  CANCIONES
# ══════════════════════════════════════════

@login_required
def songs_overview(request):
    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    orden = request.GET.get('orden', 'desc')

    pipeline = []
    match_filter = {}
    if query:
        match_filter["tituloCancion"] = {"$regex": query, "$options": "i"}
    if estado:
        match_filter["estadoPublicacion"] = estado
    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.extend([
        {
            "$lookup": {
                "from": "Album",
                "localField": "album_id",
                "foreignField": "album_id",
                "as": "album"
            }
        },
        {"$unwind": {"path": "$album", "preserveNullAndEmptyArrays": True}}
    ])

    sort_dir = -1 if orden == 'desc' else 1
    pipeline.append({"$sort": {"album.fechaLanzamiento": sort_dir}})

    docs = list(db["Cancion"].aggregate(pipeline))
    cache = get_db_cache()
    canciones = [map_cancion(d, cache) for d in docs]

    context = {
        'canciones': canciones,
        'query': query,
    }
    return render(request, 'catalogo/canciones/songs_overview.html', context)


@login_required
@csrf_exempt
def add_track_ajax(request):
    if request.method == 'GET':
        cache = get_db_cache()
        albumes = sorted(cache['albumes'].values(), key=lambda x: x['tituloalbum'] or '')
        generos = sorted(cache['generos'].values(), key=lambda x: x['nombregenero'] or '')
        artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')
        return render(request, 'catalogo/canciones/add_track.html', {
            'albumes': albumes,
            'generos': generos,
            'artistas': artistas,
        })

    if request.method == 'POST':
        try:
            titulo = request.POST.get('titulocancion')
            album_id = request.POST.get('album')
            genero_id = request.POST.get('genero')
            duracion = request.POST.get('duracionseg')
            url_portada = request.POST.get('urlportada')
            es_explicita = request.POST.get('esexplicita') == 'on'
            spotify_url = request.POST.get('spotify_url')

            if not titulo or not album_id:
                return JsonResponse({'status': 'error', 'message': 'Faltan campos obligatorios.'}, status=400)

            album_id = int(album_id)
            genero_id = int(genero_id) if genero_id else 0

            # Validar si ya existe
            if db["Cancion"].find_one({"tituloCancion": {"$regex": f"^{titulo}$", "$options": "i"}, "album_id": album_id}):
                return JsonResponse({'status': 'error', 'message': 'La canción ya existe en este álbum.'}, status=400)

            # Auto-increment id
            max_doc = db["Cancion"].find_one(sort=[("cancion_id", -1)])
            cancion_id = (max_doc["cancion_id"] + 1) if max_doc else 1

            colab_artistas = request.POST.getlist('colab_artistas')
            colab_roles = request.POST.getlist('colab_roles')
            colaboradores_list = []
            for art_id, rol in zip(colab_artistas, colab_roles):
                if art_id and rol:
                    art_id = int(art_id)
                    art_doc = db["Artista"].find_one({"artista_id": art_id})
                    if art_doc:
                        colaboradores_list.append({
                            "artista_id": art_id,
                            "nombreArtista": art_doc.get("nombreArtistico"),
                            "rolArtista": rol
                        })

            # Ensure the album's main artist is added as Principal if not already present
            album_doc = db["Album"].find_one({"album_id": album_id})
            if album_doc and album_doc.get("artista_id") is not None:
                main_art_id = int(album_doc["artista_id"])
                has_principal = any(c.get("artista_id") == main_art_id and c.get("rolArtista") == "Principal" for c in colaboradores_list)
                if not has_principal:
                    colaboradores_list = [c for c in colaboradores_list if c.get("rolArtista") != "Principal"]
                    main_art_doc = db["Artista"].find_one({"artista_id": main_art_id})
                    if main_art_doc:
                        colaboradores_list.insert(0, {
                            "artista_id": main_art_id,
                            "nombreArtista": main_art_doc.get("nombreArtistico"),
                            "rolArtista": "Principal"
                        })

            db["Cancion"].insert_one({
                "cancion_id": cancion_id,
                "tituloCancion": titulo,
                "duracionSeg": int(duracion) if duracion else 0,
                "esExplicita": es_explicita,
                "estadoPublicacion": "Borrador",
                "urlPortada": url_portada,
                "urlSpotifyAPI": spotify_url,
                "album_id": album_id,
                "genero_id": genero_id,
                "colaboradores": colaboradores_list
            })

            return JsonResponse({'status': 'success', 'message': 'Canción y colaboradores guardados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


def sync_spotify_track(request, cancion_id):
    cancion_doc = db["Cancion"].find_one({"cancion_id": int(cancion_id)})
    if not cancion_doc:
        messages.error(request, "Canción no encontrada.")
        return redirect('songs_overview')

    nombre_artista = ""
    album_doc = db["Album"].find_one({"album_id": cancion_doc.get("album_id")})
    if album_doc:
        art_doc = db["Artista"].find_one({"artista_id": album_doc.get("artista_id")})
        if art_doc:
            nombre_artista = art_doc.get("nombreArtistico", "")

    spotify = SpotifyClient()
    spotify_data = spotify.search_track_info(cancion_doc.get("tituloCancion"), nombre_artista)
    if spotify_data:
        db["Cancion"].update_one(
            {"cancion_id": int(cancion_id)},
            {"$set": {
                "urlSpotifyAPI": spotify_data['spotify_url'],
                "urlPortada": spotify_data['album_cover_url']
            }}
        )
        messages.success(request, f"'{cancion_doc.get('tituloCancion')}' sincronizada.")
    else:
        messages.error(request, f"No se pudo sincronizar '{cancion_doc.get('tituloCancion')}'.")
    return redirect('songs_overview')


@login_required
def search_spotify_ajax(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)
    spotify = SpotifyClient()
    results = spotify.search_track_info_list(query)
    if results:
        return JsonResponse(results, safe=False)
    return JsonResponse({'error': 'No encontrado'}, status=404)


def check_existence(request):
    tipo = request.GET.get('tipo')
    nombre = request.GET.get('nombre', '').strip()
    existe = False
    if tipo == 'album':
        existe = db["Album"].find_one({"tituloAlbum": {"$regex": f"^{nombre}$", "$options": "i"}}) is not None
    elif tipo == 'genero':
        existe = db["Genero"].find_one({"nombreGenero": {"$regex": f"^{nombre}$", "$options": "i"}}) is not None
    elif tipo == 'cancion':
        existe = db["Cancion"].find_one({"tituloCancion": {"$regex": f"^{nombre}$", "$options": "i"}}) is not None
    elif tipo == 'artista':
        existe = db["Artista"].find_one({"nombreArtistico": {"$regex": f"^{nombre}$", "$options": "i"}}) is not None
    return JsonResponse({'existe': existe})


@login_required
def delete_track(request, pk):
    if request.method == 'POST':
        try:
            # 1. Eliminar pista principal de MongoDB
            db["Cancion"].delete_one({"cancion_id": int(pk)})

            # 2. De forma opcional, si existen dependencias en SQL Server, hacemos una limpieza
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM [Catalogo].[Colaboracion] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Usuario].[CancionFavorita] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Usuario].[PlaylistCancion] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Auditoria].[EstadisticaDiaria] WHERE Cancion_idCancion = %s", [pk])
            except Exception:
                pass

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al eliminar la pista: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
def read_track(request, pk):
    track_doc = db["Cancion"].find_one({"cancion_id": int(pk)})
    if not track_doc:
        return redirect('songs_overview')

    cache = get_db_cache()
    cancion = map_cancion(track_doc, cache)
    duracion_formateada = fn_FormatearDuracion(cancion.get('duracionseg', 0))

    colaboradores = cancion.get('colaboradores', [])
    colaboradores_mapped = []
    for c in colaboradores:
        art_id = c.get('artista_id')
        url_perfil = ""
        if art_id is not None:
            cached_art = cache.get('artistas', {}).get(int(art_id))
            if cached_art:
                url_perfil = cached_art.get('urlperfil') or ""
        colaboradores_mapped.append({
            'idcolaboracion': None,
            'rolartista': c.get('rolArtista'),
            'artista': {
                'idartista': art_id,
                'nombreartistico': c.get('nombreArtista'),
                'urlperfil': url_perfil,
            }
        })

    colab_principal = next((c for c in colaboradores_mapped if c['rolartista'] == 'Principal'), None)
    colabs_extra = [c for c in colaboradores_mapped if c['rolartista'] != 'Principal']

    albumes = sorted(cache['albumes'].values(), key=lambda x: x['tituloalbum'] or '')
    generos = sorted(cache['generos'].values(), key=lambda x: x['nombregenero'] or '')
    artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')

    return render(request, 'catalogo/canciones/read_track.html', {
        'cancion': cancion,
        'duracion_formateada': duracion_formateada,
        'albumes': albumes,
        'generos': generos,
        'artistas': artistas,
        'estados': ['Borrador', 'Programada', 'Publicada'],
        'colab_principal': colab_principal,
        'colabs_extra': colabs_extra,
    })


@login_required
def edit_track(request, pk):
    track_doc = db["Cancion"].find_one({"cancion_id": int(pk)})
    if not track_doc:
        return redirect('songs_overview')

    if request.method == 'POST':
        url_portada_frontend = request.POST.get('urlportada')
        try:
            colab_artistas = request.POST.getlist('colab_artistas')
            colab_roles = request.POST.getlist('colab_roles')
            colaboradores_list = []
            for art_id, rol in zip(colab_artistas, colab_roles):
                if art_id and rol:
                    art_id = int(art_id)
                    art_doc = db["Artista"].find_one({"artista_id": art_id})
                    if art_doc:
                        colaboradores_list.append({
                            "artista_id": art_id,
                            "nombreArtista": art_doc.get("nombreArtistico"),
                            "rolArtista": rol
                        })

            # Ensure the album's main artist is added as Principal if not already present
            album_input_id = request.POST.get('album')
            if album_input_id:
                album_id = int(album_input_id)
                album_doc = db["Album"].find_one({"album_id": album_id})
                if album_doc and album_doc.get("artista_id") is not None:
                    main_art_id = int(album_doc["artista_id"])
                    has_principal = any(c.get("artista_id") == main_art_id and c.get("rolArtista") == "Principal" for c in colaboradores_list)
                    if not has_principal:
                        colaboradores_list = [c for c in colaboradores_list if c.get("rolArtista") != "Principal"]
                        main_art_doc = db["Artista"].find_one({"artista_id": main_art_id})
                        if main_art_doc:
                            colaboradores_list.insert(0, {
                                "artista_id": main_art_id,
                                "nombreArtista": main_art_doc.get("nombreArtistico"),
                                "rolArtista": "Principal"
                            })

            db["Cancion"].update_one(
                {"cancion_id": int(pk)},
                {"$set": {
                    "tituloCancion": request.POST.get('titulocancion'),
                    "duracionSeg": int(request.POST.get('duracionseg') or 0),
                    "esExplicita": request.POST.get('esexplicita') == 'on',
                    "estadoPublicacion": request.POST.get('estadopublicacion'),
                    "album_id": int(request.POST.get('album')),
                    "genero_id": int(request.POST.get('genero')),
                    "urlPortada": url_portada_frontend,
                    "colaboradores": colaboradores_list
                }}
            )

            return JsonResponse({'status': 'success', 'urlportada': url_portada_frontend})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # Resolving references for GET
    cache = get_db_cache()
    cancion = map_cancion(track_doc, cache)
    duracion_formateada = fn_FormatearDuracion(cancion.get('duracionseg', 0))

    colaboradores = cancion.get('colaboradores', [])
    colaboradores_mapped = []
    for c in colaboradores:
        art_id = c.get('artista_id')
        url_perfil = ""
        if art_id is not None:
            cached_art = cache.get('artistas', {}).get(int(art_id))
            if cached_art:
                url_perfil = cached_art.get('urlperfil') or ""
        colaboradores_mapped.append({
            'idcolaboracion': None,
            'rolartista': c.get('rolArtista'),
            'artista': {
                'idartista': art_id,
                'nombreartistico': c.get('nombreArtista'),
                'urlperfil': url_perfil,
            }
        })

    colab_principal = next((c for c in colaboradores_mapped if c['rolartista'] == 'Principal'), None)
    colabs_extra = [c for c in colaboradores_mapped if c['rolartista'] != 'Principal']

    albumes = sorted(cache['albumes'].values(), key=lambda x: x['tituloalbum'] or '')
    generos = sorted(cache['generos'].values(), key=lambda x: x['nombregenero'] or '')
    artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')

    context = {
        'cancion': cancion,
        'duracion_formateada': duracion_formateada,
        'albumes': albumes,
        'generos': generos,
        'artistas': artistas,
        'estados': ['Borrador', 'Programada', 'Publicada'],
        'colab_principal': colab_principal,
        'colabs_extra': colabs_extra,
    }
    return render(request, 'catalogo/canciones/edit_track.html', context)

# ══════════════════════════════════════════
#  ARTISTAS
# ══════════════════════════════════════════
def artists_overview(request):
    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    orden = request.GET.get('orden', 'desc')

    query_filter = {}
    if query:
        query_filter["nombreArtistico"] = {"$regex": query, "$options": "i"}
    if estado:
        query_filter["estadoActivo"] = estado

    sort_dir = -1 if orden == 'desc' else 1
    docs = list(db["Artista"].find(query_filter).sort("fechaRegistro", sort_dir))
    artistas = [map_artista(d) for d in docs]

    context = {
        'artistas': artistas,
        'query': query,
    }
    return render(request, 'catalogo/artistas/artists_overview.html', context)


@login_required
def read_artist(request, pk):
    art_doc = db["Artista"].find_one({"artista_id": int(pk)})
    if not art_doc:
        return redirect('artists_overview')
    artista = map_artista(art_doc)
    estados_actividad = ['Vigente', 'Archivado']
    context = {
        'artista': artista,
        'estados': estados_actividad
    }
    return render(request, 'catalogo/artistas/read_artist.html', context)


@login_required
def edit_artist(request, pk):
    art_doc = db["Artista"].find_one({"artista_id": int(pk)})
    if not art_doc:
        return redirect('artists_overview')

    if request.method == 'POST':
        db["Artista"].update_one(
            {"artista_id": int(pk)},
            {"$set": {
                "nombreArtistico": request.POST.get('nombreartistico'),
                "biografia": request.POST.get('biografia'),
                "paisOrigen": request.POST.get('paisorigen'),
                "estadoActivo": request.POST.get('estadoactivo'),
                "urlPerfil": request.POST.get('urlperfil')
            }}
        )
        return JsonResponse({'status': 'success'})

    artista = map_artista(art_doc)
    estados_actividad = ['Vigente', 'Archivado']
    context = {
        'artista': artista,
        'estados': estados_actividad
    }
    return render(request, 'catalogo/artistas/edit_artist.html', context)


@login_required
def delete_artist(request, pk):
    if request.method == 'POST':
        try:
            pk = int(pk)
            # 1. Eliminar al artista de MongoDB
            db["Artista"].delete_one({"artista_id": pk})

            # 2. Encontrar álbumes del artista para poder eliminar sus canciones
            albums = list(db["Album"].find({"artista_id": pk}))
            album_ids = [a["album_id"] for a in albums]

            # 3. Eliminar canciones de esos álbumes
            db["Cancion"].delete_many({"album_id": {"$in": album_ids}})

            # 4. Eliminar los álbumes en sí
            db["Album"].delete_many({"artista_id": pk})

            # 5. Sacar al artista de la lista de colaboradores en cualquier otra canción
            db["Cancion"].update_many(
                {},
                {"$pull": {"colaboradores": {"artista_id": pk}}}
            )

            # Opcional: Eliminar de base de datos SQL relacional si existiesen
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM [Usuario].[Seguimiento] WHERE Artista_idArtista = %s", [pk])
                    cursor.execute("DELETE FROM [Catalogo].[Colaboracion] WHERE Artista_idArtista = %s", [pk])
            except Exception:
                pass

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al eliminar en cascada: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
@csrf_exempt
def add_artist(request):
    if request.method == 'GET':
        estados_actividad = ['Vigente', 'Archivado']
        return render(request, 'catalogo/artistas/add_artist.html', {
            'estados': estados_actividad
        })

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombreartistico')
            biografia = request.POST.get('biografia', '')
            pais = request.POST.get('paisorigen', '')
            estado = request.POST.get('estadoactivo', 'Vigente')
            url_perfil = request.POST.get('urlperfil', '')

            if not nombre:
                return JsonResponse({'status': 'error', 'message': 'Falta el nombre artístico.'}, status=400)

            if db["Artista"].find_one({"nombreArtistico": {"$regex": f"^{nombre}$", "$options": "i"}}):
                return JsonResponse({'status': 'error', 'message': 'El artista ya está registrado.'}, status=400)

            # Auto-increment
            max_doc = db["Artista"].find_one(sort=[("artista_id", -1)])
            artista_id = (max_doc["artista_id"] + 1) if max_doc else 1

            db["Artista"].insert_one({
                "artista_id": artista_id,
                "nombreArtistico": nombre,
                "biografia": biografia,
                "paisOrigen": pais,
                "estadoActivo": estado,
                "fechaRegistro": datetime.datetime.now(),
                "urlPerfil": url_perfil
            })

            return JsonResponse({'status': 'success', 'message': 'Artista guardado correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
def search_artist_spotify_ajax(request):
    """Busca artistas en Spotify para el autocompletado"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)

    try:
        spotify = SpotifyClient()
        # Asumiendo que tu SpotifyClient maneja el token internamente.
        # Si no tienes un método específico para artistas, hacemos la petición manual usando su token:
        token = spotify.get_token() if hasattr(spotify, 'get_token') else spotify.token

        headers = {'Authorization': f'Bearer {token}'}
        url = f"https://api.spotify.com/v1/search?q={urllib.parse.quote(query)}&type=artist&limit=5"

        res = requests.get(url, headers=headers)
        data = res.json()
        items = data.get('artists', {}).get('items', [])

        results = []
        for item in items:
            images = item.get('images', [])
            image_url = images[0]['url'] if images else ''
            # Usamos los géneros de Spotify como una biografía inicial autocompletada
            generos = ", ".join(item.get('genres', [])).title()

            results.append({
                'name': item.get('name'),
                'image': image_url,
                'genres': f"Géneros principales: {generos}" if generos else "",
                'spotify_url': item.get('external_urls', {}).get('spotify', '')
            })

        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({'error': 'Error conectando con Spotify'}, status=500)

# ══════════════════════════════════════════
#  ÁLBUMES
# ══════════════════════════════════════════
def albums_overview(request):
    cache = get_db_cache()
    artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')

    query = request.GET.get('q', '').strip()
    artista_id = request.GET.get('artista', '')
    orden = request.GET.get('orden', 'desc')

    pipeline = []
    match_filter = {}
    if query:
        match_filter["tituloAlbum"] = {"$regex": query, "$options": "i"}
    if artista_id:
        match_filter["artista_id"] = int(artista_id)
    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.extend([
        {
            "$lookup": {
                "from": "Artista",
                "localField": "artista_id",
                "foreignField": "artista_id",
                "as": "artista"
            }
        },
        {"$unwind": {"path": "$artista", "preserveNullAndEmptyArrays": True}}
    ])

    sort_dir = -1 if orden == 'desc' else 1
    pipeline.append({"$sort": {"fechaLanzamiento": sort_dir}})

    docs = list(db["Album"].aggregate(pipeline))
    albumes = [map_album(d, cache) for d in docs]

    context = {
        'albumes': albumes,
        'artistas': artistas,
        'query': query,
    }
    return render(request, 'catalogo/albumes/albums_overview.html', context)


@login_required
def add_album(request):
    if request.method == 'GET':
        artistas = [map_artista(d) for d in db["Artista"].find().sort("nombreArtistico", 1)]
        return render(request, 'catalogo/albumes/add_album.html', {'artistas': artistas})

    if request.method == 'POST':
        try:
            titulo = request.POST.get('tituloalbum')
            fecha_lanzamiento = request.POST.get('fechalanzamiento')
            url_portada = request.POST.get('urlportada', '')
            artista_id = request.POST.get('artista')

            if not titulo or not artista_id or not fecha_lanzamiento:
                return JsonResponse({'status': 'error', 'message': 'Faltan campos obligatorios.'}, status=400)

            # Auto-increment
            max_doc = db["Album"].find_one(sort=[("album_id", -1)])
            album_id = (max_doc["album_id"] + 1) if max_doc else 1

            # Convert date
            try:
                dt = datetime.datetime.strptime(fecha_lanzamiento, "%Y-%m-%d")
            except Exception:
                dt = datetime.datetime.now()

            db["Album"].insert_one({
                "album_id": album_id,
                "tituloAlbum": titulo,
                "fechaLanzamiento": dt,
                "urlPortada": url_portada,
                "artista_id": int(artista_id)
            })

            return JsonResponse({'status': 'success', 'message': 'Álbum guardado correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
def read_album(request, pk):
    alb_doc = db["Album"].find_one({"album_id": int(pk)})
    if not alb_doc:
        return redirect('albums_overview')
    cache = get_db_cache()
    album = map_album(alb_doc, cache)
    artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')
    return render(request, 'catalogo/albumes/read_album.html', {'album': album, 'artistas': artistas})


@login_required
def edit_album(request, pk):
    alb_doc = db["Album"].find_one({"album_id": int(pk)})
    if not alb_doc:
        return redirect('albums_overview')

    if request.method == 'POST':
        try:
            url_portada = request.POST.get('urlportada')
            fecha_lanzamiento = request.POST.get('fechalanzamiento')
            try:
                dt = datetime.datetime.strptime(fecha_lanzamiento, "%Y-%m-%d")
            except Exception:
                dt = datetime.datetime.now()

            db["Album"].update_one(
                {"album_id": int(pk)},
                {"$set": {
                    "tituloAlbum": request.POST.get('tituloalbum'),
                    "fechaLanzamiento": dt,
                    "urlPortada": url_portada
                }}
            )
            return JsonResponse({'status': 'success', 'urlportada': url_portada})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    cache = get_db_cache()
    album = map_album(alb_doc, cache)
    artistas = sorted(cache['artistas'].values(), key=lambda x: x['nombreartistico'] or '')
    context = {'album': album, 'artistas': artistas}
    return render(request, 'catalogo/albumes/edit_album.html', context)


@login_required
def delete_album(request, pk):
    if request.method == 'POST':
        try:
            pk = int(pk)
            # 1. Eliminar el álbum de MongoDB
            db["Album"].delete_one({"album_id": pk})

            # 2. Eliminar todas las canciones del álbum
            db["Cancion"].delete_many({"album_id": pk})

            # Opcional: Eliminar de base de datos SQL relacional si existiesen
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    # Preparar subconsulta de canciones de este álbum en SQL
                    query_canciones = "SELECT idCancion FROM [Catalogo].[Cancion] WHERE Album_idAlbum = %s"
                    cursor.execute(f"DELETE FROM [Catalogo].[Colaboracion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(f"DELETE FROM [Usuario].[CancionFavorita] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(f"DELETE FROM [Usuario].[PlaylistCancion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(f"DELETE FROM [Auditoria].[EstadisticaDiaria] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute("DELETE FROM [Catalogo].[Cancion] WHERE Album_idAlbum = %s", [pk])
                    cursor.execute("DELETE FROM [Catalogo].[Album] WHERE idAlbum = %s", [pk])
            except Exception:
                pass

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al eliminar en cascada: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def search_album_spotify_ajax(request):
    """Busca álbumes en Spotify para autocompletado"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)

    try:
        # Reutilizamos tu cliente de Spotify
        spotify = SpotifyClient()
        token = spotify.get_token() if hasattr(spotify, 'get_token') else spotify.token

        headers = {'Authorization': f'Bearer {token}'}
        url = f"https://api.spotify.com/v1/search?q={urllib.parse.quote(query)}&type=album&limit=5"

        res = requests.get(url, headers=headers)
        data = res.json()
        items = data.get('albums', {}).get('items', [])

        results = []
        for item in items:
            images = item.get('images', [])
            image_url = images[0]['url'] if images else ''
            # Obtenemos el nombre del artista principal del álbum
            artist_name = item.get('artists', [{}])[0].get('name', 'Desconocido')

            results.append({
                'name': item.get('name'),
                'image': image_url,
                'artist': artist_name,
                'release_date': item.get('release_date', ''),
                'spotify_url': item.get('external_urls', {}).get('spotify', '')
            })

        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({'error': 'Error conectando con Spotify'}, status=500)

# ══════════════════════════════════════════
#  GÉNEROS
# ══════════════════════════════════════════

@login_required
def genre_overview(request):
    query = request.GET.get('q', '').strip()
    query_filter = {}
    if query:
        query_filter["nombreGenero"] = {"$regex": query, "$options": "i"}

    docs = list(db["Genero"].find(query_filter).sort("nombreGenero", 1))
    generos = [map_genero(d) for d in docs]

    context = {
        'generos': generos,
        'query': query
    }
    return render(request, 'catalogo/generos/genre_overview.html', context)


@login_required
def add_genre(request):
    if request.method == 'GET':
        nombre_sugerido = request.GET.get('nombre', '')
        return render(request, 'catalogo/generos/add_genre.html', {'nombre_sugerido': nombre_sugerido})

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombregenero', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()

            if not nombre:
                return JsonResponse({'status': 'error', 'message': 'El nombre del género es obligatorio.'}, status=400)

            # Check duplicate (case-insensitive)
            if db["Genero"].find_one({"nombreGenero": {"$regex": f"^{nombre}$", "$options": "i"}}):
                return JsonResponse({'status': 'error', 'message': f'El género "{nombre}" ya está registrado en el catálogo.'}, status=400)

            # Auto-increment
            max_doc = db["Genero"].find_one(sort=[("genero_id", -1)])
            genero_id = (max_doc["genero_id"] + 1) if max_doc else 1

            db["Genero"].insert_one({
                "genero_id": genero_id,
                "nombreGenero": nombre,
                "descripcion": descripcion
            })

            return JsonResponse({'status': 'success', 'message': 'Género registrado correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
def read_genre(request, pk):
    gen_doc = db["Genero"].find_one({"genero_id": int(pk)})
    if not gen_doc:
        return redirect('genre_overview')
    genero = map_genero(gen_doc)
    return render(request, 'catalogo/generos/read_genre.html', {'genero': genero})


@login_required
def edit_genre(request, pk):
    gen_doc = db["Genero"].find_one({"genero_id": int(pk)})
    if not gen_doc:
        return redirect('genre_overview')

    if request.method == 'POST':
        try:
            db["Genero"].update_one(
                {"genero_id": int(pk)},
                {"$set": {
                    "nombreGenero": request.POST.get('nombregenero'),
                    "descripcion": request.POST.get('descripcion')
                }}
            )
            return JsonResponse({'status': 'success', 'message': 'Género actualizado correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    genero = map_genero(gen_doc)
    return render(request, 'catalogo/generos/edit_genre.html', {'genero': genero})


@login_required
def delete_genre(request, pk):
    if request.method == 'POST':
        try:
            pk = int(pk)
            # 1. Buscar si ya existe el género de respaldo
            default_gen_doc = db["Genero"].find_one({"nombreGenero": "Sin género asignado"})
            if default_gen_doc:
                default_id = default_gen_doc["genero_id"]
            else:
                # Si no existe, lo creamos
                max_doc = db["Genero"].find_one(sort=[("genero_id", -1)])
                default_id = (max_doc["genero_id"] + 1) if max_doc else 1
                db["Genero"].insert_one({
                    "genero_id": default_id,
                    "nombreGenero": "Sin género asignado",
                    "descripcion": "Categoría temporal para canciones cuyo género original fue eliminado."
                })

            # 2. Protección: Evitar eliminar el de respaldo
            if pk == default_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Protección de sistema: No se puede eliminar el género de respaldo global.'
                }, status=400)

            # 3. Traspasar canciones al género comodín
            db["Cancion"].update_many(
                {"genero_id": pk},
                {"$set": {"genero_id": default_id}}
            )

            # 4. Eliminar el género
            db["Genero"].delete_one({"genero_id": pk})

            # Opcional: Eliminar de base de datos SQL si existiesen
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE [Catalogo].[Cancion] SET Genero_idGenero = %s WHERE Genero_idGenero = %s", [default_id, pk])
                    cursor.execute("DELETE FROM [Catalogo].[Genero] WHERE idGenero = %s", [pk])
            except Exception:
                pass

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al reasignar registros: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


# ══════════════════════════════════════════
#  COLABORACIONES
# ══════════════════════════════════════════



# ══════════════════════════════════════════
#  REPORTES DEL CATÁLOGO (SQL Objects)
# ══════════════════════════════════════════
# ══════════════════════════════════════════
#  REPORTES DEL CATÁLOGO (SQL Objects)
# ══════════════════════════════════════════

def _obtener_datos_sql(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _contexto_base(request):
    return {
        'fecha_generacion': datetime.datetime.now(),
        'usuario_generador': (f"{request.user.get_full_name() or request.user.username} · {request.user.email}").strip(
            ' ·'),
        'version': 'v2.1.0',
    }


def obtener_ranking_popularidad_mensual():
    stats = list(db["estadisticasDiarias"].aggregate([
        {
            "$match": {
                "fechaReporte": "2026-04-20"
            }
        },
        {
            "$group": {
                "_id": "$idCancion",
                "totalReproduccionesMes": { "$sum": "$totalRepros" }
            }
        },
        {
            "$sort": { "totalReproduccionesMes": -1 }
        },
        {
            "$limit": 10
        }
    ]))
    
    ranking = []
    cache = get_db_cache()
    for row in stats:
        track_id = row.get("_id")
        repros = row.get("totalReproduccionesMes")
        if track_id is None:
            continue
            
        track_doc = db["Cancion"].find_one({"cancion_id": int(track_id)})
        if track_doc:
            cancion = map_cancion(track_doc, cache)
            nombre_artista = "Desconocido"
            if cancion.get("album") and cancion["album"].get("artista"):
                nombre_artista = cancion["album"]["artista"].get("nombreartistico", "Desconocido")
            
            ranking.append({
                "tituloCancion": cancion.get("titulocancion"),
                "nombreArtistico": nombre_artista,
                "total_escuchas_mes": repros,
                "urlPortada": cancion.get("urlportada")
            })
    return ranking


def vw_AuditoriaMetadatosIncompletos():
    canciones = list(db["Cancion"].find({
        "estadoPublicacion": "Programada",
        "$or": [
            { "urlSpotifyAPI": { "$exists": False } },
            { "urlSpotifyAPI": None },
            { "urlPortada": { "$exists": False } },
            { "urlPortada": None }
        ]
    }))
    
    inconsistencias = []
    for c in canciones:
        c_id = c.get("cancion_id")
        titulo = c.get("tituloCancion")
        
        spotify_url = c.get("urlSpotifyAPI")
        portada_url = c.get("urlPortada")
        
        estatus_genero = "Correcto"
        estatus_jerarquia = "Correcto"
        
        if not spotify_url:
            estatus_genero = "SIN GÉNERO"
        if not portada_url:
            estatus_jerarquia = "Sin Álbum vinculado"
            
        inconsistencias.append({
            'idCancion': c_id,
            'tituloCancion': titulo,
            'EstatusGenero': estatus_genero,
            'EstatusJerarquia': estatus_jerarquia,
            'urlPortada': portada_url
        })
    return inconsistencias



# ── VISTAS BASE DE REPORTE (PANTALLA) ──
@login_required
def reporte_top_10(request):
    canciones = []
    try:
        canciones = obtener_ranking_popularidad_mensual()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    return render(request, 'catalogo/reportes/reporte_top_10.html', {'canciones': canciones})


@login_required
def reporte_auditoria_catalogo(request):
    inconsistencias = []
    try:
        inconsistencias = vw_AuditoriaMetadatosIncompletos()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    return render(request, 'catalogo/reportes/reporte_auditoria.html', {'inconsistencias': inconsistencias})


# ── VISTAS DE EXPORTACIÓN Y ENVÍO (TOP 10) ──
@login_required
def exportar_top_10_pdf(request):
    try:
        canciones = obtener_ranking_popularidad_mensual()
        context = {**_contexto_base(request), 'canciones': canciones, 'periodo': 'Últimos 30 días'}

        html_string = render_to_string('catalogo/reportes/pdf_top_10.html', context, request=request)

        # Generar PDF usando WeasyPrint
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Top_10_Popularidad_Mensual.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)


@login_required
def enviar_top_10_correo(request):
    try:
        canciones = obtener_ranking_popularidad_mensual()
        context = {**_contexto_base(request), 'canciones': canciones, 'periodo': 'Últimos 30 días'}

        html_string = render_to_string('catalogo/reportes/pdf_top_10.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Top 10 Popularidad Mensual',
            body='Adjuntamos el reporte ejecutivo de las pistas más reproducidas solicitado desde la consola.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Top_10_Popularidad_Mensual.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── VISTAS DE EXPORTACIÓN Y ENVÍO (AUDITORÍA) ──
@login_required
def exportar_auditoria_pdf(request):
    try:
        inconsistencias = vw_AuditoriaMetadatosIncompletos()
        context = {**_contexto_base(request), 'inconsistencias': inconsistencias}

        html_string = render_to_string('catalogo/reportes/pdf_auditoria.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Auditoria_Metadatos_Catalogo.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)


@login_required
def enviar_auditoria_correo(request):
    try:
        inconsistencias = vw_AuditoriaMetadatosIncompletos()
        context = {**_contexto_base(request), 'inconsistencias': inconsistencias}

        html_string = render_to_string('catalogo/reportes/pdf_auditoria.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Auditoría de Calidad del Catálogo',
            body='Adjuntamos el informe técnico con las inconsistencias detectadas para su revisión inmediata.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Auditoria_Metadatos_Catalogo.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Informe enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: CANCIONES POR GÉNERO ──
def obtener_canciones_por_genero():
    pipeline = [
        {
            "$lookup": {
                "from": "Genero",
                "localField": "genero_id",
                "foreignField": "genero_id",
                "as": "infoGenero"
            }
        },
        { "$unwind": "$infoGenero" },
        {
            "$group": {
                "_id": "$genero_id",
                "nombreGenero": { "$first": "$infoGenero.nombreGenero" },
                "totalCanciones": { "$sum": 1 }
            }
        },
        { "$sort": { "totalCanciones": -1 } }
    ]
    results = list(db["Cancion"].aggregate(pipeline))
    for r in results:
        r['id'] = r.get('_id')
    return results

@login_required
def reporte_canciones_genero(request):
    try:
        datos = obtener_canciones_por_genero()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        datos = []
    return render(request, 'catalogo/reportes/reporte_canciones_genero.html', {'datos': datos})

@login_required
def exportar_canciones_genero_pdf(request):
    try:
        datos = obtener_canciones_por_genero()
        context = {**_contexto_base(request), 'datos': datos}
        html_string = render_to_string('catalogo/reportes/pdf_canciones_genero.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Canciones_por_Genero.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)

@login_required
def enviar_canciones_genero_correo(request):
    try:
        datos = obtener_canciones_por_genero()
        context = {**_contexto_base(request), 'datos': datos}
        html_string = render_to_string('catalogo/reportes/pdf_canciones_genero.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Distribución de Canciones por Género',
            body='Adjuntamos el reporte de distribución de catálogo por género musical solicitado.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Canciones_por_Genero.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: PLAYLISTS POPULARES ──
def obtener_playlists_populares():
    playlists = list(db["playlists"].find({
        "esPublicada": True,
        "canciones.4": { "$exists": True }
    }))
    user_ids = {p.get("idUsuario") for p in playlists if p.get("idUsuario")}
    docs = db["usuarios"].find({"id": {"$in": list(user_ids)}}, {"id": 1, "nombre": 1, "apellido": 1})
    user_names = {d["id"]: f"{d.get('nombre', '')} {d.get('apellido', '')}" for d in docs}
    
    for p in playlists:
        p["id"] = str(p.get("_id"))
        p["owner_name"] = user_names.get(p.get("idUsuario"), "Usuario Desconocido")
        p["total_canciones"] = len(p.get("canciones", []))
    return playlists

@login_required
def reporte_playlists_populares(request):
    try:
        playlists = obtener_playlists_populares()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        playlists = []
    return render(request, 'catalogo/reportes/reporte_playlists_populares.html', {'playlists': playlists})

@login_required
def exportar_playlists_populares_pdf(request):
    try:
        playlists = obtener_playlists_populares()
        context = {**_contexto_base(request), 'playlists': playlists}
        html_string = render_to_string('catalogo/reportes/pdf_playlists_populares.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Playlists_Populares.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)

@login_required
def enviar_playlists_populares_correo(request):
    try:
        playlists = obtener_playlists_populares()
        context = {**_contexto_base(request), 'playlists': playlists}
        html_string = render_to_string('catalogo/reportes/pdf_playlists_populares.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Playlists Populares Publicadas',
            body='Adjuntamos el informe de playlists populares con 5 o más canciones creadas en la plataforma.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Playlists_Populares.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: ARTISTAS MÁS POPULARES (SEGUIDORES) ──
def obtener_artistas_mas_seguidos():
    pipeline = [
        { "$match": { "activo": 1 } },
        {
            "$group": {
                "_id": "$idArtista",
                "nombreArtista": { "$first": "$nombreArtista" },
                "totalSeguidores": { "$sum": 1 }
            }
        },
        {
            "$lookup": {
                "from": "Artista",
                "localField": "_id",
                "foreignField": "artista_id",
                "as": "infoArtista"
            }
        },
        { "$unwind": { "path": "$infoArtista", "preserveNullAndEmptyArrays": True } },
        { "$sort": { "totalSeguidores": -1 } }
    ]
    results = list(db["seguimientos"].aggregate(pipeline))
    artists = []
    for r in results:
        info = r.get("infoArtista", {}) or {}
        artists.append({
            "nombreArtista": r.get("nombreArtista") or info.get("nombreArtistico") or "Desconocido",
            "paisOrigen": info.get("paisOrigen") or "—",
            "totalSeguidores": r.get("totalSeguidores")
        })
    return artists

@login_required
def reporte_artistas_populares(request):
    try:
        artistas = obtener_artistas_mas_seguidos()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        artistas = []
    return render(request, 'catalogo/reportes/reporte_artistas_populares.html', {'artistas': artistas})

@login_required
def exportar_artistas_populares_pdf(request):
    try:
        artistas = obtener_artistas_mas_seguidos()
        context = {**_contexto_base(request), 'artistas': artistas}
        html_string = render_to_string('catalogo/reportes/pdf_artistas_populares.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Artistas_mas_Seguidos.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)

@login_required
def enviar_artistas_populares_correo(request):
    try:
        artistas = obtener_artistas_mas_seguidos()
        context = {**_contexto_base(request), 'artistas': artistas}
        html_string = render_to_string('catalogo/reportes/pdf_artistas_populares.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Ranking de Artistas más Seguidos',
            body='Adjuntamos el informe ejecutivo del ranking de artistas con mayor número de seguidores activos.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Artistas_mas_Seguidos.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

