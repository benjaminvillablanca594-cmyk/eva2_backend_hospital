# =====================================================================
# MENSAJES DE ERROR DE LA API (en español y con un formato único)
# ---------------------------------------------------------------------
# Django REST Framework responde algunos errores automáticamente
# (por ejemplo, cuando falta el token). Por defecto esos mensajes vienen
# en la clave "detail" y no siempre son claros.
#
# Esta función se conecta en settings.py:
#     REST_FRAMEWORK = { 'EXCEPTION_HANDLER': 'hospitalapp.api_errores.manejador_errores_api' }
#
# Así TODAS las respuestas de error de la API tienen la misma forma:
#     { "error": "mensaje claro de lo que pasó" }
# =====================================================================
from django.db import DatabaseError
from django.http import Http404

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def manejador_errores_api(exc, context):
    """
    Recibe el error (exc) que ocurrió en una vista de la API y
    devuelve la respuesta JSON que verá el cliente.
    """

    # -----------------------------------------------------------------
    # Caso especial: la base de datos no responde (ej: MySQL apagado).
    # Sin esto, Django mostraría una página HTML de error 500.
    # -----------------------------------------------------------------
    if isinstance(exc, DatabaseError):
        return Response({
            'error': 'No se pudo conectar con la base de datos. Verifica que MySQL (XAMPP) esté encendido.'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # 1. DRF arma su respuesta normal (con el código HTTP correcto)
    respuesta = exception_handler(exc, context)

    # Si DRF no reconoce el error, se deja que Django lo maneje
    if respuesta is None:
        return None

    # 2. Reemplazamos el mensaje por uno claro según el tipo de error
    if isinstance(exc, exceptions.NotAuthenticated):
        # 401: no se envió el encabezado Authorization
        mensaje = 'No se envió el token. Inicia sesión y envía el encabezado "Authorization: Token <clave>".'

    elif isinstance(exc, exceptions.AuthenticationFailed):
        # 401: se envió un token, pero no existe (inventado o borrado al cerrar sesión)
        mensaje = 'Token inválido o expirado. Vuelve a iniciar sesión para obtener uno nuevo.'

    elif isinstance(exc, exceptions.PermissionDenied):
        # 403: autenticado, pero sin permiso
        mensaje = 'No tienes permiso para realizar esta acción.'

    elif isinstance(exc, exceptions.Throttled):
        # 429: demasiados intentos de login (ver DEFAULT_THROTTLE_RATES)
        segundos = int(exc.wait) if exc.wait else 60
        mensaje = f'Demasiados intentos de inicio de sesión. Espera {segundos} segundos e inténtalo de nuevo.'

    elif isinstance(exc, exceptions.ParseError):
        # 400: el cuerpo no es un JSON válido (falta una comilla, una coma, etc.)
        mensaje = 'El cuerpo de la solicitud no es un JSON válido. Revisa comillas, comas y llaves.'

    elif isinstance(exc, exceptions.UnsupportedMediaType):
        # 415: los datos no vienen en JSON
        mensaje = 'Formato no soportado. Envía los datos en JSON (Content-Type: application/json).'

    elif isinstance(exc, exceptions.MethodNotAllowed):
        # 405: ej. hacer POST sobre /api/pacientes/5/
        mensaje = f'El método {context["request"].method} no está permitido en esta ruta.'

    elif isinstance(exc, (exceptions.NotFound, Http404)):
        # 404: el recurso no existe
        mensaje = 'El recurso solicitado no existe.'

    else:
        mensaje = 'No se pudo procesar la solicitud.'

    respuesta.data = {'error': mensaje}
    return respuesta
