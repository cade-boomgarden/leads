from django.contrib import admin
from django.urls import path, include
from companies.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('finder/', include('finder.urls')),
    path('companies/', include('companies.urls')),
    path('contacts/', include('contacts.urls')),
]