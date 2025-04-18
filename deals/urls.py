from django.urls import path
from . import views


urlpatterns = [
    # Deal URLs
    path('', views.deal_list, name='deal_list'),
    path('results/', views.deal_list_results, name='deal_list_results'),
    path('create/', views.deal_create, name='deal_create'),
    path('<int:deal_id>/', views.deal_detail, name='deal_detail'),
    path('<int:deal_id>/update/', views.deal_update, name='deal_update'),
    path('<int:deal_id>/delete/', views.deal_delete, name='deal_delete'),
    path('<int:deal_id>/win/', views.deal_mark_as_won, name='deal_mark_as_won'),
    path('<int:deal_id>/lose/', views.deal_mark_as_lost, name='deal_mark_as_lost'),
    
    # Deal Stage URLs
    path('stages/', views.stage_list, name='stage_list'),
    path('stages/create/', views.stage_create, name='stage_create'),
    path('stages/<int:stage_id>/', views.stage_detail, name='stage_detail'),
    path('stages/<int:stage_id>/update/', views.stage_update, name='stage_update'),
    path('stages/<int:stage_id>/delete/', views.stage_delete, name='stage_delete'),
    
    # Pipeline URLs
    path('pipeline/', views.pipeline_view, name='pipeline'),
]