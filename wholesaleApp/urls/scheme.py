from django.urls import path
from wholesaleApp.views.scheme_views import (
    scheme_list,
    scheme_create,
    scheme_edit,
    scheme_delete
)

urlpatterns = [
    path('scheme/list/', scheme_list, name='scheme_list'),
    path('scheme/create/', scheme_create, name='scheme_create'),
    path('scheme/<int:pk>/edit/', scheme_edit, name='scheme_edit'),
    path('scheme/<int:pk>/delete/', scheme_delete, name='scheme_delete'),
]
