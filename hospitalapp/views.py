# --- Herramientas de Django ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# --- Herramientas de Django REST Framework (API) ---

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.authtoken.models import Token

# --- Nuestro modelo ---
from .models import Paciente


# =====================================================================
# PÁGINA DE LOGIN (pública)
# =====================================================================
def login_pagina(request):
    # Solo muestra el formulario. El inicio de sesión real lo hace
    # JavaScript llamando a la API /api/login/ (LoginApiView).
    return render(request, 'hospitalapp/login.html')

# --- 1. READ (Listar Pacientes) ---
@login_required
def listar_pacientes(request):
    # 'Paciente.objects.all()' equivale a "SELECT * FROM paciente" en SQL. Trae todos los registros.
    pacientes = Paciente.objects.all()
    
    # Renderizamos (dibujamos) el HTML 'listar.html' y le pasamos los datos ('pacientes')
    # para que el HTML pueda mostrarlos en la tabla usando un ciclo {% for %}.
    return render(request, 'hospitalapp/listar.html', {'pacientes': pacientes})


# --- 2. CREATE (Crear Paciente) ---
@login_required
def crear_paciente(request):
    # Evaluamos si el usuario hizo clic en "Guardar" (esto envía los datos por el método POST).
    if request.method == 'POST':
        # Capturamos cada dato ingresado en el formulario a través de su atributo 'name="..."'.
        rut = request.POST.get('rut')
        nombre = request.POST.get('nombre_completo')
        edad = request.POST.get('edad')
        email = request.POST.get('email_contacto')
        fecha = request.POST.get('fecha_ingreso')
        estado = request.POST.get('estado')
        
        # 'Paciente.objects.create()' equivale a "INSERT INTO..." en SQL.
        # Guarda el nuevo registro directamente en la base de datos.
        Paciente.objects.create(
            rut=rut, nombre_completo=nombre, edad=edad, 
            email_contacto=email, fecha_ingreso=fecha, estado=estado
        )
        
        # Redirigimos a la vista de la tabla para evitar que, si el usuario recarga, envíe los datos de nuevo.
        return redirect('listar_pacientes')
        
    # Si el método es GET (el usuario solo entró a la URL para ver la página), mostramos el formulario vacío.
    return render(request, 'hospitalapp/crear.html')


# --- 3. UPDATE (Modificar Paciente) ---
# Recibe 'pk' (Primary Key / ID) para saber exactamente qué paciente editar.
@login_required
def editar_paciente(request, pk):
    # get_object_or_404 busca el paciente por su ID. Si no existe (ej: alguien manipula la URL),
    # muestra una página de error "404 No encontrado" en vez de romper el servidor.
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == 'POST':
        # Sobre-escribimos las propiedades del paciente existente con los nuevos datos del formulario.
        paciente.rut = request.POST.get('rut')
        paciente.nombre_completo = request.POST.get('nombre_completo')
        paciente.edad = request.POST.get('edad')
        paciente.email_contacto = request.POST.get('email_contacto')
        paciente.fecha_ingreso = request.POST.get('fecha_ingreso')
        paciente.estado = request.POST.get('estado')
        
        # Guarda las modificaciones (equivale a "UPDATE tabla SET..." en SQL).
        paciente.save() 
        return redirect('listar_pacientes')
        
    # Si es GET, enviamos el 'paciente' encontrado al HTML para rellenar los 'value' de los inputs.
    return render(request, 'hospitalapp/editar.html', {'paciente': paciente})


# --- 4. DELETE (Eliminar Paciente) ---
@login_required
def eliminar_paciente(request, pk):
    # Primero encontramos al paciente que queremos borrar.
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == 'POST':
        # Eliminamos permanentemente el registro de la base de datos (equivale a "DELETE FROM..." en SQL).
        paciente.delete()
        return redirect('listar_pacientes')
        
    # Si es GET, mostramos una pantalla de advertencia ("¿Seguro que deseas eliminar a X?")
    return render(request, 'hospitalapp/eliminar.html', {'paciente': paciente})


# =====================================================================
# API REST: AUTENTICACIÓN CON TOKEN
# =====================================================================
# Largo máximo del usuario y la contraseña (los mismos maxlength de login.html).
# En MySQL, auth_user guarda username como VARCHAR(150) y password como VARCHAR(128).
MAX_USUARIO = 30
MAX_CLAVE = 50

class LoginApiView(APIView):
    """
    Ruta:  POST /api/login/
    Recibe:  {"username": "...", "password": "..."}
    Responde:
      200 -> {"mensaje", "usuario", "token"}   credenciales correctas
      400 -> {"error"}                          faltan datos
      401 -> {"error"}                          usuario o contraseña incorrectos
      429 -> {"error"}                          más de 5 intentos en un minuto
    """

    # El login debe ser público: aún no tenemos token.
    # authentication_classes = [] evita que un token viejo o inválido
    # enviado por error bloquee el login con 401.
    authentication_classes = []
    permission_classes = [AllowAny]

    # SEGURIDAD: máximo 5 intentos por minuto (ver DEFAULT_THROTTLE_RATES
    # en settings.py). Si se supera, DRF responde 429 automáticamente.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):

        # Recibir las credenciales desde el JSON
        username = request.data.get('username')
        password = request.data.get('password')

        # Validar que vengan ambos campos y que sean texto
        if not isinstance(username, str) or not isinstance(password, str) \
                or not username.strip() or not password:
            return Response({
                'error': 'Debes ingresar usuario y contraseña'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validar largo máximo (mismos límites que el formulario)
        if len(username) > MAX_USUARIO or len(password) > MAX_CLAVE:
            return Response({
                'error': f'El usuario puede tener máximo {MAX_USUARIO} caracteres y la contraseña {MAX_CLAVE}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # authenticate() compara la contraseña con el hash guardado en la BD
        usuario = authenticate(username=username, password=password)

        # SEGURIDAD: el mensaje no dice si falló el usuario o la contraseña,
        # así no se puede averiguar qué usuarios existen.
        if usuario is None:
            return Response({
                'error': 'Usuario o contraseña incorrectos'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 1) Token para la API: se crea uno si el usuario no tiene
        token, creado = Token.objects.get_or_create(user=usuario)

        # 2) Sesión de Django para las páginas protegidas con @login_required
        login(request, usuario)

        return Response({
            'mensaje': 'Autenticación correcta',
            'usuario': usuario.username,
            'token': token.key
        }, status=status.HTTP_200_OK)


class LogoutApiView(APIView):
    """
    Ruta:  POST /api/logout/        (requiere token)
    Responde:
      200 -> {"mensaje"}   token borrado y sesión cerrada
      401 -> {"error"}     sin token o token inválido
    """

    # Usa la configuración por defecto: TokenAuthentication + IsAuthenticated.
    # Sin token válido responde 401 automáticamente.

    def post(self, request):

        # Borrar el token en la BD: queda inválido aunque alguien lo haya copiado
        request.user.auth_token.delete()

        # Cerrar también la sesión de Django (páginas web)
        logout(request)

        return Response({
            'mensaje': 'Sesión cerrada correctamente'
        }, status=status.HTTP_200_OK)
