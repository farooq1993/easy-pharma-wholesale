from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
import logging
from wholesaleApp.models.tenant import Tenant
from wholesaleApp.views.security_helpers import get_user_permissions_context, superadmin_required, log_activity

logger = logging.getLogger(__name__)

@superadmin_required
def tenant_list(request):
    """List all tenants/firms in the system."""
    tenants = Tenant.objects.filter(Q(user=request.user) | Q(user__isnull=True))
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
        gst_dealer_type = request.POST.get('gst_dealer_type', 'Regular').strip()
        dl_number = request.POST.get('dl_number', '').strip()
        dl_expiry_date = request.POST.get('dl_expiry_date', '').strip() or None
        is_active = request.POST.get('is_active') == 'on'
        business_mode = request.POST.get('business_mode', 'Wholesale').strip()
        
        if Tenant.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Tenant with name '{name}' already exists.")
        else:
            tenant = Tenant.objects.create(
                user=request.user,
                name=name,
                company_name=company_name,
                address=address,
                phone=phone,
                email=email,
                gstin=gstin,
                gst_dealer_type=gst_dealer_type,
                dl_number=dl_number,
                dl_expiry_date=dl_expiry_date,
                is_active=is_active,
                business_mode=business_mode
            )
            log_activity(request, "CREATE", "Tenant", tenant.company_name, object_id=tenant.id, description=f"New firm/tenant '{company_name}' created.")
            
            # Link current user's profile to the new tenant if not already linked
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                if not profile.tenant:
                    profile.tenant = tenant
                    profile.save()
                    request.session['active_tenant_id'] = tenant.id

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
        gst_dealer_type = request.POST.get('gst_dealer_type', 'Regular').strip()
        dl_number = request.POST.get('dl_number', '').strip()
        dl_expiry_date = request.POST.get('dl_expiry_date', '').strip() or None
        is_active = request.POST.get('is_active') == 'on'
        business_mode = request.POST.get('business_mode', 'Wholesale').strip()
        
        if Tenant.objects.filter(name__iexact=name).exclude(id=pk).exists():
            messages.error(request, f"Tenant with name '{name}' already exists.")
        else:
            tenant.name = name
            tenant.company_name = company_name
            tenant.address = address
            tenant.phone = phone
            tenant.email = email
            tenant.gstin = gstin
            tenant.gst_dealer_type = gst_dealer_type
            tenant.dl_number = dl_number
            tenant.dl_expiry_date = dl_expiry_date
            tenant.is_active = is_active
            tenant.business_mode = business_mode
            tenant.save()
            log_activity(request, "UPDATE", "Tenant", tenant.company_name, object_id=tenant.id, description=f"Tenant '{name}' updated.")
            messages.success(request, f"Tenant '{name}' updated successfully.")
            return redirect('tenant_list')
            
    context = {
        'tenant': tenant,
        'page_title': f"Edit Tenant: {tenant.name}",
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'tenant/tenant_form.html', context)


def tenant_email_settings(request):
    """View for Tenant Admin/Owner to configure SMTP details for sending bills."""
    from wholesaleApp.models.tenant import TenantEmailConfig
    
    # Check permissions
    is_admin = request.user.is_superuser
    if not is_admin and hasattr(request.user, 'profile'):
        is_admin = request.user.profile.is_tenant_admin or request.user.profile.is_super_admin
        
    if not is_admin:
        messages.error(request, "Access Denied: You do not have permission to manage email settings.")
        return redirect('home')

    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "No active Tenant/Firm detected in the context.")
        return redirect('home')

    # Get or create SMTP config for this tenant
    config, created = TenantEmailConfig.objects.get_or_create(tenant=tenant)

    if request.method == 'POST':
        email_host = request.POST.get('email_host', '').strip()
        email_port = request.POST.get('email_port', '').strip()
        email_use_tls = request.POST.get('email_use_tls') == 'on'
        email_use_ssl = request.POST.get('email_use_ssl') == 'on'
        email_host_user = request.POST.get('email_host_user', '').strip()
        email_host_password = request.POST.get('email_host_password', '').strip()
        default_from_email = request.POST.get('default_from_email', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        # Basic validations
        if not email_host or not email_host_user or not email_port:
            messages.error(request, "SMTP Host, Port, and Username/Email are required.")
        else:
            try:
                config.email_host = email_host
                config.email_port = int(email_port)
                config.email_use_tls = email_use_tls
                config.email_use_ssl = email_use_ssl
                config.email_host_user = email_host_user
                
                # Only update password if a new value is entered
                if email_host_password:
                    config.email_host_password = email_host_password
                    
                config.default_from_email = default_from_email
                config.is_active = is_active
                config.save()
                log_activity(request, "UPDATE", "TenantEmailConfig", tenant.company_name, object_id=config.id, description=f"SMTP Email settings for '{tenant.company_name}' updated.")
                
                messages.success(request, f"SMTP Email configuration for '{tenant.company_name}' updated successfully.")
                return redirect('tenant_email_settings')
            except ValueError:
                messages.error(request, "Invalid Port number.")
            except Exception as e:
                logger.error(f"Error updating SMTP settings for tenant {tenant.id}: {e}")
                messages.error(request, f"Error saving configuration: {str(e)}")

    context = {
        'config': config,
        'tenant': tenant,
        'page_title': 'Email Configuration (SMTP)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'tenant/email_settings.html', context)



