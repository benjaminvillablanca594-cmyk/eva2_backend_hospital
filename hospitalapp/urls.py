from django.urls import path
from . import views

urlpatterns = [
    # ------------------------------------------------------------
    # PÁGINAS WEB (HTML)
    # ------------------------------------------------------------
    # Página de login (pública)
    path('', views.login_pagina, name='login_pagina'),

    # Páginas del CRUD (protegidas con @login_required).
    # <int:id> solo acepta números: /editar/abc/ responde 404.
    path('pacientes/', views.listar_pacientes, name='listar_pacientes'),
    path('crear/', views.crear_paciente, name='crear_paciente'),
    path('detalle/<int:id>/', views.detalle_paciente, name='detalle_paciente'),
    path('editar/<int:id>/', views.editar_paciente, name='editar_paciente'),
    path('eliminar/<int:id>/', views.eliminar_paciente, name='eliminar_paciente'),

    # ------------------------------------------------------------
    # API REST (JSON)
    # ------------------------------------------------------------
    # Autenticación: entrega y elimina el token
    path('api/login/', views.LoginApiView.as_view(), name='login_api'),
    path('api/logout/', views.LogoutApiView.as_view(), name='logout_api'),

    # GET (listar) y POST (crear)
    path('api/pacientes/', views.PacientesApiView.as_view(), name='api_pacientes'),

    # GET (consultar), PUT/PATCH (actualizar) y DELETE (eliminar) por ID
    path('api/pacientes/<int:id>/', views.PacienteDetalleApiView.as_view(), name='api_paciente_detalle'),

    # Cualquier otra ruta que empiece con api/ -> 404 en JSON
    # (debe ir AL FINAL: Django revisa las rutas en orden)
    path('api/<path:ruta>', views.api_ruta_no_encontrada, name='api_ruta_no_encontrada'),
]
