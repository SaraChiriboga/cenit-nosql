from cenit.mongo_client import db


def user_role(request):
    """
    Inyecta 'user_role' en el contexto de todas las plantillas.
    Permite que base.html sepa qué rol tiene el usuario actual
    sin necesidad de consultar MongoDB en cada vista individualmente.
    """
    role = 'Anonimo'
    if request.user.is_authenticated:
        if request.user.is_superuser:
            role = 'Administrador'
        else:
            try:
                mongo_user = db['usuarios'].find_one({'email': request.user.email})
                if mongo_user:
                    rol = mongo_user.get('rol', {})
                    if isinstance(rol, dict):
                        role = rol.get('nombreRol', 'Usuario')
                    else:
                        role = str(rol)
            except Exception:
                role = 'Usuario'
    return {'user_role': role}
