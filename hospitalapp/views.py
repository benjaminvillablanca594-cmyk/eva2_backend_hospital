# =====================================================================
# IMPORTACIONES
# =====================================================================
import re                      # expresiones regulares (validar RUT, nombre y teléfono)
from datetime import date      # convertir texto "AAAA-MM-DD" a fecha

# --- Herramientas de Django ---
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Value
from django.db.models.functions import Replace, Upper
from django.utils import timezone

# --- Herramientas de Django REST Framework (API) ---
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.authtoken.models import Token

# --- Nuestros modelos ---
from .models import Paciente, Atencion


# =====================================================================
# PÁGINA DE LOGIN (pública)
# =====================================================================
def login_pagina(request):
    # Solo muestra el formulario. El inicio de sesión real lo hace
    # JavaScript llamando a la API /api/login/ (LoginApiView).
    return render(request, 'hospitalapp/login.html')


# =====================================================================
# PÁGINAS DEL CRUD (protegidas con @login_required)
# Igual que en el proyecto del profesor, estas vistas solo muestran el
# HTML. Los datos los obtiene JavaScript desde la API enviando el token.
# @login_required: si no hay sesión iniciada, redirige al login.
# =====================================================================
@login_required
def listar_pacientes(request):
    return render(request, 'hospitalapp/listar.html')


@login_required
def crear_paciente(request):
    return render(request, 'hospitalapp/crear.html')


@login_required
def detalle_paciente(request, id):
    # Enviamos el id al HTML para que JavaScript sepa qué paciente consultar
    return render(request, 'hospitalapp/detalle.html', {'id': id})


@login_required
def editar_paciente(request, id):
    return render(request, 'hospitalapp/editar.html', {'id': id})


@login_required
def eliminar_paciente(request, id):
    return render(request, 'hospitalapp/eliminar.html', {'id': id})


# =====================================================================
# LÍMITES Y REGLAS DE VALIDACIÓN
# Los mismos límites están en los formularios HTML (maxlength):
# el navegador no deja escribir más, y la API rechaza lo que se pase.
# =====================================================================
MAX_RUT = 10            # 8 números + guion + dígito verificador
MIN_NOMBRE = 3
MAX_NOMBRE = 50
MAX_EMAIL = 70
MIN_DETALLE = 10
MAX_DETALLE = 300       # igual que max_length de Atencion.detalle
EDAD_MAXIMA = 120
FECHA_MINIMA = date(1900, 1, 1)

# Estados válidos, tomados del modelo
ESTADOS_VALIDOS = [opcion[0] for opcion in Paciente.ESTADOS]
ESTADO_INICIAL = 'En Espera'

# FLUJO DE ATENCIÓN: a qué estados se puede pasar desde cada uno.
#   En Espera -> Atendido -> Derivado      (se envía a otro servicio)
#                         -> Dado de alta  (se va a su casa)
# Derivado y Dado de alta no tienen siguiente: la atención queda cerrada.
SIGUIENTES_ESTADOS = {
    'En Espera': ['Atendido'],
    'Atendido': ['Derivado', 'Dado de alta'],
    'Derivado': [],
    'Dado de alta': [],
}

# RUT: solo números, guion y K. Formato: 7 u 8 números, guion y dígito verificador
CARACTERES_RUT = re.compile(r'^[0-9K-]+$')
PATRON_RUT = re.compile(r'^\d{7,8}-[\dK]$')

# Nombre: solo letras (con tildes y ñ), espacios, apóstrofo y guion
PATRON_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]+$")

# Teléfono: se aceptan números, espacios y el signo +
CARACTERES_TELEFONO = re.compile(r'^[0-9+ ]+$')


# =====================================================================
# FUNCIONES DE APOYO
# =====================================================================
def siguientes_estados(estado_actual):
    # Estados a los que puede pasar el paciente. Lista vacía = atención cerrada.
    return SIGUIENTES_ESTADOS.get(estado_actual, [])


def texto_opciones(opciones):
    # ['Derivado', 'Dado de alta'] -> '"Derivado" o "Dado de alta"'
    return ' o '.join(f'"{opcion}"' for opcion in opciones)


def mensaje_cerrada(estado):
    # Mensaje cuando el paciente ya terminó su atención
    motivo = 'fue derivado' if estado == 'Derivado' else 'fue dado de alta'
    return f'El paciente ya {motivo}: su atención está cerrada.'


def atencion_a_dict(atencion):
    # Una fila del historial de atención en formato JSON
    return {
        'estado': atencion.estado,
        'detalle': atencion.detalle,
        'fecha': timezone.localtime(atencion.fecha).strftime('%Y-%m-%d %H:%M'),
        'registrado_por': atencion.registrado_por.username if atencion.registrado_por else None,
    }


def paciente_a_dict(paciente, con_historial=False):
    # Convierte un objeto Paciente en un diccionario.
    # DRF transforma ese diccionario en JSON al responder.
    datos = {
        'id': paciente.id,
        'rut': paciente.rut,
        'nombre_completo': paciente.nombre_completo,
        'fecha_nacimiento': paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else None,
        'edad': paciente.edad,                                  # calculada en el modelo
        'email_contacto': paciente.email_contacto,
        'telefono': paciente.telefono,
        'fecha_ingreso': paciente.fecha_ingreso.isoformat(),    # "AAAA-MM-DD"
        'estado': paciente.estado,
        'siguientes_estados': siguientes_estados(paciente.estado),  # para la pantalla de atención
    }
    if con_historial:
        # paciente.atenciones existe gracias a related_name en la FK
        datos['historial'] = [atencion_a_dict(a) for a in paciente.atenciones.all()]
    return datos


def calcular_dv(cuerpo):
    """
    Calcula el dígito verificador de un RUT chileno (algoritmo módulo 11).
    Ejemplo: calcular_dv('12345678') -> '5'
    """
    # Cada dígito (de derecha a izquierda) se multiplica por 2,3,4,5,6,7,2,3...
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1

    # El dígito verificador sale del resto de dividir la suma por 11
    resto = 11 - (suma % 11)
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)


def pacientes_con_rut(rut):
    """
    Busca pacientes con ese RUT comparando SIN puntos y en mayúscula.
    Así "22.222.222-2" (guardado en la EVA2) y "22222222-2" cuentan como el mismo.
    Replace y Upper se ejecutan en la base de datos (SQL REPLACE y UPPER).
    """
    return Paciente.objects.annotate(
        rut_normalizado=Upper(Replace('rut', Value('.'), Value('')))
    ).filter(rut_normalizado=rut)


def restar_anios(fecha, anios):
    # Resta años a una fecha (el 29 de febrero pasa a 28 si el año no es bisiesto)
    try:
        return fecha.replace(year=fecha.year - anios)
    except ValueError:
        return fecha.replace(year=fecha.year - anios, day=28)


def leer_fecha(valor):
    # Convierte "AAAA-MM-DD" en fecha. Devuelve None si el formato no es válido.
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        return None


def validar_paciente(datos, paciente=None, parcial=False):
    """
    Valida los DATOS DEL PACIENTE que llegan a la API antes de guardarlos.

    - paciente: el paciente que se está editando (None al crear).
    - parcial=True (PATCH): solo valida los campos que vienen.

    Devuelve (limpios, errores):
      limpios -> datos ya validados y listos para guardar
      errores -> diccionario {campo: mensaje}. Si está vacío, todo está bien.
    """
    limpios = {}
    errores = {}
    hoy = timezone.localdate()          # fecha de hoy en Chile (TIME_ZONE en settings)

    # El cuerpo debe ser un objeto JSON: { ... }
    if not isinstance(datos, dict):
        return limpios, {'general': 'Se esperaba un objeto JSON.'}

    def debe_validar(campo):
        # En PATCH se saltan los campos que no fueron enviados
        return not (parcial and campo not in datos)

    def vacio(valor):
        # Vacío = no viene, viene null o es un texto con solo espacios
        return valor is None or (isinstance(valor, str) and not valor.strip())

    # ---------------- RUT ----------------
    # Reglas: obligatorio, solo números/guion/K, máximo 10 caracteres,
    # formato 12345678-5, dígito verificador correcto y NO repetido.
    if debe_validar('rut'):
        rut = datos.get('rut')
        if vacio(rut):
            errores['rut'] = 'El RUT es obligatorio.'
        elif not isinstance(rut, str):
            errores['rut'] = 'El RUT debe ser texto.'
        else:
            rut = rut.strip().upper()
            if not CARACTERES_RUT.match(rut):
                errores['rut'] = 'El RUT solo puede contener números, el guion (-) y la letra K (sin puntos).'
            elif len(rut) > MAX_RUT:
                errores['rut'] = f'El RUT puede tener máximo {MAX_RUT} caracteres.'
            elif not PATRON_RUT.match(rut):
                errores['rut'] = 'Formato de RUT inválido. Debe ser 7 u 8 números, guion y dígito verificador (ej: 12345678-5).'
            elif calcular_dv(rut.split('-')[0]) != rut.split('-')[1]:
                errores['rut'] = 'RUT inválido: el dígito verificador no corresponde.'
            else:
                # REGLA DE NEGOCIO: no pueden existir dos pacientes con el mismo RUT.
                # Al editar se excluye el propio paciente.
                repetidos = pacientes_con_rut(rut)
                if paciente is not None:
                    repetidos = repetidos.exclude(id=paciente.id)
                if repetidos.exists():
                    errores['rut'] = 'RUT inválido: ya existe un paciente registrado con este RUT.'
                else:
                    limpios['rut'] = rut

    # ---------------- NOMBRE ----------------
    if debe_validar('nombre_completo'):
        nombre = datos.get('nombre_completo')
        if vacio(nombre):
            errores['nombre_completo'] = 'El nombre es obligatorio.'
        elif not isinstance(nombre, str):
            errores['nombre_completo'] = 'El nombre debe ser texto.'
        else:
            nombre = ' '.join(nombre.split())  # quita espacios repetidos
            if len(nombre) < MIN_NOMBRE or len(nombre) > MAX_NOMBRE:
                errores['nombre_completo'] = f'El nombre debe tener entre {MIN_NOMBRE} y {MAX_NOMBRE} caracteres.'
            elif not PATRON_NOMBRE.match(nombre):
                errores['nombre_completo'] = 'El nombre solo puede contener letras y espacios (sin números ni símbolos).'
            else:
                limpios['nombre_completo'] = nombre

    # ---------------- FECHA DE INGRESO ----------------
    # (se valida antes que la de nacimiento porque se comparan entre sí)
    if debe_validar('fecha_ingreso'):
        valor = datos.get('fecha_ingreso')
        fecha = None if vacio(valor) else leer_fecha(valor)
        if vacio(valor):
            errores['fecha_ingreso'] = 'La fecha de ingreso es obligatoria.'
        elif fecha is None:
            errores['fecha_ingreso'] = 'Fecha inválida. Usa el formato AAAA-MM-DD.'
        elif fecha > hoy:
            errores['fecha_ingreso'] = 'La fecha de ingreso no puede ser futura.'
        elif fecha < FECHA_MINIMA:
            errores['fecha_ingreso'] = 'La fecha de ingreso no puede ser anterior a 01-01-1900.'
        else:
            limpios['fecha_ingreso'] = fecha

    # ---------------- FECHA DE NACIMIENTO (reemplaza a la edad) ----------------
    if debe_validar('fecha_nacimiento'):
        valor = datos.get('fecha_nacimiento')
        fecha = None if vacio(valor) else leer_fecha(valor)

        # Fecha de ingreso con la que se compara: la nueva o la que ya tenía
        ingreso = limpios.get('fecha_ingreso') or (paciente.fecha_ingreso if paciente else None)

        if vacio(valor):
            errores['fecha_nacimiento'] = 'La fecha de nacimiento es obligatoria.'
        elif fecha is None:
            errores['fecha_nacimiento'] = 'Fecha inválida. Usa el formato AAAA-MM-DD.'
        elif fecha > hoy:
            errores['fecha_nacimiento'] = 'La fecha de nacimiento no puede ser futura.'
        elif fecha < restar_anios(hoy, EDAD_MAXIMA):
            errores['fecha_nacimiento'] = f'La edad no puede superar los {EDAD_MAXIMA} años.'
        # REGLA DE NEGOCIO: nadie puede ingresar al hospital antes de nacer
        elif ingreso and fecha > ingreso:
            errores['fecha_nacimiento'] = 'La fecha de nacimiento no puede ser posterior a la fecha de ingreso.'
        else:
            limpios['fecha_nacimiento'] = fecha

    # ---------------- EMAIL ----------------
    if debe_validar('email_contacto'):
        email = datos.get('email_contacto')
        if vacio(email):
            errores['email_contacto'] = 'El email es obligatorio.'
        elif not isinstance(email, str) or len(email.strip()) > MAX_EMAIL:
            errores['email_contacto'] = f'El email debe ser texto de máximo {MAX_EMAIL} caracteres.'
        else:
            email = email.strip().lower()
            # validate_email es el mismo validador que usa EmailField de Django
            try:
                validate_email(email)
                limpios['email_contacto'] = email
            except ValidationError:
                errores['email_contacto'] = 'El email no tiene un formato válido (ej: nombre@dominio.cl).'

    # ---------------- TELÉFONO ----------------
    # Se aceptan "+56 9 1234 5678", "912345678" o "56912345678".
    # Se guarda siempre como "+56912345678".
    if debe_validar('telefono'):
        telefono = datos.get('telefono')
        if vacio(telefono):
            errores['telefono'] = 'El teléfono es obligatorio.'
        elif not isinstance(telefono, str) or not CARACTERES_TELEFONO.match(telefono.strip()):
            errores['telefono'] = 'El teléfono solo puede contener números, espacios y el signo +.'
        else:
            numero = telefono.replace(' ', '')
            if numero.startswith('+56'):
                numero = numero[3:]
            elif numero.startswith('56') and len(numero) == 11:
                numero = numero[2:]
            # 9 dígitos: celulares empiezan con 9, teléfonos fijos con 2 a 8
            if not re.fullmatch(r'[2-9]\d{8}', numero):
                errores['telefono'] = 'Teléfono inválido: deben ser 9 dígitos (ej: +56 9 1234 5678).'
            else:
                limpios['telefono'] = '+56' + numero

    # ---------------- REGLA CRUZADA (PATCH) ----------------
    # Si solo se cambia la fecha de ingreso, se compara con la fecha de
    # nacimiento que el paciente ya tenía guardada.
    if ('fecha_ingreso' in limpios and 'fecha_nacimiento' not in datos
            and paciente is not None and paciente.fecha_nacimiento
            and paciente.fecha_nacimiento > limpios['fecha_ingreso']):
        errores['fecha_ingreso'] = 'La fecha de ingreso no puede ser anterior a la fecha de nacimiento.'
        del limpios['fecha_ingreso']

    return limpios, errores


def validar_atencion(datos, paciente=None):
    """
    Valida el ESTADO y el DETALLE DE ATENCIÓN.

    REGLAS DE NEGOCIO:
      - Todo paciente nuevo ingresa "En Espera" con un detalle (motivo de ingreso).
      - El estado solo avanza en orden:
            En Espera -> Atendido -> Derivado o Dado de alta
      - Cada cambio de estado exige escribir el detalle de la atención.
      - "Derivado" y "Dado de alta" cierran la atención.

    Devuelve (nuevo_estado, detalle, errores). nuevo_estado es None si no cambia.
    """
    errores = {}
    if not isinstance(datos, dict):
        return None, None, {}

    estado = datos.get('estado')
    detalle = datos.get('detalle_atencion')

    # ---- ¿Hay cambio de estado? ----
    if paciente is None:
        # CREAR: el estado siempre es "En Espera"
        if estado not in (None, '', ESTADO_INICIAL):
            errores['estado'] = f'Todo paciente nuevo ingresa con estado "{ESTADO_INICIAL}".'
        nuevo_estado = ESTADO_INICIAL
    elif estado in (None, '') or estado == paciente.estado:
        # EDITAR sin cambiar el estado: no se registra atención
        if not (detalle is None or (isinstance(detalle, str) and not detalle.strip())):
            opciones = siguientes_estados(paciente.estado)
            errores['detalle_atencion'] = (
                f'El detalle se registra al avanzar de estado. Puede pasar a: {texto_opciones(opciones)}.'
                if opciones else mensaje_cerrada(paciente.estado)
            )
        return None, None, errores
    elif estado not in ESTADOS_VALIDOS:
        errores['estado'] = 'Estado inválido. Debe ser: ' + ', '.join(ESTADOS_VALIDOS) + '.'
        return None, None, errores
    else:
        opciones = siguientes_estados(paciente.estado)
        if not opciones:
            errores['estado'] = mensaje_cerrada(paciente.estado)
        elif estado not in opciones:
            errores['estado'] = (f'Desde "{paciente.estado}" solo puede pasar a {texto_opciones(opciones)}. '
                                 'Orden: En Espera -> Atendido -> Derivado o Dado de alta.')
        nuevo_estado = estado

    # ---- El detalle es obligatorio al ingresar y en cada cambio de estado ----
    if detalle is None or (isinstance(detalle, str) and not detalle.strip()):
        errores['detalle_atencion'] = 'Debes escribir el detalle de la atención.'
    elif not isinstance(detalle, str):
        errores['detalle_atencion'] = 'El detalle debe ser texto.'
    else:
        detalle = ' '.join(detalle.split())
        if len(detalle) < MIN_DETALLE or len(detalle) > MAX_DETALLE:
            errores['detalle_atencion'] = f'El detalle debe tener entre {MIN_DETALLE} y {MAX_DETALLE} caracteres.'

    return nuevo_estado, detalle, errores


def buscar_paciente(id):
    # Busca un paciente por id. Devuelve None si no existe
    # (así podemos responder un 404 con mensaje claro en español).
    return Paciente.objects.filter(id=id).first()


def respuesta_no_encontrado():
    # Respuesta común cuando el id no existe: HTTP 404 Not Found
    return Response({
        'error': 'Paciente no encontrado'
    }, status=status.HTTP_404_NOT_FOUND)


def respuesta_errores(errores):
    # Respuesta común para datos inválidos: HTTP 400 Bad Request.
    # 'error' es el mensaje general; 'errores' trae el detalle por campo.
    return Response({
        'error': 'Datos inválidos. Revisa los campos indicados.',
        'errores': errores
    }, status=status.HTTP_400_BAD_REQUEST)


def respuesta_rut_repetido():
    # Si dos personas guardan el mismo RUT al mismo tiempo, la restricción
    # UNIQUE de MySQL lo impide (IntegrityError). Respondemos igual de claro.
    return respuesta_errores({'rut': 'RUT inválido: ya existe un paciente registrado con este RUT.'})


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


# =====================================================================
# API REST: PACIENTES
# Solo usuarios con token válido (TokenAuthentication + IsAuthenticated).
#   - Sin token o token inválido -> 401 automático (DRF)
# =====================================================================
class PacientesApiView(APIView):
    """
    Ruta:  /api/pacientes/          (requiere token)
      GET  -> 200: lista de pacientes en JSON
              (opcional ?rut=12345678-5 para buscar por RUT)
      POST -> 201: {"mensaje", "paciente"}   paciente creado "En Espera"
              400: {"error", "errores"}      datos inválidos (detalle por campo)
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # GET /api/pacientes/ : listar todos los pacientes
    def get(self, request):
        pacientes = Paciente.objects.all().order_by('id')

        # Filtro opcional por RUT: lo usa el formulario para avisar si ya existe
        rut = request.query_params.get('rut')
        if rut:
            pacientes = pacientes_con_rut(rut.strip().replace('.', '').upper()).order_by('id')

        datos = [paciente_a_dict(p) for p in pacientes]
        return Response(datos, status=status.HTTP_200_OK)

    # POST /api/pacientes/ : crear un paciente nuevo
    def post(self, request):
        # 1. Validar los datos del paciente y el detalle de atención
        limpios, errores = validar_paciente(request.data)
        estado, detalle, errores_atencion = validar_atencion(request.data)
        errores.update(errores_atencion)

        # 2. Si hay errores, NO se guarda nada y respondemos 400
        if errores:
            return respuesta_errores(errores)

        try:
            # 3. transaction.atomic: se guardan el paciente Y su primera atención,
            #    o no se guarda nada (si algo falla, MySQL deshace todo).
            with transaction.atomic():
                paciente = Paciente.objects.create(estado=estado, **limpios)   # INSERT paciente
                Atencion.objects.create(                                        # INSERT atención
                    paciente=paciente, estado=estado, detalle=detalle, registrado_por=request.user
                )
        except IntegrityError:
            return respuesta_rut_repetido()

        # 4. Responder 201 Created con el paciente creado
        return Response({
            'mensaje': 'Paciente creado correctamente',
            'paciente': paciente_a_dict(paciente, con_historial=True)
        }, status=status.HTTP_201_CREATED)


class PacienteDetalleApiView(APIView):
    """
    Ruta:  /api/pacientes/{id}/     (requiere token)
      GET    -> 200: datos del paciente + historial de atención
      PUT    -> 200: actualiza TODOS los datos del paciente
      PATCH  -> 200: actualiza SOLO lo enviado. Se usa para avanzar el estado:
                     {"estado": "Atendido", "detalle_atencion": "..."}
      DELETE -> 200: elimina al paciente (y su historial)
    Errores: 400 datos inválidos · 404 el id no existe · 401 sin token
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # GET /api/pacientes/<id>/ : consultar un paciente por ID
    def get(self, request, id):
        paciente = buscar_paciente(id)
        if paciente is None:
            return respuesta_no_encontrado()
        return Response(paciente_a_dict(paciente, con_historial=True), status=status.HTTP_200_OK)

    # Lógica común de PUT y PATCH
    def actualizar(self, request, id, parcial):
        paciente = buscar_paciente(id)
        if paciente is None:
            return respuesta_no_encontrado()

        # Validar datos del paciente y, si cambia el estado, el detalle de atención
        limpios, errores = validar_paciente(request.data, paciente=paciente, parcial=parcial)
        nuevo_estado, detalle, errores_atencion = validar_atencion(request.data, paciente=paciente)
        errores.update(errores_atencion)
        if errores:
            return respuesta_errores(errores)

        if not limpios and not nuevo_estado:
            return Response({
                'error': 'No se envió ningún campo válido para actualizar.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Asignar cada dato validado y guardar (UPDATE ...)
                for campo, valor in limpios.items():
                    setattr(paciente, campo, valor)

                # Si avanza el estado, se registra la atención en el historial
                if nuevo_estado:
                    paciente.estado = nuevo_estado
                    Atencion.objects.create(
                        paciente=paciente, estado=nuevo_estado, detalle=detalle, registrado_por=request.user
                    )
                paciente.save()
        except IntegrityError:
            return respuesta_rut_repetido()

        mensaje = (f'Estado actualizado a "{nuevo_estado}"' if nuevo_estado
                   else 'Paciente actualizado correctamente')
        return Response({
            'mensaje': mensaje,
            'paciente': paciente_a_dict(paciente, con_historial=True)
        }, status=status.HTTP_200_OK)

    # PUT /api/pacientes/<id>/ : actualizar TODOS los datos del paciente
    def put(self, request, id):
        return self.actualizar(request, id, parcial=False)

    # PATCH /api/pacientes/<id>/ : actualizar SOLO lo enviado (ej: avanzar el estado)
    def patch(self, request, id):
        return self.actualizar(request, id, parcial=True)

    # DELETE /api/pacientes/<id>/ : eliminar un paciente
    def delete(self, request, id):
        paciente = buscar_paciente(id)
        if paciente is None:
            return respuesta_no_encontrado()

        # Guardamos los datos ANTES de borrar, para informar qué se eliminó
        datos_eliminados = paciente_a_dict(paciente)
        paciente.delete()  # DELETE FROM ... (CASCADE borra también su historial)

        # 200 OK con mensaje de confirmación.
        # (204 No Content también es válido, pero no permite enviar mensaje)
        return Response({
            'mensaje': 'Paciente eliminado correctamente',
            'paciente': datos_eliminados
        }, status=status.HTTP_200_OK)


# =====================================================================
# RUTA DE LA API QUE NO EXISTE (ej: /api/medicos/ o /api/pacientes/abc/)
# Sin esto Django respondería una página HTML. Así la API siempre
# responde en JSON, con un mensaje claro.
# =====================================================================
def api_ruta_no_encontrada(request, ruta=None):
    # Error común en Postman: olvidar la barra final (/api/pacientes en vez de /api/pacientes/)
    if not request.path.endswith('/'):
        mensaje = f'La ruta {request.path} no existe. ¿Falta la barra final? Prueba con {request.path}/'
    else:
        mensaje = (f'La ruta {request.path} no existe en la API. Rutas disponibles: '
                   '/api/login/, /api/logout/, /api/pacientes/ y /api/pacientes/{id}/')
    return JsonResponse({'error': mensaje}, status=404)
