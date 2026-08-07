from django.shortcuts import render, redirect
from django.db.models import Sum, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from wholesaleApp.models import (
    SalesInvoice,
    SalesInvoiceItem,
    ProductBatch,
    CustomerMaster,
    SupplierMaster,
    CompanyMaster
)
from wholesaleApp.views.security_helpers import get_user_permissions_context

# ==================== REPORTS MODULE VIEWS ====================

def reports_dashboard(request):
    """Main Reports Hub listing all available reports."""
    context = {
        'page_title': 'Enterprise Wholesale Reports Hub',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/dashboard.html', context)


def report_sales(request):
    """Sales & GST Tax reporting with date filters."""
    today = timezone.now().date()
    
    # Date filter range (default current month)
    start_date_str = request.GET.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    invoices = SalesInvoice.objects.filter(invoice_date__range=[start_date, end_date]).select_related('customer')
    
    # Aggregates
    totals = invoices.aggregate(
        gross=Sum('gross_amount'),
        discount=Sum('discount_amount'),
        gst=Sum('gst_amount'),
        net=Sum('net_amount')
    )
    
    context = {
        'invoices': invoices,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'totals': totals,
        'page_title': 'GST Sales Summary Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/sales_report.html', context)


def report_expiry(request):
    """Pharmaceutical Expiry alerts and shelf-life tracking."""
    today = timezone.now().date()
    
    # Expiry limit filter in days (default 90 days)
    days_limit = int(request.GET.get('days', '90'))
    limit_date = today + timedelta(days=days_limit)
    
    batches = ProductBatch.objects.filter(
        expiry_date__lte=limit_date, 
        quantity__gt=0
    ).select_related('product').order_by('expiry_date')
    
    report_data = []
    for b in batches:
        days_left = (b.expiry_date - today).days
        report_data.append({
            'product': b.product.name,
            'pack': b.product.pack_size,
            'batch_number': b.batch_number,
            'stock': b.quantity,
            'expiry_date': b.expiry_date,
            'days_left': days_left,
            'mrp': float(b.mrp),
            'purchase_rate': float(b.purchase_rate),
            'loss_value': float(b.quantity * b.purchase_rate)
        })
        
    context = {
        'batches': report_data,
        'days': days_limit,
        'page_title': 'Pharma Expiry Alert Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/expiry_report.html', context)


def report_stock(request):
    """Current Stock levels and valuation audit reporting."""
    batches = ProductBatch.objects.filter(quantity__gt=0).select_related('product')
    
    report_data = []
    total_qty = 0
    total_purchase_val = 0.00
    total_sale_val = 0.00
    
    for b in batches:
        p_val = float(b.quantity * b.purchase_rate)
        s_val = float(b.quantity * b.sale_rate)
        total_qty += b.quantity
        total_purchase_val += p_val
        total_sale_val += s_val
        
        report_data.append({
            'product': b.product.name,
            'pack': b.product.pack_size,
            'batch_number': b.batch_number,
            'stock': b.quantity,
            'purchase_rate': float(b.purchase_rate),
            'sale_rate': float(b.sale_rate),
            'purchase_val': p_val,
            'sale_val': s_val
        })
        
    context = {
        'batches': report_data,
        'total_qty': total_qty,
        'total_purchase_val': total_purchase_val,
        'total_sale_val': total_sale_val,
        'page_title': 'Current Stock Valuation Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/stock_valuation.html', context)


def report_outstanding(request):
    """Accounts Receivables and Payables outstanding ledgers with date and area filtering."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'report_outstanding'):
        from django.contrib import messages
        messages.error(request, "Access Denied: You do not have permission to view Outstanding dues report.")
        return redirect('home')
        
    from django.db.models import Sum
    from django.utils import timezone
    from decimal import Decimal
    from wholesaleApp.models import CustomerPayment, PurchaseEntry, AreaMaster, SalesInvoice
    
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    area_id = request.GET.get('area')
    
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    
    customers = []
    suppliers = []
    
    # 1. Process Customers
    customer_qs = CustomerMaster.objects.filter(is_deleted=False)
    if area_id:
        customer_qs = customer_qs.filter(area_id=area_id)
        
    if from_date and to_date:
        for c in customer_qs:
            credit_sales = SalesInvoice.objects.filter(
                customer=c, payment_type='Credit', invoice_date__range=[from_date, to_date]
            ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
            
            payments = CustomerPayment.objects.filter(
                customer=c, payment_date__range=[from_date, to_date]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            outstanding = credit_sales - payments
            if outstanding > 0:
                c.opening_balance = outstanding
                customers.append(c)
        customers.sort(key=lambda x: x.opening_balance, reverse=True)
    else:
        customers = list(customer_qs.filter(opening_balance__gt=0).order_by('-opening_balance'))
        
    # Calculate Aging (FIFO based on current filtered balance)
    today = timezone.now().date()
    for c in customers:
        bal = c.opening_balance
        invoices = SalesInvoice.objects.filter(customer=c, payment_type='Credit').order_by('-invoice_date', '-id')
        
        oldest_date = None
        accumulated = Decimal('0.00')
        for inv in invoices:
            accumulated += inv.net_amount
            oldest_date = inv.invoice_date
            if accumulated >= bal:
                break
                
        if oldest_date:
            c.oldest_date = oldest_date
            c.pending_days = (today - oldest_date).days
        else:
            c.oldest_date = c.created_at.date()
            c.pending_days = (today - c.created_at.date()).days
            
    # 2. Process Suppliers (suppliers do not belong to sales areas)
    if area_id:
        suppliers = []
    else:
        if from_date and to_date:
            all_suppliers = SupplierMaster.objects.filter(is_deleted=False)
            for s in all_suppliers:
                credit_purchases = PurchaseEntry.objects.filter(
                    supplier=s, payment_type='Credit', invoice_date__range=[from_date, to_date]
                ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
                
                outstanding = credit_purchases
                if outstanding > 0:
                    s.opening_balance = outstanding
                    suppliers.append(s)
            suppliers.sort(key=lambda x: x.opening_balance, reverse=True)
        else:
            suppliers = list(SupplierMaster.objects.filter(is_deleted=False, opening_balance__gt=0).order_by('-opening_balance'))
            
    total_receivable = sum(c.opening_balance for c in customers)
    total_payable = sum(s.opening_balance for s in suppliers)
    
    context = {
        'customers': customers,
        'suppliers': suppliers,
        'areas': areas,
        'selected_area': int(area_id) if area_id else None,
        'total_receivable': float(total_receivable),
        'total_payable': float(total_payable),
        'from_date': from_date,
        'to_date': to_date,
        'page_title': 'Outstanding Dues Ledger',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/outstanding_report.html', context)


def report_company_sales(request):
    """Company-wise sales report with date filters."""
    today = timezone.now().date()
    
    # Date filter range (default current month)
    start_date_str = request.GET.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    company_id = request.GET.get('company', 'all')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    companies = CompanyMaster.objects.filter(is_deleted=False).order_by('name')
    
    items = SalesInvoiceItem.objects.filter(
        sales_invoice__invoice_date__range=[start_date, end_date]
    ).select_related('sales_invoice', 'sales_invoice__customer', 'product', 'batch')
    
    if company_id != 'all' and company_id:
        items = items.filter(product__company_id=company_id)
        
    items = items.order_by('-sales_invoice__invoice_date', '-id')
    
    # Compute totals
    total_qty = 0
    total_free_qty = 0
    total_taxable_value = Decimal('0.00')
    total_gst_amount = Decimal('0.00')
    total_net_amount = Decimal('0.00')
    
    processed_items = []
    for item in items:
        qty = item.quantity
        rate = item.sale_rate
        disc_pct = item.discount_percentage
        gst_pct = item.product.gst_rate
        
        # Calculate taxable value and GST
        base_val = qty * rate
        disc_val = base_val * (disc_pct / 100)
        taxable_val = base_val - disc_val
        gst_val = taxable_val * (gst_pct / 100)
        
        total_qty += qty
        total_free_qty += item.free_quantity
        total_taxable_value += taxable_val
        total_gst_amount += gst_val
        total_net_amount += item.total_amount
        
        processed_items.append({
            'item': item,
            'taxable_val': taxable_val,
            'gst_val': gst_val,
        })
        
    context = {
        'items': processed_items,
        'companies': companies,
        'selected_company': company_id,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'totals': {
            'qty': total_qty,
            'free_qty': total_free_qty,
            'gross': total_taxable_value,
            'gst': total_gst_amount,
            'net': total_net_amount,
        },
        'page_title': 'Company-wise Sales Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/company_sales.html', context)


def report_customer_sales(request):
    """Customer-wise sales report with date filters."""
    today = timezone.now().date()
    
    # Date filter range (default current month)
    start_date_str = request.GET.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    customer_id = request.GET.get('customer', 'all')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    customers = CustomerMaster.objects.filter(is_deleted=False).order_by('name')
    
    invoices = SalesInvoice.objects.filter(
        invoice_date__range=[start_date, end_date]
    ).select_related('customer')
    
    if customer_id != 'all' and customer_id:
        invoices = invoices.filter(customer_id=customer_id)
        
    invoices = invoices.order_by('-invoice_date', '-id')
    
    # Aggregates
    totals = invoices.aggregate(
        gross=Sum('gross_amount'),
        discount=Sum('discount_amount'),
        gst=Sum('gst_amount'),
        net=Sum('net_amount')
    )
    
    context = {
        'invoices': invoices,
        'customers': customers,
        'selected_customer': customer_id,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'totals': totals,
        'page_title': 'Customer-wise Sales Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/customer_sales.html', context)


def report_gst(request):
    """Detailed B2B GST Report summarizing Input and Output GST taxes."""
    from wholesaleApp.models import SalesInvoiceItem, PurchaseEntryItem
    from django.db.models import Sum
    from datetime import datetime, timedelta
    from decimal import Decimal
    from django.utils import timezone
    
    today = timezone.now().date()
    # Default range: current month
    start_date_str = request.GET.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # 1. Fetch Sales (Output GST)
    sales_items = SalesInvoiceItem.objects.filter(
        sales_invoice__invoice_date__range=[start_date, end_date]
    ).select_related('sales_invoice', 'sales_invoice__customer', 'product')
    
    # Group sales by GST rate
    sales_by_rate = {}
    sales_details = []
    
    total_sales_taxable = Decimal('0.00')
    total_sales_gst = Decimal('0.00')
    
    for item in sales_items:
        qty = Decimal(item.quantity)
        rate = Decimal(item.sale_rate)
        disc_pct = Decimal(item.discount_percentage)
        gst_pct = Decimal(item.product.gst_rate)
        
        base_taxable = qty * rate
        disc_amt = base_taxable * (disc_pct / Decimal('100.00'))
        taxable = base_taxable - disc_amt
        gst_amt = taxable * (gst_pct / Decimal('100.00'))
        cgst = gst_amt / Decimal('2.00')
        sgst = gst_amt / Decimal('2.00')
        row_total = taxable + gst_amt
        
        total_sales_taxable += taxable
        total_sales_gst += gst_amt
        
        gst_pct_str = f"{gst_pct:.1f}"
        if gst_pct_str not in sales_by_rate:
            sales_by_rate[gst_pct_str] = {
                'rate': gst_pct,
                'taxable': Decimal('0.00'),
                'cgst': Decimal('0.00'),
                'sgst': Decimal('0.00'),
                'gst': Decimal('0.00'),
                'total': Decimal('0.00')
            }
        sales_by_rate[gst_pct_str]['taxable'] += taxable
        sales_by_rate[gst_pct_str]['cgst'] += cgst
        sales_by_rate[gst_pct_str]['sgst'] += sgst
        sales_by_rate[gst_pct_str]['gst'] += gst_amt
        sales_by_rate[gst_pct_str]['total'] += row_total
        
        customer = item.sales_invoice.customer
        customer_name = customer.name if customer else (item.sales_invoice.patient_name or "Retail Counter")
        cust_gst = customer.gstin or "" if customer else ""
        if not cust_gst or cust_gst.strip().lower() in ['na', 'n/a', 'none', 'null', '']:
            cust_gst = 'URD (Retail/Unregistered)' if not customer else 'URD (Unregistered)'
            
        sales_details.append({
            'date': item.sales_invoice.invoice_date,
            'invoice_number': item.sales_invoice.invoice_number,
            'customer_name': customer_name,
            'customer_gstin': cust_gst,
            'product_name': item.product.name,
            'gst_rate': gst_pct,
            'taxable': taxable,
            'cgst': cgst,
            'sgst': sgst,
            'gst': gst_amt,
            'total': row_total
        })
        
    # 2. Fetch Purchases (Input GST)
    purchase_items = PurchaseEntryItem.objects.filter(
        purchase_entry__invoice_date__range=[start_date, end_date]
    ).select_related('purchase_entry', 'purchase_entry__supplier', 'product')
    
    purchases_by_rate = {}
    purchase_details = []
    
    total_purchases_taxable = Decimal('0.00')
    total_purchases_gst = Decimal('0.00')
    
    for item in purchase_items:
        qty = Decimal(item.quantity)
        rate = Decimal(item.purchase_rate)
        disc_pct = Decimal(item.discount_percentage)
        gst_pct = Decimal(item.product.gst_rate)
        
        base_taxable = qty * rate
        disc_amt = base_taxable * (disc_pct / Decimal('100.00'))
        taxable = base_taxable - disc_amt
        gst_amt = taxable * (gst_pct / Decimal('100.00'))
        cgst = gst_amt / Decimal('2.00')
        sgst = gst_amt / Decimal('2.00')
        row_total = taxable + gst_amt
        
        total_purchases_taxable += taxable
        total_purchases_gst += gst_amt
        
        gst_pct_str = f"{gst_pct:.1f}"
        if gst_pct_str not in purchases_by_rate:
            purchases_by_rate[gst_pct_str] = {
                'rate': gst_pct,
                'taxable': Decimal('0.00'),
                'cgst': Decimal('0.00'),
                'sgst': Decimal('0.00'),
                'gst': Decimal('0.00'),
                'total': Decimal('0.00')
            }
        purchases_by_rate[gst_pct_str]['taxable'] += taxable
        purchases_by_rate[gst_pct_str]['cgst'] += cgst
        purchases_by_rate[gst_pct_str]['sgst'] += sgst
        purchases_by_rate[gst_pct_str]['gst'] += gst_amt
        purchases_by_rate[gst_pct_str]['total'] += row_total
        
        supp_gst = item.purchase_entry.supplier.gstin or ""
        if not supp_gst or supp_gst.strip().lower() in ['na', 'n/a', 'none', 'null', '']:
            supp_gst = 'URD (Unregistered)'
            
        purchase_details.append({
            'date': item.purchase_entry.invoice_date,
            'invoice_number': item.purchase_entry.invoice_number,
            'supplier_name': item.purchase_entry.supplier.name,
            'supplier_gstin': supp_gst,
            'product_name': item.product.name,
            'gst_rate': gst_pct,
            'taxable': taxable,
            'cgst': cgst,
            'sgst': sgst,
            'gst': gst_amt,
            'total': row_total
        })
        
    net_gst_payable = total_sales_gst - total_purchases_gst
    excess_itc = Decimal('0.00')
    if net_gst_payable < 0:
        excess_itc = abs(net_gst_payable)
    
    sales_summary = sorted(sales_by_rate.values(), key=lambda x: x['rate'])
    purchases_summary = sorted(purchases_by_rate.values(), key=lambda x: x['rate'])
    
    total_sales_cgst = total_sales_gst / Decimal('2.00')
    total_sales_sgst = total_sales_gst / Decimal('2.00')
    total_purchases_cgst = total_purchases_gst / Decimal('2.00')
    total_purchases_sgst = total_purchases_gst / Decimal('2.00')
    
    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        
        'total_sales_taxable': total_sales_taxable,
        'total_sales_gst': total_sales_gst,
        'total_sales_cgst': total_sales_cgst,
        'total_sales_sgst': total_sales_sgst,
        
        'total_purchases_taxable': total_purchases_taxable,
        'total_purchases_gst': total_purchases_gst,
        'total_purchases_cgst': total_purchases_cgst,
        'total_purchases_sgst': total_purchases_sgst,
        
        'net_gst_payable': net_gst_payable,
        'excess_itc': excess_itc,
        
        'sales_summary': sales_summary,
        'purchases_summary': purchases_summary,
        'sales_details': sales_details,
        'purchase_details': purchase_details,
        
        'page_title': 'Consolidated GST Tax Return Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/gst_report.html', context)

