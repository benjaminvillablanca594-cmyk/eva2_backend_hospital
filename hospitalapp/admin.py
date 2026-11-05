from django.contrib import admin
from .models import Paciente, Atencion


# Muestra el historial de atención DENTRO de la ficha del paciente en /admin/
# (es posible gracias a la clave foránea Atencion.paciente)
class AtencionEnLinea(admin.TabularInline):
    model = Atencion
    extra = 0
    readonly_fields = ('estado', 'detalle', 'fecha', 'registrado_por')
    can_delete = False


# Registramos Paciente para verlo y administrarlo en /admin/
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'rut', 'nombre_completo', 'fecha_nacimiento', 'telefono', 'estado', 'fecha_ingreso')
    search_fields = ('rut', 'nombre_completo')
    list_filter = ('estado',)
    inlines = [AtencionEnLinea]


# Tabla del historial de atención
@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'estado', 'detalle', 'fecha', 'registrado_por')
    list_filter = ('estado',)
