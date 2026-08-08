import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from decimal import Decimal
import datetime
from wholesaleApp.models import SalesInvoice, PurchaseEntry, CustomerPayment, SupplierPayment
from wholesaleApp.models.tenant import get_current_tenant

@login_required
def tally_dashboard(request):
    tenant = get_current_tenant()
    if not tenant:
        from wholesaleApp.models.tenant import Tenant
        tenant = Tenant.objects.filter(is_active=True).first()
        
    # Check if the Tally Export module has been enabled for this tenant/firm
    is_enabled = tenant.tally_export_enabled if tenant else False
    
    if request.method == 'POST' and 'activate_demo' in request.POST:
        # Allow superusers or tenant owners to toggle demo mode for trial purposes
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_tenant_admin):
            tenant.tally_export_enabled = True
            tenant.save()
            messages.success(request, "Tally Integration Module successfully activated (Developer Trial Mode)!")
            return redirect('tally_dashboard')
            
    context = {
        'page_title': 'Tally Accounting Integration',
        'is_enabled': is_enabled,
        'today': datetime.date.today(),
        'first_day': datetime.date.today().replace(day=1)
    }
    return render(request, 'tally/dashboard.html', context)


@login_required
def tally_export_csv(request):
    tenant = get_current_tenant()
    if not tenant:
        from wholesaleApp.models.tenant import Tenant
        tenant = Tenant.objects.filter(is_active=True).first()
        
    if not tenant or not tenant.tally_export_enabled:
        messages.error(request, "Action Denied: You do not have access to the Tally Export module.")
        return redirect('tally_dashboard')
        
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_type = request.GET.get('export_type', 'sales') # sales, purchases, receipts
    
    if not start_date or not end_date:
        messages.error(request, "Please select both start and end dates.")
        return redirect('tally_dashboard')
        
    try:
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('tally_dashboard')
        
    # Create the HTTP response with CSV headers
    response = HttpResponse(content_type='text/csv')
    filename = f"Tally_{export_type}_{start_date}_to_{end_date}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    if export_type == 'sales':
        # Headers: standard ledger columns for Tally journal/sales imports
        writer.writerow([
            'Voucher Date', 'Invoice Number', 'Party Ledger Name', 'Party GSTIN', 
            'Taxable Value', 'CGST Output', 'SGST Output', 'Net Invoice Amount', 
            'Sales Ledger Account', 'CGST Ledger Name', 'SGST Ledger Name'
        ])
        
        sales = SalesInvoice.objects.filter(tenant=tenant, invoice_date__range=[start, end]).order_by('invoice_date', 'id')
        for inv in sales:
            cgst = float(inv.gst_amount) / 2.0
            sgst = float(inv.gst_amount) / 2.0
            taxable = float(inv.gross_amount)
            party_name = f"{inv.patient_name} (Retail)" if inv.is_retail else (inv.customer.name if inv.customer else "Counter Cash")
            gstin = inv.customer.gstin if (inv.customer and inv.customer.gstin) else ""
            
            writer.writerow([
                inv.invoice_date.strftime('%Y-%m-%d'),
                inv.invoice_number,
                party_name,
                gstin,
                f"{taxable:.2f}",
                f"{cgst:.2f}",
                f"{sgst:.2f}",
                f"{float(inv.net_amount):.2f}",
                "Sales Ledger - B2B Local" if not inv.is_retail else "Sales Ledger - Cash Sales",
                "CGST Output Account (9%)",
                "SGST Output Account (9%)"
            ])
            
    elif export_type == 'purchases':
        writer.writerow([
            'Voucher Date', 'Supplier Invoice No', 'Supplier Name', 'Supplier GSTIN', 
            'Taxable Value', 'CGST Input', 'SGST Input', 'Net Purchase Amount', 
            'Purchase Ledger Account', 'CGST Input Ledger Name', 'SGST Input Ledger Name'
        ])
        
        purchases = PurchaseEntry.objects.filter(tenant=tenant, invoice_date__range=[start, end]).order_by('invoice_date', 'id')
        for pe in purchases:
            cgst = float(pe.gst_amount) / 2.0
            sgst = float(pe.gst_amount) / 2.0
            taxable = float(pe.gross_amount)
            party_name = pe.supplier.name if pe.supplier else "Unknown Supplier"
            gstin = pe.supplier.gstin if (pe.supplier and pe.supplier.gstin) else ""
            
            writer.writerow([
                pe.invoice_date.strftime('%Y-%m-%d'),
                pe.invoice_number,
                party_name,
                gstin,
                f"{taxable:.2f}",
                f"{cgst:.2f}",
                f"{sgst:.2f}",
                f"{float(pe.net_amount):.2f}",
                "Purchase Ledger - Local Inputs",
                "CGST Input Account (9%)",
                "SGST Input Account (9%)"
            ])
            
    elif export_type == 'receipts':
        writer.writerow([
            'Voucher Date', 'Receipt Voucher No', 'Customer Name', 'Payment Mode', 
            'Reference Number', 'Receipt Amount', 'Contra Ledger Name'
        ])
        
        receipts = CustomerPayment.objects.filter(tenant=tenant, payment_date__range=[start, end]).order_by('payment_date', 'id')
        for pay in receipts:
            party_name = pay.customer.name if pay.customer else "Unknown Customer"
            contra_ledger = "Cash Ledger" if pay.payment_mode == 'Cash' else "Bank Current Account"
            
            writer.writerow([
                pay.payment_date.strftime('%Y-%m-%d'),
                f"RCPT-{pay.id:06d}",
                party_name,
                pay.payment_mode,
                pay.reference_no or "-",
                f"{float(pay.amount):.2f}",
                contra_ledger
            ])
            
    return response
