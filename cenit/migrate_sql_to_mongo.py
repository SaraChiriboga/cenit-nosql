import os
import django
import pymongo
import datetime

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cenit.settings')
django.setup()

from catalogo.models import Genero, Artista, Album, Cancion, Colaboracion
from django.conf import settings

def run_migration():
    # Connect to MongoDB
    mongo_client = pymongo.MongoClient(settings.MONGODB_URI)
    db = mongo_client[settings.MONGODB_NAME]

    print("Starting migration of data from SQL Server to MongoDB...")

    # 1. Migrate Genero
    db["Genero"].delete_many({})
    generos = Genero.objects.all()
    for g in generos:
        db["Genero"].insert_one({
            "genero_id": g.idgenero,
            "nombreGenero": g.nombregenero,
            "descripcion": g.descripcion
        })
    print(f"Migrated {generos.count()} Generos.")

    # 2. Migrate Artista
    db["Artista"].delete_many({})
    artistas = Artista.objects.all()
    for a in artistas:
        db["Artista"].insert_one({
            "artista_id": a.idartista,
            "nombreArtistico": a.nombreartistico,
            "biografia": a.biografia,
            "paisOrigen": a.paisorigen,
            "estadoActivo": a.estadoactivo,
            "fechaRegistro": a.fecharegistro,
            "urlPerfil": a.urlperfil
        })
    print(f"Migrated {artistas.count()} Artistas.")

    # 3. Migrate Album
    db["Album"].delete_many({})
    albumes = Album.objects.all()
    for al in albumes:
        # Convert date to datetime
        dt = datetime.datetime.combine(al.fechalanzamiento, datetime.time.min) if al.fechalanzamiento else None
        db["Album"].insert_one({
            "album_id": al.idalbum,
            "tituloAlbum": al.tituloalbum,
            "fechaLanzamiento": dt,
            "urlPortada": al.urlportada,
            "artista_id": al.artista_id
        })
    print(f"Migrated {albumes.count()} Albumes.")

    # 4. Migrate Cancion with embedded Colaboraciones
    db["Cancion"].delete_many({})
    canciones = Cancion.objects.all()
    migrated_count = 0
    for c in canciones:
        # Find collaborations for this song
        colabs = Colaboracion.objects.filter(cancion_id=c.idcancion)
        colaboradores_list = []
        for col in colabs:
            colaboradores_list.append({
                "artista_id": col.artista_id,
                "nombreArtista": col.artista.nombreartistico,
                "rolArtista": col.rolartista
            })
        
        db["Cancion"].insert_one({
            "cancion_id": c.idcancion,
            "tituloCancion": c.titulocancion,
            "duracionSeg": c.duracionseg,
            "esExplicita": c.esexplicita,
            "estadoPublicacion": c.estadopublicacion,
            "urlPortada": c.urlportada,
            "urlSpotifyAPI": c.spotifyurlapi,
            "album_id": c.album_id,
            "genero_id": c.genero_id,
            "colaboradores": colaboradores_list
        })
        migrated_count += 1
    print(f"Migrated {migrated_count} Canciones with embedded collaborators.")
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
