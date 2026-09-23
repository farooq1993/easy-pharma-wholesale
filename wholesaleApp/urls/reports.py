from django.urls import path
from wholesaleApp.views.reports_views import (
    reports_dashboard,
    report_sales,
    report_expiry,
    report_stock,
    report_outstanding,
    report_company_sales,
    report_customer_sales,
    report_gst,
    report_profit,
    report_profit_loss
)

urlpatterns = [
    path('reports/dashboard/', reports_dashboard, name='reports_dashboard'),
    path('reports/profit/', report_profit, name='report_profit'),
    path('accounts/profit-loss/', report_profit_loss, name='report_profit_loss'),
    path('reports/profit-loss/', report_profit_loss, name='report_profit_loss_alt'),
    path('reports/sales/', report_sales, name='report_sales'),
    path('reports/expiry/', report_expiry, name='report_expiry'),
    path('reports/stock/', report_stock, name='report_stock'),
    path('reports/outstanding/', report_outstanding, name='report_outstanding'),
    path('reports/sales/company/', report_company_sales, name='report_company_sales'),
    path('reports/sales/customer/', report_customer_sales, name='report_customer_sales'),
    path('reports/gst/', report_gst, name='report_gst'),
]

