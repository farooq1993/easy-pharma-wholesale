from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from wholesaleApp.models import ProductMaster, SchemeMaster
from wholesaleApp.views.security_helpers import permission_required, log_activity, get_user_permissions_context

@permission_required('product_crud')
def scheme_list(request):
    schemes = SchemeMaster.objects.all().select_related('product')
    context = {
        'schemes': schemes,
        'page_title': 'Scheme & Discount Master',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'schemes/scheme_list.html', context)

@permission_required('product_crud')
def scheme_create(request):
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    if request.method == 'POST':
        name = request.POST.get('name')
        product_id = request.POST.get('product')
        billed_qty = int(request.POST.get('billed_qty', 0))
        free_qty = int(request.POST.get('free_qty', 0))
        discount_percentage = Decimal(request.POST.get('discount_percentage', 0))
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = request.POST.get('is_active') == 'on'

        product = get_object_or_404(ProductMaster, id=product_id)

        scheme = SchemeMaster.objects.create(
            name=name,
            product=product,
            billed_qty=billed_qty,
            free_qty=free_qty,
            discount_percentage=discount_percentage,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            created_by=request.user if request.user.is_authenticated else None
        )

        log_activity(
            request,
            action='CREATE',
            model_name='SchemeMaster',
            object_id=scheme.id,
            object_repr=scheme.name,
            description=f"Created scheme for {product.name} (Buy {billed_qty} get {free_qty} + {discount_percentage}%)"
        )

        messages.success(request, f"Scheme '{name}' created successfully.")
        return redirect('scheme_list')

    context = {
        'products': products,
        'page_title': 'Create Scheme',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'schemes/scheme_form.html', context)

@permission_required('product_crud')
def scheme_edit(request, pk):
    scheme = get_object_or_404(SchemeMaster, pk=pk)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        scheme.name = request.POST.get('name')
        scheme.product_id = request.POST.get('product')
        scheme.billed_qty = int(request.POST.get('billed_qty', 0))
        scheme.free_qty = int(request.POST.get('free_qty', 0))
        scheme.discount_percentage = Decimal(request.POST.get('discount_percentage', 0))
        scheme.start_date = request.POST.get('start_date')
        scheme.end_date = request.POST.get('end_date')
        scheme.is_active = request.POST.get('is_active') == 'on'
        scheme.save()

        log_activity(
            request,
            action='UPDATE',
            model_name='SchemeMaster',
            object_id=scheme.id,
            object_repr=scheme.name,
            description=f"Updated scheme: Buy {scheme.billed_qty} get {scheme.free_qty} + {scheme.discount_percentage}%"
        )

        messages.success(request, f"Scheme '{scheme.name}' updated successfully.")
        return redirect('scheme_list')

    # Format dates for form inputs
    start_date_str = scheme.start_date.strftime('%Y-%m-%d') if scheme.start_date else ''
    end_date_str = scheme.end_date.strftime('%Y-%m-%d') if scheme.end_date else ''

    context = {
        'scheme': scheme,
        'products': products,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'page_title': 'Edit Scheme',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'schemes/scheme_form.html', context)

@permission_required('product_crud')
def scheme_delete(request, pk):
    scheme = get_object_or_404(SchemeMaster, pk=pk)
    name = scheme.name
    
    log_activity(
        request,
        action='DELETE',
        model_name='SchemeMaster',
        object_id=scheme.id,
        object_repr=name,
        description=f"Deleted scheme '{name}'"
    )
    
    scheme.delete()
    messages.success(request, f"Scheme '{name}' deleted successfully.")
    return redirect('scheme_list')
