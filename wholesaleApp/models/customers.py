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

# ==================== CUSTOMER MANAGE DETAIL (MARG STYLE) ====================
class CustomerManageDetail(TenantModel):
    customer = models.OneToOneField(CustomerMaster, on_delete=models.CASCADE, related_name='manage_detail', verbose_name="Customer")
    
    # 1. Discounts & Schemes
    item_discount_a = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Item Discount % (Rate A)")
    item_discount_b = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Item Discount % (Rate B)")
    item_discount_c = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Item Discount % (Rate C)")
    collection_disc = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Collection Disc. %")
    min_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Min. Margin %")
    volume_disc = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Volume Disc. %")
    breakage_expiry_disc = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Breakage/Expiry Disc. % [MRP]")
    product_scheme_notes = models.TextField(blank=True, null=True, verbose_name="Product Scheme & Special Deals Notes")
    
    # 2. Billing & Rates Preferences
    SALES_RATE_CHOICES = (
        ('wholesale', 'Wholesale Rate'),
        ('mrp', 'MRP'),
        ('purchase', 'Purchase Rate'),
        ('rate_a', 'Rate A'),
        ('rate_b', 'Rate B'),
    )
    sales_rate_type = models.CharField(max_length=30, choices=SALES_RATE_CHOICES, default='wholesale', verbose_name="Sales Rate")
    
    NEAR_EXP_CHOICES = (
        ('allowed', 'Allowed'),
        ('warn', 'Warn Only'),
        ('not_allowed', 'Not Allowed'),
    )
    near_expiry_action = models.CharField(max_length=20, choices=NEAR_EXP_CHOICES, default='allowed', verbose_name="Near Expiry in Bill")
    new_item_billing = models.BooleanField(default=True, verbose_name="New Item Billing Allowed")
    print_batch = models.BooleanField(default=True, verbose_name="Print Batch on Bill")
    invoice_format = models.CharField(max_length=50, default='DEFAULT', blank=True, null=True, verbose_name="Invoice Format")
    
    # 3. Credit Limits & Payment Terms
    credit_limit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Credit Limit (₹)")
    credit_limit_bills = models.IntegerField(default=0, verbose_name="Credit Limit (Bills)")
    credit_days = models.IntegerField(default=0, verbose_name="Credit Days")
    interest_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Overdue Interest %")
    
    LIMIT_ACTION_CHOICES = (
        ('indicate', 'Only Indicate / Warn'),
        ('stop', 'Stop / Block Billing'),
        ('none', 'No Restriction'),
    )
    credit_limit_action = models.CharField(max_length=20, choices=LIMIT_ACTION_CHOICES, default='indicate', verbose_name="Credit Limit Action")
    bank_rebate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Bank Rebate %")
    bank_rebate_days = models.IntegerField(default=0, verbose_name="Bank Rebate Upto (Days)")
    collection_days = models.CharField(max_length=100, default='Mon,Tue,Wed,Thu,Fri,Sat', blank=True, null=True, verbose_name="Collection Days")
    
    # 4. Transport & Banking
    transport_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Transport")
    delivery_by = models.CharField(max_length=150, blank=True, null=True, verbose_name="Delivery By / Agent")
    bank_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Bank Name")
    bank_account_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Bank Account No")
    bank_ifsc = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")
    bank_branch = models.CharField(max_length=150, blank=True, null=True, verbose_name="Branch Name")
    
    # 5. Operator Note (prominently alert billing operator)
    operator_note = models.TextField(blank=True, null=True, verbose_name="Operator Note / Billing Alert")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Customer Manage Detail"
        verbose_name_plural = "Customer Manage Details"

    def __str__(self):
        return f"Manage Details: {self.customer.name}"