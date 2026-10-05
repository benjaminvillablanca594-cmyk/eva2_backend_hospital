from django.shortcuts import render, redirect, get_object_or_404
from .models import Paciente

# --- 1. READ (Listar Pacientes) ---
def listar_pacientes(request):
    # 'Paciente.objects.all()' equivale a "SELECT * FROM paciente" en SQL. Trae todos los registros.
    pacientes = Paciente.objects.all()
    
    # Renderizamos (dibujamos) el HTML 'listar.html' y le pasamos los datos ('pacientes')
    # para que el HTML pueda mostrarlos en la tabla usando un ciclo {% for %}.
    return render(request, 'hospitalapp/listar.html', {'pacientes': pacientes})


# --- 2. CREATE (Crear Paciente) ---
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
def eliminar_paciente(request, pk):
    # Primero encontramos al paciente que queremos borrar.
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == 'POST':
        # Eliminamos permanentemente el registro de la base de datos (equivale a "DELETE FROM..." en SQL).
        paciente.delete()
        return redirect('listar_pacientes')
        
    # Si es GET, mostramos una pantalla de advertencia ("¿Seguro que deseas eliminar a X?")
    return render(request, 'hospitalapp/eliminar.html', {'paciente': paciente})