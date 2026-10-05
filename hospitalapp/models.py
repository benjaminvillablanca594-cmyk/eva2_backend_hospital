from django.db import models

# Heredamos de 'models.Model' para que Django sepa que esta clase será una tabla en la BD.
class Paciente(models.Model):

# Definimos las opciones permitidas para el estado del paciente.
# El lado izquierdo es lo que se guarda en la BD, el derecho lo que lee el usuario.
    ESTADOS = [
        ('Atendido', 'Atendido'),
        ('En Espera', 'En Espera'),
        ('Derivado', 'Derivado'),
    ]

    # CharField es para textos cortos. unique=True asegura que no existan dos RUT iguales.
    rut = models.CharField(max_length=12, unique=True)

# max_length=100 limita el largo del nombre para no desperdiciar espacio en la BD.
    nombre_completo = models.CharField(max_length=100)

# PositiveIntegerField restringe a que sean solo números enteros y positivos (sin edades negativas).
    edad = models.PositiveIntegerField()

# EmailField valida automáticamente que lo ingresado tenga formato válido de correo (@ y dominio).
    email_contacto = models.EmailField()

# DateField guarda exclusivamente el formato de fecha (YYYY-MM-DD).
    fecha_ingreso = models.DateField()

# choices=ESTADOS conecta este campo con la lista de arriba.
# default='En Espera' hace que si se omite, se guarde ese estado por defecto.
    estado = models.CharField(max_length=20, choices=ESTADOS, default='En Espera')

    # Este método "mágico" (str) permite que cuando le pidas a Django mostrar un paciente,
    # no te devuelva un código raro (ej: Object 1), sino que te muestre: "12345678-9 - Juan Pérez".
    def str(self):
        return f"{self.rut} - {self.nombre_completo}"
