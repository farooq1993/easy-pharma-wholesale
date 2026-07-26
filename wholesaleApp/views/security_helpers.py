from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from wholesaleApp.models.permissions import AppGroupModule, AppFeature, UserFeaturePermission, UserProfile
from wholesaleApp.models.tenant import Tenant

# ==================== ROLE DEFAULT PERMISSIONS PRESETS ====================
ROLE_DEFAULT_PERMISSIONS = {
    'Super Admin': '__ALL__',
    'Owner': '__ALL__',
    'Manager': [
        'sales_create', 'sales_return', 'sales_reprint', 'sales_credit_debit', 'view_margins',
        'purchase_create', 'purchase_list',
        'customer_ledger', 'payment_collection', 'report_outstanding',
        'product_crud', 'customer_crud', 'supplier_crud', 'area_crud'
    ],
    'Salesman': [
        'sales_create', 'sales_reprint', 'customer_ledger', 'payment_collection'
    ],
    'Inventory': [
        'purchase_create', 'purchase_list', 'product_crud', 'supplier_crud'
    ],
    'Delivery Boy': [
        'sales_reprint', 'payment_collection', 'report_outstanding'
    ],
    'MR': [
        'sales_create', 'sales_reprint', 'customer_ledger', 'payment_collection', 'report_outstanding'
    ]
}

def apply_role_default_permissions(user):
    """Grant or sync default feature permissions based on the user's Profile Role."""
    if not hasattr(user, 'profile'):
        return
    
    role = user.profile.role
    all_features = AppFeature.objects.filter(is_active=True)
    
    if user.is_superuser or role in ['Super Admin', 'Owner']:
        for f in all_features:
            perm, _ = UserFeaturePermission.objects.get_or_create(user=user, feature=f)
            perm.is_granted = True
            perm.save()
        return

    allowed_codenames = set(ROLE_DEFAULT_PERMISSIONS.get(role, []))
    for f in all_features:
        perm, _ = UserFeaturePermission.objects.get_or_create(user=user, feature=f)
        perm.is_granted = (f.codename in allowed_codenames)
        perm.save()


def has_feature_access(user, codename):
    """Check if the user is granted access to a specific feature codename."""
    if not user.is_authenticated:
        return True  # Support anonymous testing / local dev
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Super Admin', 'Owner']):
        return True
    return UserFeaturePermission.objects.filter(
        user=user,
        feature__codename=codename,
        feature__is_active=True,
        is_granted=True
    ).exists()


def get_user_permissions_context(user):
    """Return a set of all feature codenames granted to the user."""
    if not user.is_authenticated:
        return {f.codename for f in AppFeature.objects.filter(is_active=True)}
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Super Admin', 'Owner']):
        return {f.codename for f in AppFeature.objects.filter(is_active=True)}
    return {
        p.feature.codename 
        for p in UserFeaturePermission.objects.filter(
            user=user, 
            is_granted=True, 
            feature__is_active=True
        ).select_related('feature')
    }


# ==================== VIEW PROTECTION DECORATORS ====================
def permission_required(codename, redirect_to='home'):
    """Decorator for views that checks if user has specific feature permission codename."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please login to access this section.")
                return redirect('login')
            if not has_feature_access(request.user, codename):
                messages.error(request, f"Access Denied: You do not have permission for feature '{codename}'.")
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def tenant_owner_required(view_func):
    """Decorator for views accessible only to Tenant Owners or SaaS Super Admins."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this section.")
            return redirect('login')
        if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_tenant_admin)):
            messages.error(request, "Access Denied: Only Shop Owners or System Admins can access this section.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def superadmin_required(view_func):
    """Decorator for views accessible strictly to SaaS Super Admins."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this section.")
            return redirect('login')
        if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_super_admin)):
            messages.error(request, "Access Denied: Restricted to SaaS Platform Administrators.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def seed_default_tenant():
    """Ensure at least one default tenant exists."""
    default_tenant, created = Tenant.objects.get_or_create(
        name="Default Tenant",
        defaults={
            "company_name": "EasyPharma Wholesale Default",
            "address": "123 Main Street, Central City",
            "phone": "9876543210",
            "email": "info@easypharma.com",
            "gstin": "27AAPCG1234F1Z5",
            "dl_number": "DL-12345/20A/21B"
        }
    )
    return default_tenant


def seed_default_permissions():
    """Seed the database with default Modules, Features, and Role Presets."""
    default_tenant = seed_default_tenant()

    DEFAULT_PERMISSIONS = {
        'Sales & Billing': [
            ('sales_create', 'New Sale Bill'),
            ('sales_return', 'Sales Return'),
            ('sales_reprint', 'Re-print Sale Bill'),
            ('sales_credit_debit', 'Credit / Debit Notes'),
            ('view_margins', 'View Profit Margins & Cost Rates'),
        ],
        'Purchase & Inventory': [
            ('purchase_create', 'New Purchase Entry'),
            ('purchase_list', 'View Purchase History'),
        ],
        'Accounts & Collection': [
            ('customer_ledger', 'View Customer Ledger'),
            ('payment_collection', 'Record / Collect Payments'),
            ('report_outstanding', 'View Outstanding dues report'),
        ],
        'Master Data Settings': [
            ('product_crud', 'Manage Products (Add/Edit)'),
            ('customer_crud', 'Manage Customers (Add/Edit)'),
            ('supplier_crud', 'Manage Suppliers (Add/Edit)'),
            ('area_crud', 'Manage Areas & Subareas'),
        ]
    }

    for module_name, features in DEFAULT_PERMISSIONS.items():
        module, created = AppGroupModule.objects.get_or_create(name=module_name)
        for codename, name in features:
            AppFeature.objects.get_or_create(
                codename=codename,
                defaults={'module': module, 'name': name, 'is_active': True}
            )

    # Ensure UserProfile exists for all users and has a tenant
    for user in User.objects.all():
        profile, created = UserProfile.objects.get_or_create(user=user)
        if not profile.tenant:
            profile.tenant = default_tenant
        if user.is_superuser:
            profile.role = 'Super Admin'
        profile.save()

    # Assign all legacy/existing business objects without a tenant to the default tenant
    from wholesaleApp.models.customers import AreaMaster, SubareaMaster, CustomerMaster
    from wholesaleApp.models.supplier import SupplierMaster
    from wholesaleApp.models.products import CompanyMaster, DrugMaster, ProductTypeMaster, ProductMaster
    from wholesaleApp.models.purchase import ProductBatch, PurchaseOrder, PurchaseOrderItem, PurchaseEntry, PurchaseEntryItem
    from wholesaleApp.models.sales import SalesInvoice, SalesInvoiceItem

    models_to_update = [
        AreaMaster, SubareaMaster, CustomerMaster, SupplierMaster,
        CompanyMaster, DrugMaster, ProductTypeMaster, ProductMaster,
        ProductBatch, PurchaseOrder, PurchaseOrderItem, PurchaseEntry,
        PurchaseEntryItem, SalesInvoice, SalesInvoiceItem
    ]
    for model in models_to_update:
        if hasattr(model, 'unfiltered_objects'):
            model.unfiltered_objects.filter(tenant__isnull=True).update(tenant=default_tenant)

    # Sync default permissions for all users
    for user in User.objects.all():
        apply_role_default_permissions(user)


def user_perms_context_processor(request):
    """Context processor to make user_perms set and profile role globally available in all templates."""
    context = {
        'user_perms': get_user_permissions_context(request.user),
        'user_profile': getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    }
    return context


def tenant_context_processor(request):
    """Context processor to make tenant info globally available in templates."""
    context = {
        'current_tenant': getattr(request, 'tenant', None),
        'tenants_list': [],
    }
    if request.user.is_authenticated and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_super_admin)):
        context['tenants_list'] = Tenant.objects.filter(is_active=True)
    return context


import logging
logger = logging.getLogger('wholesaleApp')

def log_activity(request, action, model_name, object_repr, object_id=None, description=""):
    """Helper to log user actions both to Python logger and database ActivityLog."""
    from wholesaleApp.models.logs import ActivityLog
    
    user_str = request.user.username if (request and request.user and request.user.is_authenticated) else "System"
    logger.info(f"User: {user_str} | Action: {action} | Model: {model_name} | Key: {object_repr} | Details: {description}")
    
    tenant = getattr(request, 'tenant', None) if request else None
    user = request.user if (request and request.user and request.user.is_authenticated) else None
    
    try:
        ActivityLog.objects.create(
            tenant=tenant,
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr[:255] if object_repr else "",
            description=description
        )
    except Exception as e:
        logger.error(f"Error saving ActivityLog to database: {e}")


