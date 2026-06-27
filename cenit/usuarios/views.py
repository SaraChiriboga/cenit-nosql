import secrets

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
        with connection.cursor() as cursor:
            # Construimos la consulta base con JOIN para traer el Rol
            query = """
                SELECT 
                    u.idUsuario, 
                    u.nombre, 
                    u.apellido, 
                    u.email, 
                    u.estadoCuenta AS estado, 
                    r.nombreRol AS rol_nombre 
                FROM Usuario.Usuario u
                LEFT JOIN Usuario.Rol r ON u.idUsuario = r.Usuario_idUsuario
                WHERE 1=1
            """
            params = []

            # Aplicamos filtros de búsqueda si existen
            if q:
                query += " AND (u.nombre LIKE %s OR u.apellido LIKE %s OR u.email LIKE %s)"
                params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])

            if rol_filter:
                query += " AND r.nombreRol = %s"
                params.append(rol_filter)

            query += " ORDER BY u.idUsuario DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Mapeamos los resultados para la plantilla
            for row in rows:
                usuarios.append({
                    'idUsuario': row[0],
                    'nombre': row[1],
                    'apellido': row[2],
                    'email': row[3],
                    'estado': row[4],
                    'rol_nombre': row[5] or 'Usuario'
                })

    except Exception as e:
        error_db = str(e)
        print(f"❌ ERROR SQL EN USERS_OVERVIEW: {error_db}")

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
        print("\n--- 🟢 INICIANDO REGISTRO DE USUARIO ---")
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        rol_nombre = request.POST.get('rol_nombre')

        print(f"-> DATOS RECIBIDOS: Nombre={nombre}, Apellido={apellido}, Email={email}, Rol={rol_nombre}")

        password_temporal = secrets.token_urlsafe(8)
        password_hash = make_password(password_temporal).encode('utf-8')

        try:
            with connection.cursor() as cursor:
                print("-> 1. Intentando insertar en Usuario.Usuario...")
                cursor.execute("""
                    INSERT INTO Usuario.Usuario (nombre, apellido, email, passwordHash, estadoPlan, fechaRegistro, estadoCuenta, debeCambiarPassword)
                    OUTPUT inserted.idUsuario
                    VALUES (%s, %s, %s, %s, 'Free', GETDATE(), 'Activo', 1)
                """, [nombre, apellido, email, password_hash])

                nuevo_id_usuario = cursor.fetchone()[0]
                print(f"-> ÉXITO 1: Usuario insertado con ID: {nuevo_id_usuario}")

                print(
                    f"-> 2. Intentando insertar en Usuario.Rol con idUsuario={nuevo_id_usuario} y rol='{rol_nombre}'...")
                cursor.execute("""
                                    INSERT INTO Usuario.Rol (nombreRol, descripcion, Usuario_idUsuario)
                                    VALUES (%s, %s, %s)
                                """, [rol_nombre, rol_nombre, nuevo_id_usuario])

                print("-> ÉXITO 2: Rol insertado correctamente.")

            print(f"✅ CICLO COMPLETO EXITOSO. Clave temporal: {password_temporal}")
            print("----------------------------------------\n")
            return JsonResponse({'status': 'success', 'message': f'Usuario {nombre} creado con éxito.'})

        except Exception as e:
            error_str = str(e)
            print(f"❌ ERROR SQL CRÍTICO: {error_str}")
            print("----------------------------------------\n")

            if 'Usuario_email_UN' in error_str or 'UNIQUE KEY' in error_str:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Este correo ya está registrado en el sistema.'
                }, status=400)

            # Mandamos el error directamente al Toast para verlo en pantalla
            return JsonResponse({
                'status': 'error',
                'message': f'Error SQL: {error_str}'
            }, status=500)

    return render(request, 'usuarios/usuarios/add_user.html')


# ══════════════════════════════════════════
#  LEER DETALLES (read_user)
# ══════════════════════════════════════════

@login_required
def read_user(request, idUsuario):
    u = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    u.idUsuario, u.nombre, u.apellido, u.email, 
                    u.estadoCuenta, u.fechaRegistro, u.estadoPlan, u.debeCambiarPassword,
                    r.nombreRol, r.descripcion
                FROM Usuario.Usuario u
                LEFT JOIN Usuario.Rol r ON u.idUsuario = r.Usuario_idUsuario
                WHERE u.idUsuario = %s
            """, [idUsuario])
            row = cursor.fetchone()

            if row:
                u = {
                    'idUsuario': row[0],
                    'nombre': row[1],
                    'apellido': row[2],
                    'email': row[3],
                    'estado': row[4],  # Mapeamos estadoCuenta a 'estado' para la plantilla
                    'fechaRegistro': row[5],
                    'estadoPlan': row[6],
                    'debeCambiarPassword': row[7],
                    'rol_nombre': row[8] or 'Usuario',
                    'rol_descripcion': row[9] or 'Acceso básico a la plataforma.'
                }
            else:
                # Si no encuentra al usuario, redirigir al overview
                return redirect('users_overview')

    except Exception as e:
        print(f"❌ ERROR SQL EN READ_USER: {str(e)}")
        return redirect('users_overview')

    return render(request, 'usuarios/usuarios/read_user.html', {'u': u})


# ══════════════════════════════════════════
#  EDITAR USUARIO (edit_user)
# ══════════════════════════════════════════

@login_required
def edit_user(request, idUsuario):  # <-- CAMBIO 1: Recibe idUsuario
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        rol_nombre = request.POST.get('rol_nombre')
        estado_cuenta = request.POST.get('estadoCuenta')

        try:
            with connection.cursor() as cursor:
                # 1. Actualizamos el Usuario
                cursor.execute("""
                    UPDATE Usuario.Usuario 
                    SET nombre = %s, apellido = %s, email = %s, estadoCuenta = %s
                    WHERE idUsuario = %s
                """, [nombre, apellido, email, estado_cuenta, idUsuario])  # <-- CAMBIO 2: Usa idUsuario

                # 2. Actualizamos el Rol (usando el nombre dos veces para la restricción CHECK)
                cursor.execute("""
                    UPDATE Usuario.Rol 
                    SET nombreRol = %s, descripcion = %s
                    WHERE Usuario_idUsuario = %s
                """, [rol_nombre, rol_nombre, idUsuario])  # <-- CAMBIO 3: Usa idUsuario

            return JsonResponse({'status': 'success', 'message': 'Usuario actualizado con éxito.'})

        except Exception as e:
            error_str = str(e)
            print(f"❌ ERROR SQL EN EDIT_USER: {error_str}")

            if 'Usuario_email_UN' in error_str or 'UNIQUE KEY' in error_str:
                return JsonResponse({'status': 'error', 'message': 'Este correo ya está en uso.'}, status=400)

            return JsonResponse({'status': 'error', 'message': f'Error SQL: {error_str}'}, status=500)

    # Si es GET, traemos los datos actuales para llenar el formulario
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.idUsuario, u.nombre, u.apellido, u.email, u.estadoCuenta, r.nombreRol 
            FROM Usuario.Usuario u
            LEFT JOIN Usuario.Rol r ON u.idUsuario = r.Usuario_idUsuario
            WHERE u.idUsuario = %s
        """, [idUsuario])  # <-- CAMBIO 4: Usa idUsuario
        row = cursor.fetchone()

    if not row:
        return redirect('users_overview')

    u = {
        'idUsuario': row[0], 'nombre': row[1], 'apellido': row[2],
        'email': row[3], 'estadoCuenta': row[4], 'nombreRol': row[5] or 'Usuario'
    }
    return render(request, 'usuarios/usuarios/edit_user.html', {'u': u})

# ══════════════════════════════════════════
#  ACTIVAR / SUSPENDER (toggle_user)
# ══════════════════════════════════════════

from django.views.decorators.http import require_POST

@login_required
@require_POST
def toggle_user(request, idUsuario):
    try:
        with connection.cursor() as cursor:
            # CORRECCIÓN: Usar Usuario.Usuario
            cursor.execute("SELECT estadoCuenta FROM Usuario.Usuario WHERE idUsuario = %s", [idUsuario])
            row = cursor.fetchone()

            if not row:
                return JsonResponse({'status': 'error', 'message': 'Usuario no encontrado.'}, status=404)

            estado_actual = row[0]
            nuevo_estado = 'Suspendido' if estado_actual == 'Activo' else 'Activo'

            # CORRECCIÓN: Usar Usuario.Usuario
            cursor.execute("UPDATE Usuario.Usuario SET estadoCuenta = %s WHERE idUsuario = %s", [nuevo_estado, idUsuario])

        return JsonResponse({'status': 'success', 'message': f'Estado actualizado a {nuevo_estado}.'})
    except Exception as e:
        print(f"❌ ERROR SQL EN TOGGLE_USER: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ROLES
@login_required
def roles_overview(request):
    roles = []
    error_db = None

    # 1. Capturamos los filtros del GET
    query = request.GET.get('q', '').strip()
    rol_filtro = request.GET.get('rol', '').strip()

    try:
        with connection.cursor() as cursor:
            # 2. Construcción dinámica de la consulta
            sql = """
                SELECT 
                    r.idRol, r.nombreRol, r.descripcion, 
                    u.idUsuario, u.nombre, u.apellido, u.email
                FROM Usuario.Rol r
                INNER JOIN Usuario.Usuario u ON r.Usuario_idUsuario = u.idUsuario
                WHERE 1=1
            """
            params = []

            # Filtrar por texto (nombre usuario, apellido o nombre de rol)
            if query:
                sql += " AND (u.nombre LIKE %s OR u.apellido LIKE %s OR r.nombreRol LIKE %s)"
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])

            # Filtrar por tipo de rol específico
            if rol_filtro:
                sql += " AND r.nombreRol = %s"
                params.append(rol_filtro)

            sql += " ORDER BY r.idRol DESC"

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                roles.append({
                    'idRol': row[0],
                    'nombreRol': row[1],
                    'descripcion': row[2],
                    'idUsuario': row[3],
                    'usuario_nombre': f"{row[4]} {row[5]}",
                    'usuario_email': row[6]
                })

    except Exception as e:
        error_db = str(e)
        print(f"❌ ERROR SQL EN FILTROS ROLES: {error_db}")

    return render(request, 'usuarios/roles/roles_overview.html', {'roles': roles, 'error_db': error_db})
@login_required
def edit_role(request, idRol):  # <-- Faltaba el idRol y el request
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombreRol')

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Usuario.Rol 
                    SET nombreRol = %s, descripcion = %s
                    WHERE idRol = %s
                """, [nombre_rol, nombre_rol, idRol])
            return JsonResponse({'status': 'success', 'message': 'Nivel de acceso actualizado.'})
        except Exception as e:
            print(f"❌ ERROR SQL EN EDIT_ROLE: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Error al actualizar el rol.'}, status=500)

    # Si es GET, buscamos los datos actuales para llenar el formulario
    rol = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.idRol, r.nombreRol, u.nombre, u.apellido 
                FROM Usuario.Rol r
                INNER JOIN Usuario.Usuario u ON r.Usuario_idUsuario = u.idUsuario
                WHERE r.idRol = %s
            """, [idRol])
            row = cursor.fetchone()

            if row:
                rol = {
                    'idRol': row[0],
                    'nombreRol': row[1],
                    'usuario_nombre': f"{row[2]} {row[3]}"
                }
    except Exception as e:
        print(f"❌ ERROR SQL: {str(e)}")

    if not rol:
        return redirect('roles_overview')

    return render(request, 'usuarios/roles/edit_role.html', {'rol': rol})

@login_required
def read_role(request, idRol):
    # Buscamos el rol y unimos con el usuario para traer el nombre
    rol = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    r.idRol, 
                    r.nombreRol, 
                    r.descripcion, 
                    u.nombre, 
                    u.apellido 
                FROM Usuario.Rol r
                INNER JOIN Usuario.Usuario u ON r.Usuario_idUsuario = u.idUsuario
                WHERE r.idRol = %s
            """, [idRol])
            row = cursor.fetchone()

            if row:
                rol = {
                    'idRol': row[0],
                    'nombreRol': row[1],
                    'descripcion': row[2],
                    'usuario_nombre': f"{row[3]} {row[4]}"
                }
    except Exception as e:
        print(f"❌ ERROR SQL EN READ_ROLE: {str(e)}")

    if not rol:
        return redirect('roles_overview')

    return render(request, 'usuarios/roles/read_role.html', {'rol': rol})


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
    return redirect('reporte_top_10')


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