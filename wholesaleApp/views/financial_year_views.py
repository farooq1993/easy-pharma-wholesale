import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from wholesaleApp.models import FinancialYear, SalesInvoice, PurchaseEntry, CustomerPayment, SupplierPayment
from wholesaleApp.models.tenant import get_current_tenant

@login_required
def financial_year_list(request):
    tenant = get_current_tenant()
    if not tenant:
        from wholesaleApp.models.tenant import Tenant
        tenant = Tenant.objects.filter(is_active=True).first()
        
    # Handle creation
    if request.method == 'POST' and 'create_fy' in request.POST:
        name = request.POST.get('name', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not name or not start_date or not end_date:
            messages.error(request, "Please fill in all fields.")
        elif FinancialYear.objects.filter(tenant=tenant, name=name).exists():
            messages.error(request, f"Financial Year '{name}' already exists.")
        else:
            FinancialYear.objects.create(
                tenant=tenant,
                name=name,
                start_date=start_date,
                end_date=end_date,
                is_closed=False
            )
            messages.success(request, f"Financial Year '{name}' created successfully.")
            return redirect('financial_year_list')
            
    years = FinancialYear.objects.filter(tenant=tenant)
    context = {
        'page_title': 'Financial Year Settings & Closure',
        'years': years,
    }
    return render(request, 'settings/financial_year_list.html', context)


@login_required
def financial_year_close(request, pk):
    tenant = get_current_tenant()
    fy = get_object_or_404(FinancialYear, pk=pk, tenant=tenant)
    
    if fy.is_closed:
        messages.info(request, f"Financial Year '{fy.name}' is already closed.")
    else:
        fy.is_closed = True
        fy.closed_at = timezone.now()
        fy.closed_by = request.user
        fy.save()
        messages.success(request, f"Financial Year '{fy.name}' has been successfully closed. All transactions in this period are now locked.")
        
    return redirect('financial_year_list')


@login_required
def archive_dashboard(request):
    tenant = get_current_tenant()
    if not tenant:
        from wholesaleApp.models.tenant import Tenant
        tenant = Tenant.objects.filter(is_active=True).first()
        
    closed_years = FinancialYear.objects.filter(tenant=tenant, is_closed=True)
    selected_year_id = request.GET.get('fy')
    
    selected_year = None
    sales = []
    purchases = []
    customer_payments = []
    supplier_payments = []
    
    if selected_year_id:
        selected_year = get_object_or_404(FinancialYear, id=selected_year_id, tenant=tenant)
    elif closed_years.exists():
        selected_year = closed_years.first()
        
    if selected_year:
        start = selected_year.start_date
        end = selected_year.end_date
        
        sales = SalesInvoice.objects.filter(tenant=tenant, invoice_date__range=[start, end]).order_by('-invoice_date')
        purchases = PurchaseEntry.objects.filter(tenant=tenant, invoice_date__range=[start, end]).order_by('-invoice_date')
        customer_payments = CustomerPayment.objects.filter(tenant=tenant, payment_date__range=[start, end]).order_by('-payment_date')
        supplier_payments = SupplierPayment.objects.filter(tenant=tenant, payment_date__range=[start, end]).order_by('-payment_date')
        
    context = {
        'page_title': 'Yearly Historical Archives',
        'closed_years': closed_years,
        'selected_year': selected_year,
        'sales': sales,
        'purchases': purchases,
        'customer_payments': customer_payments,
        'supplier_payments': supplier_payments,
    }
    return render(request, 'archive/archive_dashboard.html', context)
