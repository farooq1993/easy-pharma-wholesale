from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from wholesaleApp.models.tenant import Tenant
from wholesaleApp.views.security_helpers import get_user_permissions_context, superadmin_required

@superadmin_required
def tenant_list(request):
    """List all tenants/firms in the system."""
    tenants = Tenant.objects.all()
    context = {
        'tenants': tenants,
        'page_title': 'Tenant / Firm Management',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'tenant/tenant_list.html', context)


@superadmin_required
def tenant_create(request):
    """Create a new tenant/firm."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        company_name = request.POST.get('company_name', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        gstin = request.POST.get('gstin', '').strip()
        dl_number = request.POST.get('dl_number', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if Tenant.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Tenant with name '{name}' already exists.")
        else:
            Tenant.objects.create(
                name=name,
                company_name=company_name,
                address=address,
                phone=phone,
                email=email,
                gstin=gstin,
                dl_number=dl_number,
                is_active=is_active
            )
            messages.success(request, f"Tenant '{name}' created successfully.")
            return redirect('tenant_list')
            
    context = {
        'page_title': 'Create New Tenant (Firm / Shop)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'tenant/tenant_form.html', context)


@superadmin_required
def tenant_edit(request, pk):
    """Edit details of an existing tenant/firm."""
    tenant = get_object_or_404(Tenant, id=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        company_name = request.POST.get('company_name', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        gstin = request.POST.get('gstin', '').strip()
        dl_number = request.POST.get('dl_number', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if Tenant.objects.filter(name__iexact=name).exclude(id=pk).exists():
            messages.error(request, f"Tenant with name '{name}' already exists.")
        else:
            tenant.name = name
            tenant.company_name = company_name
            tenant.address = address
            tenant.phone = phone
            tenant.email = email
            tenant.gstin = gstin
            tenant.dl_number = dl_number
            tenant.is_active = is_active
            tenant.save()
            messages.success(request, f"Tenant '{name}' updated successfully.")
            return redirect('tenant_list')
            
    context = {
        'tenant': tenant,
        'page_title': f"Edit Tenant: {tenant.name}",
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'tenant/tenant_form.html', context)

