from django.urls import path
from wholesaleApp.views.financial_year_views import (
    financial_year_list,
    financial_year_close,
    archive_dashboard
)

urlpatterns = [
    path('settings/financial-years/', financial_year_list, name='financial_year_list'),
    path('settings/financial-years/close/<int:pk>/', financial_year_close, name='financial_year_close'),
    path('archive/', archive_dashboard, name='archive_dashboard'),
]
