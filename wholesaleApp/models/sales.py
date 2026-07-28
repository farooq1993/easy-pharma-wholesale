from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.customers import CustomerMaster
from wholesaleApp.models.products import ProductMaster
from wholesaleApp.models.purchase import ProductBatch
from wholesaleApp.models.tenant import TenantModel

class SalesInvoice(TenantModel):
    invoice_number = models.CharField(max_length=50, verbose_name="Invoice Number")
    customer = models.ForeignKey(CustomerMaster, on_delete=models.PROTECT, related_name='sales_invoices', verbose_name="Customer", null=True, blank=True)
    patient_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Patient Name")
    patient_mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="Patient Mobile")
    doctor_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Doctor Name")
    invoice_date = models.DateField(verbose_name="Invoice Date")
    
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Gross Amount (₹)")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Discount (₹)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="GST Amount (₹)")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Net Amount Receivable (₹)")
    
    status = models.CharField(
        max_length=50,
        choices=(('Pending', 'Pending'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')),
        default='Pending',
        verbose_name="Delivery Status"
    )
    payment_type = models.CharField(
        max_length=10,
        choices=(('Cash', 'Cash'), ('Credit', 'Credit')),
        default='Credit',
        verbose_name="Payment Type"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_delivery_boy = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_deliveries', verbose_name="Assigned Delivery Staff")
    is_retail = models.BooleanField(default=False, verbose_name="Is Retail Bill (B2C)")

    class Meta:
        verbose_name = "Sales Invoice"
        verbose_name_plural = "Sales Invoices"
        ordering = ['-invoice_date', '-id']
        unique_together = ('tenant', 'invoice_number')

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class SalesInvoiceItem(TenantModel):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT, verbose_name="Product")
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, verbose_name="Batch")
    
    quantity = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Billed Qty")
    free_quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, verbose_name="Free Qty")
    sale_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Selling Rate (₹)")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Discount (%)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Item Total (₹)")
    is_retail = models.BooleanField(default=False, verbose_name="Is Retail Line")

    def __str__(self):
        return f"{self.product.name} - Qty: {self.quantity} (Batch: {self.batch.batch_number})"


# ==================== SALES RETURN ====================
class SalesReturn(TenantModel):
    return_number = models.CharField(max_length=100, verbose_name="Return Number")
    customer = models.ForeignKey(CustomerMaster, on_delete=models.PROTECT, related_name='sales_returns', verbose_name="Customer")
    return_date = models.DateField(verbose_name="Return Date")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Gross Amount (₹)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="GST Amount (₹)")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Net Refund (₹)")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Sales Return"
        verbose_name_plural = "Sales Returns"
        ordering = ['-return_date', '-id']

    def __str__(self):
        return f"SR: {self.return_number} - {self.customer.name}"


class SalesReturnItem(TenantModel):
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT, verbose_name="Product")
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, verbose_name="Batch")
    sale_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Selling Rate (₹)")
    quantity = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Returned Qty")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total (₹)")

    def __str__(self):
        return f"{self.product.name} - Qty: {self.quantity} (Batch: {self.batch.batch_number})"

