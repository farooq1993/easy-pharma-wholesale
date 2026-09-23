from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
import logging
from wholesaleApp.views.security_helpers import log_activity

logger = logging.getLogger(__name__)

def user_login(request):
    """Secure login view with premium error toast notifications."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Support case-insensitive username lookup
        try:
            user_obj = User.objects.get(username__iexact=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                auth_login(request, user)
                
                # Resolve and set the user's active tenant in session
                from wholesaleApp.models.tenant import Tenant
                user_tenant = None
                profile = getattr(user, 'profile', None)
                
                if profile and profile.tenant and profile.tenant.is_active:
                    user_tenant = profile.tenant
                elif Tenant.objects.filter(user=user, is_active=True).exists():
                    user_tenant = Tenant.objects.filter(user=user, is_active=True).first()
                    if profile:
                        profile.tenant = user_tenant
                        profile.save()
                elif user.is_superuser or (profile and profile.is_super_admin):
                    user_tenant = Tenant.objects.filter(is_active=True).first()

                if user_tenant:
                    request.session['active_tenant_id'] = user_tenant.id
                elif 'active_tenant_id' in request.session:
                    del request.session['active_tenant_id']

                messages.success(request, f"Welcome back, {user.username}!")
                log_activity(request, "LOGIN", "User", username, object_id=user.id, description=f"User '{user.username}' logged in successfully.")
                return redirect('home')
            else:
                logger.warning(f"Login failed: Account '{username}' is deactivated.")
                messages.error(request, "This account has been deactivated by the administrator.")
        else:
            logger.warning(f"Failed login attempt for username '{username}'.")
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'registration/login.html')


def user_logout(request):
    """Secure logout view."""
    if request.user.is_authenticated:
        log_activity(request, "LOGOUT", "User", request.user.username, object_id=request.user.id, description=f"User '{request.user.username}' logged out.")
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

