from django.urls import path
from wholesaleApp.views.master import HomeView, user_permission_matrix, switch_tenant, activity_log_list
from wholesaleApp.views.user_views import (
    user_list,
    user_create,
    user_edit,
    user_delete,
    create_user_public
)
from wholesaleApp.views.auth_views import user_login, user_logout
from wholesaleApp.views.tenant_views import (
    tenant_list,
    tenant_create,
    tenant_edit,
    tenant_email_settings
)


urlpatterns = [
    path('', HomeView, name='home'),
    path('settings/permissions/', user_permission_matrix, name='user_permission_matrix'),
    path('switch-tenant/', switch_tenant, name='switch_tenant'),
    path('settings/logs/', activity_log_list, name='activity_log_list'),
    
    # User Authentication
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('createuser/', create_user_public, name='create_user_public'),
    
    # User Management CRUD
    path('settings/users/', user_list, name='user_list'),
    path('settings/users/create/', user_create, name='user_create'),
    path('settings/users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('settings/users/<int:pk>/delete/', user_delete, name='user_delete'),
    
    # Tenant Management CRUD
    path('settings/tenants/', tenant_list, name='tenant_list'),
    path('settings/tenants/create/', tenant_create, name='tenant_create'),
    path('settings/tenants/<int:pk>/edit/', tenant_edit, name='tenant_edit'),
    path('settings/tenant/email/', tenant_email_settings, name='tenant_email_settings'),

]

