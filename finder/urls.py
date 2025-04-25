from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.finder_dashboard, name='finder_dashboard'),
    
    # Company search URLs
    path('companies/', views.company_search_list, name='company_search_list'),
    path('companies/<int:search_id>/', views.company_search_detail, name='company_search_detail'),
    path('companies/<int:search_id>/add-to-list/', views.add_companies_to_list, name='add_companies_to_list'),
    path('companies/new/serpapi/', views.serpapi_search, name='serpapi_search'),
    
    # Contact search URLs
    path('contacts/', views.contact_search_list, name='contact_search_list'),
    path('contacts/<int:search_id>/', views.contact_search_detail, name='contact_search_detail'),
    path('contacts/<int:search_id>/add-to-list/', views.add_contacts_to_list, name='add_contacts_to_list'),
    path('contacts/new/webscrape/', views.webscrape_search, name='webscrape_search'),
    path('contacts/new/hunter/', views.hunter_search, name='hunter_search'),
    
    # Email validation URLs
    path('validations/', views.zerobounce_validation_list, name='zerobounce_validation_list'),
    path('validations/<int:batch_id>/', views.zerobounce_validation_detail, name='zerobounce_validation_detail'),
    path('validations/new/', views.zerobounce_validation, name='zerobounce_validation'),
]