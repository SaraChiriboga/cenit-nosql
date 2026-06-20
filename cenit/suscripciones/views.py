from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    TipoSuscripcion, Promocion, Suscripcion,
    Notificacion, Playlist, PlaylistCancion, EstadisticaDiaria
)


# ══════════════════════════════════════════
#  TIPOS DE SUSCRIPCIÓN
# ══════════════════════════════════════════

@login_required
def plan_list(request):
    planes = TipoSuscripcion.objects.all()
    query = request.GET.get('q', '')
    if query:
        planes = planes.filter(
            Q(nombreplan__icontains=query) | Q(moneda__icontains=query)
        )
    return render(request, 'Suscripciones/plan/plan_list.html', {
        'planes': planes,
        'query': query,
    })


@login_required
def plan_add(request):
    MONEDAS = ['USD', 'EUR', 'GBP', 'AUD', 'BRL', 'CAD', 'CHF',
               'CNY', 'INR', 'JPY', 'KRW', 'MXN', 'RUB', 'ZAR']
    if request.method == 'POST':
        try:
            nombreplan = request.POST.get('nombreplan')
            precio = request.POST.get('precio')
            moneda = request.POST.get('moneda')
            duracion = request.POST.get('duracion')

            if not all([nombreplan, precio, moneda, duracion]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/plan/plan_form.html', {'action': 'Nuevo', 'monedas': MONEDAS})

            # Crear sin idtipo (se genera solo)
            TipoSuscripcion.objects.create(
                nombreplan=nombreplan,
                precio=precio,
                moneda=moneda,
                duracion=duracion,
            )
            messages.success(request, f"Plan '{nombreplan}' creado correctamente.")
            return redirect('plan_list')
        except Exception as e:
            messages.error(request, f'Error al crear el plan: {e}')
    return render(request, 'Suscripciones/plan/plan_form.html', {'action': 'Nuevo', 'monedas': MONEDAS})


@login_required
def plan_edit(request, pk):
    plan = get_object_or_404(TipoSuscripcion, pk=pk)
    MONEDAS = ['USD', 'EUR', 'GBP', 'AUD', 'BRL', 'CAD', 'CHF',
               'CNY', 'INR', 'JPY', 'KRW', 'MXN', 'RUB', 'ZAR']
    if request.method == 'POST':
        try:
            plan.nombreplan = request.POST.get('nombreplan')
            plan.precio     = request.POST.get('precio')
            plan.moneda     = request.POST.get('moneda')
            plan.duracion   = request.POST.get('duracion')
            plan.save()
            messages.success(request, f"Plan '{plan.nombreplan}' actualizado.")
            return redirect('plan_list')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {e}')

    return render(request, 'Suscripciones/plan/plan_form.html', {
        'action': 'Editar',
        'plan': plan,
        'monedas': MONEDAS,
    })


@login_required
def plan_delete(request, pk):
    plan = get_object_or_404(TipoSuscripcion, pk=pk)
    if request.method == 'POST':
        nombre = plan.nombreplan
        plan.delete()
        messages.success(request, f"Plan '{nombre}' eliminado.")
        return redirect('plan_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': plan,
        'tipo': 'plan de suscripción',
        'cancel_url': 'plan_list',
    })


# ══════════════════════════════════════════
#  PROMOCIONES
# ══════════════════════════════════════════

@login_required
def promocion_list(request):
    promociones = Promocion.objects.select_related('tiposuscripcion').all()
    query = request.GET.get('q', '')
    if query:
        promociones = promociones.filter(
            Q(descripcion__icontains=query) |
            Q(tiposuscripcion__nombreplan__icontains=query)
        )
    return render(request, 'Suscripciones/promocion/promocion_list.html', {
        'promociones': promociones,
        'query': query,
    })


@login_required
def promocion_add(request):
    planes = TipoSuscripcion.objects.all()
    if request.method == 'POST':
        try:
            descripcion = request.POST.get('descripcion')
            porcentajedesc = request.POST.get('porcentajedesc')
            fechainicio = request.POST.get('fechainicio')
            fechaexpira = request.POST.get('fechaexpira') or None
            estadoactivo = request.POST.get('estadoactivo') == 'on'
            idtipo = request.POST.get('tiposuscripcion')

            if not all([descripcion, porcentajedesc, fechainicio, idtipo]):
                messages.error(request, 'Faltan campos obligatorios.')
                return render(request, 'Suscripciones/promocion/promocion_form.html', {'action': 'Nueva', 'planes': planes})

            Promocion.objects.create(
                descripcion=descripcion,
                porcentajedesc=porcentajedesc,
                fechainicio=fechainicio,
                fechaexpira=fechaexpira,
                estadoactivo=estadoactivo,
                tiposuscripcion_id=idtipo,
            )
            messages.success(request, f"Promoción '{descripcion}' creada.")
            return redirect('promocion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')
    return render(request, 'Suscripciones/promocion/promocion_form.html', {'action': 'Nueva', 'planes': planes})


@login_required
def promocion_edit(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    planes = TipoSuscripcion.objects.all()
    if request.method == 'POST':
        try:
            promocion.descripcion    = request.POST.get('descripcion')
            promocion.porcentajedesc = request.POST.get('porcentajedesc')
            promocion.fechainicio    = request.POST.get('fechainicio')
            promocion.fechaexpira    = request.POST.get('fechaexpira') or None
            promocion.estadoactivo   = request.POST.get('estadoactivo') == 'on'
            promocion.tiposuscripcion_id = request.POST.get('tiposuscripcion')
            promocion.save()
            messages.success(request, f"Promoción '{promocion.descripcion}' actualizada.")
            return redirect('promocion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/promocion/promocion_form.html', {
        'action': 'Editar',
        'promocion': promocion,
        'planes': planes,
    })


@login_required
def promocion_delete(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        desc = promocion.descripcion
        promocion.delete()
        messages.success(request, f"Promoción '{desc}' eliminada.")
        return redirect('promocion_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': promocion,
        'tipo': 'promoción',
        'cancel_url': 'promocion_list',
    })


# ══════════════════════════════════════════
#  SUSCRIPCIONES
# ══════════════════════════════════════════

@login_required
def suscripcion_list(request):
    suscripciones = Suscripcion.objects.select_related(
        'usuario', 'tiposuscripcion', 'promocion'
    ).all()
    query = request.GET.get('q', '')
    if query:
        suscripciones = suscripciones.filter(
            Q(estado__icontains=query) |
            Q(tiposuscripcion__nombreplan__icontains=query) |
            Q(usuario__nombre__icontains=query)
        )
    return render(request, 'Suscripciones/suscripcion/suscripcion_list.html', {
        'suscripciones': suscripciones,
        'query': query,
    })


@login_required
def suscripcion_add(request):
    from usuarios.models import Usuario
    planes = TipoSuscripcion.objects.all()
    promociones = Promocion.objects.filter(estadoactivo=True)
    usuarios = Usuario.objects.all()

    if request.method == 'POST':
        try:
            fechainicio = request.POST.get('fechainicio')
            fechafin = request.POST.get('fechafin')
            estado = request.POST.get('estado')
            idusuario = request.POST.get('usuario') or None
            idtipo = request.POST.get('tiposuscripcion')
            idpromo = request.POST.get('promocion') or None

            # Quitamos idsuscripcion de la validación
            if not all([fechainicio, fechafin, estado, idtipo]):
                messages.error(request, 'Faltan campos obligatorios.')
                return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
                    'action': 'Nueva', 'planes': planes,
                    'promociones': promociones, 'usuarios': usuarios,
                })

            Suscripcion.objects.create(
                # idsuscripcion ya no se envía (se genera automáticamente la PK 'id')
                fechainicio=fechainicio,
                fechafin=fechafin,
                estado=estado,
                usuario_id=idusuario,
                tiposuscripcion_id=idtipo,
                promocion_id=idpromo,
            )
            messages.success(request, 'Suscripción registrada correctamente.')
            return redirect('suscripcion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
        'action': 'Nueva',
        'planes': planes,
        'promociones': promociones,
        'usuarios': usuarios,
        'estados': ['Activa', 'Cancelada', 'Expirada'],
    })


@login_required
def suscripcion_edit(request, pk):
    from usuarios.models import Usuario  # ← import local igual que en add
    suscripcion = get_object_or_404(Suscripcion, pk=pk)
    planes = TipoSuscripcion.objects.all()
    promociones = Promocion.objects.filter(estadoactivo=True)
    usuarios = Usuario.objects.all()   # ← AGREGAR

    if request.method == 'POST':
        try:
            suscripcion.fechainicio = request.POST.get('fechainicio')
            suscripcion.fechafin = request.POST.get('fechafin')
            suscripcion.estado = request.POST.get('estado')
            suscripcion.tiposuscripcion_id = request.POST.get('tiposuscripcion')
            suscripcion.promocion_id = request.POST.get('promocion') or None
            suscripcion.usuario_id = request.POST.get('usuario') or None   # ← AGREGAR
            suscripcion.save()
            messages.success(request, 'Suscripción actualizada.')
            return redirect('suscripcion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
        'action': 'Editar',
        'suscripcion': suscripcion,
        'planes': planes,
        'promociones': promociones,
        'usuarios': usuarios,   
        'estados': ['Activa', 'Cancelada', 'Expirada'],
    })


@login_required
def suscripcion_delete(request, pk):
    suscripcion = get_object_or_404(Suscripcion, pk=pk)
    if request.method == 'POST':
        suscripcion.delete()
        messages.success(request, 'Suscripción eliminada.')
        return redirect('suscripcion_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': suscripcion,
        'tipo': 'suscripción',
        'cancel_url': 'suscripcion_list',
    })


# ══════════════════════════════════════════
#  NOTIFICACIONES
# ══════════════════════════════════════════

@login_required
def notificacion_list(request):
    notificaciones = Notificacion.objects.select_related('usuario', 'promocion').all()
    query = request.GET.get('q', '')
    if query:
        notificaciones = notificaciones.filter(
            Q(tiponotif__icontains=query) |
            Q(usuario__nombre__icontains=query) |
            Q(mensaje__icontains=query)
        )
    return render(request, 'Suscripciones/notificacion/notificacion_list.html', {
        'notificaciones': notificaciones,
        'query': query,
    })


@login_required
def notificacion_add(request):
    from usuarios.models import Usuario
    usuarios = Usuario.objects.all()
    promociones = Promocion.objects.all()
    TIPOS = ['Aviso de Seguridad', 'Nuevo Lanzamiento', 'Pago Exitoso']

    if request.method == 'POST':
        try:
            # ya no se captura idnotificacion
            tiponotif = request.POST.get('tiponotif')
            mensaje = request.POST.get('mensaje')
            idusuario = request.POST.get('usuario')
            idpromo = request.POST.get('promocion')

            if not all([tiponotif, mensaje, idusuario, idpromo]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/notificacion/notificacion_form.html', {
                    'action': 'Nueva', 'usuarios': usuarios,
                    'promociones': promociones, 'tipos': TIPOS,
                })

            Notificacion.objects.create(
                # idnotificacion ya no se envía
                tiponotif=tiponotif,
                mensaje=mensaje,
                usuario_id=idusuario,
                promocion_id=idpromo,
            )
            messages.success(request, 'Notificación creada correctamente.')
            return redirect('notificacion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/notificacion/notificacion_form.html', {
        'action': 'Nueva',
        'usuarios': usuarios,
        'promociones': promociones,
        'tipos': TIPOS,
    })


@login_required
def notificacion_delete(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)
    if request.method == 'POST':
        notificacion.delete()
        messages.success(request, 'Notificación eliminada.')
        return redirect('notificacion_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': notificacion,
        'tipo': 'notificación',
        'cancel_url': 'notificacion_list',
    })


# ══════════════════════════════════════════
#  PLAYLISTS
# ══════════════════════════════════════════

@login_required
def playlist_list(request):
    playlists = Playlist.objects.select_related('usuario').all()
    query = request.GET.get('q', '')
    if query:
        playlists = playlists.filter(
            Q(nombre__icontains=query) |
            Q(usuario__nombre__icontains=query)
        )
    return render(request, 'Suscripciones/playlist/playlist_list.html', {
        'playlists': playlists,
        'query': query,
    })


@login_required
def playlist_add(request):
    from usuarios.models import Usuario
    usuarios = Usuario.objects.all()

    if request.method == 'POST':
        try:
            # ya no se captura idplaylist
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion') or None
            esprivada = request.POST.get('esprivada') == 'on'
            espublicada = request.POST.get('espublicada') == 'on'
            imagenportada = request.POST.get('imagenportada') or None
            idusuario = request.POST.get('usuario') or None

            # validar solo los campos que siguen siendo obligatorios
            if not nombre:
                messages.error(request, 'El nombre es obligatorio.')
                return render(request, 'Suscripciones/playlist/playlist_form.html',
                              {'action': 'Nueva', 'usuarios': usuarios})

            Playlist.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                esprivada=esprivada,
                espublicada=espublicada,
                imagenportada=imagenportada,
                usuario_id=idusuario,
            )
            messages.success(request, f"Playlist '{nombre}' creada.")
            return redirect('playlist_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/playlist/playlist_form.html', {
        'action': 'Nueva',
        'usuarios': usuarios,
    })


@login_required
def playlist_edit(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)
    from usuarios.models import Usuario
    usuarios = Usuario.objects.all()

    if request.method == 'POST':
        try:
            playlist.nombre        = request.POST.get('nombre')
            playlist.descripcion   = request.POST.get('descripcion') or None
            playlist.esprivada     = request.POST.get('esprivada') == 'on'
            playlist.espublicada   = request.POST.get('espublicada') == 'on'
            playlist.imagenportada = request.POST.get('imagenportada') or None
            playlist.usuario_id    = request.POST.get('usuario') or None
            playlist.save()
            messages.success(request, f"Playlist '{playlist.nombre}' actualizada.")
            return redirect('playlist_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/playlist/playlist_form.html', {
        'action': 'Editar',
        'playlist': playlist,
        'usuarios': usuarios,
    })


@login_required
def playlist_delete(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)
    if request.method == 'POST':
        nombre = playlist.nombre
        playlist.delete()
        messages.success(request, f"Playlist '{nombre}' eliminada.")
        return redirect('playlist_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': playlist,
        'tipo': 'playlist',
        'cancel_url': 'playlist_list',
    })


# ══════════════════════════════════════════
#  PLAYLIST — CANCIONES
# ══════════════════════════════════════════

@login_required
def playlist_canciones(request, pk):
    playlist  = get_object_or_404(Playlist, pk=pk)
    entradas  = PlaylistCancion.objects.select_related('cancion').filter(
        playlist=playlist
    ).order_by('orden')
    return render(request, 'Suscripciones/playlist/playlist_canciones.html', {
        'playlist': playlist,
        'entradas': entradas,
    })


@login_required
def playlist_cancion_agregar(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)
    from catalogo.models import Cancion
    canciones = Cancion.objects.all()

    if request.method == 'POST':
        try:
            cancion_id   = request.POST.get('cancion')
            orden        = request.POST.get('orden')

            if PlaylistCancion.objects.filter(playlist=playlist, cancion_id=cancion_id).exists():
                messages.error(request, 'Esa canción ya está en la playlist.')
                return render(request, 'Suscripciones/playlist/playlist_cancion_form.html', {
                    'playlist': playlist, 'canciones': canciones,
                })

            PlaylistCancion.objects.create(
                playlist=playlist,
                cancion_id=cancion_id,
                orden=orden or 0,
            )
            messages.success(request, 'Canción agregada a la playlist.')
            return redirect('playlist_canciones', pk=pk)

        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/playlist/playlist_cancion_form.html', {
        'playlist': playlist,
        'canciones': canciones,
    })


@login_required
def playlist_cancion_quitar(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)

    if request.method == 'POST':
        cancion_id = request.POST.get('cancion_id')
        entrada = PlaylistCancion.objects.filter(
            playlist=playlist, cancion_id=cancion_id
        ).first()
        if entrada:
            entrada.delete()
            messages.success(request, 'Canción quitada de la playlist.')
        else:
            messages.error(request, 'No se encontró esa canción en la playlist.')
        return redirect('playlist_canciones', pk=pk)

    return redirect('playlist_canciones', pk=pk)


# ══════════════════════════════════════════
#  ESTADÍSTICAS DIARIAS
# ══════════════════════════════════════════

@login_required
def estadistica_list(request):
    estadisticas = EstadisticaDiaria.objects.select_related('cancion', 'cancion__album').all().order_by('-fechareporte')
    query = request.GET.get('q', '')
    if query:
        estadisticas = estadisticas.filter(
            Q(cancion__titulocancion__icontains=query) |
            Q(fechareporte__icontains=query)
        )
    return render(request, 'Suscripciones/estadistica/estadistica_list.html', {
        'estadisticas': estadisticas,
        'query': query,
    })


@login_required
def estadistica_add(request):
    from catalogo.models import Cancion
    canciones = Cancion.objects.all()

    if request.method == 'POST':
        try:
            totalrepros  = request.POST.get('totalrepros')
            fechareporte = request.POST.get('fechareporte')
            cancion_id   = request.POST.get('cancion')

            if not all([totalrepros, fechareporte, cancion_id]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/estadistica/estadistica_form.html',
                              {'action': 'Nueva', 'canciones': canciones})

            EstadisticaDiaria.objects.create(
                totalrepros=totalrepros,
                fechareporte=fechareporte,
                cancion_id=cancion_id,
            )
            messages.success(request, 'Estadística registrada.')
            return redirect('estadistica_list')

        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/estadistica/estadistica_form.html', {
        'action': 'Nueva',
        'canciones': canciones,
    })


@login_required
def estadistica_delete(request, pk):
    estadistica = get_object_or_404(EstadisticaDiaria, pk=pk)
    if request.method == 'POST':
        estadistica.delete()
        messages.success(request, 'Estadística eliminada.')
        return redirect('estadistica_list')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto': estadistica,
        'tipo': 'estadística',
        'cancel_url': 'estadistica_list',
    })


# ══════════════════════════════════════════
#  REPORTES
# ══════════════════════════════════════════

@login_required
def reporte_vencimientos(request):
    """Informe B: Suscripciones que vencen en los próximos 5 días."""
    hoy    = timezone.now()
    limite = hoy + timedelta(days=5)
    proximas = Suscripcion.objects.select_related(
        'usuario', 'tiposuscripcion'
    ).filter(
        estado='Activa',
        fechafin__gte=hoy,
        fechafin__lte=limite,
    ).order_by('fechafin')

    return render(request, 'Suscripciones/reportes/reporte_vencimientos.html', {
        'proximas': proximas,
        'hoy': hoy,
        'limite': limite,
    })


@login_required
def reporte_promociones_vencidas(request):
    """Informe D: Promociones expiradas que aún figuran como activas."""
    ahora = timezone.now()
    vencidas = Promocion.objects.select_related('tiposuscripcion').filter(
        estadoactivo=True,
        fechaexpira__lt=ahora,
    ).order_by('fechaexpira')

    return render(request, 'Suscripciones/reportes/reporte_promociones_vencidas.html', {
        'vencidas': vencidas,
        'ahora': ahora,
    })