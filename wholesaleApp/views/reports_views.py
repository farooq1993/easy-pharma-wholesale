from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
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

@login_required
def reports_dashboard(request):
    """Main Reports Hub listing all available reports."""
    context = {
        'page_title': 'Enterprise Wholesale Reports Hub',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
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


@login_required
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


@login_required
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


@login_required
def report_outstanding(request):
    """Customer outstanding ledger with search, filters, and pagination."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'report_outstanding'):
        from django.contrib import messages
        messages.error(request, "Access Denied: You do not have permission to view Outstanding dues report.")
        return redirect('home')
        
    from django.db.models import Q, Sum
    from django.utils import timezone
    from decimal import Decimal
    from wholesaleApp.models import CustomerPayment, AreaMaster, SalesInvoice
    from django.core.paginator import Paginator
    
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    area_id = request.GET.get('area')
    search_query = request.GET.get('q', '').strip()
    
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    
    customers = []
    suppliers = []
    
    # 1. Process Customers
    customer_qs = CustomerMaster.objects.filter(is_deleted=False).select_related('area')
    if area_id:
        customer_qs = customer_qs.filter(area_id=area_id)
    if search_query:
        customer_qs = customer_qs.filter(
            Q(name__icontains=search_query) |
            Q(mobile__icontains=search_query)
        )
        
    if from_date and to_date:
        # Pre-group sales and payments by customer in 2 fast queries to eliminate 2*N queries
        sales_by_cust = {
            r['customer_id']: r['total']
            for r in SalesInvoice.objects.filter(
                payment_type='Credit', invoice_date__range=[from_date, to_date], customer__isnull=False
            ).values('customer_id').annotate(total=Sum('net_amount'))
        }
        payments_by_cust = {
            r['customer_id']: r['total']
            for r in CustomerPayment.objects.filter(
                payment_date__range=[from_date, to_date], customer__isnull=False
            ).values('customer_id').annotate(total=Sum('amount'))
        }
        for c in customer_qs:
            credit_sales = sales_by_cust.get(c.id, Decimal('0.00'))
            payments = payments_by_cust.get(c.id, Decimal('0.00'))
            outstanding = credit_sales - payments
            if outstanding > 0:
                c.opening_balance = outstanding
                customers.append(c)
        customers.sort(key=lambda x: x.opening_balance, reverse=True)
    else:
        customers = list(customer_qs.filter(opening_balance__gt=0).order_by('-opening_balance'))
        
    total_receivable = sum(c.opening_balance for c in customers)
    customer_page = Paginator(customers, 10).get_page(request.GET.get('page'))
    
    # Calculate Aging (FIFO) ONLY for customers on current page to eliminate hundreds of queries!
    today = timezone.now().date()
    page_customers = list(customer_page.object_list)
    if page_customers:
        page_cust_ids = [c.id for c in page_customers]
        credit_invoices = SalesInvoice.objects.filter(
            customer_id__in=page_cust_ids,
            payment_type='Credit'
        ).order_by('-invoice_date', '-id')
        
        invoices_by_customer = defaultdict(list)
        for inv in credit_invoices:
            invoices_by_customer[inv.customer_id].append(inv)
            
        for c in page_customers:
            bal = c.opening_balance
            invoices = invoices_by_customer.get(c.id, [])
            
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
    
    context = {
        'customers': customers,
        'customer_page': customer_page,
        'areas': areas,
        'selected_area': int(area_id) if area_id else None,
        'total_receivable': float(total_receivable),
        'from_date': from_date,
        'to_date': to_date,
        'search_query': search_query,
        'page_title': 'Outstanding Dues Ledger',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/outstanding_report.html', context)


@login_required
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
    ).select_related('sales_invoice', 'sales_invoice__customer', 'product__company', 'batch')
    
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


@login_required
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


@login_required
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


@login_required
def report_profit(request):
    """Profit & Margins Report across Date-wise, Bill-wise, Customer-wise, and Company-wise tabs."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not (request.user.is_superuser or has_feature_access(request.user, 'view_margins') or has_feature_access(request.user, 'sales_view')):
        from django.contrib import messages
        messages.error(request, "Access Denied: You do not have permission to view Profit Margins.")
        return redirect('home')

    today = timezone.now().date()
    
    # Date filters (default current month)
    default_start = today.replace(day=1)
    start_date_str = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    customer_id = request.GET.get('customer', 'all')
    company_id = request.GET.get('company', 'all')
    active_tab = request.GET.get('tab', 'date')
    if active_tab not in ['date', 'bill', 'customer', 'company']:
        active_tab = 'date'
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = default_start
        start_date_str = default_start.strftime('%Y-%m-%d')
        
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end_date = today
        end_date_str = today.strftime('%Y-%m-%d')

    customers = CustomerMaster.objects.filter(is_deleted=False).order_by('name')
    companies = CompanyMaster.objects.filter(is_deleted=False).order_by('name')
    
    # Base query for sold invoice items
    items_qs = SalesInvoiceItem.objects.filter(
        sales_invoice__invoice_date__range=[start_date, end_date]
    ).select_related(
        'sales_invoice',
        'sales_invoice__customer',
        'sales_invoice__customer__area',
        'product',
        'product__company',
        'batch'
    )
    
    if customer_id != 'all' and customer_id:
        items_qs = items_qs.filter(sales_invoice__customer_id=customer_id)
        
    if company_id != 'all' and company_id:
        items_qs = items_qs.filter(product__company_id=company_id)
        
    items_qs = items_qs.order_by('-sales_invoice__invoice_date', '-sales_invoice__id')
    
    # In-memory fast aggregations
    date_dict = defaultdict(lambda: {
        'date': None,
        'invoice_ids': set(),
        'billed_qty': Decimal('0.00'),
        'free_qty': Decimal('0.00'),
        'total_qty': Decimal('0.00'),
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
    })
    
    bill_dict = defaultdict(lambda: {
        'invoice': None,
        'items_count': 0,
        'billed_qty': Decimal('0.00'),
        'free_qty': Decimal('0.00'),
        'total_qty': Decimal('0.00'),
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
        'items': []
    })
    
    customer_dict = defaultdict(lambda: {
        'customer_name': '',
        'city': '',
        'area': '',
        'invoice_ids': set(),
        'billed_qty': Decimal('0.00'),
        'free_qty': Decimal('0.00'),
        'total_qty': Decimal('0.00'),
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
    })
    
    company_dict = defaultdict(lambda: {
        'company_name': '',
        'product_ids': set(),
        'invoice_ids': set(),
        'billed_qty': Decimal('0.00'),
        'free_qty': Decimal('0.00'),
        'total_qty': Decimal('0.00'),
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
    })
    
    overall_sales = Decimal('0.00')
    overall_cost = Decimal('0.00')
    overall_billed_qty = Decimal('0.00')
    overall_free_qty = Decimal('0.00')
    overall_invoices_set = set()
    total_line_items = 0

    for item in items_qs:
        inv = item.sales_invoice
        prod = item.product
        batch = item.batch
        
        b_qty = Decimal(item.quantity or 0)
        f_qty = Decimal(item.free_quantity or 0)
        tot_qty = b_qty + f_qty
        
        s_rate = Decimal(item.sale_rate or 0)
        disc_pct = Decimal(item.discount_percentage or 0)
        
        # Item Taxable Sales Revenue
        base_amt = b_qty * s_rate
        disc_amt = base_amt * (disc_pct / Decimal('100.00'))
        sale_val = base_amt - disc_amt
        
        # Item Purchase Cost (Cost of Goods Sold - including free quantities issued)
        p_rate = Decimal(batch.purchase_rate or 0) if batch else Decimal('0.00')
        cost_val = tot_qty * p_rate
        
        item_profit = sale_val - cost_val
        item_margin = (item_profit / sale_val * Decimal('100.00')) if sale_val > 0 else Decimal('0.00')
        
        # Accumulate Overall
        overall_sales += sale_val
        overall_cost += cost_val
        overall_billed_qty += b_qty
        overall_free_qty += f_qty
        overall_invoices_set.add(inv.id)
        total_line_items += 1
        
        # 1. Accumulate Date-wise
        dt = inv.invoice_date
        d_row = date_dict[dt]
        d_row['date'] = dt
        d_row['invoice_ids'].add(inv.id)
        d_row['billed_qty'] += b_qty
        d_row['free_qty'] += f_qty
        d_row['total_qty'] += tot_qty
        d_row['total_sales'] += sale_val
        d_row['total_cost'] += cost_val
        d_row['total_profit'] += item_profit
        
        # 2. Accumulate Bill-wise
        b_row = bill_dict[inv.id]
        b_row['invoice'] = inv
        b_row['items_count'] += 1
        b_row['billed_qty'] += b_qty
        b_row['free_qty'] += f_qty
        b_row['total_qty'] += tot_qty
        b_row['total_sales'] += sale_val
        b_row['total_cost'] += cost_val
        b_row['total_profit'] += item_profit
        b_row['items'].append({
            'product_name': prod.name,
            'batch_number': batch.batch_number if batch else '-',
            'expiry_date': batch.expiry_date if batch else None,
            'billed_qty': b_qty,
            'free_qty': f_qty,
            'total_qty': tot_qty,
            'sale_rate': s_rate,
            'purchase_rate': p_rate,
            'discount_pct': disc_pct,
            'sale_val': sale_val,
            'cost_val': cost_val,
            'profit': item_profit,
            'margin_pct': item_margin
        })
        
        # 3. Accumulate Customer-wise
        cust = inv.customer
        cust_key = cust.id if cust else f"retail_{inv.patient_name or 'counter'}"
        c_row = customer_dict[cust_key]
        if not c_row['customer_name']:
            if cust:
                c_row['customer_name'] = cust.name
                c_row['city'] = cust.city or (cust.area.city if cust.area else '')
                c_row['area'] = cust.subarea.name if cust.subarea else (cust.area.city if cust.area else '')
            else:
                c_row['customer_name'] = f"{inv.patient_name or 'Walk-in Retail'}"
                c_row['city'] = 'Retail Counter'
                c_row['area'] = '-'
        c_row['invoice_ids'].add(inv.id)
        c_row['billed_qty'] += b_qty
        c_row['free_qty'] += f_qty
        c_row['total_qty'] += tot_qty
        c_row['total_sales'] += sale_val
        c_row['total_cost'] += cost_val
        c_row['total_profit'] += item_profit
        
        # 4. Accumulate Company-wise
        comp = prod.company if prod else None
        comp_key = comp.id if comp else 'no_company'
        cp_row = company_dict[comp_key]
        if not cp_row['company_name']:
            cp_row['company_name'] = comp.name if comp else 'Generic / Unassigned'
        cp_row['product_ids'].add(prod.id)
        cp_row['invoice_ids'].add(inv.id)
        cp_row['billed_qty'] += b_qty
        cp_row['free_qty'] += f_qty
        cp_row['total_qty'] += tot_qty
        cp_row['total_sales'] += sale_val
        cp_row['total_cost'] += cost_val
        cp_row['total_profit'] += item_profit

    overall_profit = overall_sales - overall_cost
    overall_margin = (overall_profit / overall_sales * Decimal('100.00')) if overall_sales > 0 else Decimal('0.00')

    # Post-process and sort collections
    date_report = []
    for dt, data in date_dict.items():
        sales = data['total_sales']
        profit = data['total_profit']
        margin = (profit / sales * Decimal('100.00')) if sales > 0 else Decimal('0.00')
        date_report.append({
            'date': dt,
            'bills_count': len(data['invoice_ids']),
            'billed_qty': data['billed_qty'],
            'free_qty': data['free_qty'],
            'total_qty': data['total_qty'],
            'total_sales': sales,
            'total_cost': data['total_cost'],
            'total_profit': profit,
            'margin_pct': margin
        })
    date_report.sort(key=lambda x: x['date'], reverse=True)
    
    bill_report = []
    for inv_id, data in bill_dict.items():
        sales = data['total_sales']
        profit = data['total_profit']
        margin = (profit / sales * Decimal('100.00')) if sales > 0 else Decimal('0.00')
        bill_report.append({
            'invoice': data['invoice'],
            'items_count': data['items_count'],
            'billed_qty': data['billed_qty'],
            'free_qty': data['free_qty'],
            'total_qty': data['total_qty'],
            'total_sales': sales,
            'total_cost': data['total_cost'],
            'total_profit': profit,
            'margin_pct': margin,
            'items': data['items']
        })
    bill_report.sort(key=lambda x: (x['invoice'].invoice_date, x['invoice'].id), reverse=True)
    
    customer_report = []
    for cust_k, data in customer_dict.items():
        sales = data['total_sales']
        profit = data['total_profit']
        margin = (profit / sales * Decimal('100.00')) if sales > 0 else Decimal('0.00')
        share = (profit / overall_profit * Decimal('100.00')) if overall_profit > 0 else Decimal('0.00')
        customer_report.append({
            'customer_name': data['customer_name'],
            'city': data['city'],
            'area': data['area'],
            'bills_count': len(data['invoice_ids']),
            'billed_qty': data['billed_qty'],
            'free_qty': data['free_qty'],
            'total_qty': data['total_qty'],
            'total_sales': sales,
            'total_cost': data['total_cost'],
            'total_profit': profit,
            'margin_pct': margin,
            'profit_share': share
        })
    customer_report.sort(key=lambda x: x['total_profit'], reverse=True)
    
    company_report = []
    for comp_k, data in company_dict.items():
        sales = data['total_sales']
        profit = data['total_profit']
        margin = (profit / sales * Decimal('100.00')) if sales > 0 else Decimal('0.00')
        share = (profit / overall_profit * Decimal('100.00')) if overall_profit > 0 else Decimal('0.00')
        company_report.append({
            'company_name': data['company_name'],
            'products_count': len(data['product_ids']),
            'bills_count': len(data['invoice_ids']),
            'billed_qty': data['billed_qty'],
            'free_qty': data['free_qty'],
            'total_qty': data['total_qty'],
            'total_sales': sales,
            'total_cost': data['total_cost'],
            'total_profit': profit,
            'margin_pct': margin,
            'profit_share': share
        })
    company_report.sort(key=lambda x: x['total_profit'], reverse=True)

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_customer': customer_id,
        'selected_company': company_id,
        'active_tab': active_tab,
        'customers': customers,
        'companies': companies,
        
        # Summary Totals
        'overall_sales': overall_sales,
        'overall_cost': overall_cost,
        'overall_profit': overall_profit,
        'overall_margin': overall_margin,
        'overall_bills_count': len(overall_invoices_set),
        'overall_billed_qty': overall_billed_qty,
        'overall_free_qty': overall_free_qty,
        'overall_total_qty': overall_billed_qty + overall_free_qty,
        'total_line_items': total_line_items,
        
        # Tab Datasets
        'date_report': date_report,
        'bill_report': bill_report,
        'customer_report': customer_report,
        'company_report': company_report,
        
        'page_title': 'Profit & Margins Report',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'reports/profit_report.html', context)


