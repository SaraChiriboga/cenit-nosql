from django.db import models


class Sysdiagrams(models.Model):
    name = models.CharField(max_length=128, db_collation='SQL_Latin1_General_CP1_CI_AS')
    principal_id = models.IntegerField()
    diagram_id = models.AutoField(primary_key=True)
    version = models.IntegerField(blank=True, null=True)
    definition = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sysdiagrams'
        unique_together = (('principal_id', 'name'),)


class Artista(models.Model):
    idartista = models.IntegerField(db_column='idArtista', primary_key=True)  # Clave primaria asignada
    nombreartistico = models.CharField(db_column='nombreArtistico', max_length=100,
                                       db_collation='SQL_Latin1_General_CP1_CI_AS')
    biografia = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS')
    paisorigen = models.CharField(db_column='paisOrigen', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')
    estadoactivo = models.CharField(db_column='estadoActivo', max_length=50,
                                    db_collation='SQL_Latin1_General_CP1_CI_AS')
    fecharegistro = models.DateTimeField(db_column='fechaRegistro')
    urlperfil = models.CharField(db_column='urlPerfil', max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Catalogo].[Artista'
        verbose_name = 'Artista'
        verbose_name_plural = 'Artistas'

    def __str__(self):
        return self.nombreartistico


class Genero(models.Model):
    idgenero = models.IntegerField(db_column='idGenero', primary_key=True)  # Clave primaria asignada
    nombregenero = models.CharField(db_column='nombreGenero', max_length=50,
                                    db_collation='SQL_Latin1_General_CP1_CI_AS')
    descripcion = models.CharField(max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS')

    class Meta:
        managed = False
        db_table = 'Catalogo].[Genero'
        verbose_name = 'Genero'
        verbose_name_plural = 'Géneros'

    def __str__(self):
        return self.nombregenero


class Album(models.Model):
    idalbum = models.IntegerField(db_column='idAlbum', primary_key=True)  # Clave primaria asignada
    tituloalbum = models.CharField(db_column='tituloAlbum', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')
    fechalanzamiento = models.DateField(db_column='fechaLanzamiento')
    urlportada = models.CharField(db_column='urlPortada', max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    # Transformado a ForeignKey para conectar con Artista
    artista = models.ForeignKey(Artista, on_delete=models.DO_NOTHING, db_column='Artista_idArtista')

    class Meta:
        managed = False
        db_table = 'Catalogo].[Album'
        verbose_name = 'Álbum'
        verbose_name_plural = 'Álbumes'

    def __str__(self):
        return self.tituloalbum


class Cancion(models.Model):
    idcancion = models.IntegerField(db_column='idCancion', primary_key=True)  # Clave primaria asignada
    titulocancion = models.CharField(db_column='tituloCancion', max_length=150,
                                     db_collation='SQL_Latin1_General_CP1_CI_AS')
    duracionseg = models.IntegerField(db_column='duracionSeg')
    esexplicita = models.BooleanField(db_column='esExplicita')
    estadopublicacion = models.CharField(db_column='estadoPublicacion', max_length=50,
                                         db_collation='SQL_Latin1_General_CP1_CI_AS')
    urlportada = models.CharField(db_column='urlPortada', max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS',
                                  blank=True, null=True)
    # Transformados a ForeignKey relacionales
    album = models.ForeignKey(Album, on_delete=models.DO_NOTHING, db_column='Album_idAlbum')
    genero = models.ForeignKey(Genero, on_delete=models.DO_NOTHING, db_column='Genero_idGenero')
    spotifyurlapi = models.CharField(db_column='spotifyUrlAPI', max_length=500,
                                     db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Catalogo].[Cancion'
        verbose_name = 'Canción'
        verbose_name_plural = 'Canciones'

    def __str__(self):
        return self.titulocancion


class Colaboracion(models.Model):
    idcolaboracion = models.IntegerField(db_column='idColaboracion', primary_key=True)  # Clave primaria asignada
    rolartista = models.CharField(db_column='rolArtista', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')
    # Relaciones ForeignKey
    cancion = models.ForeignKey(Cancion, on_delete=models.DO_NOTHING, db_column='Cancion_idCancion')
    artista = models.ForeignKey(Artista, on_delete=models.DO_NOTHING, db_column='Artista_idArtista')

    class Meta:
        managed = False
        db_table = 'Catalogo].[Colaboracion'
        verbose_name = 'Colaboración'
        verbose_name_plural = 'Colaboraciones'