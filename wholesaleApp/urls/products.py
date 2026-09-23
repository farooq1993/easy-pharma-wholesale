from django.urls import path
from wholesaleApp.views.products_views import (
    # Company CRUD
    company_list,
    company_create,
    company_edit,
    company_delete,
    # Drug Composition CRUD
    drug_list,
    drug_create,
    drug_edit,
    drug_delete,
    # Product Type CRUD
    type_list,
    type_create,
    type_edit,
    type_delete,
    # Tax Master (GST Slabs) CRUD
    tax_list,
    tax_create,
    tax_edit,
    tax_delete,
    # Schedule Master (Drug Schedules) CRUD
    schedule_list,
    schedule_create,
    schedule_edit,
    schedule_delete,
    # Product CRUD
    product_list,
    product_create,
    product_edit,
    product_delete
)

urlpatterns = [
    # Company Master URLs
    path('company/list/', company_list, name='company_list'),
    path('company/create/', company_create, name='company_create'),
    path('company/edit/<int:pk>/', company_edit, name='company_edit'),
    path('company/delete/<int:pk>/', company_delete, name='company_delete'),

    # Drug Composition Master URLs
    path('drug/list/', drug_list, name='drug_list'),
    path('drug/create/', drug_create, name='drug_create'),
    path('drug/edit/<int:pk>/', drug_edit, name='drug_edit'),
    path('drug/delete/<int:pk>/', drug_delete, name='drug_delete'),

    # Product Type Master URLs
    path('product-type/list/', type_list, name='type_list'),
    path('product-type/create/', type_create, name='type_create'),
    path('product-type/edit/<int:pk>/', type_edit, name='type_edit'),
    path('product-type/delete/<int:pk>/', type_delete, name='type_delete'),

    # Tax Master (GST Slabs) URLs
    path('tax/list/', tax_list, name='tax_list'),
    path('tax/create/', tax_create, name='tax_create'),
    path('tax/edit/<int:pk>/', tax_edit, name='tax_edit'),
    path('tax/delete/<int:pk>/', tax_delete, name='tax_delete'),

    # Schedule Master (Drug Schedules) URLs
    path('schedule/list/', schedule_list, name='schedule_list'),
    path('schedule/create/', schedule_create, name='schedule_create'),
    path('schedule/edit/<int:pk>/', schedule_edit, name='schedule_edit'),
    path('schedule/delete/<int:pk>/', schedule_delete, name='schedule_delete'),

    # Product Master (Item catalog) URLs
    path('product/list/', product_list, name='product_list'),
    path('product/create/', product_create, name='product_create'),
    path('product/edit/<int:pk>/', product_edit, name='product_edit'),
    path('product/delete/<int:pk>/', product_delete, name='product_delete'),
]
