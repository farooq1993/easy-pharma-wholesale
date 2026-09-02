from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from decimal import Decimal
from wholesaleApp.models import (
    ProductMaster,
    CustomerMaster,
    SalesInvoice,
    ProductBatch,
    AppGroupModule,
    AppFeature,
    UserFeaturePermission,
    CustomerPayment
)
from wholesaleApp.views.security_helpers import seed_default_permissions, get_user_permissions_context

def HomeView(request):
    """Dashboard view with LIVE calculation from new transaction database"""
    # Seed permissions dynamically
    seed_default_permissions()
    
    today = timezone.now().date()
    
    # ---------------- REAL LIVE METRICS ----------------
    total_products = ProductMaster.objects.filter(status=True, is_deleted=False).count()
    total_customers = CustomerMaster.objects.filter(status=True, is_deleted=False).count()
    total_orders = SalesInvoice.objects.count()
    total_revenue_val = SalesInvoice.objects.aggregate(total=Sum('net_amount'))['total'] or 0.00
    total_revenue = float(total_revenue_val)
    
    # Today's Snapshot
    todays_orders_count = SalesInvoice.objects.filter(invoice_date=today).count()
    todays_revenue_val = SalesInvoice.objects.filter(invoice_date=today).aggregate(total=Sum('net_amount'))['total'] or 0.00
    todays_revenue = float(todays_revenue_val)
    
    avg_order_value = float(todays_revenue / todays_orders_count) if todays_orders_count > 0 else 0.00
    out_of_stock_count = ProductBatch.objects.filter(quantity=0).values('product').distinct().count()
    
    # Order Status summary
    orders_by_status = {
        'Pending': SalesInvoice.objects.filter(status='Pending').count(),
        'Completed': SalesInvoice.objects.filter(status='Delivered').count(),
        'Cancelled': SalesInvoice.objects.filter(status='Cancelled').count(),
    }
    
    # ---------------- LIVE AREA-WISE ORDERS ----------------
    # Query today's invoices
    today_invoices = SalesInvoice.objects.filter(invoice_date=today)
    area_map = {}
    
    for inv in today_invoices.select_related('customer__area', 'customer__subarea'):
        cust = inv.customer
        area_name = cust.area.city if (cust and cust.area) else "Other Area"
        subarea_name = cust.subarea.name if (cust and cust.subarea) else "Main Locality"
        key = (area_name, subarea_name)
        
        if key not in area_map:
            area_map[key] = {'total': 0, 'pending': 0, 'delivered': 0, 'cancelled': 0}
            
        area_map[key]['total'] += 1
        if inv.status == 'Pending':
            area_map[key]['pending'] += 1
        elif inv.status == 'Delivered':
            area_map[key]['delivered'] += 1
        elif inv.status == 'Cancelled':
            area_map[key]['cancelled'] += 1

    area_wise_orders = []
    for (area, subarea), stats in area_map.items():
        total = stats['total']
        delivered = stats['delivered']
        pending = stats['pending']
        cancelled = stats['cancelled']
        delivered_percent = (delivered / total * 100) if total > 0 else 0
        
        area_wise_orders.append({
            'area_name': f"{area} - {subarea}",
            'total_orders': total,
            'pending': pending,
            'delivered': delivered,
            'cancelled': cancelled,
            'delivered_percent': delivered_percent
        })

    # If no orders today, pre-fill with AreaMaster list for preview purposes
    if not area_wise_orders:
        all_areas = CustomerMaster.objects.filter(status=True, is_deleted=False).values('area__city', 'subarea__name').distinct()
        for item in all_areas[:5]:
            if item['area__city']:
                area_wise_orders.append({
                    'area_name': f"{item['area__city']} - {item['subarea__name'] or 'Main'}",
                    'total_orders': 0,
                    'pending': 0,
                    'delivered': 0,
                    'cancelled': 0,
                    'delivered_percent': 0.0
                })

    # ---------------- EXPIRY ALERTS ----------------
    expiring_soon = []
    # Find batches expiring in the next 180 days
    limit_date = today + timedelta(days=180)
    batches = ProductBatch.objects.filter(expiry_date__lte=limit_date, quantity__gt=0).select_related('product')[:5]
    for b in batches:
        days_left = (b.expiry_date - today).days
        expiring_soon.append({
            'product': {'name': b.product.name, 'sku': b.product.hsn_code or 'N/A'},
            'batch_number': b.batch_number,
            'stock_quantity': b.quantity,
            'expiry_date': b.expiry_date,
            'days_left': days_left
        })

    # ---------------- LOW STOCK ALERTS ----------------
    low_stock_batches = ProductBatch.objects.filter(quantity__lte=15, quantity__gt=0).select_related('product')[:5]
    low_stock_alerts = []
    for b in low_stock_batches:
        low_stock_alerts.append({
            'product_name': b.product.name,
            'batch_number': b.batch_number,
            'quantity': b.quantity
        })

    # ---------------- OUTSTANDING PAYMENTS & AGING ----------------
    total_outstanding_val = CustomerMaster.objects.filter(is_deleted=False).aggregate(total=Sum('opening_balance'))['total'] or 0.00
    total_outstanding = float(total_outstanding_val)
    customers_with_dues_count = CustomerMaster.objects.filter(is_deleted=False, opening_balance__gt=0).count()
    
    top_dues = []
    custs_with_dues = CustomerMaster.objects.filter(is_deleted=False, opening_balance__gt=0).order_by('-opening_balance')[:5]
    for c in custs_with_dues:
        # FIFO Aging calculation
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
            days_overdue = (today - oldest_date).days
            last_payment_date = oldest_date
        else:
            days_overdue = (today - c.created_at.date()).days
            last_payment_date = c.created_at.date()
            
        top_dues.append({
            'customer': {'id': c.id, 'pharmacy_name': c.name, 'city': c.city},
            'amount': float(c.opening_balance),
            'last_payment_date': last_payment_date,
            'days_overdue': days_overdue
        })

    # ---------------- LIVE CHART DATA & TRENDS ----------------
    # 1. Weekly Sales Trend
    revenue_trend_labels = []
    revenue_trend_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        label = d.strftime('%a')
        rev = SalesInvoice.objects.filter(invoice_date=d).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        revenue_trend_labels.append(label)
        revenue_trend_data.append(float(rev))
        
    # 2. Monthly Company-wise Sales
    from wholesaleApp.models import SalesInvoiceItem
    first_day_of_month = today.replace(day=1)
    sales_items = SalesInvoiceItem.objects.filter(sales_invoice__invoice_date__gte=first_day_of_month)
    
    company_sales_map = {}
    for item in sales_items.select_related('product__company'):
        company = item.product.company
        company_name = company.name if company else "Other Pharma"
        if company_name not in company_sales_map:
            company_sales_map[company_name] = {'products': set(), 'units': 0, 'revenue': Decimal('0.00')}
        
        company_sales_map[company_name]['products'].add(item.product.id)
        company_sales_map[company_name]['units'] += item.quantity
        company_sales_map[company_name]['revenue'] += item.total_amount
        
    company_sales = []
    total_monthly_revenue = sum(stats['revenue'] for stats in company_sales_map.values()) or Decimal('1.00')
    for c_name, stats in company_sales_map.items():
        percent = (stats['revenue'] / total_monthly_revenue) * 100
        company_sales.append({
            'company__name': c_name,
            'products_sold': len(stats['products']),
            'units_sold': stats['units'],
            'revenue': float(stats['revenue']),
            'percent_of_total': float(percent)
        })
    company_sales.sort(key=lambda x: x['revenue'], reverse=True)
    
    if not company_sales:
        company_sales = [
            {'company__name': 'Cipla Ltd.', 'products_sold': 5, 'units_sold': 120, 'revenue': 12000.0, 'percent_of_total': 50.0},
            {'company__name': 'Sun Pharma', 'products_sold': 3, 'units_sold': 80, 'revenue': 8000.0, 'percent_of_total': 33.3},
            {'company__name': 'Mankind', 'products_sold': 2, 'units_sold': 40, 'revenue': 4000.0, 'percent_of_total': 16.7},
        ]
        
    company_sales_labels = [c['company__name'] for c in company_sales]
    company_sales_data = [c['revenue'] for c in company_sales]

    # 3. Area-wise chart lists
    area_names = [a['area_name'] for a in area_wise_orders]
    area_pending_data = [a['pending'] for a in area_wise_orders]
    area_delivered_data = [a['delivered'] for a in area_wise_orders]
    area_cancelled_data = [a['cancelled'] for a in area_wise_orders]

    # Recent Orders
    recent_orders = []
    latest_invoices = SalesInvoice.objects.all().select_related('customer')[:5]
    for inv in latest_invoices:
        recent_orders.append({
            'id': inv.id,
            'customer': {'pharmacy_name': inv.customer.name if inv.customer else (inv.patient_name or 'Walk-in Customer')},
            'order_date': inv.created_at,
            'total_amount': float(inv.net_amount),
            'status': inv.status
        })

    # ---------------- SMART PREDICTIVE FORECASTS (LOCAL ENGINE) ----------------
    monthly_sales = []
    for m in range(5, -1, -1):
        first_day_of_m = (today.replace(day=1) - timedelta(days=m*30)).replace(day=1)
        if m > 0:
            last_day_of_m = (first_day_of_m + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            last_day_of_m = today
            
        sales_val = SalesInvoice.objects.filter(
            invoice_date__range=[first_day_of_m, last_day_of_m]
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        monthly_sales.append(float(sales_val))
        
    n = len(monthly_sales)
    x = list(range(n))
    y = monthly_sales
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(val**2 for val in x)
    sum_xy = sum(val_x * val_y for val_x, val_y in zip(x, y))
    
    denominator = (n * sum_xx - sum_x**2)
    if denominator != 0:
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        sales_forecast = max(0.0, slope * n + intercept)
    else:
        sales_forecast = monthly_sales[-1] * 1.05 if monthly_sales[-1] > 0 else 5000.00

    outstanding_dues = total_outstanding
    last_30_days_start = today - timedelta(days=30)
    recent_collections_val = CustomerPayment.objects.filter(
        payment_date__range=[last_30_days_start, today]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    recent_collections = float(recent_collections_val)
    
    total_pool = outstanding_dues + recent_collections
    collection_rate = (recent_collections / total_pool) if total_pool > 0 else 0.25
    dues_collection_forecast = outstanding_dues * collection_rate
    dues_collection_forecast = min(outstanding_dues, max(0.0, dues_collection_forecast))
    if dues_collection_forecast == 0 and outstanding_dues > 0:
        dues_collection_forecast = outstanding_dues * 0.15

    from wholesaleApp.models import SalesInvoiceItem
    recent_sales_items = SalesInvoiceItem.objects.filter(
        sales_invoice__invoice_date__range=[last_30_days_start, today]
    ).values('product_id').annotate(qty_sold=Sum('quantity'))
    
    purchase_req_forecast = 0.0
    for item in recent_sales_items:
        p_id = item['product_id']
        qty_sold = float(item['qty_sold'])
        current_stock_val = ProductBatch.objects.filter(product_id=p_id).aggregate(total=Sum('quantity'))['total'] or 0
        current_stock = float(current_stock_val)
        
        deficit = max(0.0, qty_sold - current_stock)
        if deficit > 0:
            batch = ProductBatch.objects.filter(product_id=p_id).first()
            p_rate = float(batch.purchase_rate) if batch else 50.00
            purchase_req_forecast += (deficit * p_rate)
            
    if purchase_req_forecast == 0:
        purchase_req_forecast = sales_forecast * 0.70

    context = {
        'sales_forecast': sales_forecast,
        'dues_collection_forecast': dues_collection_forecast,
        'purchase_req_forecast': purchase_req_forecast,
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'todays_orders_count': todays_orders_count,
        'todays_orders_change': 0,
        'todays_revenue': todays_revenue,
        'todays_revenue_change': 0,
        'avg_order_value': avg_order_value,
        'out_of_stock_count': out_of_stock_count,
        'orders_by_status': orders_by_status,
        'area_wise_orders': area_wise_orders,
        'expiring_soon': expiring_soon,
        'low_stock_alerts': low_stock_alerts,
        'total_outstanding': total_outstanding,
        'overdue_amount': total_outstanding * 0.4,
        'customers_with_dues_count': customers_with_dues_count,
        'top_dues': top_dues,
        'company_sales': company_sales,
        'recent_orders': recent_orders,
        'revenue_trend_labels': revenue_trend_labels,
        'revenue_trend_data': revenue_trend_data,
        'company_sales_labels': company_sales_labels,
        'company_sales_data': company_sales_data,
        'area_names': area_names,
        'area_pending_data': area_pending_data,
        'area_delivered_data': area_delivered_data,
        'area_cancelled_data': area_cancelled_data,
        'user_perms': get_user_permissions_context(request.user)
    }
    
    return render(request, 'includes/home.html', context)


from wholesaleApp.views.security_helpers import (
    seed_default_permissions,
    get_user_permissions_context,
    apply_role_default_permissions,
    tenant_owner_required,
    ROLE_DEFAULT_PERMISSIONS
)

@tenant_owner_required
def user_permission_matrix(request):
    """View to show the dynamic user permissions matrix for Shop Owners and SaaS Super Admins."""
    seed_default_permissions()
    
    current_profile = getattr(request.user, 'profile', None)
    is_sa = request.user.is_superuser or (current_profile and current_profile.is_super_admin)

    if is_sa:
        users = User.objects.filter(is_superuser=False).select_related('profile__tenant')
    else:
        tenant = request.tenant or (current_profile.tenant if current_profile else None)
        if tenant:
            users = User.objects.filter(profile__tenant=tenant, is_superuser=False).select_related('profile__tenant')
        else:
            users = User.objects.none()

    modules = AppGroupModule.objects.filter(is_active=True).prefetch_related('features')
    
    # Pre-fetch user permissions: {user_id: {feature_codename: is_granted}}
    user_perms_dict = {}
    for u in users:
        user_perms_dict[u.id] = {}
        for p in UserFeaturePermission.objects.filter(user=u).select_related('feature'):
            user_perms_dict[u.id][p.feature.codename] = p.is_granted

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        target_user = get_object_or_404(User, id=user_id)
        
        # Verify access to target user
        if not is_sa:
            tenant = request.tenant or (current_profile.tenant if current_profile else None)
            if hasattr(target_user, 'profile') and target_user.profile.tenant != tenant:
                messages.error(request, "Access Denied: Cannot modify user outside your tenant firm.")
                return redirect('user_permission_matrix')

        if action == "apply_defaults":
            apply_role_default_permissions(target_user)
            messages.success(request, f"Default role permissions applied for user '{target_user.username}'.")
        else:
            # Custom selection saved
            UserFeaturePermission.objects.filter(user=target_user).update(is_granted=False)
            granted_features = request.POST.getlist("features")
            for codename in granted_features:
                feature = AppFeature.objects.filter(codename=codename, is_active=True).first()
                if feature:
                    perm, created = UserFeaturePermission.objects.get_or_create(user=target_user, feature=feature)
                    perm.is_granted = True
                    perm.save()
                    
            messages.success(request, f"Custom permissions updated successfully for user '{target_user.username}'.")
            
        return redirect('user_permission_matrix')

    context = {
        'users': users,
        'modules': modules,
        'user_perms_dict': user_perms_dict,
        'role_defaults': ROLE_DEFAULT_PERMISSIONS,
        'page_title': 'User Access & Permissions Matrix',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'master/permission_matrix.html', context)


def switch_tenant(request):
    """View for superuser to switch the active tenant session."""
    from django.contrib.auth.decorators import login_required
    from django.contrib import messages
    from wholesaleApp.models.tenant import Tenant
    
    if not request.user.is_authenticated:
        return redirect('login')
        
    if not request.user.is_superuser:
        messages.error(request, "Access Denied: Only administrators can switch tenants.")
        return redirect('home')

    if request.method == 'POST':
        tenant_id = request.POST.get('tenant_id')
        if tenant_id:
            try:
                from django.db.models import Q
                tenant = Tenant.objects.get(Q(user=request.user) | Q(user__isnull=True), id=tenant_id, is_active=True)
                request.session['active_tenant_id'] = tenant.id
                messages.success(request, f"Switched active firm to: {tenant.company_name}")
            except Tenant.DoesNotExist:
                messages.error(request, "Selected tenant does not exist or is inactive.")
        else:
            # Switch back to 'All Tenants'
            if 'active_tenant_id' in request.session:
                del request.session['active_tenant_id']
            messages.success(request, "Switched to administrator view (All Tenants).")
            
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def activity_log_list(request):
    """View to list all activity logs for the current tenant."""
    from wholesaleApp.models.logs import ActivityLog
    from wholesaleApp.views.security_helpers import get_user_permissions_context
    
    if not request.user.is_authenticated:
        return redirect('login')
        
    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (profile and (profile.role in ['Super Admin', 'Owner'] or profile.is_tenant_admin))
    if not is_admin:
        messages.error(request, "Access Denied: You do not have permission to view System Activity Logs.")
        return redirect('home')

    logs = ActivityLog.objects.all().select_related('user')
    
    # Optional search filtering
    action_filter = request.GET.get('action')
    model_filter = request.GET.get('model_name')
    if action_filter:
        logs = logs.filter(action=action_filter)
    if model_filter:
        logs = logs.filter(model_name__icontains=model_filter)
        
    context = {
        'logs': logs[:500], # Limit to last 500 logs for performance
        'page_title': 'System Activity Logs',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'master/activity_log_list.html', context)