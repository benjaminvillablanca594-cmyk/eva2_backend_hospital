from django.urls import path
from . import views

urlpatterns = [
    # Ruta vacía ('') es la página principal (listar)
    path('', views.listar_pacientes, name='listar_pacientes'),
    
    # Rutas para el resto del CRUD
    path('crear/', views.crear_paciente, name='crear_paciente'),
    path('editar/<int:pk>/', views.editar_paciente, name='editar_paciente'),
    path('eliminar/<int:pk>/', views.eliminar_paciente, name='eliminar_paciente'),
]