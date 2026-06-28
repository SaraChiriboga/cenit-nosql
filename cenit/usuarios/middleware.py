from django.shortcuts import redirect
from cenit.mongo_client import db

class RoleRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Excluir archivos estáticos, media y páginas públicas principales
        if (path.startswith('/static/') or 
            path.startswith('/media/') or 
            path == '/' or 
            path == '/logout/' or
            path.startswith('/admin/')):
            return self.get_response(request)

        # Excluir los endpoints de inicio de sesión para evitar bucles de redirección
        login_paths = ['/login/', '/login/analista/', '/login/player/']
        if any(path == lp for lp in login_paths):
            return self.get_response(request)

        # 1. Validaciones para usuarios NO autenticados (Anónimos)
        if not request.user.is_authenticated:
            if path.startswith('/player/'):
                return redirect('login_player')
            elif '/reportes/' in path or '/estadisticas/' in path:
                return redirect('login_analista')
            elif (path.startswith('/catalogo/') or 
                  path.startswith('/usuarios/') or 
                  path.startswith('/suscripciones/')):
                return redirect('login')
            return self.get_response(request)

        # 2. Validaciones de roles para usuarios autenticados
        role = self.get_user_role(request.user)

        # ── ROL: USUARIO ──
        if role == 'Usuario':
            # Solo puede ingresar a '/player/'
            if not path.startswith('/player/'):
                return redirect('player_home')

        # ── ROL: ANALISTA ──
        elif role == 'Analista':
            # Solo puede ingresar a reportes, estadísticas o su dashboard
            is_allowed = '/reportes/' in path or '/estadisticas/' in path
            if not is_allowed:
                return redirect('analista_dashboard')

        # ── ROL: ADMINISTRADOR ──
        elif role == 'Administrador':
            # Puede entrar a todo excepto al reproductor (/player/) y al login del analista
            if path.startswith('/player/'):
                return redirect('songs_overview')
            if path.startswith('/login/analista/'):
                return redirect('songs_overview')

        return self.get_response(request)

    def get_user_role(self, user):
        if user.is_superuser:
            return 'Administrador'
        try:
            # Buscamos en MongoDB por el correo del usuario autenticado
            mongo_user = db["usuarios"].find_one({"email": user.email})
            if mongo_user:
                rol = mongo_user.get("rol", {})
                if isinstance(rol, dict):
                    return rol.get("nombreRol", "Usuario")
                return str(rol)
        except Exception as e:
            print("❌ Error al obtener rol desde MongoDB:", e)
        return 'Usuario'
