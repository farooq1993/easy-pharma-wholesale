from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages

def user_login(request):
    """Secure login view with premium error toast notifications."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password']

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
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('home')
            else:
                messages.error(request, "This account has been deactivated by the administrator.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'registration/login.html')


def user_logout(request):
    """Secure logout view."""
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')
