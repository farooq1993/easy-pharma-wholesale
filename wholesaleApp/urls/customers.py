from django.urls import path
from wholesaleApp.views.customers_views import (
    customer_list,
    customer_create,
    customer_edit,
    customer_delete,
    area_list,
    area_create,
    area_edit,
    area_delete,
    subarea_create,
    subarea_edit,
    subarea_delete,
    customer_ledger,
    customer_payment_add,
    customer_payment_delete,
    customer_payment_list,
    customer_payment_create,
    customer_payment_edit,
    get_customer_outstanding_invoices,
    customer_manage,
    get_customer_manage_details
)

urlpatterns = [
    path("customer/list/", customer_list, name='customer_list'),
    path("customer/manage/<int:pk>/", customer_manage, name='customer_manage'),
    path("api/customer/<int:customer_id>/manage-details/", get_customer_manage_details, name='api_customer_manage_details'),
    path("customer/payment/list/", customer_payment_list, name='customer_payment_list'),
    path("customer/payment/create/", customer_payment_create, name='customer_payment_create'),
    path("customer/payment/edit/<int:pk>/", customer_payment_edit, name='customer_payment_edit'),
    path("api/customer/<int:customer_id>/outstanding-invoices/", get_customer_outstanding_invoices, name='api_customer_outstanding_invoices'),


    path("customer/create/", customer_create, name='createcustomer'),
    path("customer/edit/<int:pk>/", customer_edit, name='customer_edit'),
    path("customer/delete/<int:pk>/", customer_delete, name='customer_delete'),
    
    path("customer/ledger/", customer_ledger, name='customer_ledger'),
    path("customer/payment/add/", customer_payment_add, name='customer_payment_add'),
    path("customer/payment/delete/<int:pk>/", customer_payment_delete, name='customer_payment_delete'),
    
    # Area Master
    path("area/list/", area_list, name='area_list'),
    path("area/create/", area_create, name='area_create'),
    path("area/edit/<int:pk>/", area_edit, name='area_edit'),
    path("area/delete/<int:pk>/", area_delete, name='area_delete'),
    
    # Subarea Master
    path("subarea/create/", subarea_create, name='subarea_create'),
    path("subarea/edit/<int:pk>/", subarea_edit, name='subarea_edit'),
    path("subarea/delete/<int:pk>/", subarea_delete, name='subarea_delete'),
]