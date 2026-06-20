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

from cenit import settings
from .models import Cancion, Artista, Album, Genero, Colaboracion
from .spotify_service import SpotifyClient

ESTADOS_PUBLICACION = ['Borrador', 'Programada', 'Publicada']
# ══════════════════════════════════════════
#  CANCIONES
# ══════════════════════════════════════════

@login_required
def songs_overview(request):
    canciones = Cancion.objects.select_related('album').all()

    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    orden = request.GET.get('orden', 'desc')

    if query:
        canciones = canciones.filter(titulocancion__icontains=query)

    if estado:
        # Aquí verificamos exacto el estado, si quieres hacer match con mayúsculas/minúsculas usa `iexact`
        canciones = canciones.filter(estadopublicacion__iexact=estado)

    # Ordenamiento basado en la fecha de lanzamiento del álbum relacionado (o idcancion si prefieres)
    if orden == 'asc':
        canciones = canciones.order_by('album__fechalanzamiento')
    else:
        canciones = canciones.order_by('-album__fechalanzamiento')

    context = {
        'canciones': canciones,
        'query': query,
    }
    return render(request, 'catalogo/canciones/songs_overview.html', context)


from django.db import connection  # Asegúrate de importar esto


@login_required
@csrf_exempt
def add_track_ajax(request):
    if request.method == 'GET':
        return render(request, 'catalogo/canciones/add_track.html', {
            'albumes': Album.objects.all(),
            'generos': Genero.objects.all(),
            'artistas': Artista.objects.all(),
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

            # Validar si ya existe
            if Cancion.objects.filter(titulocancion__iexact=titulo, album_id=album_id).exists():
                return JsonResponse({'status': 'error', 'message': 'La canción ya existe en este álbum.'}, status=400)

            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Insertar la canción y recuperar su ID en una sola instrucción usando OUTPUT
                    cursor.execute("""
                        INSERT INTO [Catalogo].[Cancion] 
                        (tituloCancion, duracionSeg, esExplicita, estadoPublicacion, urlPortada, Album_idAlbum, Genero_idGenero, spotifyUrlAPI)
                        OUTPUT inserted.idCancion
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, [titulo, duracion or 0, 1 if es_explicita else 0, 'Borrador', url_portada, album_id, genero_id,
                          spotify_url])

                    # 2. Capturar el ID que devolvió el OUTPUT
                    cancion_id = cursor.fetchone()[0]

                    # 3. Procesar los colaboradores dinámicos
                    colab_artistas = request.POST.getlist('colab_artistas')
                    colab_roles = request.POST.getlist('colab_roles')

                    for artista_id, rol in zip(colab_artistas, colab_roles):
                        if artista_id and rol:
                            # Validar que no se duplique el mismo artista en la misma canción
                            cursor.execute("""
                                SELECT idColaboracion FROM [Catalogo].[Colaboracion] 
                                WHERE Cancion_idCancion = %s AND Artista_idArtista = %s
                            """, [cancion_id, artista_id])

                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO [Catalogo].[Colaboracion] (Cancion_idCancion, Artista_idArtista, rolArtista)
                                    VALUES (%s, %s, %s)
                                """, [cancion_id, artista_id, rol])

            return JsonResponse({'status': 'success', 'message': 'Canción y colaboradores guardados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

def sync_spotify_track(request, cancion_id):
    cancion = get_object_or_404(Cancion, idcancion=cancion_id)
    nombre_artista = cancion.album.artista.nombreartistico if cancion.album and cancion.album.artista else ""
    spotify = SpotifyClient()
    spotify_data = spotify.search_track_info(cancion.titulocancion, nombre_artista)
    if spotify_data:
        cancion.spotifyurlapi = spotify_data['spotify_url']
        cancion.urlportada = spotify_data['album_cover_url']
        cancion.save(update_fields=['spotifyurlapi', 'urlportada'])
        messages.success(request, f"'{cancion.titulocancion}' sincronizada.")
    else:
        messages.error(request, f"No se pudo sincronizar '{cancion.titulocancion}'.")
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
        from .models import Album
        existe = Album.objects.filter(tituloalbum__iexact=nombre).exists()
    elif tipo == 'genero':
        from .models import Genero
        existe = Genero.objects.filter(nombregenero__iexact=nombre).exists()
    elif tipo == 'cancion':
        from .models import Cancion
        existe = Cancion.objects.filter(titulocancion__iexact=nombre).exists()
    elif tipo == 'artista':  # <--- AÑADE ESTO
        from .models import Artista
        existe = Artista.objects.filter(nombreartistico__iexact=nombre).exists()

    return JsonResponse({'existe': existe})


@login_required
def delete_track(request, pk):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Eliminar dependencias en otros esquemas y tablas
                    cursor.execute("DELETE FROM [Catalogo].[Colaboracion] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Usuario].[CancionFavorita] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Usuario].[PlaylistCancion] WHERE Cancion_idCancion = %s", [pk])
                    cursor.execute("DELETE FROM [Auditoria].[EstadisticaDiaria] WHERE Cancion_idCancion = %s", [pk])

                    # 2. Eliminar la pista principal
                    cursor.execute("DELETE FROM [Catalogo].[Cancion] WHERE idCancion = %s", [pk])

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al eliminar la pista: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@login_required
def read_track(request, pk):
    cancion = get_object_or_404(
        Cancion.objects.select_related('album__artista', 'genero'),
        idcancion=pk
    )
    colaboraciones = Colaboracion.objects.select_related('artista').filter(cancion_id=pk)

    # Ejecutamos la función escalar de SQL Server directamente
    with connection.cursor() as cursor:
        cursor.execute("SELECT [Catalogo].[fn_FormatearDuracion](%s)", [cancion.duracionseg or 0])
        duracion_formateada = cursor.fetchone()[0]

    return render(request, 'catalogo/canciones/read_track.html', {
        'cancion': cancion,
        'duracion_formateada': duracion_formateada,  # <-- Enviamos el tiempo amigable MM:SS
        'albumes': Album.objects.all(),
        'generos': Genero.objects.all(),
        'artistas': Artista.objects.all(),
        'estados': ['Borrador', 'Programada', 'Publicada'],
        'colab_principal': colaboraciones.filter(rolartista='Principal').first(),
        'colabs_extra': colaboraciones.exclude(rolartista='Principal'),
    })


@login_required
def edit_track(request, pk):
    cancion = get_object_or_404(Cancion, idcancion=pk)

    if request.method == 'POST':
        url_portada_frontend = request.POST.get('urlportada')
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE [Catalogo].[Cancion]
                        SET tituloCancion=%s, duracionSeg=%s, esExplicita=%s,
                            estadoPublicacion=%s, Album_idAlbum=%s, Genero_idGenero=%s, urlPortada=%s
                        WHERE idCancion=%s
                    """, [
                        request.POST.get('titulocancion'),
                        request.POST.get('duracionseg'),
                        1 if request.POST.get('esexplicita') == 'on' else 0,
                        request.POST.get('estadopublicacion'),
                        request.POST.get('album'),
                        request.POST.get('genero'),
                        url_portada_frontend,
                        pk
                    ])

                    cursor.execute("""
                        DELETE FROM [Catalogo].[Colaboracion] 
                        WHERE Cancion_idCancion = %s AND rolArtista != 'Principal'
                    """, [pk])

                    colab_artistas = request.POST.getlist('colab_artistas')
                    colab_roles = request.POST.getlist('colab_roles')

                    for artista_id, rol in zip(colab_artistas, colab_roles):
                        if artista_id and rol:
                            cursor.execute("""
                                SELECT idColaboracion FROM [Catalogo].[Colaboracion] 
                                WHERE Cancion_idCancion = %s AND Artista_idArtista = %s
                            """, [pk, artista_id])

                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO [Catalogo].[Colaboracion] (Cancion_idCancion, Artista_idArtista, rolArtista)
                                    VALUES (%s, %s, %s)
                                """, [pk, artista_id, rol])

            return JsonResponse({'status': 'success', 'urlportada': url_portada_frontend})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    colaboraciones = Colaboracion.objects.filter(cancion_id=pk)

    # Ejecutamos la función escalar de SQL Server para el modo edición clásico
    with connection.cursor() as cursor:
        cursor.execute("SELECT [Catalogo].[fn_FormatearDuracion](%s)", [cancion.duracionseg or 0])
        duracion_formateada = cursor.fetchone()[0]

    context = {
        'cancion': cancion,
        'duracion_formateada': duracion_formateada,  # <-- Enviamos aquí también
        'albumes': Album.objects.all(),
        'generos': Genero.objects.all(),
        'artistas': Artista.objects.all(),
        'estados': ['Borrador', 'Programada', 'Publicada'],
        'colab_principal': colaboraciones.filter(rolartista='Principal').first(),
        'colabs_extra': colaboraciones.exclude(rolartista='Principal'),
    }
    return render(request, 'catalogo/canciones/edit_track.html', context)


@login_required
def edit_track(request, pk):
    cancion = get_object_or_404(Cancion, idcancion=pk)

    if request.method == 'POST':
        url_portada_frontend = request.POST.get('urlportada')
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE [Catalogo].[Cancion]
                        SET tituloCancion=%s, duracionSeg=%s, esExplicita=%s,
                            estadoPublicacion=%s, Album_idAlbum=%s, Genero_idGenero=%s, urlPortada=%s
                        WHERE idCancion=%s
                    """, [
                        request.POST.get('titulocancion'),
                        request.POST.get('duracionseg'),
                        1 if request.POST.get('esexplicita') == 'on' else 0,
                        request.POST.get('estadopublicacion'),
                        request.POST.get('album'),
                        request.POST.get('genero'),
                        url_portada_frontend,
                        pk
                    ])

                    cursor.execute("""
                        DELETE FROM [Catalogo].[Colaboracion] 
                        WHERE Cancion_idCancion = %s AND rolArtista != 'Principal'
                    """, [pk])

                    colab_artistas = request.POST.getlist('colab_artistas')
                    colab_roles = request.POST.getlist('colab_roles')

                    for artista_id, rol in zip(colab_artistas, colab_roles):
                        if artista_id and rol:
                            cursor.execute("""
                                SELECT idColaboracion FROM [Catalogo].[Colaboracion] 
                                WHERE Cancion_idCancion = %s AND Artista_idArtista = %s
                            """, [pk, artista_id])

                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO [Catalogo].[Colaboracion] (Cancion_idCancion, Artista_idArtista, rolArtista)
                                    VALUES (%s, %s, %s)
                                """, [pk, artista_id, rol])

            return JsonResponse({'status': 'success', 'urlportada': url_portada_frontend})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    colaboraciones = Colaboracion.objects.filter(cancion_id=pk)

    # Ejecutamos la función escalar de SQL Server para el modo edición clásico
    with connection.cursor() as cursor:
        cursor.execute("SELECT [Catalogo].[fn_FormatearDuracion](%s)", [cancion.duracionseg or 0])
        duracion_formateada = cursor.fetchone()[0]

    context = {
        'cancion': cancion,
        'duracion_formateada': duracion_formateada,  # <-- Enviamos aquí también
        'albumes': Album.objects.all(),
        'generos': Genero.objects.all(),
        'artistas': Artista.objects.all(),
        'estados': ['Borrador', 'Programada', 'Publicada'],
        'colab_principal': colaboraciones.filter(rolartista='Principal').first(),
        'colabs_extra': colaboraciones.exclude(rolartista='Principal'),
    }
    return render(request, 'catalogo/canciones/edit_track.html', context)

# ══════════════════════════════════════════
#  ARTISTAS
# ══════════════════════════════════════════
def artists_overview(request):
    artistas = Artista.objects.all()

    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    orden = request.GET.get('orden', 'desc')

    if query:
        artistas = artistas.filter(nombreartistico__icontains=query)

    if estado:
        artistas = artistas.filter(estadoactivo=estado)

    if orden == 'asc':
        artistas = artistas.order_by('fecharegistro')
    else:
        artistas = artistas.order_by('-fecharegistro')

    context = {
        'artistas': artistas,
        'query': query,
    }
    return render(request, 'catalogo/artistas/artists_overview.html', context)

@login_required
def read_artist(request, pk):
    artista = get_object_or_404(Artista, idartista=pk)

    # Añadimos los estados exactos que permite tu SQL Server
    estados_actividad = ['Vigente', 'Archivado']

    context = {
        'artista': artista,
        'estados': estados_actividad
    }

    return render(request, 'catalogo/artistas/read_artist.html', context)

@login_required
def edit_artist(request, pk):
    artista = get_object_or_404(Artista, idartista=pk)

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE [Catalogo].[Artista]
                SET nombreArtistico=%s, 
                    biografia=%s, 
                    paisOrigen=%s,
                    estadoActivo=%s, 
                    urlPerfil=%s
                WHERE idArtista=%s
            """, [
                request.POST.get('nombreartistico'),
                request.POST.get('biografia'),
                request.POST.get('paisorigen'),
                request.POST.get('estadoactivo'),
                request.POST.get('urlperfil'),
                pk
            ])
            # connection.commit() # Descomentar si tu SQL Server lo requiere

        return JsonResponse({'status': 'success'})

    # Variables para los <select> del formulario
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
            # transaction.atomic() asegura que se borre todo junto o no se borre nada
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Eliminar Seguimientos del artista (ESQUEMA: Usuario)
                    cursor.execute("DELETE FROM [Usuario].[Seguimiento] WHERE Artista_idArtista = %s", [pk])

                    # 2. Eliminar Colaboraciones donde este artista fue invitado (ESQUEMA: Catalogo)
                    cursor.execute("DELETE FROM [Catalogo].[Colaboracion] WHERE Artista_idArtista = %s", [pk])

                    # --- PREPARAMOS LA SUBCONSULTA DE CANCIONES ---
                    query_canciones = """
                        SELECT idCancion FROM [Catalogo].[Cancion] c
                        INNER JOIN [Catalogo].[Album] a ON c.Album_idAlbum = a.idAlbum
                        WHERE a.Artista_idArtista = %s
                    """

                    # 3. Eliminar dependencias de las CANCIONES del artista respetando sus esquemas
                    cursor.execute(
                        f"DELETE FROM [Catalogo].[Colaboracion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Usuario].[CancionFavorita] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Usuario].[PlaylistCancion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Auditoria].[EstadisticaDiaria] WHERE Cancion_idCancion IN ({query_canciones})",
                        [pk])

                    # 4. Eliminar las Canciones en sí (ESQUEMA: Catalogo)
                    cursor.execute("""
                        DELETE FROM [Catalogo].[Cancion] 
                        WHERE Album_idAlbum IN (SELECT idAlbum FROM [Catalogo].[Album] WHERE Artista_idArtista = %s)
                    """, [pk])

                    # 5. Eliminar los Álbumes (ESQUEMA: Catalogo)
                    cursor.execute("DELETE FROM [Catalogo].[Album] WHERE Artista_idArtista = %s", [pk])

                    # 6. Finalmente, Eliminar al Artista (ESQUEMA: Catalogo)
                    cursor.execute("DELETE FROM [Catalogo].[Artista] WHERE idArtista = %s", [pk])

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

            if Artista.objects.filter(nombreartistico__iexact=nombre).exists():
                return JsonResponse({'status': 'error', 'message': 'El artista ya está registrado.'}, status=400)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [Catalogo].[Artista] 
                    (nombreArtistico, biografia, paisOrigen, estadoActivo, fechaRegistro, urlPerfil)
                    VALUES (%s, %s, %s, %s, GETDATE(), %s)
                """, [nombre, biografia, pais, estado, url_perfil])

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
    # Base QuerySets
    albumes = Album.objects.select_related('artista').all()
    artistas = Artista.objects.all().order_by('nombreartistico')

    # Capturar parámetros de la URL
    query = request.GET.get('q', '').strip()
    artista_id = request.GET.get('artista', '')
    orden = request.GET.get('orden', 'desc')

    # 1. Filtro por búsqueda de texto (en el título del álbum)
    if query:
        albumes = albumes.filter(tituloalbum__icontains=query)

    # 2. Filtro exacto por ID de artista
    if artista_id:
        albumes = albumes.filter(artista_id=artista_id)

    # 3. Ordenamiento por fecha de lanzamiento
    if orden == 'asc':
        albumes = albumes.order_by('fechalanzamiento')
    else:
        albumes = albumes.order_by('-fechalanzamiento')  # El guion indica orden descendente

    context = {
        'albumes': albumes,
        'artistas': artistas,
        'query': query,
    }
    return render(request, 'catalogo/albumes/albums_overview.html', context)

@login_required
def add_album(request):
    if request.method == 'GET':
        artistas = Artista.objects.all()
        return render(request, 'catalogo/albumes/add_album.html', {'artistas': artistas})

    if request.method == 'POST':
        try:
            titulo = request.POST.get('tituloalbum')
            fecha_lanzamiento = request.POST.get('fechalanzamiento')
            url_portada = request.POST.get('urlportada', '')
            artista_id = request.POST.get('artista')

            if not titulo or not artista_id or not fecha_lanzamiento:
                return JsonResponse({'status': 'error', 'message': 'Faltan campos obligatorios.'}, status=400)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [Catalogo].[Album] 
                    (tituloAlbum, fechaLanzamiento, urlPortada, Artista_idArtista)
                    VALUES (%s, %s, %s, %s)
                """, [titulo, fecha_lanzamiento, url_portada, artista_id])

            return JsonResponse({'status': 'success', 'message': 'Álbum guardado correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def read_album(request, pk):
    album = get_object_or_404(Album, idalbum=pk)
    artistas = Artista.objects.all()
    return render(request, 'catalogo/albumes/read_album.html', {'album': album, 'artistas': artistas})


@login_required
def edit_album(request, pk):
    album = get_object_or_404(Album, idalbum=pk)

    if request.method == 'POST':
        try:
            url_portada = request.POST.get('urlportada')
            with connection.cursor() as cursor:
                # Quitamos Artista_idArtista del UPDATE
                cursor.execute("""
                    UPDATE [Catalogo].[Album]
                    SET tituloAlbum=%s, 
                        fechaLanzamiento=%s, 
                        urlPortada=%s
                    WHERE idAlbum=%s
                """, [
                    request.POST.get('tituloalbum'),
                    request.POST.get('fechalanzamiento'),
                    url_portada,
                    pk
                ])
            return JsonResponse({'status': 'success', 'urlportada': url_portada})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # Para el GET, seguimos enviando los artistas por si necesitas mostrar el nombre
    artistas = Artista.objects.all()
    context = {'album': album, 'artistas': artistas}

    # Esta vista se renderiza en edit_album.html o se maneja por AJAX en read_album.html
    return render(request, 'catalogo/albumes/edit_album.html', context)

    artistas = Artista.objects.all()
    context = {'album': album, 'artistas': artistas}
    return render(request, 'catalogo/albumes/edit_album.html', context)

@login_required
def delete_album(request, pk):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Preparar subconsulta de canciones de este álbum
                    query_canciones = "SELECT idCancion FROM [Catalogo].[Cancion] WHERE Album_idAlbum = %s"

                    # 1. Limpiar dependencias de las canciones en otros esquemas
                    cursor.execute(
                        f"DELETE FROM [Catalogo].[Colaboracion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Usuario].[CancionFavorita] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Usuario].[PlaylistCancion] WHERE Cancion_idCancion IN ({query_canciones})", [pk])
                    cursor.execute(
                        f"DELETE FROM [Auditoria].[EstadisticaDiaria] WHERE Cancion_idCancion IN ({query_canciones})",
                        [pk])

                    # 2. Eliminar las canciones del álbum
                    cursor.execute("DELETE FROM [Catalogo].[Cancion] WHERE Album_idAlbum = %s", [pk])

                    # 3. Eliminar el álbum
                    cursor.execute("DELETE FROM [Catalogo].[Album] WHERE idAlbum = %s", [pk])

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
    query = request.GET.get('q', '')
    if query:
        generos = Genero.objects.filter(nombregenero__icontains=query)
    else:
        generos = Genero.objects.all()

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
            # Capturamos y limpiamos espacios extra al inicio o final
            nombre = request.POST.get('nombregenero', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()

            if not nombre:
                return JsonResponse({'status': 'error', 'message': 'El nombre del género es obligatorio.'}, status=400)

            with connection.cursor() as cursor:
                # 1. VERIFICACIÓN DE DUPLICADOS (Case-insensitive)
                cursor.execute("SELECT idGenero FROM [Catalogo].[Genero] WHERE LOWER(nombreGenero) = LOWER(%s)", [nombre])
                if cursor.fetchone():
                    # Si encuentra un resultado, frena todo y lanza el error al Toast
                    return JsonResponse({'status': 'error', 'message': f'El género "{nombre}" ya está registrado en el catálogo.'}, status=400)

                # 2. INSERCIÓN (Si pasó la prueba anterior)
                cursor.execute("""
                    INSERT INTO [Catalogo].[Genero] (nombreGenero, descripcion)
                    VALUES (%s, %s)
                """, [nombre, descripcion])

            return JsonResponse({'status': 'success', 'message': 'Género registrado correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def read_genre(request, pk):
    genero = get_object_or_404(Genero, idgenero=pk)
    return render(request, 'catalogo/generos/read_genre.html', {'genero': genero})

@login_required
def edit_genre(request, pk):
    genero = get_object_or_404(Genero, idgenero=pk)

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE [Catalogo].[Genero]
                    SET nombreGenero = %s,
                        descripcion = %s
                    WHERE idGenero = %s
                """, [
                    request.POST.get('nombregenero'),
                    request.POST.get('descripcion'),
                    pk
                ])
            return JsonResponse({'status': 'success', 'message': 'Género actualizado correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return render(request, 'catalogo/generos/edit_genre.html', {'genero': genero})


@login_required
def delete_genre(request, pk):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Buscar si ya existe el género de respaldo
                    cursor.execute(
                        "SELECT idGenero FROM [Catalogo].[Genero] WHERE nombreGenero = 'Sin género asignado'")
                    row = cursor.fetchone()

                    if row:
                        default_id = row[0]
                    else:
                        # Si no existe, lo creamos de forma automática en una fila nueva
                        cursor.execute("""
                            INSERT INTO [Catalogo].[Genero] (nombreGenero, descripcion)
                            VALUES ('Sin género asignado', 'Categoría temporal para canciones cuyo género original fue eliminado.')
                        """)
                        # Capturamos el ID asignado por el IDENTITY de SQL Server
                        cursor.execute("SELECT SCOPE_IDENTITY()")
                        default_id = int(cursor.fetchone()[0])

                    # 2. Protección integral: Evitar que se elimine el mismísimo registro de respaldo
                    if int(pk) == default_id:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Protección de sistema: No se puede eliminar el género de respaldo global.'
                        }, status=400)

                    # 3. Traspasar las canciones al género comodín (Evita el borrado de tracks)
                    cursor.execute("""
                        UPDATE [Catalogo].[Cancion]
                        SET Genero_idGenero = %s
                        WHERE Genero_idGenero = %s
                    """, [default_id, pk])

                    # 4. Una vez liberadas las amarras, eliminamos el género original de forma segura
                    cursor.execute("DELETE FROM [Catalogo].[Genero] WHERE idGenero = %s", [pk])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error al reasignar registros: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


# ══════════════════════════════════════════
#  COLABORACIONES
# ══════════════════════════════════════════
def colabs_overview(request):
    colaboraciones = Colaboracion.objects.select_related('cancion', 'artista', 'cancion__album').all()

    query = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '')
    orden = request.GET.get('orden', 'desc')

    if query:
        # Búsqueda combinada: puede buscar por nombre de artista o título de canción
        colaboraciones = colaboraciones.filter(
            Q(artista__nombreartistico__icontains=query) |
            Q(cancion__titulocancion__icontains=query)
        )

    if rol:
        colaboraciones = colaboraciones.filter(rolartista__iexact=rol)

    # Ordenamiento basado en idcolaboracion (o puedes usar fechas si tu modelo las tiene)
    if orden == 'asc':
        colaboraciones = colaboraciones.order_by('idcolaboracion')
    else:
        colaboraciones = colaboraciones.order_by('-idcolaboracion')

    context = {
        'colaboraciones': colaboraciones,
        'query': query,
    }
    return render(request, 'catalogo/colaboraciones/colabs_overview.html', context)


@login_required
def add_colab(request):
    if request.method == 'GET':
        context = {
            'canciones': Cancion.objects.all(),
            'artistas': Artista.objects.all(),
        }
        return render(request, 'catalogo/colaboraciones/add_colab.html', context)

    if request.method == 'POST':
        try:
            id_cancion = request.POST.get('cancion')
            id_artista = request.POST.get('artista')
            rol_obtenido = request.POST.get('rol', '').strip()  # Lo recibimos del form como 'rol'

            if not all([id_cancion, id_artista, rol_obtenido]):
                return JsonResponse({'status': 'error', 'message': 'Todos los campos son obligatorios.'}, status=400)

            with connection.cursor() as cursor:
                # Verificación de duplicado
                cursor.execute("""
                    SELECT idColaboracion FROM [Catalogo].[Colaboracion] 
                    WHERE Cancion_idCancion = %s AND Artista_idArtista = %s
                """, [id_cancion, id_artista])

                if cursor.fetchone():
                    return JsonResponse(
                        {'status': 'error', 'message': 'Este artista ya está vinculado a esta canción.'}, status=400)

                # INSERCIÓN CORREGIDA (Apuntando a rolArtista)
                cursor.execute("""
                    INSERT INTO [Catalogo].[Colaboracion] (Cancion_idCancion, Artista_idArtista, rolArtista)
                    VALUES (%s, %s, %s)
                """, [id_cancion, id_artista, rol_obtenido])

            return JsonResponse({'status': 'success', 'message': 'Colaboración registrada.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def read_colab(request, pk):
    colaboracion = get_object_or_404(Colaboracion.objects.select_related('cancion', 'artista'), idcolaboracion=pk)
    # Mandamos las listas para el modo edición inline
    context = {
        'colaboracion': colaboracion,
        'canciones': Cancion.objects.all(),
        'artistas': Artista.objects.all(),
    }
    return render(request, 'catalogo/colaboraciones/read_colab.html', context)


@login_required
def edit_colab(request, pk):
    colaboracion = get_object_or_404(Colaboracion.objects.select_related('cancion', 'artista'), idcolaboracion=pk)

    if request.method == 'GET':
        context = {
            'colaboracion': colaboracion,
            'canciones': Cancion.objects.all(),
            'artistas': Artista.objects.all(),
        }
        return render(request, 'catalogo/colaboraciones/edit_colab.html', context)

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE [Catalogo].[Colaboracion]
                    SET Cancion_idCancion = %s,
                        Artista_idArtista = %s,
                        rolArtista = %s
                    WHERE idColaboracion = %s
                """, [
                    request.POST.get('cancion'),
                    request.POST.get('artista'),
                    request.POST.get('rol'),
                    pk
                ])
            return JsonResponse({'status': 'success', 'message': 'Colaboración actualizada.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return colabs_overview(request)

@login_required
def delete_colab(request, pk):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # La eliminación aquí es sencilla porque nadie depende de esta tabla intermedia
                cursor.execute("DELETE FROM [Catalogo].[Colaboracion] WHERE idColaboracion = %s", [pk])
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error: {str(e)}"}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


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


# ── VISTAS BASE DE REPORTE (PANTALLA) ──
@login_required
def reporte_top_10(request):
    canciones = []
    try:
        canciones = _obtener_datos_sql("EXEC Auditoria.sp_RankingPopularidadMensual")
    except Exception as e:
        messages.error(request, f"Error SQL: {str(e)}")
    return render(request, 'catalogo/reportes/reporte_top_10.html', {'canciones': canciones})


@login_required
def reporte_auditoria_catalogo(request):
    inconsistencias = []
    try:
        inconsistencias = _obtener_datos_sql("SELECT * FROM Catalogo.vw_AuditoriaMetadatosIncompletos")
    except Exception as e:
        messages.error(request, f"Error SQL: {str(e)}")
    return render(request, 'catalogo/reportes/reporte_auditoria.html', {'inconsistencias': inconsistencias})


# ── VISTAS DE EXPORTACIÓN Y ENVÍO (TOP 10) ──
@login_required
def exportar_top_10_pdf(request):
    try:
        canciones = _obtener_datos_sql("EXEC Auditoria.sp_RankingPopularidadMensual")
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
        canciones = _obtener_datos_sql("EXEC Auditoria.sp_RankingPopularidadMensual")
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
        inconsistencias = _obtener_datos_sql("SELECT * FROM Catalogo.vw_AuditoriaMetadatosIncompletos")
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
        inconsistencias = _obtener_datos_sql("SELECT * FROM Catalogo.vw_AuditoriaMetadatosIncompletos")
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
