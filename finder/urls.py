from django.urls import path
from . import views

urlpatterns = [
    # Company search URLs
    path('serpapi/', views.serpapi_search, name='serpapi_search'),
    path('searches/', views.search_list, name='search_list'),
    path('searches/<int:search_id>/', views.search_detail, name='search_detail'),
    
    # Contact search URLs
    path('webscrape/', views.webscrape_search, name='webscrape_search'),
    path('contact-searches/', views.contact_search_list, name='contact_search_list'),
    path('contact-searches/<int:search_id>/', views.contact_search_detail, name='contact_search_detail'),
]