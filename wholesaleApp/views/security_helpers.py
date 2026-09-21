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
        'sales_view', 'sales_create', 'sales_edit', 'sales_delete', 'sales_reprint',
        'sales_return_view', 'sales_return_create', 'sales_return_delete',
        'sales_credit_debit_view', 'sales_credit_debit_create', 'sales_credit_debit_delete',
        'view_margins',
        'po_view', 'po_create',
        'purchase_view', 'purchase_create', 'purchase_edit', 'purchase_delete',
        'purchase_return_view', 'purchase_return_create', 'purchase_return_delete',
        'supplier_payment_view', 'supplier_payment_create', 'supplier_payment_delete',
        'customer_ledger',
        'payment_collection_view', 'payment_collection_create', 'payment_collection_delete',
        'report_outstanding',
        'product_view', 'product_create', 'product_edit', 'product_delete',
        'customer_view', 'customer_create', 'customer_edit', 'customer_delete',
        'supplier_view', 'supplier_create', 'supplier_edit', 'supplier_delete',
        'area_view', 'area_create', 'area_edit', 'area_delete'
    ],
    'Salesman': [
        'sales_view', 'sales_create', 'sales_reprint', 'customer_ledger',
        'payment_collection_view', 'payment_collection_create'
    ],
    'Inventory': [
        'po_view', 'po_create',
        'purchase_view', 'purchase_create', 'purchase_edit', 'purchase_delete',
        'product_view', 'product_create', 'product_edit', 'product_delete',
        'supplier_view', 'supplier_create', 'supplier_edit', 'supplier_delete'
    ],
    'Delivery Boy': [
        'sales_view', 'sales_reprint', 'payment_collection_view', 'payment_collection_create', 'report_outstanding'
    ],
    'MR': [
        'sales_view', 'sales_create', 'sales_reprint', 'customer_ledger',
        'payment_collection_view', 'payment_collection_create', 'report_outstanding'
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
        return False
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
        return set()
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
        if not request.user.is_superuser:
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
    from django.core.cache import cache
    if cache.get('permissions_seeded_v1') and AppFeature.objects.filter(is_active=True).exists():
        return

    default_tenant = seed_default_tenant()

    DEFAULT_PERMISSIONS = {
        'Sales & Billing': [
            ('sales_view', 'View Sale Bills'),
            ('sales_create', 'New Sale Bill'),
            ('sales_edit', 'Edit Sale Bill'),
            ('sales_delete', 'Delete Sale Bill'),
            ('sales_reprint', 'Re-print Sale Bill'),
            ('sales_return_view', 'View Sales Return'),
            ('sales_return_create', 'New Sales Return'),
            ('sales_return_delete', 'Delete Sales Return'),
            ('sales_credit_debit_view', 'View Credit / Debit Notes'),
            ('sales_credit_debit_create', 'New Credit / Debit Note'),
            ('sales_credit_debit_delete', 'Delete Credit / Debit Note'),
            ('view_margins', 'View Profit Margins & Cost Rates'),
        ],
        'Purchase & Inventory': [
            ('po_view', 'View Purchase Orders'),
            ('po_create', 'New Purchase Order'),
            ('purchase_view', 'View Purchase History'),
            ('purchase_create', 'New Purchase Entry'),
            ('purchase_edit', 'Edit Purchase Entry'),
            ('purchase_delete', 'Delete Purchase Entry'),
            ('purchase_return_view', 'View Purchase Returns'),
            ('purchase_return_create', 'New Purchase Return'),
            ('purchase_return_delete', 'Delete Purchase Return'),
            ('supplier_payment_view', 'View Supplier Payments'),
            ('supplier_payment_create', 'New Supplier Payment'),
            ('supplier_payment_delete', 'Delete Supplier Payment'),
        ],
        'Accounts & Collection': [
            ('customer_ledger', 'View Customer Ledger'),
            ('payment_collection_view', 'View Payments Collection'),
            ('payment_collection_create', 'Record / Collect Payments'),
            ('payment_collection_delete', 'Delete Payments Collection'),
            ('report_outstanding', 'View Outstanding dues report'),
        ],
        'Master Data Settings': [
            ('product_view', 'View Products'),
            ('product_create', 'Add Product'),
            ('product_edit', 'Edit Product'),
            ('product_delete', 'Delete Product'),
            ('customer_view', 'View Customers'),
            ('customer_create', 'Add Customer'),
            ('customer_edit', 'Edit Customer'),
            ('customer_delete', 'Delete Customer'),
            ('supplier_view', 'View Suppliers'),
            ('supplier_create', 'Add Supplier'),
            ('supplier_edit', 'Edit Supplier'),
            ('supplier_delete', 'Delete Supplier'),
            ('area_view', 'View Areas & Subareas'),
            ('area_create', 'Add Area/Subarea'),
            ('area_edit', 'Edit Area/Subarea'),
            ('area_delete', 'Delete Area/Subarea'),
        ]
    }

    new_codenames = set()
    for module_name, features in DEFAULT_PERMISSIONS.items():
        module, created = AppGroupModule.objects.get_or_create(name=module_name)
        for codename, name in features:
            new_codenames.add(codename)
            AppFeature.objects.get_or_create(
                codename=codename,
                defaults={'module': module, 'name': name, 'is_active': True}
            )

    # Deactivate obsolete features
    AppFeature.objects.exclude(codename__in=new_codenames).update(is_active=False)

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

    cache.set('permissions_seeded_v1', True, timeout=86400)


def user_perms_context_processor(request):
    """Context processor to make user_perms set and profile role globally available in all templates."""
    context = {
        'user_perms': get_user_permissions_context(request.user),
        'user_profile': getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    }
    return context


def tenant_context_processor(request):
    """Context processor to make logged-in tenant firm info globally available in templates."""
    current_tenant = getattr(request, 'tenant', None)
    if not current_tenant and hasattr(request, 'user') and request.user.is_authenticated:
        session_tenant_id = request.session.get('active_tenant_id')
        if session_tenant_id:
            current_tenant = Tenant.objects.filter(id=session_tenant_id, is_active=True).first()
        if not current_tenant and hasattr(request.user, 'profile') and request.user.profile.tenant:
            current_tenant = request.user.profile.tenant
        if not current_tenant:
            current_tenant = Tenant.objects.filter(is_active=True).first()

    context = {
        'current_tenant': current_tenant,
        'tenants_list': [],
    }
    if hasattr(request, 'user') and request.user.is_authenticated and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_super_admin)):
        from django.db.models import Q
        context['tenants_list'] = Tenant.objects.filter(Q(user=request.user) | Q(user__isnull=True), is_active=True)
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


