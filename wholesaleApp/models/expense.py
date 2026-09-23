from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel

class ExpenseCategory(TenantModel):
    name = models.CharField(max_length=150, verbose_name="Category / Expense Head")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(TenantModel):
    PAYMENT_MODE_CHOICES = (
        ('Cash', 'Cash'),
        ('UPI/Online', 'UPI / Online'),
        ('Bank Transfer', 'Bank Transfer / NEFT'),
        ('Cheque', 'Cheque'),
    )

    expense_date = models.DateField(verbose_name="Expense Date")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses', verbose_name="Expense Category")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount (₹)")
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='Cash', verbose_name="Payment Mode")
    paid_to = models.CharField(max_length=200, blank=True, null=True, verbose_name="Paid To / Payee")
    reference_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="Receipt / Voucher / Ref No")
    remarks = models.TextField(blank=True, null=True, verbose_name="Description / Remarks")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Expense Voucher"
        verbose_name_plural = "Expense Vouchers"
        ordering = ['-expense_date', '-id']

    def __str__(self):
        return f"{self.expense_date} - {self.category.name}: ₹{self.amount}"
