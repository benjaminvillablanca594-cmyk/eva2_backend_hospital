from django.conf import settings
from django.db import models
from django.utils import timezone


# =====================================================================
# MODELO PACIENTE  ->  tabla hospitalapp_paciente
# Heredamos de 'models.Model' para que Django sepa que esta clase será una tabla en la BD.
# =====================================================================
class Paciente(models.Model):

    # Opciones permitidas para el estado del paciente, EN EL ORDEN de la atención:
    #   En Espera -> Atendido -> Derivado  (se envía a otro servicio)
    #                         -> Dado de alta  (se va a su casa)
    # Derivado y Dado de alta son estados FINALES: la atención se cierra.
    # El lado izquierdo es lo que se guarda en la BD, el derecho lo que lee el usuario.
    ESTADOS = [
        ('En Espera', 'En Espera'),
        ('Atendido', 'Atendido'),
        ('Derivado', 'Derivado'),
        ('Dado de alta', 'Dado de alta'),
    ]

    # CharField = VARCHAR en MySQL. unique=True crea una restricción UNIQUE:
    # la base de datos no permite dos filas con el mismo RUT.
    rut = models.CharField(max_length=12, unique=True)

    # VARCHAR(100) en la BD. Para los nuevos ingresos la API acepta máximo 50
    # caracteres (ver validar_paciente en views.py); se deja 100 en la tabla
    # para no romper registros antiguos más largos.
    nombre_completo = models.CharField(max_length=100)

    # Reemplaza a la antigua "edad": guardamos la fecha y la edad se CALCULA.
    # null=True: los pacientes registrados antes de este cambio no la tienen.
    fecha_nacimiento = models.DateField(null=True, blank=True)

    # EmailField = VARCHAR(254) que además valida el formato de correo.
    # Para los nuevos ingresos la API acepta máximo 70 caracteres.
    email_contacto = models.EmailField()

    # Teléfono de contacto, guardado como "+56912345678" (12 caracteres).
    # default='': los pacientes antiguos quedan con el teléfono vacío.
    telefono = models.CharField(max_length=12, blank=True, default='')

    # DateField guarda exclusivamente la fecha (AAAA-MM-DD).
    fecha_ingreso = models.DateField()

    # Estado ACTUAL del paciente. Cada cambio queda registrado en la tabla Atencion.
    estado = models.CharField(max_length=20, choices=ESTADOS, default='En Espera')

    # Edad calculada a partir de la fecha de nacimiento (no se guarda en la BD).
    # @property permite usarla como un atributo: paciente.edad
    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        nacimiento = self.fecha_nacimiento
        # Se resta 1 si este año todavía no ha llegado su cumpleaños
        return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))

    # Cómo se muestra el paciente en el admin: "12345678-5 - Juan Pérez"
    def __str__(self):
        return f"{self.rut} - {self.nombre_completo}"


# =====================================================================
# MODELO ATENCION  ->  tabla hospitalapp_atencion
# Historial de atención: cada vez que el paciente ingresa o cambia de
# estado se guarda una fila con el estado, el detalle y quién lo registró.
# =====================================================================
class Atencion(models.Model):

    # CLAVE FORÁNEA (FK): cada atención pertenece a UN paciente.
    # Un paciente puede tener MUCHAS atenciones (relación uno a muchos).
    # on_delete=CASCADE: si se elimina el paciente, se elimina su historial.
    # related_name='atenciones': permite hacer paciente.atenciones.all()
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='atenciones')

    # Estado en que quedó el paciente con esta atención
    estado = models.CharField(max_length=20, choices=Paciente.ESTADOS)

    # Detalle de la atención: VARCHAR(300)
    detalle = models.CharField(max_length=300)

    # Fecha y hora en que se registró (se completa sola al crear la fila)
    fecha = models.DateTimeField(auto_now_add=True)

    # SEGUNDA FK: el usuario del sistema que registró la atención.
    # SET_NULL: si se borra el usuario, la atención se conserva sin autor.
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['fecha', 'id']        # del más antiguo al más reciente

    def __str__(self):
        return f"{self.paciente.rut} - {self.estado} ({self.fecha:%d-%m-%Y %H:%M})"
