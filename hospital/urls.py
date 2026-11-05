from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Esta línea le dice a Django que envíe todo el tráfico web a tu aplicación hospitalapp
    path('', include('hospitalapp.urls')), 
]