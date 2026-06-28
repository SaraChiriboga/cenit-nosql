import secrets
import datetime
from bson import ObjectId
from cenit.mongo_client import db as mongo_db

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import AuditoriaAcceso, Rol, Seguimiento, CancionFavorita


# ══════════════════════════════════════════
#  AUDITORÍA DE ACCESO
# ══════════════════════════════════════════

@login_required
def auditoria_list(request):
    registros = AuditoriaAcceso.objects.select_related('rol').all()
    query = request.GET.get('q', '')
    if query:
        registros = registros.filter(
            Q(accion__icontains=query) |
            Q(iporigen__icontains=query) |
            Q(rol__nombrerol__icontains=query)
        )
    return render(request, 'Usuarios/auditoria/auditoria_list.html', {
        'registros': registros,
        'query': query,
    })


@login_required
def auditoria_add(request):
    roles = Rol.objects.all()
    if request.method == 'POST':
        try:
            accion   = request.POST.get('accion')
            iporigen = request.POST.get('iporigen')
            rol_id   = request.POST.get('rol')

            if not rol_id:
                messages.error(request, 'El rol es obligatorio.')
                return render(request, 'Usuarios/auditoria/auditoria_form.html',
                              {'action': 'Nuevo', 'roles': roles})

            AuditoriaAcceso.objects.create(
                accion=accion or None,
                iporigen=iporigen or None,
                rol_id=rol_id,
            )
            messages.success(request, 'Registro de auditoría creado.')
            return redirect('auditoria_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Usuarios/auditoria/auditoria_form.html', {
        'action': 'Nuevo',
        'roles': roles,
    })


@login_required
def auditoria_delete(request, pk):
    registro = get_object_or_404(AuditoriaAcceso, pk=pk)
    if request.method == 'POST':
        registro.delete()
        messages.success(request, 'Registro de auditoría eliminado.')
        return redirect('auditoria_list')
    return render(request, 'Usuarios/confirm_delete.html', {
        'objeto': registro,
        'tipo': 'registro de auditoría',
        'cancel_url': 'auditoria_list',
    })


# ══════════════════════════════════════════
#  SEGUIMIENTOS
# ══════════════════════════════════════════

@login_required
def seguimiento_list(request):
    seguimientos = Seguimiento.objects.select_related('usuario', 'artista').all()
    query = request.GET.get('q', '')
    if query:
        seguimientos = seguimientos.filter(
            Q(usuario__nombre__icontains=query) |
            Q(artista__nombre__icontains=query)
        )
    return render(request, 'Usuarios/seguimiento/seguimiento_list.html', {
        'seguimientos': seguimientos,
        'query': query,
    })


@login_required
def seguimiento_add(request):
    from .models import Usuario
    from catalogo.models import Artista
    usuarios = Usuario.objects.all()
    artistas = Artista.objects.all()

    if request.method == 'POST':
        try:
            usuario_id = request.POST.get('usuario')
            artista_id = request.POST.get('artista')

            if not all([usuario_id, artista_id]):
                messages.error(request, 'Usuario y artista son obligatorios.')
                return render(request, 'Usuarios/seguimiento/seguimiento_form.html', {
                    'action': 'Nuevo', 'usuarios': usuarios, 'artistas': artistas,
                })

            if Seguimiento.objects.filter(usuario_id=usuario_id, artista_id=artista_id).exists():
                messages.error(request, 'Ese usuario ya sigue a ese artista.')
                return render(request, 'Usuarios/seguimiento/seguimiento_form.html', {
                    'action': 'Nuevo', 'usuarios': usuarios, 'artistas': artistas,
                })

            Seguimiento.objects.create(
                usuario_id=usuario_id,
                artista_id=artista_id,
            )
            messages.success(request, 'Seguimiento registrado.')
            return redirect('seguimiento_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Usuarios/seguimiento/seguimiento_form.html', {
        'action': 'Nuevo',
        'usuarios': usuarios,
        'artistas': artistas,
    })


@login_required
def seguimiento_delete(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        artista_id = request.POST.get('artista_id')
        entrada = Seguimiento.objects.filter(
            usuario_id=usuario_id, artista_id=artista_id
        ).first()
        if entrada:
            entrada.delete()
            messages.success(request, 'Seguimiento eliminado.')
        else:
            messages.error(request, 'No se encontró ese seguimiento.')
        return redirect('seguimiento_list')

    return redirect('seguimiento_list')


# ══════════════════════════════════════════
#  CANCIONES FAVORITAS
# ══════════════════════════════════════════

@login_required
def favorita_list(request):
    favoritas = CancionFavorita.objects.select_related('usuario', 'cancion','cancion__album').all()
    query = request.GET.get('q', '')
    if query:
        favoritas = favoritas.filter(
            Q(usuario__nombre__icontains=query) |
            Q(cancion__titulocancion__icontains=query)
        )
    return render(request, 'Usuarios/favorita/favorita_list.html', {
        'favoritas': favoritas,
        'query': query,
    })


@login_required
def favorita_add(request):
    from .models import Usuario
    from catalogo.models import Cancion
    usuarios = Usuario.objects.all()
    canciones = Cancion.objects.all()

    if request.method == 'POST':
        try:
            usuario_id = request.POST.get('usuario')
            cancion_id = request.POST.get('cancion')

            if not all([usuario_id, cancion_id]):
                messages.error(request, 'Usuario y canción son obligatorios.')
                return render(request, 'Usuarios/favorita/favorita_form.html', {
                    'action': 'Nueva', 'usuarios': usuarios, 'canciones': canciones,
                })

            if CancionFavorita.objects.filter(usuario_id=usuario_id, cancion_id=cancion_id).exists():
                messages.error(request, 'Esa canción ya está en favoritas de ese usuario.')
                return render(request, 'Usuarios/favorita/favorita_form.html', {
                    'action': 'Nueva', 'usuarios': usuarios, 'canciones': canciones,
                })

            CancionFavorita.objects.create(
                usuario_id=usuario_id,
                cancion_id=cancion_id,
            )
            messages.success(request, 'Canción agregada a favoritas.')
            return redirect('favorita_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'Usuarios/favorita/favorita_form.html', {
        'action': 'Nueva',
        'usuarios': usuarios,
        'canciones': canciones,
    })


@login_required
def favorita_delete(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        cancion_id = request.POST.get('cancion_id')
        entrada = CancionFavorita.objects.filter(
            usuario_id=usuario_id, cancion_id=cancion_id
        ).first()
        if entrada:
            entrada.delete()
            messages.success(request, 'Canción quitada de favoritas.')
        else:
            messages.error(request, 'No se encontró esa entrada en favoritas.')
        return redirect('favorita_list')

    return redirect('favorita_list')

def _obtener_datos_sql(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# ══════════════════════════════════════════
#  DIRECTORIO GENERAL (users_overview)
# ══════════════════════════════════════════

# ══════════════════════════════════════════
#  DIRECTORIO GENERAL (users_overview)
# ══════════════════════════════════════════

@login_required
def users_overview(request):
    q = request.GET.get('q', '')
    rol_filter = request.GET.get('rol', '')
    usuarios = []
    error_db = None

    try:
        query = {}
        if q:
            query["$or"] = [
                {"nombre": {"$regex": q, "$options": "i"}},
                {"apellido": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}}
            ]
        if rol_filter:
            query["rol.nombreRol"] = rol_filter

        mongo_users = mongo_db["usuarios"].find(query).sort("_id", -1)
        
        for u in mongo_users:
            rol_data = u.get("rol", {})
            nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
            
            usuarios.append({
                'idUsuario': str(u.get("_id")),
                'nombre': u.get("nombre", ""),
                'apellido': u.get("apellido", ""),
                'email': u.get("email", ""),
                'estado': u.get("estadoCuenta", "Activo"),
                'rol_nombre': nombre_rol
            })

    except Exception as e:
        error_db = str(e)
        print(f"❌ ERROR MONGODB EN USERS_OVERVIEW: {error_db}")

    context = {
        'usuarios': usuarios,
        'error_db': error_db
    }
    return render(request, 'usuarios/usuarios/users_overview.html', context)


# ══════════════════════════════════════════
#  CREAR USUARIO (add_user)
# ══════════════════════════════════════════
@login_required
def add_user(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        rol_nombre = request.POST.get('rol_nombre')

        password_temporal = secrets.token_urlsafe(8)
        password_hash = make_password(password_temporal)

        try:
            if mongo_db["usuarios"].find_one({"email": email}):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Este correo ya está registrado en el sistema.'
                }, status=400)

            new_user = {
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "contrasena": password_hash,
                "estadoPlan": "Free",
                "fechaRegistro": datetime.datetime.now(),
                "estadoCuenta": "Activo",
                "debeCambiarPassword": True,
                "rol": {
                    "nombreRol": rol_nombre,
                    "descripcion": rol_nombre
                }
            }
            
            mongo_db["usuarios"].insert_one(new_user)
            return JsonResponse({'status': 'success', 'message': f'Usuario {nombre} creado con éxito. Clave temporal: {password_temporal}'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)

    return render(request, 'usuarios/usuarios/add_user.html')


# ══════════════════════════════════════════
#  LEER DETALLES (read_user)
# ══════════════════════════════════════════

@login_required
def read_user(request, idUsuario):
    u = None
    try:
        mongo_user = mongo_db["usuarios"].find_one({"_id": ObjectId(idUsuario)})
        if mongo_user:
            rol_data = mongo_user.get("rol", {})
            nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
            desc_rol = rol_data.get("descripcion", nombre_rol) if isinstance(rol_data, dict) else str(rol_data)
            
            u = {
                'idUsuario': str(mongo_user.get("_id")),
                'nombre': mongo_user.get("nombre", ""),
                'apellido': mongo_user.get("apellido", ""),
                'email': mongo_user.get("email", ""),
                'estado': mongo_user.get("estadoCuenta", "Activo"),
                'fechaRegistro': mongo_user.get("fechaRegistro", ""),
                'estadoPlan': mongo_user.get("estadoPlan", "Free"),
                'debeCambiarPassword': mongo_user.get("debeCambiarPassword", True),
                'rol_nombre': nombre_rol,
                'rol_descripcion': desc_rol
            }
        else:
            return redirect('users_overview')
    except Exception as e:
        print(f"❌ ERROR EN READ_USER: {str(e)}")
        return redirect('users_overview')

    return render(request, 'usuarios/usuarios/read_user.html', {'u': u})


# ══════════════════════════════════════════
#  EDITAR USUARIO (edit_user)
# ══════════════════════════════════════════

@login_required
def edit_user(request, idUsuario):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        rol_nombre = request.POST.get('rol_nombre')
        estado_cuenta = request.POST.get('estadoCuenta')

        try:
            # Check if email is used by another user
            existing = mongo_db["usuarios"].find_one({"email": email, "_id": {"$ne": ObjectId(idUsuario)}})
            if existing:
                return JsonResponse({'status': 'error', 'message': 'Este correo ya está en uso.'}, status=400)

            mongo_db["usuarios"].update_one(
                {"_id": ObjectId(idUsuario)},
                {"$set": {
                    "nombre": nombre,
                    "apellido": apellido,
                    "email": email,
                    "estadoCuenta": estado_cuenta,
                    "rol": {
                        "nombreRol": rol_nombre,
                        "descripcion": rol_nombre
                    }
                }}
            )
            return JsonResponse({'status': 'success', 'message': 'Usuario actualizado con éxito.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)

    try:
        mongo_user = mongo_db["usuarios"].find_one({"_id": ObjectId(idUsuario)})
        if not mongo_user:
            return redirect('users_overview')
            
        rol_data = mongo_user.get("rol", {})
        nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
        
        u = {
            'idUsuario': str(mongo_user.get("_id")),
            'nombre': mongo_user.get("nombre", ""),
            'apellido': mongo_user.get("apellido", ""),
            'email': mongo_user.get("email", ""),
            'estadoCuenta': mongo_user.get("estadoCuenta", "Activo"),
            'nombreRol': nombre_rol
        }
        return render(request, 'usuarios/usuarios/edit_user.html', {'u': u})
    except Exception as e:
        print(f"❌ ERROR EN EDIT_USER: {str(e)}")
        return redirect('users_overview')

# ══════════════════════════════════════════
#  ACTIVAR / SUSPENDER (toggle_user)
# ══════════════════════════════════════════

from django.views.decorators.http import require_POST

@login_required
@require_POST
def toggle_user(request, idUsuario):
    try:
        mongo_user = mongo_db["usuarios"].find_one({"_id": ObjectId(idUsuario)})
        if not mongo_user:
            return JsonResponse({'status': 'error', 'message': 'Usuario no encontrado.'}, status=404)
            
        estado_actual = mongo_user.get("estadoCuenta", "Activo")
        nuevo_estado = 'Suspendido' if estado_actual == 'Activo' else 'Activo'
        
        mongo_db["usuarios"].update_one(
            {"_id": ObjectId(idUsuario)},
            {"$set": {"estadoCuenta": nuevo_estado}}
        )
        return JsonResponse({'status': 'success', 'message': f'Estado actualizado a {nuevo_estado}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ROLES
@login_required
def roles_overview(request):
    roles = []
    error_db = None
    query = request.GET.get('q', '').strip()
    rol_filtro = request.GET.get('rol', '').strip()

    try:
        mongo_query = {}
        if query:
            mongo_query["$or"] = [
                {"nombre": {"$regex": query, "$options": "i"}},
                {"apellido": {"$regex": query, "$options": "i"}},
                {"rol.nombreRol": {"$regex": query, "$options": "i"}}
            ]
        if rol_filtro:
            mongo_query["rol.nombreRol"] = rol_filtro

        mongo_users = mongo_db["usuarios"].find(mongo_query).sort("_id", -1)
        for u in mongo_users:
            rol_data = u.get("rol", {})
            nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
            desc_rol = rol_data.get("descripcion", nombre_rol) if isinstance(rol_data, dict) else str(rol_data)
            
            roles.append({
                'idRol': str(u.get("_id")), # En mongo usamos el id del usuario ya que el rol esta embedido
                'nombreRol': nombre_rol,
                'descripcion': desc_rol,
                'idUsuario': str(u.get("_id")),
                'usuario_nombre': f"{u.get('nombre', '')} {u.get('apellido', '')}".strip(),
                'usuario_email': u.get("email", "")
            })
    except Exception as e:
        error_db = str(e)
        print(f"❌ ERROR MONGODB EN ROLES_OVERVIEW: {error_db}")

    return render(request, 'usuarios/roles/roles_overview.html', {'roles': roles, 'error_db': error_db})
@login_required
def edit_role(request, idRol):
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombreRol')
        try:
            mongo_db["usuarios"].update_one(
                {"_id": ObjectId(idRol)},
                {"$set": {
                    "rol": {
                        "nombreRol": nombre_rol,
                        "descripcion": nombre_rol
                    }
                }}
            )
            return JsonResponse({'status': 'success', 'message': 'Nivel de acceso actualizado.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Error al actualizar el rol.'}, status=500)

    try:
        mongo_user = mongo_db["usuarios"].find_one({"_id": ObjectId(idRol)})
        if not mongo_user:
            return redirect('roles_overview')
            
        rol_data = mongo_user.get("rol", {})
        nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
        
        rol = {
            'idRol': str(mongo_user.get("_id")),
            'nombreRol': nombre_rol,
            'usuario_nombre': f"{mongo_user.get('nombre', '')} {mongo_user.get('apellido', '')}".strip()
        }
        return render(request, 'usuarios/roles/edit_role.html', {'rol': rol})
    except Exception as e:
        return redirect('roles_overview')

@login_required
def read_role(request, idRol):
    try:
        mongo_user = mongo_db["usuarios"].find_one({"_id": ObjectId(idRol)})
        if not mongo_user:
            return redirect('roles_overview')
            
        rol_data = mongo_user.get("rol", {})
        nombre_rol = rol_data.get("nombreRol", "Usuario") if isinstance(rol_data, dict) else str(rol_data)
        desc_rol = rol_data.get("descripcion", nombre_rol) if isinstance(rol_data, dict) else str(rol_data)
        
        rol = {
            'idRol': str(mongo_user.get("_id")),
            'nombreRol': nombre_rol,
            'descripcion': desc_rol,
            'usuario_nombre': f"{mongo_user.get('nombre', '')} {mongo_user.get('apellido', '')}".strip()
        }
        return render(request, 'usuarios/roles/read_role.html', {'rol': rol})
    except Exception as e:
        return redirect('roles_overview')


# ══════════════════════════════════════════
#  VISTAS DE LOGIN POR ROL
#  Cada consola solo acepta el rol correcto.
# ══════════════════════════════════════════

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from cenit.mongo_client import db as mongo_db


def _get_role_from_user(user):
    """Devuelve el rol del usuario consultando MongoDB (igual que el middleware)."""
    if user.is_superuser:
        return 'Administrador'
    try:
        mongo_user = mongo_db["usuarios"].find_one({"email": user.email})
        if mongo_user:
            rol = mongo_user.get("rol", {})
            if isinstance(rol, dict):
                return rol.get("nombreRol", "Usuario")
            return str(rol)
    except Exception as e:
        print("❌ Error al obtener rol:", e)
    return 'Usuario'


@require_http_methods(["GET", "POST"])
def login_admin_view(request):
    """Login exclusivo para Administradores."""
    if request.method == 'GET':
        if request.user.is_authenticated:
            role = _get_role_from_user(request.user)
            if role == 'Administrador':
                return redirect('songs_overview')
            logout(request)
        return render(request, 'registration/login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, 'registration/login.html', {'form': _fake_error_form()})

    role = _get_role_from_user(user)
    if role != 'Administrador':
        return render(request, 'registration/login.html', {
            'form': _fake_error_form(),
            'role_error': 'Esta consola es exclusiva para administradores.',
        })

    login(request, user)
    return redirect('songs_overview')


@require_http_methods(["GET", "POST"])
def login_analista_view(request):
    """Login exclusivo para Analistas."""
    if request.method == 'GET':
        if request.user.is_authenticated:
            role = _get_role_from_user(request.user)
            if role == 'Analista':
                return redirect('reporte_top_10')
            logout(request)
        return render(request, 'registration/login_analista.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, 'registration/login_analista.html', {'form': _fake_error_form()})

    role = _get_role_from_user(user)
    if role != 'Analista':
        return render(request, 'registration/login_analista.html', {
            'form': _fake_error_form(),
            'role_error': 'Esta consola es exclusiva para analistas de datos.',
        })

    login(request, user)
    return redirect('analista_dashboard')


@require_http_methods(["GET", "POST"])
def login_player_view(request):
    """Login exclusivo para Usuarios del reproductor."""
    if request.method == 'GET':
        if request.user.is_authenticated:
            role = _get_role_from_user(request.user)
            if role == 'Usuario':
                return redirect('player_home')
            logout(request)
        return render(request, 'registration/login_player.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, 'registration/login_player.html', {'form': _fake_error_form()})

    role = _get_role_from_user(user)
    if role != 'Usuario':
        return render(request, 'registration/login_player.html', {
            'form': _fake_error_form(),
            'role_error': 'Esta consola es exclusiva para usuarios del reproductor.',
        })

    login(request, user)
    return redirect('player_home')


class _fake_error_form:
    """Objeto mínimo para que {% if form.errors %} sea True en los templates."""
    errors = True
