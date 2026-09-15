from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging
from wholesaleApp.models import SupplierMaster
from wholesaleApp.views.security_helpers import has_feature_access, log_activity

logger = logging.getLogger(__name__)

@login_required
def supplier_list(request):
    if not has_feature_access(request.user, 'supplier_view'):
        messages.error(request, "Access Denied: You do not have permission to view Supplier Master.")
        return redirect('home')
    suppliers = SupplierMaster.objects.filter(is_deleted=False)
    context = {
        'suppliers': suppliers,
        'page_title': 'Supplier Master'
    }
    return render(request, 'suppliers/supplier_list.html', context)

@login_required
def supplier_create(request):
    if not has_feature_access(request.user, 'supplier_create'):
        messages.error(request, "Access Denied: You do not have permission to add Supplier Master.")
        return redirect('supplier_list')
    if request.method == 'POST':
        supplier = SupplierMaster(
            name=request.POST['name'],
            mobile=request.POST['mobile'],
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            pincode=request.POST.get('pincode', ''),
            opening_balance=request.POST.get('opening_balance', 0),
            credit_limit=request.POST.get('credit_limit', 0),
            credit_days=request.POST.get('credit_days', 0),
            created_by=request.user if request.user.is_authenticated else None
        )
        supplier.save()
        log_activity(request, "CREATE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' (Mobile: {supplier.mobile}) created.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({
                'status': 'success',
                'id': supplier.id,
                'name': supplier.name,
                'mobile': supplier.mobile
            })
            
        messages.success(request, 'Supplier created successfully!')
        return redirect('supplier_list')
    
    context = {'page_title': 'Add New Supplier'}
    return render(request, 'suppliers/supplier_form.html', context)

@login_required
def supplier_edit(request, pk):
    if not has_feature_access(request.user, 'supplier_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Supplier Master.")
        return redirect('supplier_list')
    supplier = get_object_or_404(SupplierMaster, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        supplier.name = request.POST['name']
        supplier.mobile = request.POST['mobile']
        supplier.address = request.POST.get('address', '')
        supplier.city = request.POST.get('city', '')
        supplier.state = request.POST.get('state', '')
        supplier.pincode = request.POST.get('pincode', '')
        supplier.opening_balance = request.POST.get('opening_balance', 0)
        supplier.credit_limit = request.POST.get('credit_limit', 0)
        supplier.credit_days = request.POST.get('credit_days', 0)
        supplier.save()
        log_activity(request, "UPDATE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' updated.")
        messages.success(request, 'Supplier updated successfully!')
        return redirect('supplier_list')
    
    context = {'supplier': supplier, 'page_title': 'Edit Supplier'}
    return render(request, 'suppliers/supplier_form.html', context)

@login_required
def supplier_delete(request, pk):
    if not has_feature_access(request.user, 'supplier_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Supplier Master.")
        return redirect('supplier_list')
    supplier = get_object_or_404(SupplierMaster, pk=pk)
    supplier.is_deleted = True
    supplier.save()
    log_activity(request, "DELETE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' soft deleted.")
    messages.success(request, 'Supplier deleted successfully!')
    return redirect('supplier_list')