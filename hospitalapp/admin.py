from django.contrib import admin
from .models import Paciente


# Registramos Paciente para poder verlo y administrarlo en /admin/
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'rut', 'nombre_completo', 'edad', 'estado', 'fecha_ingreso')
    search_fields = ('rut', 'nombre_completo')
    list_filter = ('estado',)
