# Hospital · Gestión de Pacientes

Aplicación Django conectada a MySQL para registrar pacientes y seguir su atención: En Espera → Atendido → Derivado o Dado de alta. Tiene inicio de sesión con token, páginas protegidas, una API REST con Django REST Framework y validaciones en el navegador y en el servidor.

Programación Backend · EVA3 · Prof. Eric Railef

## Integrantes y aportes

| Integrante | Rama | Aporte |
|---|---|---|
| Benja | `bejota` | Login y cierre de sesión con token (TokenAuthentication de DRF), protección de páginas y endpoints, mensajes de error de la API, migración inicial y diseño (estilos, íconos, plantilla base y página de login). |
| Compañero | `zut` | Modelos `Paciente` y `Atencion` (FK), migraciones 0002 y 0003, API REST de pacientes con validaciones, formulario compartido y ficha con el avance de la atención. |

## Cómo ejecutar (Windows + XAMPP)

1. Enciende MySQL en XAMPP. Debe existir la base de datos `hospital`.
2. En la carpeta del proyecto:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

3. Abre http://127.0.0.1:8000/ e ingresa con el usuario creado.

## API

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/api/login/` | Recibe usuario y contraseña y devuelve el token |
| POST | `/api/logout/` | Borra el token y cierra la sesión (requiere token) |
| GET | `/api/pacientes/` | Lista los pacientes (filtro opcional `?rut=`) |
| POST | `/api/pacientes/` | Crea un paciente: queda En Espera con su primera atención |
| GET | `/api/pacientes/{id}/` | Consulta un paciente con su historial |
| PUT | `/api/pacientes/{id}/` | Actualiza todos los datos del paciente |
| PATCH | `/api/pacientes/{id}/` | Avanza el estado con el detalle de la atención |
| DELETE | `/api/pacientes/{id}/` | Elimina el paciente y su historial |

Las rutas de pacientes piden el encabezado `Authorization: Token <token>`. Sin token o con uno inválido responden 401.
