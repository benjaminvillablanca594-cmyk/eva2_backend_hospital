from django.urls import path
from . import views

urlpatterns = [
    # RUTA PÁGINA DE LOGIN (pública)
    path('', views.login_pagina, name='login_pagina'),

    # PÁGINAS DEL CRUD (protegidas con @login_required)
    path('pacientes/', views.listar_pacientes, name='listar_pacientes'),
    path('crear/', views.crear_paciente, name='crear_paciente'),
    path('editar/<int:pk>/', views.editar_paciente, name='editar_paciente'),
    path('eliminar/<int:pk>/', views.eliminar_paciente, name='eliminar_paciente'),

    # API REST para autenticación
    path('api/login/', views.LoginApiView.as_view(), name='login_api'),
    path('api/logout/', views.LogoutApiView.as_view(), name='logout_api'),
]
