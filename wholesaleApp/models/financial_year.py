import datetime
from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel, get_current_tenant

class FinancialYear(TenantModel):
    name = models.CharField(max_length=50, verbose_name="Financial Year Name")  # e.g. "FY 2026-27"
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    is_closed = models.BooleanField(default=False, verbose_name="Is Closed")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Closed At")
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Closed By")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Financial Year"
        verbose_name_plural = "Financial Years"
        ordering = ['-start_date']
        unique_together = ('tenant', 'name')

    def __str__(self):
        status = "Closed" if self.is_closed else "Active"
        return f"{self.name} ({status})"


def is_date_in_closed_fy(date_val, tenant=None):
    """
    Check if the given date falls under a closed financial year for the tenant.
    Auto-creates the current financial year if no financial years exist.
    """
    if not date_val:
        return False
        
    if not tenant:
        tenant = get_current_tenant()
    
    if not tenant:
        from wholesaleApp.models.tenant import Tenant
        tenant = Tenant.objects.filter(is_active=True).first()
        
    if not tenant:
        return False
        
    # Parse date if string
    if isinstance(date_val, str):
        try:
            date_val = datetime.datetime.strptime(date_val, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return False
            
    # Auto-seed the current financial year if none exist for this tenant
    # This prevents blocking active users on fresh databases
    if not FinancialYear.objects.filter(tenant=tenant).exists():
        today = datetime.date.today()
        # Indian FY logic
        if today.month < 4:
            fy_start_year = today.year - 1
        else:
            fy_start_year = today.year
        fy_end_year = fy_start_year + 1
        
        start_yy = str(fy_start_year)[-2:]
        end_yy = str(fy_end_year)[-2:]
        fy_name = f"FY 20{start_yy}-20{end_yy}"
        
        FinancialYear.objects.create(
            tenant=tenant,
            name=fy_name,
            start_date=datetime.date(fy_start_year, 4, 1),
            end_date=datetime.date(fy_end_year, 3, 31),
            is_closed=False
        )

    # Check if any closed FY covers this date
    return FinancialYear.objects.filter(
        tenant=tenant,
        is_closed=True,
        start_date__lte=date_val,
        end_date__gte=date_val
    ).exists()
