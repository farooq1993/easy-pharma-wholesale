from django.urls import path
from wholesaleApp.views.sales_views import (
    invoice_list,
    invoice_create,
    invoice_edit,
    invoice_delete,
    invoice_print,
    invoice_email_bulk,
    delivery_management,
    get_product_batches,
    get_product_last_purchase_rate,
    get_customer_product_sales_history,
    get_customer_credit_notes,
    sales_return_list,
    sales_return_create,
    sales_return_delete
)

urlpatterns = [
    # Sales Invoicing
    path('sales/invoice/list/', invoice_list, name='invoice_list'),
    path('sales/invoice/create/', invoice_create, name='invoice_create'),
    path('sales/invoice/<int:pk>/edit/', invoice_edit, name='invoice_edit'),
    path('sales/invoice/<int:pk>/delete/', invoice_delete, name='invoice_delete'),
    path('sales/invoice/<int:pk>/print/', invoice_print, name='invoice_print'),
    path('sales/invoice/email-bulk/', invoice_email_bulk, name='invoice_email_bulk'),
    path('sales/delivery-management/', delivery_management, name='delivery_management'),


    # Sales Returns
    path('sales/return/list/', sales_return_list, name='sales_return_list'),
    path('sales/return/create/', sales_return_create, name='sales_return_create'),
    path('sales/return/<int:pk>/delete/', sales_return_delete, name='sales_return_delete'),

    # API batch/rate fetchers
    path('api/product/<int:pk>/batches/', get_product_batches, name='api_product_batches'),
    path('api/product/<int:pk>/last-purchase/', get_product_last_purchase_rate, name='api_product_last_purchase'),
    path('api/customer/<int:customer_id>/product/<int:product_id>/sales-history/', get_customer_product_sales_history, name='api_customer_product_sales_history'),
    path('api/customer/<int:customer_id>/credit-notes/', get_customer_credit_notes, name='api_customer_credit_notes'),
]

