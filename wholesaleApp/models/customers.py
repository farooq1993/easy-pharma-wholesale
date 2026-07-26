from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel

# ==================== AREA MASTER ====================
class AreaMaster(TenantModel):
    # name = models.CharField(max_length=150, unique=True, verbose_name="Area Name")
    code = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Area Master"
        verbose_name_plural = "Area Masters"
        ordering = ['city']
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"({self.city})"

class SubareaMaster(TenantModel):
    area = models.ForeignKey(AreaMaster, on_delete=models.CASCADE, related_name='subareas')
    name = models.CharField(max_length=150, verbose_name="Subarea Name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subarea Master"
        verbose_name_plural = "Subarea Masters"
        ordering = ['name']

    def __str__(self):
        return f"({self.area.city}) - {self.name}"

# ==================== CUSTOMER MASTER ====================
class CustomerMaster(TenantModel):
    CUSTOMER_TYPE_CHOICES = (
        ('Retailer', 'Retailer / Chemist'),
        ('Wholesaler', 'Wholesaler / Sub-distributor'),
    )
    name = models.CharField(max_length=255, verbose_name="Customer Name")
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='Retailer', verbose_name="Customer Type")
    mobile = models.CharField(max_length=15)
    alternate_mobile = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    dl_number_1 = models.CharField(max_length=15, blank=True, null=True)
    dl_number_2 = models.CharField(max_length=15, blank=True, null=True)
    dl_number_3 = models.CharField(max_length=15, blank=True, null=True)
    
    area = models.ForeignKey('AreaMaster', on_delete=models.PROTECT, related_name='customers')
    subarea = models.ForeignKey('SubareaMaster', on_delete=models.PROTECT, related_name='customers', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
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
        verbose_name = "Customer Master"
        verbose_name_plural = "Customer Masters"
        ordering = ['name']
        unique_together = ('tenant', 'mobile')

    def __str__(self):
        return self.name

class CustomerPayment(TenantModel):
    customer = models.ForeignKey(CustomerMaster, on_delete=models.CASCADE, related_name='payments', verbose_name="Customer")
    invoice = models.ForeignKey('wholesaleApp.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments', verbose_name="Adjusted Invoice")
    payment_date = models.DateField(verbose_name="Payment Date")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount Received (₹)")
    payment_mode = models.CharField(
        max_length=20,
        choices=(('Cash', 'Cash'), ('Bank', 'Bank Transfer'), ('UPI', 'UPI'), ('Cheque', 'Cheque')),
        default='Cash',
        verbose_name="Payment Mode"
    )
    reference_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ref / Trans No.")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Customer Payment"
        verbose_name_plural = "Customer Payments"
        ordering = ['-payment_date', '-id']

    def __str__(self):
        return f"Payment {self.id} - {self.customer.name} - ₹{self.amount}"