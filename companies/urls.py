from django.urls import path
from . import views

urlpatterns = [
    # Company List URLs
    path('lists/', views.company_list_list, name='company_list_list'),
    path('lists/create/', views.company_list_create, name='company_list_create'),
    path('lists/<int:list_id>/', views.company_list_detail, name='company_list_detail'),
    path('lists/<int:list_id>/update/', views.company_list_update, name='company_list_update'),
    path('lists/<int:list_id>/delete/', views.company_list_delete, name='company_list_delete'),
    path('lists/<int:list_id>/export/', views.company_list_export, name='company_list_export'),
    path('lists/<int:list_id>/add-companies/', views.company_list_add_companies, name='company_list_add_companies'),
    path('lists/<int:list_id>/add-search-results/<int:search_id>/', views.company_list_add_search_results, name='company_list_add_search_results'),
    path('lists/<int:list_id>/remove-company/<int:company_id>/', views.company_list_remove_company, name='company_list_remove_company'),
    path('lists/add-from-filter/', views.company_list_add_from_filter, name='company_list_add_from_filter'),
    path('lists/<int:list_id>/remove-multiple/', views.company_list_remove_multiple, name='company_list_remove_multiple'),
    
    # Company URLs
    path('', views.company_list, name='company_list'),
    path('create/', views.company_create, name='company_create'),
    path('<int:company_id>/', views.company_detail, name='company_detail'),
    path('<int:company_id>/update/', views.company_update, name='company_update'),
    path('<int:company_id>/delete/', views.company_delete, name='company_delete'),
]