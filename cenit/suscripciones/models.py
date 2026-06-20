from django.db import models

# ==========================================
# 1. TipoSuscripcion
# ==========================================
class TipoSuscripcion(models.Model):
    idtipo = models.AutoField(db_column='idTipo', primary_key=True)  # ← AutoField
    nombreplan = models.CharField(db_column='nombrePlan', max_length=50)
    precio = models.DecimalField(db_column='precio', max_digits=10, decimal_places=2)
    moneda = models.CharField(db_column='moneda', max_length=3)
    duracion = models.IntegerField(db_column='duracion')

    class Meta:
        managed = False
        db_table = '[Negocio].[TipoSuscripcion]'

    def __str__(self):
        return f"{self.nombreplan} ({self.moneda} {self.precio})"


# ==========================================
# 2. Promocion
# ==========================================
class Promocion(models.Model):
    idpromo = models.AutoField(db_column='idPromo', primary_key=True)  
    descripcion = models.CharField(db_column='descripcion', max_length=255)
    porcentajedesc = models.DecimalField(db_column='porcentajeDesc', max_digits=5, decimal_places=2)
    fechainicio = models.DateTimeField(db_column='fechaInicio')
    fechaexpira = models.DateTimeField(db_column='fechaExpira', blank=True, null=True)
    estadoactivo = models.BooleanField(db_column='estadoActivo')
    tiposuscripcion = models.ForeignKey(TipoSuscripcion, on_delete=models.DO_NOTHING,
                                        db_column='TipoSuscripcion_idTipo')

    class Meta:
        managed = False
        db_table = '[Negocio].[Promocion]'

    def __str__(self):
        return self.descripcion


# ==========================================
# 3. Suscripcion
# ==========================================
class Suscripcion(models.Model):
    id = models.AutoField(primary_key=True)  # ← PK autoincremental
    idsuscripcion = models.IntegerField(db_column='idSuscripcion', blank=True, null=True)
    fechainicio = models.DateTimeField(db_column='fechaInicio')
    fechafin = models.DateTimeField(db_column='fechaFin')
    estado = models.CharField(db_column='estado', max_length=20)
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario', blank=True, null=True)
    tiposuscripcion = models.ForeignKey(TipoSuscripcion, on_delete=models.DO_NOTHING,
                                        db_column='TipoSuscripcion_idTipo')
    promocion = models.ForeignKey(Promocion, on_delete=models.DO_NOTHING,
                                  db_column='Promocion_idPromo', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[Negocio].[Suscripcion]'

    def __str__(self):
        return f"Suscripción {self.idsuscripcion} - {self.estado}"


# ==========================================
# 4. Notificacion
# ==========================================
class Notificacion(models.Model):
    idnotificacion = models.AutoField(db_column='idNotificacion', primary_key=True)
    tiponotif = models.CharField(db_column='tipoNotif', max_length=50)
    mensaje = models.TextField(db_column='mensaje')
    fechaenvio = models.DateTimeField(db_column='fechaEnvio')
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario')
    promocion = models.ForeignKey(Promocion, on_delete=models.DO_NOTHING,
                                  db_column='Promocion_idPromo')

    class Meta:
        managed = False
        db_table = '[Auditoria].[Notificacion]'

    def __str__(self):
        return f"Notificación {self.idnotificacion} ({self.tiponotif})"


# ==========================================
# 5. Playlist
# ==========================================
class Playlist(models.Model):
    idplaylist = models.AutoField(db_column='idPlaylist', primary_key=True)
    nombre = models.CharField(db_column='nombre', max_length=100)
    descripcion = models.CharField(db_column='descripcion', max_length=255, blank=True, null=True)
    esprivada = models.BooleanField(db_column='esPrivada')
    espublicada = models.BooleanField(db_column='esPublicada')
    imagenportada = models.TextField(db_column='imagenPortada', blank=True, null=True)
    fechacreacion = models.DateTimeField(db_column='fechaCreacion')
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[Usuario].[Playlist]'

    def __str__(self):
        return self.nombre


# ==========================================
# 6. PlaylistCancion
# ==========================================
class PlaylistCancion(models.Model):
    id = models.AutoField(primary_key=True)
    playlist = models.ForeignKey(Playlist, on_delete=models.DO_NOTHING,
                                 db_column='Playlist_idPlaylist')
    cancion = models.ForeignKey('catalogo.Cancion', on_delete=models.DO_NOTHING,
                                db_column='Cancion_idCancion')
    fechaadicion = models.DateTimeField(db_column='fechaAdicion')
    orden = models.IntegerField(db_column='orden')

    class Meta:
        managed = False
        db_table = '[Usuario].[PlaylistCancion]'
        unique_together = (('playlist', 'cancion'),)

    def __str__(self):
        return f"{self.playlist} - {self.cancion}"


# ==========================================
# 7. EstadisticaDiaria
# ==========================================
class EstadisticaDiaria(models.Model):
    idestat = models.AutoField(db_column='idEstat', primary_key=True)
    totalrepros = models.IntegerField(db_column='totalRepros')
    fechareporte = models.DateField(db_column='fechaReporte')
    cancion = models.ForeignKey('catalogo.Cancion', on_delete=models.DO_NOTHING,
                                db_column='Cancion_idCancion')

    class Meta:
        managed = False
        db_table = '[Auditoria].[EstadisticaDiaria]'

    def __str__(self):
        return f"Estadística {self.idestat} - {self.fechareporte}"