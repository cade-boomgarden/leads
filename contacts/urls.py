from django.urls import path
from . import views

urlpatterns = [
    # Contact List URLs
    path('lists/', views.contact_list_list, name='contact_list_list'),
    path('lists/create/', views.contact_list_create, name='contact_list_create'),
    path('lists/<int:list_id>/', views.contact_list_detail, name='contact_list_detail'),
    path('lists/<int:list_id>/update/', views.contact_list_update, name='contact_list_update'),
    path('lists/<int:list_id>/delete/', views.contact_list_delete, name='contact_list_delete'),
    path('lists/<int:list_id>/export/', views.contact_list_export, name='contact_list_export'),
    path('lists/<int:list_id>/add-contacts/', views.contact_list_add_contacts, name='contact_list_add_contacts'),
    path('lists/<int:list_id>/add-search-results/<int:search_id>/', views.contact_list_add_search_results, name='contact_list_add_search_results'),
    path('lists/<int:list_id>/remove-contact/<int:contact_id>/', views.contact_list_remove_contact, name='contact_list_remove_contact'),
    path('lists/add-from-filter/', views.contact_list_add_from_filter, name='contact_list_add_from_filter'),
    
    # Contact URLs
    path('', views.contact_list, name='contact_list'),
    path('create/', views.contact_create, name='contact_create'),
    path('<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path('<int:contact_id>/update/', views.contact_update, name='contact_update'),
    path('<int:contact_id>/delete/', views.contact_delete, name='contact_delete'),
    
    # Cohort URLs
    path('cohorts/', views.cohort_list, name='cohort_list'),
    path('cohorts/create/', views.cohort_create, name='cohort_create'),
    path('cohorts/<int:cohort_id>/', views.cohort_detail, name='cohort_detail'),
    path('cohorts/<int:cohort_id>/update/', views.cohort_update, name='cohort_update'),
    path('cohorts/<int:cohort_id>/delete/', views.cohort_delete, name='cohort_delete'),
    path('cohorts/<int:cohort_id>/export/', views.cohort_export, name='cohort_export'),
]