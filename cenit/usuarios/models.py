from django.db import models

# ==========================================
# 1. Usuario
# ==========================================
class Usuario(models.Model):
    idusuario = models.AutoField(db_column='idUsuario', primary_key=True)
    nombre = models.CharField(db_column='nombre', max_length=50)
    apellido = models.CharField(db_column='apellido', max_length=50)
    email = models.CharField(db_column='email', max_length=50)
    passwordhash = models.BinaryField(db_column='passwordHash', max_length=256)
    estadoplan = models.CharField(db_column='estadoPlan', max_length=10)
    fecharegistro = models.DateField(db_column='fechaRegistro')

    class Meta:
        managed = False
        db_table = '[Usuario].[Usuario]'

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


# ==========================================
# 2. Rol
# ==========================================
class Rol(models.Model):
    idrol = models.AutoField(db_column='idRol', primary_key=True)
    nombrerol = models.CharField(db_column='nombreRol', max_length=30, blank=True, null=True)
    descripcion = models.CharField(db_column='descripcion', max_length=255, blank=True, null=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario')

    class Meta:
        managed = False
        db_table = '[Usuario].[Rol]'

    def __str__(self):
        return f"{self.nombrerol}"


# ==========================================
# 3. AuditoriaAcceso
# ==========================================
class AuditoriaAcceso(models.Model):
    idlog = models.AutoField(db_column='idLog', primary_key=True)
    accion = models.CharField(db_column='accion', max_length=100, blank=True, null=True)
    iporigen = models.CharField(db_column='ipOrigen', max_length=45, blank=True, null=True)
    rol = models.ForeignKey(Rol, on_delete=models.DO_NOTHING,
                            db_column='Rol_idRol')

    class Meta:
        managed = False
        db_table = '[Auditoria].[AuditoriaAcceso]'

    def __str__(self):
        return f"Log {self.idlog} - {self.accion}"


# ==========================================
# 4. Seguimiento
# ==========================================
class Seguimiento(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario')
    artista = models.ForeignKey('catalogo.Artista', on_delete=models.DO_NOTHING,
                                db_column='Artista_idArtista')
    fechaseguimiento = models.DateTimeField(db_column='fechaSeguimiento', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[Usuario].[Seguimiento]'
        unique_together = (('usuario', 'artista'),)

    def __str__(self):
        return f"{self.usuario} -> {self.artista}"


# ==========================================
# 5. CancionFavorita
# ==========================================
class CancionFavorita(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING,
                                db_column='Usuario_idUsuario')
    cancion = models.ForeignKey('catalogo.Cancion', on_delete=models.DO_NOTHING,
                                db_column='Cancion_idCancion')
    fechalike = models.DateTimeField(db_column='fechaLike', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[Usuario].[CancionFavorita]'
        unique_together = (('usuario', 'cancion'),)

    def __str__(self):
        return f"{self.usuario} ♥ {self.cancion}"