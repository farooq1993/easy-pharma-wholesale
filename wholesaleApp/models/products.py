from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel

# ==================== COMPANY MASTER ====================
class CompanyMaster(TenantModel):
    name = models.CharField(max_length=255, verbose_name="Company Name")
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Company Code")
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Company Master"
        verbose_name_plural = "Company Masters"
        ordering = ['name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return self.name


# ==================== DRUG MASTER (GENERIC COMPOSITION) ====================
class DrugMaster(TenantModel):
    name = models.CharField(max_length=255, verbose_name="Generic Composition")
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Drug Master"
        verbose_name_plural = "Drug Masters"
        ordering = ['name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return self.name


# ==================== PRODUCT TYPE MASTER ====================
class ProductTypeMaster(TenantModel):
    name = models.CharField(max_length=100, verbose_name="Product Type / Form")
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Product Type Master"
        verbose_name_plural = "Product Type Masters"
        ordering = ['name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return self.name


# ==================== TAX MASTER (GST SLABS) ====================
class TaxMaster(TenantModel):
    name = models.CharField(max_length=100, verbose_name="Tax Slab Name (e.g. 12% Standard Pharma)")
    rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Total GST Rate (%)")
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="CGST Rate (%)")
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="SGST Rate (%)")
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="IGST Rate (%)")
    is_default = models.BooleanField(default=False, verbose_name="Default Slab for Products")
    description = models.TextField(blank=True, null=True, verbose_name="Description / Remarks")
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Tax Master"
        verbose_name_plural = "Tax Masters"
        ordering = ['rate', 'name']
        unique_together = ('tenant', 'rate', 'name')

    def save(self, *args, **kwargs):
        if self.rate is not None:
            if not self.cgst_rate and not self.sgst_rate:
                half_rate = round(self.rate / 2, 2)
                self.cgst_rate = half_rate
                self.sgst_rate = half_rate
            if not self.igst_rate:
                self.igst_rate = self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


# ==================== SCHEDULE MASTER (DRUG SCHEDULES) ====================
class ScheduleMaster(TenantModel):
    name = models.CharField(max_length=100, verbose_name="Schedule Name (e.g. Schedule H, Schedule H1)")
    code = models.CharField(max_length=20, verbose_name="Schedule Code (e.g. H, H1, X, OTC)")
    warning_text = models.TextField(blank=True, null=True, verbose_name="Statutory Warning / Prescription Note")
    requires_prescription = models.BooleanField(default=True, verbose_name="Prescription Required (Rx)")
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Schedule Master"
        verbose_name_plural = "Schedule Masters"
        ordering = ['name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return f"{self.name} ({self.code})"


# ==================== PRODUCT MASTER (ITEM MASTER) ====================
class ProductMaster(TenantModel):
    name = models.CharField(max_length=255, verbose_name="Brand Name")
    company = models.ForeignKey(CompanyMaster, on_delete=models.PROTECT, related_name='products', verbose_name="Company")
    drug_composition = models.ForeignKey(DrugMaster, on_delete=models.PROTECT, related_name='products', blank=True, null=True, verbose_name="Drug Composition")
    product_type = models.ForeignKey(ProductTypeMaster, on_delete=models.PROTECT, related_name='products', verbose_name="Product Type")
    tax_slab = models.ForeignKey(TaxMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Tax Slab (GST)")
    schedule = models.ForeignKey(ScheduleMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Drug Schedule")
    
    pack_size = models.CharField(max_length=50, verbose_name="Packaging (e.g., 10 Tab, 100ml)")
    units_per_strip = models.IntegerField(default=1, verbose_name="Conversion Factor (Units per Strip)")
    hsn_code = models.CharField(max_length=15, blank=True, null=True, verbose_name="HSN Code")
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=12.00, verbose_name="GST Rate (%)")
    min_stock = models.IntegerField(default=10, verbose_name="Minimum Stock Level")
    scheme_qty = models.IntegerField(default=0, verbose_name="Scheme Billed Qty (e.g. 10)")
    scheme_free = models.IntegerField(default=0, verbose_name="Scheme Free Qty (e.g. 1)")
    
    status = models.BooleanField(default=True, verbose_name="Active")
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Product Master"
        verbose_name_plural = "Product Masters"
        ordering = ['name']

    @property
    def total_stock(self):
        if hasattr(self, 'annotated_stock'):
            return self.annotated_stock
        if hasattr(self, '_prefetched_objects_cache') and 'batches' in self._prefetched_objects_cache:
            return sum(b.quantity for b in self.batches.all() if b.quantity > 0)
        from django.db.models import Sum
        return self.batches.filter(quantity__gt=0).aggregate(total=Sum('quantity'))['total'] or 0

    def __str__(self):
        return f"{self.name} ({self.pack_size})"
