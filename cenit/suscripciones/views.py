from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from bson import ObjectId
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from cenit.mongo_client import db
from .models import MongoDoc, prepare_doc, parse_date

# ── Colecciones de MongoDB ──────────────────────────────
tipo_suscripciones_col = db['tipoSuscripciones']
promociones_col        = db['promociones']
suscripciones_col      = db['suscripciones']
notificaciones_col     = db['notificaciones']
playlists_col          = db['playlists']
estadisticas_col       = db['estadisticasDiarias']
usuarios_col           = db['usuarios']
canciones_col          = db['Cancion']


# ── Helpers ─────────────────────────────────────────────

def _get_or_404(collection, filtro, request, redirect_url, msg='No encontrado.'):
    """Busca un documento; si no existe, redirige con mensaje de error."""
    doc = collection.find_one(filtro)
    if not doc:
        messages.error(request, msg)
        return None
    return doc


def _usuarios_dropdown():
    """Devuelve lista de usuarios para los dropdowns de formularios."""
    docs = usuarios_col.find({}, {'id': 1, 'nombre': 1, 'apellido': 1}).sort('nombre', 1)
    return [MongoDoc(d) for d in docs]


def _planes_dropdown():
    """Devuelve lista de planes para los dropdowns."""
    return [MongoDoc(d) for d in tipo_suscripciones_col.find().sort('tipo_id', 1)]


def _promociones_dropdown(solo_activas=False):
    """Devuelve lista de promociones para los dropdowns."""
    filtro = {'estadoActivo': True} if solo_activas else {}
    return [MongoDoc(d) for d in promociones_col.find(filtro).sort('promo_id', 1)]


def _canciones_dropdown():
    """Devuelve lista de canciones para los dropdowns."""
    docs = canciones_col.find({}, {'cancion_id': 1, 'tituloCancion': 1}).sort('tituloCancion', 1)
    return [MongoDoc(d) for d in docs]


def _lookup_usuarios(user_ids):
    """Dado un set de IDs de usuario, retorna un dict {id: 'Nombre Apellido'}."""
    if not user_ids:
        return {}
    docs = usuarios_col.find({'id': {'$in': list(user_ids)}}, {'id': 1, 'nombre': 1, 'apellido': 1})
    return {d['id']: f"{d.get('nombre', '')} {d.get('apellido', '')}" for d in docs}


def _next_id(collection, field):
    """Genera el siguiente ID numérico auto-incremental para una colección."""
    last = collection.find_one(sort=[(field, -1)])
    return (last[field] + 1) if last else 1


# ══════════════════════════════════════════
#  TIPOS DE SUSCRIPCIÓN
# ══════════════════════════════════════════

MONEDAS = ['USD', 'EUR', 'GBP', 'AUD', 'BRL', 'CAD', 'CHF',
           'CNY', 'INR', 'JPY', 'KRW', 'MXN', 'RUB', 'ZAR']


@login_required
def plan_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    if query:
        filtro = {'$or': [
            {'nombrePlan': {'$regex': query, '$options': 'i'}},
            {'moneda':     {'$regex': query, '$options': 'i'}},
        ]}
    planes = [MongoDoc(d) for d in tipo_suscripciones_col.find(filtro).sort('tipo_id', 1)]
    import sys
    if planes:
        print(f"DEBUG VIEW: plan type is {type(planes[0])}", file=sys.stderr)
        print(f"DEBUG VIEW: plan._data is {planes[0]._data}", file=sys.stderr)
        print(f"DEBUG VIEW: plan.tipo_id evaluates to {getattr(planes[0], 'tipo_id', 'NOT FOUND')}", file=sys.stderr)
    return render(request, 'Suscripciones/plan/plan_list.html', {
        'planes': planes,
        'query': query,
    })


@login_required
def plan_add(request):
    if request.method == 'POST':
        try:
            nombre  = request.POST.get('nombreplan')
            precio  = request.POST.get('precio')
            moneda  = request.POST.get('moneda')
            duracion = request.POST.get('duracion')

            if not all([nombre, precio, moneda, duracion]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/plan/plan_form.html',
                              {'action': 'Nuevo', 'monedas': MONEDAS})

            tipo_suscripciones_col.insert_one({
                'tipo_id':    _next_id(tipo_suscripciones_col, 'tipo_id'),
                'nombrePlan': nombre,
                'precio':     float(precio),
                'moneda':     moneda,
                'duracion':   int(duracion),
            })
            messages.success(request, f"Plan '{nombre}' creado correctamente.")
            return redirect('plan_list')
        except Exception as e:
            messages.error(request, f'Error al crear el plan: {e}')
    return render(request, 'Suscripciones/plan/plan_form.html',
                  {'action': 'Nuevo', 'monedas': MONEDAS})


@login_required
def plan_edit(request, pk):
    doc = _get_or_404(tipo_suscripciones_col, {'tipo_id': pk}, request, 'plan_list')
    if not doc:
        return redirect('plan_list')

    if request.method == 'POST':
        try:
            new_name = request.POST.get('nombreplan')
            tipo_suscripciones_col.update_one({'tipo_id': pk}, {'$set': {
                'nombrePlan': new_name,
                'precio':     float(request.POST.get('precio')),
                'moneda':     request.POST.get('moneda'),
                'duracion':   int(request.POST.get('duracion')),
            }})
            messages.success(request, f"Plan '{new_name}' actualizado.")
            return redirect('plan_list')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {e}')
            doc = tipo_suscripciones_col.find_one({'tipo_id': pk})

    return render(request, 'Suscripciones/plan/plan_form.html', {
        'action': 'Editar',
        'plan':    MongoDoc(doc),
        'monedas': MONEDAS,
    })


@login_required
def plan_delete(request, pk):
    doc = _get_or_404(tipo_suscripciones_col, {'tipo_id': pk}, request, 'plan_list')
    if not doc:
        return redirect('plan_list')

    if request.method == 'POST':
        nombre = doc.get('nombrePlan')
        tipo_suscripciones_col.delete_one({'tipo_id': pk})
        messages.success(request, f"Plan '{nombre}' eliminado.")
        return redirect('plan_list')

    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     doc.get('nombrePlan'),
        'tipo':       'plan de suscripción',
        'cancel_url': 'plan_list',
    })


# ══════════════════════════════════════════
#  PROMOCIONES
# ══════════════════════════════════════════

@login_required
def promocion_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    if query:
        filtro = {'$or': [
            {'descripcion':                {'$regex': query, '$options': 'i'}},
            {'tipoSuscripcion.nombrePlan': {'$regex': query, '$options': 'i'}},
        ]}
    docs = list(promociones_col.find(filtro).sort('promo_id', 1))
    for d in docs:
        prepare_doc(d)
    promociones = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/promocion/promocion_list.html', {
        'promociones': promociones,
        'query': query,
    })


@login_required
def promocion_add(request):
    planes = _planes_dropdown()
    if request.method == 'POST':
        try:
            descripcion    = request.POST.get('descripcion')
            porcentajedesc = request.POST.get('porcentajedesc')
            fechainicio     = request.POST.get('fechainicio')
            fechaexpira     = request.POST.get('fechaexpira') or None
            estadoactivo    = request.POST.get('estadoactivo') == 'on'
            idtipo          = request.POST.get('tiposuscripcion')

            if not all([descripcion, porcentajedesc, fechainicio, idtipo]):
                messages.error(request, 'Faltan campos obligatorios.')
                return render(request, 'Suscripciones/promocion/promocion_form.html',
                              {'action': 'Nueva', 'planes': planes})

            # Buscar el plan para embeber
            plan_doc = tipo_suscripciones_col.find_one({'tipo_id': int(idtipo)})
            tipo_embed = {
                '_id':        int(idtipo),
                'nombrePlan': plan_doc['nombrePlan'] if plan_doc else '',
            }

            fecha_inicio_str = f"{fechainicio}T00:00:00" if fechainicio and 'T' not in fechainicio else fechainicio
            fecha_expira_str = (f"{fechaexpira}T00:00:00" if fechaexpira and 'T' not in fechaexpira else fechaexpira) if fechaexpira else None

            promociones_col.insert_one({
                'promo_id':         _next_id(promociones_col, 'promo_id'),
                'descripcion':      descripcion,
                'porcentajeDesc':   int(porcentajedesc),
                'fechaInicio':      fecha_inicio_str,
                'fechaExpira':      fecha_expira_str,
                'estadoActivo':     estadoactivo,
                'tipoSuscripcion':  tipo_embed,
            })
            messages.success(request, f"Promoción '{descripcion}' creada.")
            return redirect('promocion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')
    return render(request, 'Suscripciones/promocion/promocion_form.html',
                  {'action': 'Nueva', 'planes': planes})


@login_required
def promocion_edit(request, pk):
    doc = _get_or_404(promociones_col, {'promo_id': pk}, request, 'promocion_list')
    if not doc:
        return redirect('promocion_list')

    planes = _planes_dropdown()

    if request.method == 'POST':
        try:
            desc     = request.POST.get('descripcion')
            idtipo   = request.POST.get('tiposuscripcion')
            fechainicio = request.POST.get('fechainicio')
            fechaexpira = request.POST.get('fechaexpira') or None

            plan_doc = tipo_suscripciones_col.find_one({'tipo_id': int(idtipo)})
            tipo_embed = {
                '_id':        int(idtipo),
                'nombrePlan': plan_doc['nombrePlan'] if plan_doc else '',
            }

            fecha_inicio_str = f"{fechainicio}T00:00:00" if fechainicio and 'T' not in fechainicio else fechainicio
            fecha_expira_str = (f"{fechaexpira}T00:00:00" if fechaexpira and 'T' not in fechaexpira else fechaexpira) if fechaexpira else None

            promociones_col.update_one({'promo_id': pk}, {'$set': {
                'descripcion':     desc,
                'porcentajeDesc':  int(request.POST.get('porcentajedesc')),
                'fechaInicio':     fecha_inicio_str,
                'fechaExpira':     fecha_expira_str,
                'estadoActivo':    request.POST.get('estadoactivo') == 'on',
                'tipoSuscripcion': tipo_embed,
            }})
            messages.success(request, f"Promoción '{desc}' actualizada.")
            return redirect('promocion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            doc = promociones_col.find_one({'promo_id': pk})

    prepare_doc(doc)
    # Añadir campo auxiliar para el select del formulario
    doc['tiposuscripcion_id'] = doc.get('tipoSuscripcion', {}).get('_id')
    return render(request, 'Suscripciones/promocion/promocion_form.html', {
        'action':    'Editar',
        'promocion': MongoDoc(doc),
        'planes':    planes,
    })


@login_required
def promocion_delete(request, pk):
    doc = _get_or_404(promociones_col, {'promo_id': pk}, request, 'promocion_list')
    if not doc:
        return redirect('promocion_list')

    if request.method == 'POST':
        desc = doc.get('descripcion')
        promociones_col.delete_one({'promo_id': pk})
        messages.success(request, f"Promoción '{desc}' eliminada.")
        return redirect('promocion_list')

    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     doc.get('descripcion'),
        'tipo':       'promoción',
        'cancel_url': 'promocion_list',
    })


# ══════════════════════════════════════════
#  SUSCRIPCIONES
# ══════════════════════════════════════════

ESTADOS_SUSCRIPCION = ['Activa', 'Cancelada', 'Expirada']


@login_required
def suscripcion_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    if query:
        filtro = {'$or': [
            {'estado':                       {'$regex': query, '$options': 'i'}},
            {'tipoSuscripcion.nombrePlan':   {'$regex': query, '$options': 'i'}},
        ]}

    docs = list(suscripciones_col.find(filtro))
    # Lookup nombres de usuario
    user_ids = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
    user_names = _lookup_usuarios(user_ids)

    for d in docs:
        prepare_doc(d)
        uid = d.get('idUsuario')
        d['usuario_nombre'] = user_names.get(uid, '—')

    suscripciones = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/suscripcion/suscripcion_list.html', {
        'suscripciones': suscripciones,
        'query': query,
    })


@login_required
def suscripcion_add(request):
    planes      = _planes_dropdown()
    promociones = _promociones_dropdown(solo_activas=True)
    usuarios    = _usuarios_dropdown()

    if request.method == 'POST':
        try:
            fechainicio = request.POST.get('fechainicio')
            fechafin    = request.POST.get('fechafin')
            estado      = request.POST.get('estado')
            idusuario   = request.POST.get('usuario') or None
            idtipo      = request.POST.get('tiposuscripcion')
            idpromo     = request.POST.get('promocion') or None

            if not all([fechainicio, fechafin, estado, idtipo]):
                messages.error(request, 'Faltan campos obligatorios.')
                return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
                    'action': 'Nueva', 'planes': planes,
                    'promociones': promociones, 'usuarios': usuarios,
                    'estados': ESTADOS_SUSCRIPCION,
                })

            # Embeber tipoSuscripcion
            plan_doc = tipo_suscripciones_col.find_one({'tipo_id': int(idtipo)})
            tipo_embed = {
                '_id':        int(idtipo),
                'nombrePlan': plan_doc['nombrePlan'] if plan_doc else '',
                'precio':     plan_doc['precio'] if plan_doc else 0,
            }

            # Embeber promocion
            promo_embed = {'_id': None, 'descripcion': None, 'porcentajeDesc': None}
            if idpromo:
                promo_doc = promociones_col.find_one({'promo_id': int(idpromo)})
                if promo_doc:
                    promo_embed = {
                        '_id':             int(idpromo),
                        'descripcion':     promo_doc.get('descripcion'),
                        'porcentajeDesc':  promo_doc.get('porcentajeDesc'),
                    }

            fi = f"{fechainicio}T00:00:00" if fechainicio and 'T' not in fechainicio else fechainicio
            ff = f"{fechafin}T00:00:00" if fechafin and 'T' not in fechafin else fechafin

            suscripciones_col.insert_one({
                'fechaInicio':      fi,
                'fechaFin':         ff,
                'estado':           estado,
                'idUsuario':        int(idusuario) if idusuario else None,
                'tipoSuscripcion':  tipo_embed,
                'promocion':        promo_embed,
            })
            messages.success(request, 'Suscripción registrada correctamente.')
            return redirect('suscripcion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
        'action':      'Nueva',
        'planes':      planes,
        'promociones': promociones,
        'usuarios':    usuarios,
        'estados':     ESTADOS_SUSCRIPCION,
    })


@login_required
def suscripcion_edit(request, pk):
    doc = _get_or_404(suscripciones_col, {'_id': ObjectId(pk)}, request, 'suscripcion_list')
    if not doc:
        return redirect('suscripcion_list')

    planes      = _planes_dropdown()
    promociones = _promociones_dropdown(solo_activas=True)
    usuarios    = _usuarios_dropdown()

    if request.method == 'POST':
        try:
            fechainicio = request.POST.get('fechainicio')
            fechafin    = request.POST.get('fechafin')
            estado      = request.POST.get('estado')
            idusuario   = request.POST.get('usuario') or None
            idtipo      = request.POST.get('tiposuscripcion')
            idpromo     = request.POST.get('promocion') or None

            plan_doc = tipo_suscripciones_col.find_one({'tipo_id': int(idtipo)})
            tipo_embed = {
                '_id':        int(idtipo),
                'nombrePlan': plan_doc['nombrePlan'] if plan_doc else '',
                'precio':     plan_doc['precio'] if plan_doc else 0,
            }

            promo_embed = {'_id': None, 'descripcion': None, 'porcentajeDesc': None}
            if idpromo:
                promo_doc = promociones_col.find_one({'promo_id': int(idpromo)})
                if promo_doc:
                    promo_embed = {
                        '_id':             int(idpromo),
                        'descripcion':     promo_doc.get('descripcion'),
                        'porcentajeDesc':  promo_doc.get('porcentajeDesc'),
                    }

            fi = f"{fechainicio}T00:00:00" if fechainicio and 'T' not in fechainicio else fechainicio
            ff = f"{fechafin}T00:00:00" if fechafin and 'T' not in fechafin else fechafin

            suscripciones_col.update_one({'_id': ObjectId(pk)}, {'$set': {
                'fechaInicio':      fi,
                'fechaFin':         ff,
                'estado':           estado,
                'idUsuario':        int(idusuario) if idusuario else None,
                'tipoSuscripcion':  tipo_embed,
                'promocion':        promo_embed,
            }})
            messages.success(request, 'Suscripción actualizada.')
            return redirect('suscripcion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            doc = suscripciones_col.find_one({'_id': ObjectId(pk)})

    prepare_doc(doc)
    # Campos auxiliares para los selects del formulario
    doc['tiposuscripcion_id'] = doc.get('tipoSuscripcion', {}).get('_id')
    promo = doc.get('promocion', {})
    doc['promocion_id'] = promo.get('_id') if promo else None
    doc['usuario_id'] = doc.get('idUsuario')

    return render(request, 'Suscripciones/suscripcion/suscripcion_form.html', {
        'action':       'Editar',
        'suscripcion':  MongoDoc(doc),
        'planes':       planes,
        'promociones':  promociones,
        'usuarios':     usuarios,
        'estados':      ESTADOS_SUSCRIPCION,
    })


@login_required
def suscripcion_delete(request, pk):
    doc = _get_or_404(suscripciones_col, {'_id': ObjectId(pk)}, request, 'suscripcion_list')
    if not doc:
        return redirect('suscripcion_list')

    if request.method == 'POST':
        suscripciones_col.delete_one({'_id': ObjectId(pk)})
        messages.success(request, 'Suscripción eliminada.')
        return redirect('suscripcion_list')

    plan_name = doc.get('tipoSuscripcion', {}).get('nombrePlan', '')
    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     f"Suscripción {plan_name} — {doc.get('estado', '')}",
        'tipo':       'suscripción',
        'cancel_url': 'suscripcion_list',
    })


# ══════════════════════════════════════════
#  NOTIFICACIONES
# ══════════════════════════════════════════

TIPOS_NOTIFICACION = ['Aviso de Seguridad', 'Nuevo Lanzamiento', 'Pago Exitoso']


@login_required
def notificacion_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    if query:
        filtro = {'$or': [
            {'tipoNotif': {'$regex': query, '$options': 'i'}},
            {'mensaje':   {'$regex': query, '$options': 'i'}},
        ]}

    docs = list(notificaciones_col.find(filtro))

    # Lookup usuarios y promociones
    user_ids  = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
    promo_ids = {d.get('idPromocion') for d in docs if d.get('idPromocion')}
    user_names = _lookup_usuarios(user_ids)
    promo_descs = {}
    if promo_ids:
        for p in promociones_col.find({'promo_id': {'$in': list(promo_ids)}}):
            promo_descs[p['promo_id']] = p.get('descripcion', '')

    for d in docs:
        prepare_doc(d)
        d['usuario_nombre'] = user_names.get(d.get('idUsuario'), '—')
        d['promocion_desc'] = promo_descs.get(d.get('idPromocion'), '—')

    notificaciones = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/notificacion/notificacion_list.html', {
        'notificaciones': notificaciones,
        'query': query,
    })


@login_required
def notificacion_add(request):
    usuarios    = _usuarios_dropdown()
    promociones = _promociones_dropdown()

    if request.method == 'POST':
        try:
            tiponotif = request.POST.get('tiponotif')
            mensaje   = request.POST.get('mensaje')
            idusuario = request.POST.get('usuario')
            idpromo   = request.POST.get('promocion')

            if not all([tiponotif, mensaje, idusuario, idpromo]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/notificacion/notificacion_form.html', {
                    'action': 'Nueva', 'usuarios': usuarios,
                    'promociones': promociones, 'tipos': TIPOS_NOTIFICACION,
                })

            notificaciones_col.insert_one({
                'tipoNotif':   tiponotif,
                'mensaje':     mensaje,
                'fechaEnvio':  datetime.now().isoformat(),
                'idUsuario':   int(idusuario),
                'idPromocion': int(idpromo),
            })
            messages.success(request, 'Notificación creada correctamente.')
            return redirect('notificacion_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/notificacion/notificacion_form.html', {
        'action':      'Nueva',
        'usuarios':    usuarios,
        'promociones': promociones,
        'tipos':       TIPOS_NOTIFICACION,
    })


@login_required
def notificacion_delete(request, pk):
    doc = _get_or_404(notificaciones_col, {'_id': ObjectId(pk)}, request, 'notificacion_list')
    if not doc:
        return redirect('notificacion_list')

    if request.method == 'POST':
        notificaciones_col.delete_one({'_id': ObjectId(pk)})
        messages.success(request, 'Notificación eliminada.')
        return redirect('notificacion_list')

    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     f"{doc.get('tipoNotif', '')} — {doc.get('mensaje', '')[:50]}",
        'tipo':       'notificación',
        'cancel_url': 'notificacion_list',
    })


# ══════════════════════════════════════════
#  PLAYLISTS
# ══════════════════════════════════════════

@login_required
def playlist_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    if query:
        filtro = {'$or': [
            {'nombre': {'$regex': query, '$options': 'i'}},
        ]}

    docs = list(playlists_col.find(filtro))
    user_ids = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
    user_names = _lookup_usuarios(user_ids)

    for d in docs:
        prepare_doc(d)
        d['usuario_nombre'] = user_names.get(d.get('idUsuario'), '—')

    playlists = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/playlist/playlist_list.html', {
        'playlists': playlists,
        'query': query,
    })


@login_required
def playlist_add(request):
    usuarios = _usuarios_dropdown()

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            if not nombre:
                messages.error(request, 'El nombre es obligatorio.')
                return render(request, 'Suscripciones/playlist/playlist_form.html',
                              {'action': 'Nueva', 'usuarios': usuarios})

            idusuario = request.POST.get('usuario') or None
            playlists_col.insert_one({
                'nombre':        nombre,
                'descripcion':   request.POST.get('descripcion') or '',
                'esPrivada':     request.POST.get('esprivada') == 'on',
                'esPublicada':   request.POST.get('espublicada') == 'on',
                'imagenPortada': request.POST.get('imagenportada') or '',
                'fechaCreacion': datetime.now().isoformat(),
                'idUsuario':     int(idusuario) if idusuario else None,
                'canciones':     [],
            })
            messages.success(request, f"Playlist '{nombre}' creada.")
            return redirect('playlist_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/playlist/playlist_form.html', {
        'action':   'Nueva',
        'usuarios': usuarios,
    })


@login_required
def playlist_edit(request, pk):
    doc = _get_or_404(playlists_col, {'_id': ObjectId(pk)}, request, 'playlist_list')
    if not doc:
        return redirect('playlist_list')

    usuarios = _usuarios_dropdown()

    if request.method == 'POST':
        try:
            idusuario = request.POST.get('usuario') or None
            playlists_col.update_one({'_id': ObjectId(pk)}, {'$set': {
                'nombre':        request.POST.get('nombre'),
                'descripcion':   request.POST.get('descripcion') or '',
                'esPrivada':     request.POST.get('esprivada') == 'on',
                'esPublicada':   request.POST.get('espublicada') == 'on',
                'imagenPortada': request.POST.get('imagenportada') or '',
                'idUsuario':     int(idusuario) if idusuario else None,
            }})
            messages.success(request, f"Playlist actualizada.")
            return redirect('playlist_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            doc = playlists_col.find_one({'_id': ObjectId(pk)})

    prepare_doc(doc)
    doc['usuario_id'] = doc.get('idUsuario')
    return render(request, 'Suscripciones/playlist/playlist_form.html', {
        'action':   'Editar',
        'playlist': MongoDoc(doc),
        'usuarios': usuarios,
    })


@login_required
def playlist_delete(request, pk):
    doc = _get_or_404(playlists_col, {'_id': ObjectId(pk)}, request, 'playlist_list')
    if not doc:
        return redirect('playlist_list')

    if request.method == 'POST':
        nombre = doc.get('nombre')
        playlists_col.delete_one({'_id': ObjectId(pk)})
        messages.success(request, f"Playlist '{nombre}' eliminada.")
        return redirect('playlist_list')

    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     doc.get('nombre'),
        'tipo':       'playlist',
        'cancel_url': 'playlist_list',
    })


# ══════════════════════════════════════════
#  PLAYLIST — CANCIONES (embebidas)
# ══════════════════════════════════════════

@login_required
def playlist_canciones(request, pk):
    doc = _get_or_404(playlists_col, {'_id': ObjectId(pk)}, request, 'playlist_list')
    if not doc:
        return redirect('playlist_list')

    prepare_doc(doc)
    canciones_data = doc.get('canciones') or []

    # Lookup nombres de canciones
    cancion_ids = [c.get('idCancion') for c in canciones_data if c.get('idCancion')]
    canciones_lookup = {}
    if cancion_ids:
        for c in canciones_col.find({'cancion_id': {'$in': cancion_ids}}):
            canciones_lookup[c['cancion_id']] = c.get('tituloCancion', f"Canción #{c['cancion_id']}")

    entradas = []
    for c in canciones_data:
        c['cancion_nombre'] = canciones_lookup.get(c.get('idCancion'), f"Canción #{c.get('idCancion', '?')}")
        if isinstance(c.get('fechaAdicion'), str):
            c['fechaAdicion'] = parse_date(c['fechaAdicion'])
        entradas.append(MongoDoc(c))

    # Ordenar por el campo 'orden'
    entradas.sort(key=lambda e: e.orden or 0)

    playlist = MongoDoc(doc)
    return render(request, 'Suscripciones/playlist/playlist_canciones.html', {
        'playlist': playlist,
        'entradas': entradas,
    })


@login_required
def playlist_cancion_agregar(request, pk):
    doc = _get_or_404(playlists_col, {'_id': ObjectId(pk)}, request, 'playlist_list')
    if not doc:
        return redirect('playlist_list')

    canciones = _canciones_dropdown()

    if request.method == 'POST':
        try:
            cancion_id = int(request.POST.get('cancion'))
            orden      = int(request.POST.get('orden') or 0)

            # Verificar duplicados
            existing = doc.get('canciones') or []
            if any(c.get('idCancion') == cancion_id for c in existing):
                messages.error(request, 'Esa canción ya está en la playlist.')
                prepare_doc(doc)
                return render(request, 'Suscripciones/playlist/playlist_cancion_form.html', {
                    'playlist': MongoDoc(doc), 'canciones': canciones,
                })

            playlists_col.update_one({'_id': ObjectId(pk)}, {'$push': {
                'canciones': {
                    'idCancion':    cancion_id,
                    'fechaAdicion': datetime.now().isoformat(),
                    'orden':        orden,
                }
            }})
            messages.success(request, 'Canción agregada a la playlist.')
            return redirect('playlist_canciones', pk=pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    prepare_doc(doc)
    return render(request, 'Suscripciones/playlist/playlist_cancion_form.html', {
        'playlist':  MongoDoc(doc),
        'canciones': canciones,
    })


@login_required
def playlist_cancion_quitar(request, pk):
    if request.method == 'POST':
        cancion_id = int(request.POST.get('cancion_id', 0))
        result = playlists_col.update_one(
            {'_id': ObjectId(pk)},
            {'$pull': {'canciones': {'idCancion': cancion_id}}}
        )
        if result.modified_count:
            messages.success(request, 'Canción quitada de la playlist.')
        else:
            messages.error(request, 'No se encontró esa canción en la playlist.')

    return redirect('playlist_canciones', pk=pk)


# ══════════════════════════════════════════
#  ESTADÍSTICAS DIARIAS
# ══════════════════════════════════════════

@login_required
def estadistica_list(request):
    query = request.GET.get('q', '')
    filtro = {}
    # La búsqueda por nombre de canción requiere lookup
    docs = list(estadisticas_col.find().sort('fechaReporte', -1))

    # Lookup canciones
    cancion_ids = list({d.get('idCancion') for d in docs if d.get('idCancion')})
    canciones_lookup = {}
    if cancion_ids:
        for c in canciones_col.find({'cancion_id': {'$in': cancion_ids}}):
            canciones_lookup[c['cancion_id']] = c

    filtered = []
    for d in docs:
        cid = d.get('idCancion')
        cancion = canciones_lookup.get(cid, {})
        d['cancion_nombre']  = cancion.get('tituloCancion', f'Canción #{cid}')
        d['cancion_portada'] = cancion.get('urlPortada', '')
        d['cancion_album']   = cancion.get('album_id', '')
        prepare_doc(d)

        # Filtro de búsqueda (se hace en Python porque depende del lookup)
        if query:
            search = query.lower()
            if (search not in d['cancion_nombre'].lower()
                    and search not in str(d.get('fechaReporte', ''))):
                continue
        filtered.append(d)

    estadisticas = [MongoDoc(d) for d in filtered]
    return render(request, 'Suscripciones/estadistica/estadistica_list.html', {
        'estadisticas': estadisticas,
        'query': query,
    })


@login_required
def estadistica_add(request):
    canciones = _canciones_dropdown()

    if request.method == 'POST':
        try:
            totalrepros  = request.POST.get('totalrepros')
            fechareporte = request.POST.get('fechareporte')
            cancion_id   = request.POST.get('cancion')

            if not all([totalrepros, fechareporte, cancion_id]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return render(request, 'Suscripciones/estadistica/estadistica_form.html',
                              {'action': 'Nueva', 'canciones': canciones})

            estadisticas_col.insert_one({
                'totalRepros':  int(totalrepros),
                'fechaReporte': fechareporte,
                'idCancion':    int(cancion_id),
            })
            messages.success(request, 'Estadística registrada.')
            return redirect('estadistica_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Suscripciones/estadistica/estadistica_form.html', {
        'action':    'Nueva',
        'canciones': canciones,
    })


@login_required
def estadistica_delete(request, pk):
    doc = _get_or_404(estadisticas_col, {'_id': ObjectId(pk)}, request, 'estadistica_list')
    if not doc:
        return redirect('estadistica_list')

    if request.method == 'POST':
        estadisticas_col.delete_one({'_id': ObjectId(pk)})
        messages.success(request, 'Estadística eliminada.')
        return redirect('estadistica_list')

    return render(request, 'Suscripciones/confirm_delete.html', {
        'objeto':     f"Estadística del {doc.get('fechaReporte', '')}",
        'tipo':       'estadística',
        'cancel_url': 'estadistica_list',
    })


# ══════════════════════════════════════════
#  REPORTES
# ══════════════════════════════════════════

@login_required
def reporte_vencimientos(request):
    """Informe B: Suscripciones que vencen en los próximos 5 días."""
    docs = list(suscripciones_col.find({
        'estado': 'Expirada',
        'tipoSuscripcion.nombrePlan': {
            '$in': [
                'Premium Individual',
                'Premium Duo',
                'Premium Familiar',
                'Premium Estudiante'
            ]
        }
    }).sort('fechaFin', 1))

    user_ids = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
    user_names = _lookup_usuarios(user_ids)

    for d in docs:
        prepare_doc(d)
        resolved_name = user_names.get(d.get('idUsuario'), '—')
        d['usuario_nombre'] = resolved_name
        d['usuario_nombre_nombre'] = resolved_name

    proximas = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/reportes/reporte_vencimientos.html', {
        'proximas': proximas,
        'hoy':      datetime.now(),
        'limite':   datetime.now() + timedelta(days=5),
    })


@login_required
def reporte_promociones_vencidas(request):
    """Informe D: Promociones expiradas que aún figuran como activas."""
    docs = list(promociones_col.find({
        'estadoActivo': True,
        'porcentajeDesc': {'$gt': 20}
    }).sort('fechaExpira', 1))

    for d in docs:
        prepare_doc(d)

    vencidas = [MongoDoc(d) for d in docs]
    return render(request, 'Suscripciones/reportes/reporte_promociones_vencidas.html', {
        'vencidas': vencidas,
        'ahora':    datetime.now(),
    })


# Helper to get base context for reports
def _contexto_base(request):
    return {
        'fecha_generacion': datetime.now(),
        'usuario_generador': (f"{request.user.get_full_name() or request.user.username} · {request.user.email}").strip(' ·'),
        'version': 'v2.1.0',
    }

# ── EXPORTACIÓN SUSCRIPCIONES EXPIRADAS (VENCIMIENTOS) ──
@login_required
def exportar_vencimientos_pdf(request):
    try:
        docs = list(suscripciones_col.find({
            'estado': 'Expirada',
            'tipoSuscripcion.nombrePlan': {
                '$in': [
                    'Premium Individual',
                    'Premium Duo',
                    'Premium Familiar',
                    'Premium Estudiante'
                ]
            }
        }).sort('fechaFin', 1))
        user_ids = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
        user_names = _lookup_usuarios(user_ids)
        for d in docs:
            prepare_doc(d)
            resolved_name = user_names.get(d.get('idUsuario'), '—')
            d['usuario_nombre'] = resolved_name
            d['usuario_nombre_nombre'] = resolved_name
        proximas = [MongoDoc(d) for d in docs]
        
        context = {
            **_contexto_base(request),
            'proximas': proximas,
            'hoy':      datetime.now(),
            'limite':   datetime.now() + timedelta(days=5),
        }
        html_string = render_to_string('Suscripciones/reportes/pdf_vencimientos.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Suscripciones_Expiradas.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_vencimientos_correo(request):
    try:
        docs = list(suscripciones_col.find({
            'estado': 'Expirada',
            'tipoSuscripcion.nombrePlan': {
                '$in': [
                    'Premium Individual',
                    'Premium Duo',
                    'Premium Familiar',
                    'Premium Estudiante'
                ]
            }
        }).sort('fechaFin', 1))
        user_ids = {d.get('idUsuario') for d in docs if d.get('idUsuario')}
        user_names = _lookup_usuarios(user_ids)
        for d in docs:
            prepare_doc(d)
            resolved_name = user_names.get(d.get('idUsuario'), '—')
            d['usuario_nombre'] = resolved_name
            d['usuario_nombre_nombre'] = resolved_name
        proximas = [MongoDoc(d) for d in docs]

        context = {
            **_contexto_base(request),
            'proximas': proximas,
            'hoy':      datetime.now(),
            'limite':   datetime.now() + timedelta(days=5),
        }
        html_string = render_to_string('Suscripciones/reportes/pdf_vencimientos.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Informe de Suscripciones Expiradas',
            body='Adjuntamos el informe detallado de suscripciones Premium inactivas/expiradas.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Suscripciones_Expiradas.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── EXPORTACIÓN PROMOCIONES ALTO DESCUENTO ──
@login_required
def exportar_promociones_vencidas_pdf(request):
    try:
        docs = list(promociones_col.find({
            'estadoActivo': True,
            'porcentajeDesc': {'$gt': 20}
        }).sort('fechaExpira', 1))
        for d in docs:
            prepare_doc(d)
        vencidas = [MongoDoc(d) for d in docs]
        
        context = {
            **_contexto_base(request),
            'vencidas': vencidas,
            'ahora':    datetime.now(),
        }
        html_string = render_to_string('Suscripciones/reportes/pdf_promociones_vencidas.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Promociones_Alto_Descuento.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_promociones_vencidas_correo(request):
    try:
        docs = list(promociones_col.find({
            'estadoActivo': True,
            'porcentajeDesc': {'$gt': 20}
        }).sort('fechaExpira', 1))
        for d in docs:
            prepare_doc(d)
        vencidas = [MongoDoc(d) for d in docs]

        context = {
            **_contexto_base(request),
            'vencidas': vencidas,
            'ahora':    datetime.now(),
        }
        html_string = render_to_string('Suscripciones/reportes/pdf_promociones_vencidas.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Promociones Activas con Alto Descuento',
            body='Adjuntamos el informe ejecutivo de las promociones con descuento superior al 20%.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Promociones_Alto_Descuento.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: USUARIOS PREMIUM ACTIVOS ──
def obtener_usuarios_premium_activos():
    users = list(db["usuarios"].find({
        "estadoPlan": "Premium",
        "estadoActivo": "Activo"
    }))
    for u in users:
        u["id"] = str(u.get("_id"))
        u["nombre_completo"] = f"{u.get('nombre', '')} {u.get('apellido', '')}"
        if isinstance(u.get("fechaRegistro"), str):
            u["fechaRegistro"] = parse_date(u["fechaRegistro"])
    return users

@login_required
def reporte_usuarios_premium(request):
    try:
        usuarios = obtener_usuarios_premium_activos()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        usuarios = []
    return render(request, 'Suscripciones/reportes/reporte_usuarios_premium.html', {'usuarios': usuarios})

@login_required
def exportar_usuarios_premium_pdf(request):
    try:
        usuarios = obtener_usuarios_premium_activos()
        context = {**_contexto_base(request), 'usuarios': usuarios}
        html_string = render_to_string('Suscripciones/reportes/pdf_usuarios_premium.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Usuarios_Premium_Activos.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_usuarios_premium_correo(request):
    try:
        usuarios = obtener_usuarios_premium_activos()
        context = {**_contexto_base(request), 'usuarios': usuarios}
        html_string = render_to_string('Suscripciones/reportes/pdf_usuarios_premium.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Usuarios con Plan Premium Activo',
            body='Adjuntamos el informe detallado de usuarios con suscripción Premium activa.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Usuarios_Premium_Activos.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: CANDIDATOS A PLAN PREMIUM ──
def obtener_candidatos_premium():
    users = list(db["usuarios"].find({
        "estadoPlan": "Free",
        "estadoActivo": "Activo"
    }).sort("fechaRegistro", -1))
    for u in users:
        u["id"] = str(u.get("_id"))
        u["nombre_completo"] = f"{u.get('nombre', '')} {u.get('apellido', '')}"
        if isinstance(u.get("fechaRegistro"), str):
            u["fechaRegistro"] = parse_date(u["fechaRegistro"])
    return users

@login_required
def reporte_usuarios_free(request):
    try:
        usuarios = obtener_candidatos_premium()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        usuarios = []
    return render(request, 'Suscripciones/reportes/reporte_usuarios_free.html', {'usuarios': usuarios})

@login_required
def exportar_usuarios_free_pdf(request):
    try:
        usuarios = obtener_candidatos_premium()
        context = {**_contexto_base(request), 'usuarios': usuarios}
        html_string = render_to_string('Suscripciones/reportes/pdf_usuarios_free.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Candidatos_Plan_Premium.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_usuarios_free_correo(request):
    try:
        usuarios = obtener_candidatos_premium()
        context = {**_contexto_base(request), 'usuarios': usuarios}
        html_string = render_to_string('Suscripciones/reportes/pdf_usuarios_free.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Candidatos a Conversión Premium (Plan Free)',
            body='Adjuntamos el informe de usuarios activos en plan Free para campañas de conversión.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Candidatos_Plan_Premium.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: INTENTOS DE ACCESO FALLIDOS ──
def obtener_accesos_fallidos():
    docs = list(db["auditoriaAcceso"].find({"resultado": "Fallido"}).sort("fechaHora", -1))
    user_ids = {d.get("idUsuario") for d in docs if d.get("idUsuario")}
    users = db["usuarios"].find({"id": {"$in": list(user_ids)}}, {"id": 1, "nombre": 1, "apellido": 1})
    user_names = {u["id"]: f"{u.get('nombre', '')} {u.get('apellido', '')}" for u in users}
    for d in docs:
        d["id"] = str(d.get("_id"))
        d["usuario_nombre"] = user_names.get(d.get("idUsuario"), f"Usuario {d.get('idUsuario', '—')}")
        if isinstance(d.get("fechaHora"), str):
            d["fechaHora"] = parse_date(d["fechaHora"])
    return docs

@login_required
def reporte_accesos_fallidos(request):
    try:
        accesos = obtener_accesos_fallidos()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        accesos = []
    return render(request, 'Suscripciones/reportes/reporte_accesos_fallidos.html', {'accesos': accesos})

@login_required
def exportar_accesos_fallidos_pdf(request):
    try:
        accesos = obtener_accesos_fallidos()
        context = {**_contexto_base(request), 'accesos': accesos}
        html_string = render_to_string('Suscripciones/reportes/pdf_accesos_fallidos.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Accesos_Fallidos_Audit.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_accesos_fallidos_correo(request):
    try:
        accesos = obtener_accesos_fallidos()
        context = {**_contexto_base(request), 'accesos': accesos}
        html_string = render_to_string('Suscripciones/reportes/pdf_accesos_fallidos.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Auditoría de Intentos de Acceso Fallidos',
            body='Adjuntamos la auditoría de seguridad detallando los intentos fallidos de inicio de sesión.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Accesos_Fallidos_Audit.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── REPORTE: ACCIONES DE ADMINISTRACIÓN ──
def obtener_acciones_admin():
    docs = list(db["auditoriaAcceso"].find({
        "accion": {
            "$in": [
                "CAMBIO_CONTRASENA",
                "CAMBIO_PLAN",
                "ADMIN_ACCION"
            ]
        }
    }).sort("fechaHora", -1))
    user_ids = {d.get("idUsuario") for d in docs if d.get("idUsuario")}
    users = db["usuarios"].find({"id": {"$in": list(user_ids)}}, {"id": 1, "nombre": 1, "apellido": 1})
    user_names = {u["id"]: f"{u.get('nombre', '')} {u.get('apellido', '')}" for u in users}
    for d in docs:
        d["id"] = str(d.get("_id"))
        d["usuario_nombre"] = user_names.get(d.get("idUsuario"), f"Usuario {d.get('idUsuario', '—')}")
        if isinstance(d.get("fechaHora"), str):
            d["fechaHora"] = parse_date(d["fechaHora"])
    return docs

@login_required
def reporte_acciones_admin(request):
    try:
        acciones = obtener_acciones_admin()
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        acciones = []
    return render(request, 'Suscripciones/reportes/reporte_acciones_admin.html', {'acciones': acciones})

@login_required
def exportar_acciones_admin_pdf(request):
    try:
        acciones = obtener_acciones_admin()
        context = {**_contexto_base(request), 'acciones': acciones}
        html_string = render_to_string('Suscripciones/reportes/pdf_acciones_admin.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Acciones_Administracion_Audit.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@login_required
def enviar_acciones_admin_correo(request):
    try:
        acciones = obtener_acciones_admin()
        context = {**_contexto_base(request), 'acciones': acciones}
        html_string = render_to_string('Suscripciones/reportes/pdf_acciones_admin.html', context, request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        destinatario = request.user.email or 'admin@cenit.com'
        email = EmailMessage(
            subject='CÉNIT — Auditoría de Acciones de Administración',
            body='Adjuntamos la auditoría detallada de acciones administrativas críticas en la plataforma.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach('Acciones_Administracion_Audit.pdf', pdf_file, 'application/pdf')
        email.send()
        return JsonResponse({'status': 'success', 'message': f'Reporte enviado a {destinatario}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)