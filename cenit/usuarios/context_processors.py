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


def custom_reports(request):
    """
    Inyecta 'reportes_personalizados' en el contexto de todas las plantillas.
    Permite cargar el listado de reportes creados en el sidebar.
    """
    reportes = []
    if request.user.is_authenticated:
        try:
            # Traer los reportes de la colección
            reportes_cursor = db['reportes_personalizados'].find({}, {'titulo': 1, 'metodo': 1})
            for doc in reportes_cursor:
                doc['id_str'] = str(doc['_id'])
                reportes.append(doc)
        except Exception:
            pass
    return {'reportes_personalizados': reportes}
