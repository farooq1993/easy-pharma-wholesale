from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.products import ProductMaster
from wholesaleApp.models.supplier import SupplierMaster
from wholesaleApp.models.tenant import TenantModel

# ==================== PRODUCT BATCH INVENTORY ====================
class ProductBatch(TenantModel):
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name='batches', verbose_name="Product")
    batch_number = models.CharField(max_length=100, verbose_name="Batch Number")
    expiry_date = models.DateField(verbose_name="Expiry Date")
    mrp = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="MRP (₹)")
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Purchase Rate (₹)")
    sale_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Sale Rate (₹)")
    wholesale_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Wholesale Rate (₹)")
    quantity = models.IntegerField(default=0, verbose_name="Available Stock (Packs)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Batch"
        verbose_name_plural = "Product Batches"
        unique_together = ('product', 'batch_number', 'expiry_date', 'mrp', 'purchase_rate', 'sale_rate')
        ordering = ['expiry_date', 'product__name']

    def __str__(self):
        return f"{self.product.name} - Batch: {self.batch_number} (Exp: {self.expiry_date}) [Stock: {self.quantity}]"


# ==================== PURCHASE ORDER ====================
class PurchaseOrder(TenantModel):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    po_number = models.CharField(max_length=50, verbose_name="PO Number")
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.PROTECT, related_name='purchase_orders', verbose_name="Supplier")
    po_date = models.DateField(verbose_name="PO Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Status")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Net Amount (₹)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ['-po_date', '-id']
        unique_together = ('tenant', 'po_number')

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"


class PurchaseOrderItem(TenantModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT, verbose_name="Product")
    quantity = models.IntegerField(verbose_name="Ordered Qty (Packs)")
    expected_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Expected Purchase Rate (₹)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total (₹)")

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.expected_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} packs)"


# ==================== PURCHASE ENTRY ====================
class PurchaseEntry(TenantModel):
    invoice_number = models.CharField(max_length=100, verbose_name="Supplier Invoice No")
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.PROTECT, related_name='purchase_entries', verbose_name="Supplier")
    entry_date = models.DateField(auto_now_add=True, verbose_name="Date Recorded")
    invoice_date = models.DateField(verbose_name="Invoice Date")
    payment_type = models.CharField(max_length=10, choices=(('Cash', 'Cash'), ('Credit', 'Credit')), default='Credit', verbose_name="Payment Type")
    
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Gross Amount (₹)")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Discount (₹)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="GST Amount (₹)")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Net Payable (₹)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Purchase Entry"
        verbose_name_plural = "Purchase Entries"
        ordering = ['-invoice_date', '-id']

    def __str__(self):
        return f"Inv: {self.invoice_number} - {self.supplier.name}"


class PurchaseEntryItem(TenantModel):
    purchase_entry = models.ForeignKey(PurchaseEntry, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT, verbose_name="Product")
    batch_number = models.CharField(max_length=100, verbose_name="Batch Number")
    expiry_date = models.DateField(verbose_name="Expiry Date")
    
    mrp = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="MRP (₹)")
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Purchase Rate (₹)")
    sale_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Sale Rate (₹)")
    wholesale_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Wholesale Rate (₹)")
    
    quantity = models.IntegerField(verbose_name="Billed Qty (Packs)")
    free_quantity = models.IntegerField(default=0, verbose_name="Free Qty")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Discount (%)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Item Total (₹)")

    def __str__(self):
        return f"{self.product.name} - Batch: {self.batch_number}"


# ==================== SUPPLIER PAYMENT ====================
class SupplierPayment(TenantModel):
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.CASCADE, related_name='payments', verbose_name="Supplier")
    payment_date = models.DateField(verbose_name="Payment Date")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount Paid (₹)")
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
        verbose_name = "Supplier Payment"
        verbose_name_plural = "Supplier Payments"
        ordering = ['-payment_date', '-id']

    def __str__(self):
        return f"Payment {self.id} - {self.supplier.name} - ₹{self.amount}"


# ==================== PURCHASE RETURN ====================
class PurchaseReturn(TenantModel):
    return_number = models.CharField(max_length=100, verbose_name="Return Number")
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.PROTECT, related_name='purchase_returns', verbose_name="Supplier")
    return_date = models.DateField(verbose_name="Return Date")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Gross Amount (₹)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="GST Amount (₹)")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Net Refund (₹)")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Purchase Return"
        verbose_name_plural = "Purchase Returns"
        ordering = ['-return_date', '-id']

    def __str__(self):
        return f"PR: {self.return_number} - {self.supplier.name}"


class PurchaseReturnItem(TenantModel):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT, verbose_name="Product")
    batch_number = models.CharField(max_length=100, verbose_name="Batch Number")
    expiry_date = models.DateField(verbose_name="Expiry Date")
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Purchase Rate (₹)")
    quantity = models.IntegerField(verbose_name="Returned Qty")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total (₹)")

    def __str__(self):
        return f"{self.product.name} - Qty: {self.quantity}"

