import os

with open('usuarios/views.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('mongo_db["Artista"].find_one({"idArtista": doc.get("idArtista")})', 'mongo_db["Artista"].find_one({"artista_id": doc.get("idArtista")})')

c = c.replace("'fechaseguimiento': doc.get('fechaSeguimiento'),", "'fechaseguimiento': parse_datetime(doc.get('fechaSeguimiento')) if doc.get('fechaSeguimiento') and isinstance(doc.get('fechaSeguimiento'), str) else doc.get('fechaSeguimiento'),")

c = c.replace("'fechalike': doc.get('fechaLike'),", "'fechalike': parse_datetime(doc.get('fechaLike')) if doc.get('fechaLike') and isinstance(doc.get('fechaLike'), str) else doc.get('fechaLike'),")

if "from django.utils.dateparse import parse_datetime" not in c:
    c = "from django.utils.dateparse import parse_datetime\n" + c

with open('usuarios/views.py', 'w', encoding='utf-8') as f:
    f.write(c)
