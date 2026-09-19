from django.urls import path
from wholesaleApp.views.supplier_views import (
    supplier_list,
    supplier_create,
    supplier_edit,
    supplier_delete,
    api_gst_lookup
)

urlpatterns = [
    path('supplier/list/', supplier_list, name='supplier_list'),
    path('supplier/create/', supplier_create, name='supplier_create'),
    path('supplier/edit/<int:pk>/', supplier_edit, name='supplier_edit'),
    path('supplier/delete/<int:pk>/', supplier_delete, name='supplier_delete'),
    path('api/gst-lookup/', api_gst_lookup, name='api_gst_lookup'),
]
