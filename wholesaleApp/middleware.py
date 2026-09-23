from wholesaleApp.models.tenant import Tenant, set_current_tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check session for an active tenant ID
            session_tenant_id = request.session.get('active_tenant_id')
            if session_tenant_id:
                try:
                    tenant = Tenant.objects.get(id=session_tenant_id, is_active=True)
                except Tenant.DoesNotExist:
                    tenant = None
            
            # If no valid active tenant in session, look up user's assigned or owned tenant
            if not tenant and hasattr(request.user, 'profile') and request.user.profile.tenant and request.user.profile.tenant.is_active:
                tenant = request.user.profile.tenant
                request.session['active_tenant_id'] = tenant.id

            if not tenant:
                owned_tenant = Tenant.objects.filter(user=request.user, is_active=True).first()
                if owned_tenant:
                    tenant = owned_tenant
                    request.session['active_tenant_id'] = tenant.id
                    if hasattr(request.user, 'profile') and not request.user.profile.tenant:
                        request.user.profile.tenant = owned_tenant
                        request.user.profile.save()

            # Fallback for SaaS Super Admin / Superuser
            if not tenant and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_super_admin)):
                tenant = Tenant.objects.filter(is_active=True).first()
                if tenant:
                    request.session['active_tenant_id'] = tenant.id
        
        # Set the thread-local tenant
        set_current_tenant(tenant)
        request.tenant = tenant

        try:
            return self.get_response(request)
        finally:
            # Clear thread-local tenant to prevent memory leaks / context bleeding
            set_current_tenant(None)
