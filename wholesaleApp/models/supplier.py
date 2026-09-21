from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel

# ==================== SUPPLIER MASTER ====================
class SupplierMaster(TenantModel):
    name = models.CharField(max_length=255, verbose_name="Supplier Name")
    mobile = models.CharField(max_length=15)
    alternate_mobile = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    dl_number_1 = models.CharField(max_length=100, blank=True, null=True)
    dl_number_2 = models.CharField(max_length=100, blank=True, null=True)
    dl_number_3 = models.CharField(max_length=100, blank=True, null=True)
    
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    is_out_state = models.BooleanField(default=False, verbose_name="Out of State / Interstate (IGST)")
    pincode = models.CharField(max_length=6, blank=True, null=True)
    
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_days = models.IntegerField(default=0)
    
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Supplier Master"
        verbose_name_plural = "Supplier Masters"
        ordering = ['name']
        unique_together = ('tenant', 'mobile')

    def __str__(self):
        return self.name