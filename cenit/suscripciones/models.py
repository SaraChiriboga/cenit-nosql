"""
Módulo de modelos para suscripciones — MongoDB.

Reemplaza los modelos ORM de Django por clases wrapper que permiten
acceder a los campos de documentos MongoDB con dot-notation en templates.
"""
from datetime import datetime


# ══════════════════════════════════════════
#  Utilidades
# ══════════════════════════════════════════

# Campos de fecha que se deben parsear de string ISO → datetime
_DATE_FIELDS = {
    'fechaInicio', 'fechaFin', 'fechaExpira', 'fechaEnvio',
    'fechaCreacion', 'fechaReporte', 'fechaAdicion',
}


def parse_date(date_str):
    """Convierte un string ISO 8601 a un objeto datetime."""
    if not date_str:
        return None
    try:
        if 'T' in str(date_str):
            return datetime.fromisoformat(str(date_str))
        return datetime.strptime(str(date_str), '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def prepare_doc(doc):
    """
    Prepara un documento de MongoDB para ser consumido por los templates:
    - Convierte strings de fecha a objetos datetime.
    - Mapea _id (ObjectId) a un campo 'id' accesible en templates.
    """
    if not doc:
        return doc
    for field in _DATE_FIELDS:
        if field in doc and isinstance(doc[field], str):
            doc[field] = parse_date(doc[field])
    # _id no es accesible en Django templates (empieza con _)
    if '_id' in doc and not isinstance(doc['_id'], (int, float)):
        doc['id'] = str(doc['_id'])
    return doc


# ══════════════════════════════════════════
#  MongoDoc — Wrapper de diccionario → objeto
# ══════════════════════════════════════════

class MongoDoc:
    """
    Envuelve un diccionario de MongoDB para que sus claves sean
    accesibles como atributos (dot-notation) en los templates de Django.

    Uso:
        doc = MongoDoc({'nombrePlan': 'Premium', 'precio': 5.99})
        {{ doc.nombrePlan }}   → 'Premium'
        {{ doc.precio }}       → 5.99

    Los subdocumentos embebidos se envuelven automáticamente.
    """

    def __init__(self, data=None):
        self._data = data or {}

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        value = self._data.get(name)
        if isinstance(value, dict):
            return MongoDoc(value)
        if isinstance(value, list):
            return [MongoDoc(item) if isinstance(item, dict) else item
                    for item in value]
        return value

    def __str__(self):
        # Intenta mostrar un campo descriptivo útil
        for key in ('nombrePlan', 'descripcion', 'nombre', 'tipoNotif', 'id'):
            if key in self._data:
                return str(self._data[key])
        return str(self._data.get('id', ''))

    def __bool__(self):
        return bool(self._data)

    def __eq__(self, other):
        if isinstance(other, (int, float, str)):
            return False
        if isinstance(other, MongoDoc):
            return self._data == other._data
        return NotImplemented

    def __repr__(self):
        return f"MongoDoc({self._data})"