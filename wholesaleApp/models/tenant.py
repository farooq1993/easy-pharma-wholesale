from django.db import models
from django.utils import timezone
import threading

# Thread-local storage for current tenant
_thread_locals = threading.local()

def get_current_tenant():
    """Retrieve the current active tenant from the thread-local context."""
    return getattr(_thread_locals, 'tenant', None)

def set_current_tenant(tenant):
    """Set the current active tenant in the thread-local context."""
    _thread_locals.tenant = tenant


class Tenant(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tenant Name")
    company_name = models.CharField(max_length=200, verbose_name="Company Name")
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True, verbose_name="GSTIN")
    gst_dealer_type = models.CharField(
        max_length=20,
        choices=(
            ('Regular', 'Registered (Regular)'),
            ('Composition', 'Registered (Composition Scheme)'),
            ('Unregistered', 'Unregistered'),
        ),
        default='Regular',
        verbose_name="GST Dealer Type"
    )
    dl_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Drug License Number")
    
    is_active = models.BooleanField(default=True)
    business_mode = models.CharField(
        max_length=20,
        choices=(('Wholesale', 'Wholesale Only'), ('Dual', 'Retail + Wholesale (Dual Mode)')),
        default='Wholesale',
        verbose_name="Business Mode"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant / Firm"
        verbose_name_plural = "Tenants / Firms"

    def __str__(self):
        return f"{self.name} ({self.company_name})"


class TenantManager(models.Manager):
    def get_queryset(self):
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs


class TenantModel(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name="%(class)s_records")
    
    objects = TenantManager()
    unfiltered_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
            else:
                # Fallback to default tenant if no active tenant is set
                default_tenant = Tenant.objects.filter(is_active=True).first()
                if default_tenant:
                    self.tenant = default_tenant
        super().save(*args, **kwargs)


class TenantEmailConfig(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='email_config', verbose_name="Tenant / Firm")
    email_host = models.CharField(max_length=255, default='smtp.gmail.com', verbose_name="SMTP Host")
    email_port = models.IntegerField(default=587, verbose_name="SMTP Port")
    email_use_tls = models.BooleanField(default=True, verbose_name="Use TLS")
    email_use_ssl = models.BooleanField(default=False, verbose_name="Use SSL")
    email_host_user = models.EmailField(max_length=255, verbose_name="SMTP Username / Email")
    email_host_password = models.CharField(max_length=255, verbose_name="SMTP Password")
    default_from_email = models.CharField(max_length=255, blank=True, null=True, verbose_name="Default Sender Display Name/Email", help_text="e.g. 'Your Company <sales@yourcompany.com>'")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant Email Config"
        verbose_name_plural = "Tenant Email Configs"

    def __str__(self):
        return f"Email Config for {self.tenant.company_name}"

