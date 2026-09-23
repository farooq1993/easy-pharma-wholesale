from django.urls import path
from wholesaleApp.views.purchase_views import (
    po_list,
    po_create,
    po_email_send,
    purchase_entry_list,
    purchase_entry_create,
    purchase_entry_edit,
    purchase_entry_delete,
    purchase_entry_print,
    get_product_details,
    supplier_payment_list,
    supplier_payment_create,
    supplier_payment_delete,
    purchase_return_list,
    purchase_return_create,
    purchase_return_delete,
    scan_purchase_bill,
    check_purchase_invoice_number,
    batch_update_list,
    api_batch_update
)

urlpatterns = [
    # Purchase Orders
    path('purchase/order/list/', po_list, name='po_list'),
    path('purchase/order/create/', po_create, name='po_create'),
    path('purchase/order/<int:pk>/email/', po_email_send, name='po_email_send'),

    # Purchase Entries
    path('purchase/entry/list/', purchase_entry_list, name='purchase_entry_list'),
    path('purchase/entry/create/', purchase_entry_create, name='purchase_entry_create'),
    path('purchase/entry/<int:pk>/edit/', purchase_entry_edit, name='purchase_entry_edit'),
    path('purchase/entry/<int:pk>/delete/', purchase_entry_delete, name='purchase_entry_delete'),
    path('purchase/entry/<int:pk>/print/', purchase_entry_print, name='purchase_entry_print'),

    # Batch Stock Management & Rate/Expiry Correction
    path('purchase/batch-update/', batch_update_list, name='batch_update_list'),

    # Supplier Payments
    path('purchase/payment/list/', supplier_payment_list, name='supplier_payment_list'),
    path('purchase/payment/create/', supplier_payment_create, name='supplier_payment_create'),
    path('purchase/payment/<int:pk>/delete/', supplier_payment_delete, name='supplier_payment_delete'),

    # Purchase Returns
    path('purchase/return/list/', purchase_return_list, name='purchase_return_list'),
    path('purchase/return/create/', purchase_return_create, name='purchase_return_create'),
    path('purchase/return/<int:pk>/delete/', purchase_return_delete, name='purchase_return_delete'),

    # API endpoints
    path('api/product/<int:pk>/details/', get_product_details, name='api_product_details'),
    path('api/purchase/scan-bill/', scan_purchase_bill, name='scan_purchase_bill'),
    path('api/purchase/check-invoice-number/', check_purchase_invoice_number, name='check_purchase_invoice_number'),
    path('api/purchase/batch/<int:pk>/update/', api_batch_update, name='api_batch_update'),
]

