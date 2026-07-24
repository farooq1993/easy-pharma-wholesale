from django.db import models
from django.contrib.auth.models import User

# ==================== MODULE GROUPS ====================
class AppGroupModule(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Module Group Name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Module Group"
        verbose_name_plural = "Module Groups"
        ordering = ['name']

    def __str__(self):
        return self.name

# ==================== SYSTEM FEATURES ====================
class AppFeature(models.Model):
    module = models.ForeignKey(AppGroupModule, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=150, verbose_name="Feature Name")
    codename = models.CharField(max_length=100, unique=True, verbose_name="System Codename")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "App Feature"
        verbose_name_plural = "App Features"
        ordering = ['module__name', 'name']

    def __str__(self):
        return f"{self.module.name} - {self.name} ({self.codename})"

# ==================== USER FEATURE PERMISSIONS ====================
class UserFeaturePermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feature_permissions')
    feature = models.ForeignKey(AppFeature, on_delete=models.CASCADE)
    is_granted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "User Feature Permission"
        verbose_name_plural = "User Feature Permissions"
        unique_together = ('user', 'feature')

    def __str__(self):
        return f"{self.user.username} - {self.feature.codename}: {self.is_granted}"


from wholesaleApp.models.tenant import Tenant

# ==================== USER PROFILE (ROLES) ====================
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('Super Admin', 'SaaS Platform Admin'),
        ('Owner', 'Tenant Shop Owner'),
        ('Manager', 'Store Manager'),
        ('Salesman', 'Salesman / Billing Clerk'),
        ('Inventory', 'Inventory & Purchase Clerk'),
        ('Delivery Boy', 'Delivery Boy / Field Operator'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Salesman')
    mobile = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    @property
    def is_super_admin(self):
        return self.user.is_superuser or self.role == 'Super Admin'

    @property
    def is_tenant_owner(self):
        return self.role == 'Owner'

    @property
    def is_tenant_admin(self):
        return self.is_super_admin or self.is_tenant_owner

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# Django signals to auto-create profile for new users
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Save profile if it exists
        if hasattr(instance, 'profile'):
            instance.profile.save()
