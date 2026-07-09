from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ajax-drilldown/', views.ajax_drilldown, name='ajax_drilldown'),
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    path('export-excel/', views.export_excel, name='export_excel'),
]
