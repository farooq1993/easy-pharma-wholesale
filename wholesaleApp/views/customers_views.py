from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from wholesaleApp.models.customers import CustomerMaster, AreaMaster, SubareaMaster

# ==================== CUSTOMER MASTER VIEWS ====================
# @login_required
def customer_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'customer_view'):
        messages.error(request, "Access Denied: You do not have permission to view Customers.")
        return redirect('home')
        
    customers = CustomerMaster.objects.filter(is_deleted=False).select_related('area')
    context = {
        'customers': customers,
        'page_title': 'Customer Master',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_list.html', context)

# @login_required
def customer_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'customer_create'):
        messages.error(request, "Access Denied: You do not have permission to create Customers.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True)
    if request.method == 'POST':
        # Form handling
        customer = CustomerMaster(
            name=request.POST['name'],
            customer_type=request.POST.get('customer_type', 'Retailer'),
            mobile=request.POST['mobile'],
            alternate_mobile=request.POST.get('alternate_mobile', ''),
            email=request.POST.get('email', ''),
            gstin=request.POST.get('gstin', ''),
            dl_number_1=request.POST.get('dl_number_1', ''),
            dl_number_2=request.POST.get('dl_number_2', ''),
            dl_number_3=request.POST.get('dl_number_3', ''),
            area_id=request.POST['area'],
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            pincode=request.POST.get('pincode', ''),
            opening_balance=request.POST.get('opening_balance', 0),
            credit_limit=request.POST.get('credit_limit', 0),
            credit_days=request.POST.get('credit_days', 0),
            created_by=request.user if request.user.is_authenticated else None
        )
        customer.save()
        
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
        'page_title': 'Add New Customer',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_form.html', context)

# @login_required
def customer_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'customer_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Customers.")
        return redirect('home')
        
    customer = get_object_or_404(CustomerMaster, pk=pk, is_deleted=False)
    areas = AreaMaster.objects.filter(is_active=True)
    
    if request.method == 'POST':
        customer.name = request.POST['name']
        customer.customer_type = request.POST.get('customer_type', 'Retailer')
        customer.mobile = request.POST['mobile']
        customer.alternate_mobile = request.POST.get('alternate_mobile', '')
        customer.email = request.POST.get('email', '')
        customer.gstin = request.POST.get('gstin', '')
        customer.dl_number_1 = request.POST.get('dl_number_1', '')
        customer.dl_number_2 = request.POST.get('dl_number_2', '')
        customer.dl_number_3 = request.POST.get('dl_number_3', '')
        customer.area_id = request.POST['area']
        customer.address = request.POST.get('address', '')
        customer.city = request.POST.get('city', '')
        customer.state = request.POST.get('state', '')
        customer.pincode = request.POST.get('pincode', '')
        customer.opening_balance = request.POST.get('opening_balance', 0)
        customer.credit_limit = request.POST.get('credit_limit', 0)
        customer.credit_days = request.POST.get('credit_days', 0)
        customer.save()
        messages.success(request, 'Customer updated successfully!')
        return redirect('customer_list')
    
    context = {
        'customer': customer, 
        'areas': areas, 
        'page_title': 'Edit Customer',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/customer_form.html', context)

# @login_required
def customer_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'customer_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Customers.")
        return redirect('home')
        
    customer = get_object_or_404(CustomerMaster, pk=pk)
    customer.is_deleted = True
    customer.save()
    messages.success(request, 'Customer deleted successfully!')
    return redirect('customer_list')


# ==================== AREA MASTER VIEWS ====================
# @login_required
def area_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_view'):
        messages.error(request, "Access Denied: You do not have permission to view Areas.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True)
    subareas = SubareaMaster.objects.filter(is_active=True).select_related('area')
    context = {
        'areas': areas,
        'subareas': subareas,
        'page_title': 'Area & Subarea Master',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/area_list.html', context)

# @login_required
def area_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_create'):
        messages.error(request, "Access Denied: You do not have permission to create Areas.")
        return redirect('home')
        
    if request.method == 'POST':
        city = request.POST['city']
        code = request.POST.get('code', '')
        
        # Check if already exists
        if AreaMaster.objects.filter(city__iexact=city).exists():
            messages.error(request, f"Area for city '{city}' already exists.")
        else:
            area = AreaMaster(city=city, code=code)
            area.save()
            messages.success(request, 'Area created successfully!')
            return redirect('area_list')
            
    context = {
        'page_title': 'Add New Area',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/area_form.html', context)

# @login_required
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

# @login_required
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
# @login_required
def subarea_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'area_create'):
        messages.error(request, "Access Denied: You do not have permission to create Subareas.")
        return redirect('home')
        
    areas = AreaMaster.objects.filter(is_active=True)
    if request.method == 'POST':
        area_id = request.POST['area']
        name = request.POST['name']
        
        if SubareaMaster.objects.filter(area_id=area_id, name__iexact=name).exists():
            messages.error(request, f"Subarea '{name}' already exists in this area.")
        else:
            subarea = SubareaMaster(area_id=area_id, name=name)
            subarea.save()
            messages.success(request, 'Subarea created successfully!')
            return redirect('area_list')
            
    context = {
        'areas': areas, 
        'page_title': 'Add New Subarea',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/subarea_form.html', context)

# @login_required
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

# @login_required
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
# @login_required
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
                'url': f"/invoice/print/{inv.id}/"
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


# @login_required
from django.db import transaction
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


# @login_required
@transaction.atomic
def customer_payment_delete(request, pk):
    from wholesaleApp.models import CustomerPayment
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete payments.")
        return redirect(f"/customer/ledger/?customer={get_object_or_404(CustomerPayment, pk=pk).customer.id}")
    
    payment = get_object_or_404(CustomerPayment, pk=pk)
    customer = payment.customer
    
    # Add amount back to customer balance
    customer.opening_balance += payment.amount
    customer.save()
    
    # Delete payment
    payment.delete()
    
    messages.success(request, "Payment deleted and customer balance adjusted.")
    return redirect(f"/customer/ledger/?customer={customer.id}")


def customer_payment_list(request):
    """View to list all customer payments (collections)."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'payment_collection_view'):
        messages.error(request, "Access Denied: You do not have permission to view Payments Collection.")
        return redirect('home')
        
    from wholesaleApp.models import CustomerPayment
    from wholesaleApp.views.security_helpers import get_user_permissions_context
    
    payments = CustomerPayment.objects.all().select_related('customer')
    context = {
        'payments': payments,
        'page_title': 'Customer Payments (Collection)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/payment_list.html', context)


def get_customer_outstanding_invoices(request, customer_id):
    """API endpoint to get outstanding credit invoices for a customer."""
    from wholesaleApp.models.sales import SalesInvoice
    from django.db.models import Sum
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    invoices = SalesInvoice.objects.filter(
        customer_id=customer_id,
        payment_type='Credit',
        status__in=['Pending', 'Delivered']
    ).annotate(
        paid_amount=Coalesce(Sum('payments__amount'), Decimal('0.00'))
    )
    
    data = []
    for inv in invoices:
        outstanding = inv.net_amount - inv.paid_amount
        if outstanding > 0:
            data.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date.strftime('%Y-%m-%d'),
                'net_amount': float(inv.net_amount),
                'paid_amount': float(inv.paid_amount),
                'outstanding_amount': float(outstanding)
            })
            
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
    
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        invoice_id = request.POST.get('invoice')
        payment_date = request.POST.get('payment_date')
        amount = Decimal(request.POST.get('amount', 0))
        payment_mode = request.POST.get('payment_mode', 'Cash')
        reference_no = request.POST.get('reference_no', '')
        remarks = request.POST.get('remarks', '')
        
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
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'customers/payment_form.html', context)