from django.urls import path
from . import views

urlpatterns = [
    path('serpapi/', views.serpapi_search, name='serpapi_search'),
    path('searches/', views.search_list, name='search_list'),
    path('searches/<int:search_id>/', views.search_detail, name='search_detail'),
]