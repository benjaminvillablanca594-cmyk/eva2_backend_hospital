# Hospital · Gestión de Pacientes

Aplicación Django conectada a MySQL para registrar pacientes. Tiene inicio de sesión con token, páginas protegidas y una API REST con Django REST Framework.

Programación Backend · EVA3 · Prof. Eric Railef

## Integrantes y aportes

| Integrante | Rama | Aporte |
|---|---|---|
| Benja | `bejota` | Login y cierre de sesión con token (TokenAuthentication de DRF), protección de páginas y endpoints, mensajes de error de la API, migración inicial y diseño (estilos, íconos, plantilla base y página de login). |

## Cómo ejecutar (Windows + XAMPP)

1. Enciende MySQL en XAMPP. Debe existir la base de datos `hospital`.
2. En la carpeta del proyecto:

```
py -3.12 -m venv venv
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
