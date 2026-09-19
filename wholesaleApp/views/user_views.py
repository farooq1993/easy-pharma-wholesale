from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from wholesaleApp.models.permissions import UserProfile
from wholesaleApp.models.tenant import Tenant
from wholesaleApp.views.security_helpers import (
    get_user_permissions_context,
    apply_role_default_permissions,
    tenant_owner_required,
    log_activity
)

# ==================== USER MANAGEMENT CRUD ====================

@tenant_owner_required
def user_list(request):
    """List all employees/staff users belonging strictly to the logged-in Tenant Owner's firm."""
    current_profile = getattr(request.user, 'profile', None)
    tenant = getattr(request, 'tenant', None) or (current_profile.tenant if current_profile else None)
    
    if tenant:
        # Strictly filter users belonging to this logged-in tenant firm ONLY
        users = User.objects.filter(profile__tenant=tenant, is_superuser=False).select_related('profile__tenant')
    elif request.user.is_superuser:
        # Platform Superuser without active tenant filter sees all non-superuser accounts
        users = User.objects.filter(is_superuser=False).select_related('profile__tenant')
    else:
        users = User.objects.none()

    context = {
        'users': users,
        'page_title': 'User Management (Staff & Roles)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'master/user_list.html', context)


@tenant_owner_required
def user_create(request):
    """Create a new staff user & auto-assign role-based default permissions for the logged-in tenant."""
    current_profile = getattr(request.user, 'profile', None)
    tenant_obj = getattr(request, 'tenant', None) or (current_profile.tenant if current_profile else None)
    is_sa = request.user.is_superuser and not tenant_obj

    # Role choices available
    if is_sa:
        role_choices = UserProfile.ROLE_CHOICES
    else:
        # Shop Owners create staff roles for their shop
        role_choices = [
            ('Manager', 'Store Manager'),
            ('Salesman', 'Salesman / Billing Clerk'),
            ('MR', 'Medical Representative (MR)'),
            ('Inventory', 'Inventory & Purchase Clerk'),
            ('Delivery Boy', 'Delivery Boy / Field Operator'),
        ]

    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST.get('email', '').strip()
        password = request.POST['password']
        role = request.POST.get('role', 'Salesman')
        mobile = request.POST.get('mobile', '').strip()

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"User with username '{username}' already exists.")
        else:
            # Create Django user
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Setup User Profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.mobile = mobile
            profile.tenant = tenant_obj
            profile.save()

            # Apply Role Preset Default Permissions
            apply_role_default_permissions(user)

            messages.success(request, f"Staff user '{username}' successfully created with '{role}' role defaults!")
            return redirect('user_list')

    context = {
        'role_choices': role_choices,
        'is_super_admin': is_sa,
        'page_title': 'Add New Staff / Field Operator',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'master/user_form.html', context)


@tenant_owner_required
def user_edit(request, pk):
    """Edit existing staff user details within the logged-in tenant."""
    current_profile = getattr(request.user, 'profile', None)
    tenant = getattr(request, 'tenant', None) or (current_profile.tenant if current_profile else None)
    is_sa = request.user.is_superuser and not tenant

    if is_sa:
        target_user = get_object_or_404(User, id=pk, is_superuser=False)
        role_choices = UserProfile.ROLE_CHOICES
    else:
        target_user = get_object_or_404(User, id=pk, profile__tenant=tenant, is_superuser=False)
        role_choices = [
            ('Manager', 'Store Manager'),
            ('Salesman', 'Salesman / Billing Clerk'),
            ('MR', 'Medical Representative (MR)'),
            ('Inventory', 'Inventory & Purchase Clerk'),
            ('Delivery Boy', 'Delivery Boy / Field Operator'),
        ]

    profile, created = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', profile.role)
        mobile = request.POST.get('mobile', '').strip()
        reset_perms = request.POST.get('reset_role_perms') == '1'

        if User.objects.filter(username__iexact=username).exclude(id=pk).exists():
            messages.error(request, f"Username '{username}' is already in use by another user.")
        else:
            target_user.username = username
            target_user.email = email
            target_user.save()

            role_changed = (profile.role != role)
            profile.role = role
            profile.mobile = mobile
            profile.tenant = tenant or profile.tenant
            profile.save()

            # Auto sync permissions if role changed or explicitly requested
            if role_changed or reset_perms:
                apply_role_default_permissions(target_user)
                messages.success(request, f"User '{username}' role updated to '{role}' and default permissions synced.")
            else:
                messages.success(request, f"User '{username}' details updated successfully!")

            return redirect('user_list')

    context = {
        'target_user': target_user,
        'profile': profile,
        'role_choices': role_choices,
        'is_super_admin': is_sa,
        'page_title': f"Edit Staff: {target_user.username}",
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'master/user_form.html', context)


@tenant_owner_required
def user_delete(request, pk):
    """Delete a staff user within the logged-in tenant."""
    current_profile = getattr(request.user, 'profile', None)
    tenant = getattr(request, 'tenant', None) or (current_profile.tenant if current_profile else None)
    is_sa = request.user.is_superuser and not tenant

    if is_sa:
        target_user = get_object_or_404(User, id=pk, is_superuser=False)
    else:
        target_user = get_object_or_404(User, id=pk, profile__tenant=tenant, is_superuser=False)

    username = target_user.username
    target_user.delete()

    messages.success(request, f"Staff user '{username}' deleted successfully!")
    return redirect('user_list')


def create_user_public(request):
    """Create a new Super Admin user. Allowed publicly only for initial setup if no superusers exist."""
    if User.objects.filter(is_superuser=True).exists():
        if not (request.user.is_authenticated and request.user.is_superuser):
            messages.error(request, "Access Denied: Admin user registration is closed.")
            return redirect('login')

    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST.get('email', '').strip()
        password = request.POST['password']
        mobile = request.POST.get('mobile', '').strip()

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"User with username '{username}' already exists.")
        else:
            # Create Django Superuser
            user = User.objects.create_superuser(username=username, email=email, password=password)
            
            # Setup User Profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'Super Admin'
            profile.mobile = mobile
            profile.tenant = None
            profile.save()

            # Apply Role Preset Default Permissions
            apply_role_default_permissions(user)

            # Log Activity
            log_activity(
                request, 
                action='CREATE', 
                model_name='User', 
                object_repr=username, 
                object_id=user.id, 
                description="Publicly registered Super Admin user"
            )

            messages.success(request, f"Super Admin user '{username}' successfully created! Please login to configure your firm.")
            return redirect('login')

    context = {
        'page_title': 'Create Admin Account'
    }
    return render(request, 'registration/create_user.html', context)


