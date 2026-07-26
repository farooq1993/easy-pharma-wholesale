from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel
from wholesaleApp.models.products import ProductMaster

class SchemeMaster(TenantModel):
    name = models.CharField(max_length=150, verbose_name="Scheme Name")
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name='schemes', verbose_name="Product")
    billed_qty = models.IntegerField(default=0, verbose_name="Billed Qty")
    free_qty = models.IntegerField(default=0, verbose_name="Free Qty")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Discount (%)")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Scheme Master"
        verbose_name_plural = "Scheme Masters"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.product.name} (Buy {self.billed_qty} Get {self.free_qty} Free + {self.discount_percentage}%)"
