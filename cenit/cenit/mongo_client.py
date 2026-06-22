"""
Conexión centralizada a MongoDB Atlas para el proyecto Cénit.
Importar 'db' desde este módulo para acceder a cualquier colección.
"""
from pymongo import MongoClient

MONGO_URI = (
    'mongodb+srv://choloplay:Cenit2026'
    '@clusterudla01.3scysxe.mongodb.net/C%C3%A9nit'
    '?retryWrites=true&w=majority'
)

client = MongoClient(MONGO_URI)
db = client['Cénit']
