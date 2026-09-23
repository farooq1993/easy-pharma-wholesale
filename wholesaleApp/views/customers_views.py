from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from wholesaleApp.models.customers import CustomerMaster, AreaMaster, SubareaMaster, CustomerManageDetail

# ==================== CUSTOMER MASTER VIEWS ====================
@login_required
def customer_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    from wholesaleApp.utils.list_helpers import paginate_queryset, invalidate_list_cache
    from django.db.models import Q

    if not has_feature_access(request.user, 'customer_view'):
        messages.error(request, "Access Denied: You do not have permission to view Customers.")
        return redirect('home')

    q = request.GET.get('q', '').strip()
    customer_type = request.GET.get('customer_type', '').strip()
    area_id = request.GET.get('area', '').strip()

    customers = CustomerMaster.objects.filter(is_deleted=False).select_related('area', 'subarea')

    if q:
        customers = customers.filter(
            Q(name__icontains=q) |
            Q(mobile__icontains=q) |
            Q(city__icontains=q) |
            Q(gstin__icontains=q)
        )

    if customer_type:
        customers = customers.filter(customer_type=customer_type)

    if area_id and area_id.isdigit():
        customers = customers.filter(area_id=int(area_id))

    customers = customers.order_by('name')
    page_data = paginate_queryset(request, customers, default_per_page=25)
    filter_areas = AreaMaster.objects.filter(is_active=True).order_by('city')

    context = {
        'page_obj': page_data['page_obj'],
        'paginator': page_data['paginator'],
        'extra_query': page_data['extra_query'],
        'per_page': page_data['per_page'],
        'total_count': page_data['total_count'],
        'filter_areas': filter_areas,
        'q': q,
        'customer_type': customer_type,
        'area_id': area_id,
        'page_title': 'Customer Master',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_list.html', context)

@login_required
def customer_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'customer_create'):
        messages.error(request, "Access Denied: You do not have permission to create Customers.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    subareas = SubareaMaster.objects.filter(is_active=True).select_related('area').order_by('name')
    if request.method == 'POST':
        # Form handling
        mobile = request.POST.get('mobile', '').strip()
        if CustomerMaster.objects.filter(mobile=mobile, is_deleted=False).exists():
            error_message = 'A customer with this mobile number already exists.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            messages.error(request, error_message)
            return redirect('createcustomer')
        dl_number_1 = request.POST.get('dl_number_1', '').strip()
        if not dl_number_1:
            error_message = 'Drug Licence Number is required to create a customer.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            messages.error(request, error_message)
            return redirect('createcustomer')
        area_id = request.POST.get('area')
        subarea_id = request.POST.get('subarea') or None
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        if not city and area_id:
            try:
                area_obj = AreaMaster.objects.get(id=area_id)
                city = area_obj.city
            except Exception:
                pass

        customer = CustomerMaster(
            name=request.POST['name'].strip(),
            customer_type=request.POST.get('customer_type', 'Retailer'),
            mobile=mobile,
            alternate_mobile=request.POST.get('alternate_mobile', ''),
            email=request.POST.get('email', ''),
            gstin=request.POST.get('gstin', ''),
            dl_number_1=dl_number_1,
            dl_number_2=request.POST.get('dl_number_2', ''),
            dl_number_3=request.POST.get('dl_number_3', ''),
            area_id=area_id,
            subarea_id=subarea_id if subarea_id and subarea_id.isdigit() else None,
            address=request.POST.get('address', ''),
            city=city,
            state=state,
            pincode=request.POST.get('pincode', ''),
            opening_balance=request.POST.get('opening_balance', 0),
            credit_limit=request.POST.get('credit_limit', 0),
            credit_days=request.POST.get('credit_days', 0),
            created_by=request.user if request.user.is_authenticated else None
        )
        customer.save()
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('customers')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({
                'status': 'success',
                'id': customer.id,
                'name': customer.name,
                'city': customer.city,
                'customer_type': customer.customer_type
            })
            
        messages.success(request, 'Customer created successfully!')
        return redirect('customer_list')
    
    context = {
        'areas': areas, 
        'subareas': subareas,
        'page_title': 'Add New Customer',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_form.html', context)

@login_required
def customer_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'customer_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Customers.")
        return redirect('home')
        
    customer = get_object_or_404(CustomerMaster, pk=pk, is_deleted=False)
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    subareas = SubareaMaster.objects.filter(is_active=True).select_related('area').order_by('name')
    
    if request.method == 'POST':
        dl_number_1 = request.POST.get('dl_number_1', '').strip()
        if not dl_number_1:
            messages.error(request, 'Drug Licence Number is required for every customer.')
            return redirect('customer_edit', pk=customer.pk)
        customer.name = request.POST['name']
        customer.customer_type = request.POST.get('customer_type', 'Retailer')
        customer.mobile = request.POST['mobile']
        customer.alternate_mobile = request.POST.get('alternate_mobile', '')
        customer.email = request.POST.get('email', '')
        customer.gstin = request.POST.get('gstin', '')
        customer.dl_number_1 = dl_number_1
        customer.dl_number_2 = request.POST.get('dl_number_2', '')
        customer.dl_number_3 = request.POST.get('dl_number_3', '')
        area_id = request.POST.get('area')
        subarea_id = request.POST.get('subarea') or None
        city = request.POST.get('city', '').strip()
        if not city and area_id:
            try:
                area_obj = AreaMaster.objects.get(id=area_id)
                city = area_obj.city
            except Exception:
                pass

        customer.area_id = area_id
        customer.subarea_id = subarea_id if subarea_id and subarea_id.isdigit() else None
        customer.address = request.POST.get('address', '')
        customer.city = city
        customer.state = request.POST.get('state', '')
        customer.pincode = request.POST.get('pincode', '')
        customer.opening_balance = request.POST.get('opening_balance', 0)
        customer.credit_limit = request.POST.get('credit_limit', 0)
        customer.credit_days = request.POST.get('credit_days', 0)
        customer.save()
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('customers')
        messages.success(request, 'Customer updated successfully!')
        return redirect('customer_list')
    
    context = {
        'customer': customer, 
        'areas': areas, 
        'subareas': subareas,
        'page_title': 'Edit Customer',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_form.html', context)

@login_required
def customer_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'customer_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Customers.")
        return redirect('home')
        
    customer = get_object_or_404(CustomerMaster, pk=pk)
    customer.is_deleted = True
    customer.save()
    from wholesaleApp.utils.list_helpers import invalidate_list_cache
    invalidate_list_cache('customers')
    messages.success(request, 'Customer deleted successfully!')
    return redirect('customer_list')


# ==================== AREA MASTER VIEWS ====================
@login_required
def area_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_view'):
        messages.error(request, "Access Denied: You do not have permission to view Areas.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    subareas = SubareaMaster.objects.filter(is_active=True).select_related('area').order_by('name')
    context = {
        'areas': areas,
        'subareas': subareas,
        'page_title': 'Area & Subarea Master',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/area_list.html', context)

@login_required
def area_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'
    
    if not has_feature_access(request.user, 'area_create'):
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': "Access Denied: You do not have permission to create Areas."}, status=403)
        messages.error(request, "Access Denied: You do not have permission to create Areas.")
        return redirect('home')
        
    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        code = request.POST.get('code', '').strip()
        
        if not city:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': "Area / City name is required."}, status=400)
            messages.error(request, "Area / City name is required.")
            return render(request, 'customers/area_form.html', {'page_title': 'Add New Area'})

        # Check if already exists
        if AreaMaster.objects.filter(city__iexact=city).exists():
            existing = AreaMaster.objects.filter(city__iexact=city).first()
            if is_ajax:
                return JsonResponse({
                    'status': 'error', 
                    'message': f"Area / City '{city}' already exists.",
                    'id': existing.id,
                    'city': existing.city,
                    'code': existing.code or ''
                }, status=400)
            messages.error(request, f"Area for city '{city}' already exists.")
        else:
            area = AreaMaster(city=city, code=code)
            area.save()
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': f"Area / City '{city}' created successfully!",
                    'id': area.id,
                    'city': area.city,
                    'code': area.code or ''
                })
            messages.success(request, 'Area created successfully!')
            return redirect('area_list')
            
    context = {
        'page_title': 'Add New Area',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/area_form.html', context)

@login_required
def area_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Areas.")
        return redirect('home')
        
    area = get_object_or_404(AreaMaster, pk=pk)
    if request.method == 'POST':
        area.city = request.POST['city']
        area.code = request.POST.get('code', '')
        area.save()
        messages.success(request, 'Area updated successfully!')
        return redirect('area_list')
        
    context = {
        'area': area, 
        'page_title': 'Edit Area',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/area_form.html', context)

@login_required
def area_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'area_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Areas.")
        return redirect('home')
        
    area = get_object_or_404(AreaMaster, pk=pk)
    area.is_active = False
    area.save()
    messages.success(request, 'Area deleted successfully!')
    return redirect('area_list')


# ==================== SUBAREA MASTER VIEWS ====================
@login_required
def subarea_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'
    
    if not has_feature_access(request.user, 'area_create'):
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': "Access Denied: You do not have permission to create Subareas."}, status=403)
        messages.error(request, "Access Denied: You do not have permission to create Subareas.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True).order_by('city')
    if request.method == 'POST':
        area_id = request.POST.get('area')
        name = request.POST.get('name', '').strip()
        
        if not name or not area_id:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': "Parent Area and Subarea name are required."}, status=400)
            messages.error(request, "Area and Subarea name are required.")
            return render(request, 'customers/subarea_form.html', {'areas': areas, 'page_title': 'Add New Subarea'})

        if SubareaMaster.objects.filter(area_id=area_id, name__iexact=name).exists():
            existing = SubareaMaster.objects.filter(area_id=area_id, name__iexact=name).first()
            if is_ajax:
                return JsonResponse({
                    'status': 'error', 
                    'message': f"Subarea '{name}' already exists in this area.",
                    'id': existing.id,
                    'name': existing.name,
                    'area_id': existing.area_id
                }, status=400)
            messages.error(request, f"Subarea '{name}' already exists in this area.")
        else:
            subarea = SubareaMaster(area_id=area_id, name=name)
            subarea.save()
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': f"Subarea '{name}' created successfully!",
                    'id': subarea.id,
                    'name': subarea.name,
                    'area_id': subarea.area_id,
                    'area_city': subarea.area.city
                })
            messages.success(request, 'Subarea created successfully!')
            return redirect('area_list')
            
    context = {
        'areas': areas, 
        'page_title': 'Add New Subarea',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/subarea_form.html', context)

@login_required
def subarea_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Subareas.")
        return redirect('home')
        
    subarea = get_object_or_404(SubareaMaster, pk=pk)
    areas = AreaMaster.objects.filter(is_active=True)
    if request.method == 'POST':
        subarea.area_id = request.POST['area']
        subarea.name = request.POST['name']
        subarea.save()
        messages.success(request, 'Subarea updated successfully!')
        return redirect('area_list')
        
    context = {
        'subarea': subarea, 
        'areas': areas, 
        'page_title': 'Edit Subarea',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/subarea_form.html', context)

@login_required
def subarea_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'area_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Subareas.")
        return redirect('home')
        
    subarea = get_object_or_404(SubareaMaster, pk=pk)
    subarea.is_active = False
    subarea.save()
    messages.success(request, 'Subarea deleted successfully!')
    return redirect('area_list')


# ==================== CUSTOMER LEDGER & PAYMENTS ====================
@login_required
def customer_ledger(request):
    from wholesaleApp.views.security_helpers import get_user_permissions_context, has_feature_access
    if not has_feature_access(request.user, 'customer_ledger'):
        from django.contrib import messages
        messages.error(request, "Access Denied: You do not have permission to view Customer Ledger.")
        return redirect('home')
        
    from wholesaleApp.models import CustomerMaster, SalesInvoice, CustomerPayment
    from decimal import Decimal
    
    customers = CustomerMaster.objects.filter(is_deleted=False).order_by('name')
    selected_customer_id = request.GET.get('customer')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    customer = None
    ledger_entries = []
    initial_balance = Decimal('0.00')
    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    
    if selected_customer_id:
        customer = get_object_or_404(CustomerMaster, id=selected_customer_id, is_deleted=False)
        
        # Get all Credit Sales Invoices
        invoices = SalesInvoice.objects.filter(customer=customer, payment_type='Credit').order_by('invoice_date', 'id')
        # Get all Customer Payments
        payments = CustomerPayment.objects.filter(customer=customer).order_by('payment_date', 'id')
        
        # Build entries
        all_debit = Decimal('0.00')
        all_credit = Decimal('0.00')
        for inv in invoices:
            ledger_entries.append({
                'date': inv.invoice_date,
                'type': 'Sales Invoice',
                'number': inv.invoice_number,
                'debit': inv.net_amount,
                'credit': Decimal('0.00'),
                'remarks': f"Delivery Status: {inv.status}",
                'id': inv.id,
                'is_payment': False,
                'url': f"/sales/invoice/{inv.id}/print/"
            })
            all_debit += inv.net_amount
            
        for pay in payments:
            ledger_entries.append({
                'date': pay.payment_date,
                'type': f"Payment Received ({pay.payment_mode})",
                'number': pay.reference_no or f"PAY-{pay.id:04d}",
                'debit': Decimal('0.00'),
                'credit': pay.amount,
                'remarks': pay.remarks or '',
                'id': pay.id,
                'is_payment': True,
                'url': None
            })
            all_credit += pay.amount
            
        # Sort chronologically by date, payment type, and ID
        ledger_entries.sort(key=lambda x: (x['date'], x['is_payment'], x['id']))
        
        # Calculate initial balance:
        # B_prior = B_current - sum(Debit) + sum(Credit)
        initial_balance = customer.opening_balance - all_debit + all_credit
        
        # Calculate running balance
        running = initial_balance
        for entry in ledger_entries:
            if entry['debit'] > 0:
                running += entry['debit']
            elif entry['credit'] > 0:
                running -= entry['credit']
            entry['running_balance'] = running

        # Filter by date range if provided
        display_opening_balance = initial_balance
        filtered_entries = []
        
        from django.utils.dateparse import parse_date
        fd = parse_date(from_date) if from_date else None
        td = parse_date(to_date) if to_date else None
        
        if fd:
            debits_before = Decimal('0.00')
            credits_before = Decimal('0.00')
            for entry in ledger_entries:
                if entry['date'] < fd:
                    debits_before += entry['debit']
                    credits_before += entry['credit']
            display_opening_balance = initial_balance + debits_before - credits_before
            
        for entry in ledger_entries:
            keep = True
            if fd and entry['date'] < fd:
                keep = False
            if td and entry['date'] > td:
                keep = False
            if keep:
                filtered_entries.append(entry)
                total_debit += entry['debit']
                total_credit += entry['credit']
                
        ledger_entries = filtered_entries
        initial_balance = display_opening_balance

    context = {
        'customers': customers,
        'customer': customer,
        'ledger_entries': ledger_entries,
        'initial_balance': initial_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'from_date': from_date,
        'to_date': to_date,
        'page_title': 'Customer Ledger',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_ledger.html', context)


from django.db import transaction
@login_required
@transaction.atomic
def customer_payment_add(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_create'):
        messages.error(request, "Access Denied: You do not have permission to record payments.")
        return redirect('customer_ledger')
        
    from wholesaleApp.models import CustomerMaster, CustomerPayment
    from decimal import Decimal
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        payment_date = request.POST.get('payment_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(payment_date):
            messages.error(request, "Action Denied: The selected payment date falls within a closed Financial Year.")
            return redirect('customer_ledger')
        amount = Decimal(request.POST.get('amount', 0))
        payment_mode = request.POST.get('payment_mode', 'Cash')
        reference_no = request.POST.get('reference_no', '')
        remarks = request.POST.get('remarks', '')
        
        customer = get_object_or_404(CustomerMaster, id=customer_id)
        
        # Create payment
        payment = CustomerPayment.objects.create(
            customer=customer,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_mode,
            reference_no=reference_no,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Deduct from customer balance
        customer.opening_balance -= amount
        customer.save()
        
        messages.success(request, f"Payment of ₹{amount} successfully recorded for {customer.name}.")
        return redirect(f"/customer/ledger/?customer={customer.id}")
        
    return redirect('customer_ledger')


@login_required
@transaction.atomic
def customer_payment_delete(request, pk):
    from wholesaleApp.models import CustomerPayment
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete payments.")
        return redirect(f"/customer/ledger/?customer={get_object_or_404(CustomerPayment, pk=pk).customer.id}")
    
    payment = get_object_or_404(CustomerPayment, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(payment.payment_date):
        messages.error(request, "Action Denied: This payment falls within a closed Financial Year and cannot be deleted.")
        return redirect(f"/customer/ledger/?customer={payment.customer.id}")
    customer = payment.customer
    
    # Add amount back to customer balance
    customer.opening_balance += payment.amount
    customer.save()
    
    # Delete payment
    payment.delete()
    
    messages.success(request, "Payment deleted and customer balance adjusted.")
    return redirect(f"/customer/ledger/?customer={customer.id}")


def customer_payment_list(request):
    """View to list all customer payments (collections) with analytical metrics."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_view'):
        messages.error(request, "Access Denied: You do not have permission to view Payments Collection.")
        return redirect('home')
        
    from wholesaleApp.models import CustomerPayment
    from wholesaleApp.views.security_helpers import get_user_permissions_context
    from django.db.models import Sum
    from django.utils import timezone
    today = timezone.now().date()
    
    payments = CustomerPayment.objects.all().select_related('customer', 'invoice').order_by('-payment_date', '-id')
    
    total_collections = payments.aggregate(total=Sum('amount'))['total'] or 0
    today_collections = payments.filter(payment_date=today).aggregate(total=Sum('amount'))['total'] or 0
    cash_collections = payments.filter(payment_mode='Cash').aggregate(total=Sum('amount'))['total'] or 0
    digital_collections = payments.filter(payment_mode__in=['UPI', 'Bank', 'Cheque']).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'payments': payments,
        'total_collections': float(total_collections),
        'today_collections': float(today_collections),
        'cash_collections': float(cash_collections),
        'digital_collections': float(digital_collections),
        'total_count': payments.count(),
        'page_title': 'Customer Payments (Collection)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/payment_list.html', context)


def get_customer_outstanding_invoices(request, customer_id):
    """API endpoint to get outstanding credit invoices for a customer."""
    from django.core.cache import cache
    exclude_payment_id = request.GET.get('exclude_payment_id', '')
    current_inv_id = request.GET.get('current_inv_id', '')
    cache_key = f"cust_outstanding_inv_{customer_id}_{exclude_payment_id}_{current_inv_id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data, safe=False)

    from wholesaleApp.models.sales import SalesInvoice
    from django.db.models import Sum, Q
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    invoices = SalesInvoice.objects.filter(
        customer_id=customer_id,
        payment_type='Credit',
        status__in=['Pending', 'Delivered']
    )
    
    if exclude_payment_id and exclude_payment_id.isdigit():
        invoices = invoices.annotate(
            paid_amount=Coalesce(Sum('payments__amount', filter=~Q(payments__id=int(exclude_payment_id))), Decimal('0.00'))
        )
    else:
        invoices = invoices.annotate(
            paid_amount=Coalesce(Sum('payments__amount'), Decimal('0.00'))
        )
    
    data = []
    for inv in invoices:
        outstanding = inv.net_amount - inv.paid_amount
        is_current = bool(current_inv_id and str(inv.id) == str(current_inv_id))
        if outstanding > 0 or is_current:
            data.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date.strftime('%Y-%m-%d'),
                'net_amount': float(inv.net_amount),
                'paid_amount': float(inv.paid_amount),
                'outstanding_amount': float(max(Decimal('0.00'), outstanding))
            })
            
    cache.set(cache_key, data, timeout=60)
    return JsonResponse(data, safe=False)


@transaction.atomic
def customer_payment_create(request):
    """View to record customer payment directly and adjust against a specific invoice."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_create'):
        messages.error(request, "Access Denied: You do not have permission to record payments.")
        return redirect('customer_payment_list')
        
    from wholesaleApp.models import CustomerMaster, CustomerPayment
    from wholesaleApp.views.security_helpers import get_user_permissions_context, log_activity
    from decimal import Decimal
    
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False).select_related('area', 'subarea').order_by('name')
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        invoice_id = request.POST.get('invoice')
        payment_date = request.POST.get('payment_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(payment_date):
            messages.error(request, "Action Denied: The selected payment date falls within a closed Financial Year.")
            return redirect('customer_payment_list')
            
        if not customer_id:
            messages.error(request, "Validation Error: Please select a customer.")
            return redirect('customer_payment_create')
            
        amount = Decimal(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, "Validation Error: Amount received must be greater than ₹0.00.")
            return redirect('customer_payment_create')
            
        payment_mode = request.POST.get('payment_mode', 'Cash')
        reference_no = request.POST.get('reference_no', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        
        customer = get_object_or_404(CustomerMaster, id=customer_id)
        
        payment = CustomerPayment.objects.create(
            customer=customer,
            invoice_id=invoice_id if invoice_id else None,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_mode,
            reference_no=reference_no,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Deduct from customer balance
        customer.opening_balance -= amount
        customer.save()
        
        invoice_repr = ""
        if payment.invoice:
            invoice_repr = f" adjusted against Invoice {payment.invoice.invoice_number}"
        
        log_activity(
            request,
            action='CREATE',
            model_name='CustomerPayment',
            object_id=payment.id,
            object_repr=f"Payment from {customer.name}",
            description=f"Received ₹{amount} via {payment_mode}{invoice_repr}"
        )
        
        messages.success(request, f"Payment of ₹{amount} from {customer.name} recorded successfully{invoice_repr}.")
        return redirect('customer_payment_list')
        
    context = {
        'customers': customers,
        'page_title': 'Record Customer Payment (Collection)',
        'is_edit': False,
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/payment_form.html', context)


@transaction.atomic
def customer_payment_edit(request, pk):
    """View to edit an existing customer payment collection and balance adjustment."""
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    if not has_feature_access(request.user, 'payment_collection_create'):
        messages.error(request, "Access Denied: You do not have permission to edit payments.")
        return redirect('customer_payment_list')
        
    from wholesaleApp.models import CustomerMaster, CustomerPayment
    from decimal import Decimal
    
    payment = get_object_or_404(CustomerPayment.objects.select_related('customer', 'invoice'), pk=pk)
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False).select_related('area', 'subarea').order_by('name')
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        invoice_id = request.POST.get('invoice')
        payment_date = request.POST.get('payment_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(payment_date):
            messages.error(request, "Action Denied: The selected payment date falls within a closed Financial Year.")
            return redirect('customer_payment_list')
            
        if not customer_id:
            messages.error(request, "Validation Error: Please select a customer.")
            return redirect('customer_payment_edit', pk=payment.id)
            
        new_amount = Decimal(request.POST.get('amount', 0))
        if new_amount <= 0:
            messages.error(request, "Validation Error: Amount received must be greater than ₹0.00.")
            return redirect('customer_payment_edit', pk=payment.id)
            
        payment_mode = request.POST.get('payment_mode', 'Cash')
        reference_no = request.POST.get('reference_no', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        
        new_customer = get_object_or_404(CustomerMaster, id=customer_id)
        old_customer = payment.customer
        old_amount = payment.amount
        
        # Adjust customer balances accurately
        if old_customer.id == new_customer.id:
            diff = new_amount - old_amount
            new_customer.opening_balance -= diff
            new_customer.save()
        else:
            old_customer.opening_balance += old_amount
            old_customer.save()
            new_customer.opening_balance -= new_amount
            new_customer.save()
            
        payment.customer = new_customer
        payment.invoice_id = invoice_id if invoice_id else None
        payment.payment_date = payment_date
        payment.amount = new_amount
        payment.payment_mode = payment_mode
        payment.reference_no = reference_no
        payment.remarks = remarks
        payment.save()
        
        log_activity(
            request,
            action='UPDATE',
            model_name='CustomerPayment',
            object_id=payment.id,
            object_repr=f"Payment from {new_customer.name}",
            description=f"Updated payment #{payment.id}: ₹{new_amount} via {payment_mode}"
        )
        messages.success(request, f"Payment #{payment.id} for {new_customer.name} updated successfully.")
        return redirect('customer_payment_list')
        
    context = {
        'payment': payment,
        'customers': customers,
        'page_title': f"Edit Payment #{payment.id} - {payment.customer.name}",
        'is_edit': True,
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/payment_form.html', context)


# ==================== CUSTOMER MANAGE VIEW (MARG STYLE) ====================
@login_required
def customer_manage(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    from wholesaleApp.models import SalesInvoice, CustomerPayment
    from django.db.models import Sum
    from decimal import Decimal
    from django.utils import timezone
    from datetime import timedelta

    if not has_feature_access(request.user, 'customer_view'):
        messages.error(request, "Access Denied: You do not have permission to view or manage Customers.")
        return redirect('customer_list')

    customer = get_object_or_404(CustomerMaster, pk=pk, is_deleted=False)
    manage_detail, _ = CustomerManageDetail.objects.get_or_create(customer=customer)

    if request.method == 'POST':
        if not has_feature_access(request.user, 'customer_edit'):
            messages.error(request, "Access Denied: You do not have permission to update customer settings.")
            return redirect('customer_manage', pk=pk)

        # 1. Discounts & Schemes
        manage_detail.item_discount_a = Decimal(request.POST.get('item_discount_a') or '0.00')
        manage_detail.item_discount_b = Decimal(request.POST.get('item_discount_b') or '0.00')
        manage_detail.item_discount_c = Decimal(request.POST.get('item_discount_c') or '0.00')
        manage_detail.collection_disc = Decimal(request.POST.get('collection_disc') or '0.00')
        manage_detail.min_margin = Decimal(request.POST.get('min_margin') or '0.00')
        manage_detail.volume_disc = Decimal(request.POST.get('volume_disc') or '0.00')
        manage_detail.breakage_expiry_disc = Decimal(request.POST.get('breakage_expiry_disc') or '0.00')
        manage_detail.product_scheme_notes = request.POST.get('product_scheme_notes', '').strip()

        # 2. Billing & Rates Preferences
        manage_detail.sales_rate_type = request.POST.get('sales_rate_type', 'wholesale')
        manage_detail.near_expiry_action = request.POST.get('near_expiry_action', 'allowed')
        manage_detail.new_item_billing = request.POST.get('new_item_billing') in ['on', 'true', '1']
        manage_detail.print_batch = request.POST.get('print_batch') in ['on', 'true', '1']
        manage_detail.invoice_format = request.POST.get('invoice_format', 'DEFAULT')

        # 3. Credit Limits & Payment Terms
        credit_limit_amount = Decimal(request.POST.get('credit_limit_amount') or '0.00')
        credit_days = int(request.POST.get('credit_days') or '0')
        manage_detail.credit_limit_amount = credit_limit_amount
        manage_detail.credit_limit_bills = int(request.POST.get('credit_limit_bills') or '0')
        manage_detail.credit_days = credit_days
        manage_detail.interest_percentage = Decimal(request.POST.get('interest_percentage') or '0.00')
        manage_detail.credit_limit_action = request.POST.get('credit_limit_action', 'indicate')
        manage_detail.bank_rebate_percent = Decimal(request.POST.get('bank_rebate_percent') or '0.00')
        manage_detail.bank_rebate_days = int(request.POST.get('bank_rebate_days') or '0')
        
        # Collection days checklist
        selected_days = request.POST.getlist('collection_days')
        manage_detail.collection_days = ','.join(selected_days) if selected_days else ''

        # 4. Transport & Banking
        manage_detail.transport_name = request.POST.get('transport_name', '').strip()
        manage_detail.delivery_by = request.POST.get('delivery_by', '').strip()
        manage_detail.bank_name = request.POST.get('bank_name', '').strip()
        manage_detail.bank_account_no = request.POST.get('bank_account_no', '').strip()
        manage_detail.bank_ifsc = request.POST.get('bank_ifsc', '').strip()
        manage_detail.bank_branch = request.POST.get('bank_branch', '').strip()

        # 5. Operator Note
        manage_detail.operator_note = request.POST.get('operator_note', '').strip()

        if request.user.is_authenticated and not manage_detail.created_by:
            manage_detail.created_by = request.user

        manage_detail.save()

        # Keep CustomerMaster sync'd
        customer.credit_limit = credit_limit_amount
        customer.credit_days = credit_days
        customer.save(update_fields=['credit_limit', 'credit_days'])

        log_activity(
            request,
            action='UPDATE',
            model_name='CustomerManageDetail',
            object_id=manage_detail.id,
            object_repr=f"Manage Detail: {customer.name}",
            description=f"Updated billing, discount, and credit management settings for {customer.name}"
        )

        messages.success(request, f"Management settings for '{customer.name}' updated successfully.")
        return redirect('customer_manage', pk=pk)

    # Calculate 360 Financials & Statistics
    invoices = SalesInvoice.objects.filter(customer=customer)
    total_sales = invoices.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
    total_invoices_count = invoices.count()

    payments = CustomerPayment.objects.filter(customer=customer)
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    outstanding_balance = (customer.opening_balance or Decimal('0.00')) + total_sales - total_payments

    # Aging calculations
    today = timezone.now().date()
    aging_30_days = today - timedelta(days=30)
    aging_60_days = today - timedelta(days=60)

    sales_0_30 = invoices.filter(invoice_date__gte=aging_30_days).aggregate(tot=Sum('net_amount'))['tot'] or Decimal('0.00')
    sales_31_60 = invoices.filter(invoice_date__lt=aging_30_days, invoice_date__gte=aging_60_days).aggregate(tot=Sum('net_amount'))['tot'] or Decimal('0.00')
    sales_60_plus = invoices.filter(invoice_date__lt=aging_60_days).aggregate(tot=Sum('net_amount'))['tot'] or Decimal('0.00')

    # Credit limit usage percentage
    credit_limit = manage_detail.credit_limit_amount or customer.credit_limit or Decimal('0.00')
    credit_used_pct = 0
    if credit_limit > 0:
        credit_used_pct = min(100, int((max(Decimal('0.00'), outstanding_balance) / credit_limit) * 100))

    # Active collection days set
    saved_days = [d.strip() for d in (manage_detail.collection_days or '').split(',') if d.strip()]

    context = {
        'customer': customer,
        'manage_detail': manage_detail,
        'page_title': f"Manage Customer: {customer.name}",
        'user_perms': get_user_permissions_context(request.user),
        'total_sales': total_sales,
        'total_invoices_count': total_invoices_count,
        'total_payments': total_payments,
        'outstanding_balance': outstanding_balance,
        'sales_0_30': sales_0_30,
        'sales_31_60': sales_31_60,
        'sales_60_plus': sales_60_plus,
        'credit_limit': credit_limit,
        'credit_used_pct': credit_used_pct,
        'saved_days': saved_days,
        'recent_invoices': invoices.order_by('-invoice_date', '-id')[:5],
    }
    return render(request, 'customers/customer_manage.html', context)


@login_required
def get_customer_manage_details(request, customer_id):
    """API endpoint to get customer manage preferences for billing autocomplete & alerts."""
    try:
        detail = CustomerManageDetail.objects.get(customer_id=customer_id)
        return JsonResponse({
            'success': True,
            'item_discount_a': float(detail.item_discount_a),
            'item_discount_b': float(detail.item_discount_b),
            'item_discount_c': float(detail.item_discount_c),
            'collection_disc': float(detail.collection_disc),
            'volume_disc': float(detail.volume_disc),
            'sales_rate_type': detail.sales_rate_type,
            'credit_limit_amount': float(detail.credit_limit_amount),
            'credit_limit_action': detail.credit_limit_action,
            'operator_note': detail.operator_note or '',
            'near_expiry_action': detail.near_expiry_action,
        })
    except CustomerManageDetail.DoesNotExist:
        return JsonResponse({
            'success': False,
            'item_discount_a': 0.0,
            'item_discount_b': 0.0,
            'item_discount_c': 0.0,
            'collection_disc': 0.0,
            'volume_disc': 0.0,
            'sales_rate_type': 'wholesale',
            'credit_limit_amount': 0.0,
            'credit_limit_action': 'indicate',
            'operator_note': '',
            'near_expiry_action': 'allowed',
        })