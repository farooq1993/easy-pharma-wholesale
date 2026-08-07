from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from wholesaleApp.models import (
    SupplierMaster,
    ProductMaster,
    ProductBatch,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseEntry,
    PurchaseEntryItem
)

# ==================== AJAX API ENDPOINTS ====================
# @login_required
def get_product_details(request, pk):
    """API endpoint to get product details like GST rate and packaging."""
    product = get_object_or_404(ProductMaster, pk=pk, is_deleted=False)
    data = {
        'id': product.id,
        'name': product.name,
        'pack_size': product.pack_size,
        'gst_rate': float(product.gst_rate),
        'hsn_code': product.hsn_code or ''
    }
    return JsonResponse(data)


# ==================== PURCHASE ORDER VIEWS ====================
# @login_required
def po_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'po_view'):
        from django.contrib import messages
        messages.error(request, "Access Denied: You do not have permission to view Purchase Orders.")
        return redirect('home')
    import urllib.parse
    orders = PurchaseOrder.objects.all().select_related('supplier', 'tenant').prefetch_related('items__product')
    
    for order in orders:
        items_list = []
        for item in order.items.all():
            items_list.append(f"- {item.product.name}: {item.quantity} packs")
        items_text = "\n".join(items_list)
        
        tenant_name = order.tenant.company_name if order.tenant else "easyPharma"
        text = f"Hello {order.supplier.name},\n\nPlease find Purchase Order *{order.po_number}* from *{tenant_name}*.\n\n*Items Ordered*:\n{items_text}\n\n*Total Expected Value*: Rs. {order.net_amount}\n\nPlease confirm the order."
        order.whatsapp_url = f"https://wa.me/{order.supplier.mobile}?text={urllib.parse.quote(text)}"
        
    context = {
        'orders': orders,
        'page_title': 'Purchase Orders'
    }
    return render(request, 'purchase/po_list.html', context)

# @login_required
@transaction.atomic
def po_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'po_create'):
        messages.error(request, "Access Denied: You do not have permission to create Purchase Orders.")
        return redirect('po_list')
    suppliers = SupplierMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        po_date = request.POST.get('po_date')
        po_number = request.POST.get('po_number')
        
        # Create Purchase Order
        po = PurchaseOrder.objects.create(
            po_number=po_number,
            supplier_id=supplier_id,
            po_date=po_date,
            status='Sent',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        expected_rates = request.POST.getlist('expected_rate[]')
        
        net_amount = Decimal('0.00')
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            qty = int(quantities[i])
            rate = Decimal(expected_rates[i])
            total = qty * rate
            net_amount += total
            
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_id=prod_id,
                quantity=qty,
                expected_rate=rate,
                total_amount=total
            )
            
        po.net_amount = net_amount
        po.save()
        
        messages.success(request, f"Purchase Order {po_number} created and saved successfully!")
        return redirect('po_list')
        
    # Generate auto PO number (PO-YYYYMMDD-ID)
    import datetime
    today = datetime.date.today().strftime('%Y%m%d')
    next_id = (PurchaseOrder.objects.count() + 1)
    auto_po_number = f"PO-{today}-{next_id:04d}"
    
    context = {
        'suppliers': suppliers,
        'products': products,
        'auto_po_number': auto_po_number,
        'page_title': 'Create Purchase Order'
    }
    return render(request, 'purchase/po_form.html', context)


# ==================== PURCHASE ENTRY (INVOICE) VIEWS ====================
# @login_required
def purchase_entry_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not (has_feature_access(request.user, 'purchase_view') or has_feature_access(request.user, 'purchase_create')):
        messages.error(request, "Access Denied: You do not have permission to view Purchase Entries.")
        return redirect('home')
        
    entries = PurchaseEntry.objects.all().select_related('supplier')
    context = {
        'entries': entries,
        'page_title': 'Purchase Entries (Supplier Bills)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/entry_list.html', context)

# @login_required
@transaction.atomic
def purchase_entry_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'purchase_create'):
        messages.error(request, "Access Denied: You do not have permission to record Purchase Entries.")
        return redirect('home')
        
    suppliers = SupplierMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        invoice_number = request.POST.get('invoice_number')
        invoice_date = request.POST.get('invoice_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(invoice_date):
            messages.error(request, "Action Denied: The selected invoice date falls within a closed Financial Year.")
            return redirect('purchase_entry_list')
        payment_type = request.POST.get('payment_type', 'Credit')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        discount_amount = Decimal(request.POST.get('discount_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        
        # Create the purchase entry
        entry = PurchaseEntry.objects.create(
            supplier_id=supplier_id,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            payment_type=payment_type,
            gross_amount=gross_amount,
            discount_amount=discount_amount,
            gst_amount=gst_amount,
            net_amount=net_amount,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Extract item rows
        product_ids = request.POST.getlist('product[]')
        batches = request.POST.getlist('batch_number[]')
        expiries = request.POST.getlist('expiry_date[]')
        mrps = request.POST.getlist('mrp[]')
        p_rates = request.POST.getlist('purchase_rate[]')
        s_rates = request.POST.getlist('sale_rate[]')
        wholesale_rates = request.POST.getlist('wholesale_rate[]')
        quantities = request.POST.getlist('quantity[]')
        free_quantities = request.POST.getlist('free_quantity[]')
        discounts = request.POST.getlist('discount_percentage[]')
        totals = request.POST.getlist('total_amount[]')
        
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_no = batches[i]
            exp_date = expiries[i]
            mrp_val = Decimal(mrps[i])
            pr_val = Decimal(p_rates[i])
            sr_val = Decimal(s_rates[i])
            wr_val = Decimal(wholesale_rates[i]) if (i < len(wholesale_rates) and wholesale_rates[i]) else Decimal('0.00')
            qty = int(quantities[i])
            free_qty = int(free_quantities[i]) if free_quantities[i] else 0
            disc_pct = Decimal(discounts[i]) if discounts[i] else Decimal('0.00')
            total_val = Decimal(totals[i])
            
            # 1. Create Purchase Entry Item
            PurchaseEntryItem.objects.create(
                purchase_entry=entry,
                product_id=prod_id,
                batch_number=batch_no,
                expiry_date=exp_date,
                mrp=mrp_val,
                purchase_rate=pr_val,
                sale_rate=sr_val,
                wholesale_rate=wr_val,
                quantity=qty,
                free_quantity=free_qty,
                discount_percentage=disc_pct,
                total_amount=total_val
            )
            
            # 2. Update/Create Batch Inventory Stock
            batch, created = ProductBatch.objects.get_or_create(
                product_id=prod_id,
                batch_number=batch_no,
                expiry_date=exp_date,
                mrp=mrp_val,
                purchase_rate=pr_val,
                sale_rate=sr_val,
                defaults={'quantity': 0, 'wholesale_rate': wr_val}
            )
            batch.quantity += (qty + free_qty)
            if not created:
                batch.wholesale_rate = wr_val
            batch.save()
            
        # 3. Update Supplier balance if Credit type
        if entry.payment_type == 'Credit':
            supplier = SupplierMaster.objects.get(id=supplier_id)
            supplier.opening_balance += entry.net_amount
            supplier.save()
            
        messages.success(request, f"Purchase Entry recorded successfully! Stock added for {len(product_ids)} items.")
        return redirect('purchase_entry_list')
        
    context = {
        'suppliers': suppliers,
        'products': products,
        'page_title': 'Add Purchase Entry (Supplier Bill)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/entry_form.html', context)


# @login_required
@transaction.atomic
def purchase_entry_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'purchase_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Purchase Entries.")
        return redirect('purchase_entry_list')
        
    entry = get_object_or_404(PurchaseEntry, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(entry.invoice_date):
        messages.error(request, "Action Denied: This purchase entry falls within a closed Financial Year and cannot be modified.")
        return redirect('purchase_entry_list')
    suppliers = SupplierMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        invoice_number = request.POST.get('invoice_number')
        invoice_date = request.POST.get('invoice_date')
        if is_date_in_closed_fy(invoice_date):
            messages.error(request, "Action Denied: The selected invoice date falls within a closed Financial Year.")
            return redirect('purchase_entry_list')
        payment_type = request.POST.get('payment_type', 'Credit')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        discount_amount = Decimal(request.POST.get('discount_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        
        # 1. Revert previous stock additions
        old_items = list(entry.items.all())
        for item in old_items:
            # Look up batch in database to revert stock
            try:
                batch = ProductBatch.objects.get(
                    product=item.product,
                    batch_number=item.batch_number,
                    expiry_date=item.expiry_date,
                    mrp=item.mrp,
                    purchase_rate=item.purchase_rate,
                    sale_rate=item.sale_rate
                )
                batch.quantity -= (item.quantity + item.free_quantity)
                batch.save()
            except ProductBatch.DoesNotExist:
                pass
                
        # 2. Revert supplier outstanding balance if it was a Credit purchase
        if entry.payment_type == 'Credit':
            old_supplier = entry.supplier
            old_supplier.opening_balance -= entry.net_amount
            old_supplier.save()
            
        # 3. Delete old items
        entry.items.all().delete()
        
        # 4. Save updated entry headers
        entry.supplier_id = supplier_id
        entry.invoice_number = invoice_number
        entry.invoice_date = invoice_date
        entry.payment_type = payment_type
        entry.gross_amount = gross_amount
        entry.discount_amount = discount_amount
        entry.gst_amount = gst_amount
        entry.net_amount = net_amount
        entry.save()
        
        # 5. Extract item rows
        product_ids = request.POST.getlist('product[]')
        batches = request.POST.getlist('batch_number[]')
        expiries = request.POST.getlist('expiry_date[]')
        mrps = request.POST.getlist('mrp[]')
        p_rates = request.POST.getlist('purchase_rate[]')
        s_rates = request.POST.getlist('sale_rate[]')
        wholesale_rates = request.POST.getlist('wholesale_rate[]')
        quantities = request.POST.getlist('quantity[]')
        free_quantities = request.POST.getlist('free_quantity[]')
        discounts = request.POST.getlist('discount_percentage[]')
        totals = request.POST.getlist('total_amount[]')
        
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_no = batches[i]
            exp_date = expiries[i]
            mrp_val = Decimal(mrps[i])
            pr_val = Decimal(p_rates[i])
            sr_val = Decimal(s_rates[i])
            wr_val = Decimal(wholesale_rates[i]) if (i < len(wholesale_rates) and wholesale_rates[i]) else Decimal('0.00')
            qty = int(quantities[i])
            free_qty = int(free_quantities[i]) if free_quantities[i] else 0
            disc_pct = Decimal(discounts[i]) if discounts[i] else Decimal('0.00')
            total_val = Decimal(totals[i])
            
            # Create Purchase Entry Item
            PurchaseEntryItem.objects.create(
                purchase_entry=entry,
                product_id=prod_id,
                batch_number=batch_no,
                expiry_date=exp_date,
                mrp=mrp_val,
                purchase_rate=pr_val,
                sale_rate=sr_val,
                wholesale_rate=wr_val,
                quantity=qty,
                free_quantity=free_qty,
                discount_percentage=disc_pct,
                total_amount=total_val
            )
            
            # Update/Create Batch Inventory Stock
            batch, created = ProductBatch.objects.get_or_create(
                product_id=prod_id,
                batch_number=batch_no,
                expiry_date=exp_date,
                mrp=mrp_val,
                purchase_rate=pr_val,
                sale_rate=sr_val,
                defaults={'quantity': 0, 'wholesale_rate': wr_val}
            )
            batch.quantity += (qty + free_qty)
            if not created:
                batch.wholesale_rate = wr_val
            batch.save()
            
        # 6. Update Supplier balance if new type is Credit
        if entry.payment_type == 'Credit':
            new_supplier = entry.supplier
            new_supplier.opening_balance += entry.net_amount
            new_supplier.save()
            
        messages.success(request, f"Purchase Entry {entry.invoice_number} updated successfully!")
        return redirect('purchase_entry_list')
        
    context = {
        'entry': entry,
        'suppliers': suppliers,
        'products': products,
        'page_title': f'Edit Purchase Entry {entry.invoice_number}',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/entry_edit.html', context)


# @login_required
@transaction.atomic
def purchase_entry_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'purchase_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete/cancel Purchase Entries.")
        return redirect('purchase_entry_list')
        
    entry = get_object_or_404(PurchaseEntry, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(entry.invoice_date):
        messages.error(request, "Action Denied: This purchase entry falls within a closed Financial Year and cannot be deleted.")
        return redirect('purchase_entry_list')
    
    # 1. Revert stock additions
    for item in entry.items.all():
        try:
            batch = ProductBatch.objects.get(
                product=item.product,
                batch_number=item.batch_number,
                expiry_date=item.expiry_date,
                mrp=item.mrp,
                purchase_rate=item.purchase_rate,
                sale_rate=item.sale_rate
            )
            batch.quantity -= (item.quantity + item.free_quantity)
            batch.save()
        except ProductBatch.DoesNotExist:
            pass
            
    # 2. Subtract from supplier outstanding balance if it was Credit
    if entry.payment_type == 'Credit':
        supplier = entry.supplier
        supplier.opening_balance -= entry.net_amount
        supplier.save()
        
    # 3. Delete the entry
    invoice_number = entry.invoice_number
    entry.delete()
    
    messages.success(request, f"Purchase Entry {invoice_number} deleted successfully, stock adjustments reverted.")
    return redirect('purchase_entry_list')


# ==================== SUPPLIER PAYMENTS ====================
@transaction.atomic
def supplier_payment_list(request):
    from wholesaleApp.models import SupplierPayment
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'supplier_payment_view'):
        messages.error(request, "Access Denied: You do not have permission to view Supplier Payments.")
        return redirect('home')
    
    payments = SupplierPayment.objects.all().select_related('supplier')
    context = {
        'payments': payments,
        'page_title': 'Supplier Payments',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/payment_list.html', context)


@transaction.atomic
def supplier_payment_create(request):
    from wholesaleApp.models import SupplierPayment, SupplierMaster
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    if not has_feature_access(request.user, 'supplier_payment_create'):
        messages.error(request, "Access Denied: You do not have permission to record Supplier Payments.")
        return redirect('supplier_payment_list')
    
    suppliers = SupplierMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        payment_date = request.POST.get('payment_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(payment_date):
            messages.error(request, "Action Denied: The selected payment date falls within a closed Financial Year.")
            return redirect('supplier_payment_list')
        amount = Decimal(request.POST.get('amount', 0))
        payment_mode = request.POST.get('payment_mode', 'Cash')
        reference_no = request.POST.get('reference_no', '')
        remarks = request.POST.get('remarks', '')
        
        supplier = get_object_or_404(SupplierMaster, id=supplier_id)
        
        payment = SupplierPayment.objects.create(
            supplier=supplier,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_mode,
            reference_no=reference_no,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Deduct from supplier balance (since we paid them, our liability decreases)
        supplier.opening_balance -= amount
        supplier.save()
        
        log_activity(
            request,
            action='CREATE',
            model_name='SupplierPayment',
            object_id=payment.id,
            object_repr=f"Payment to {supplier.name}",
            description=f"Paid ₹{amount} via {payment_mode}"
        )
        
        messages.success(request, f"Payment of ₹{amount} to {supplier.name} recorded successfully.")
        return redirect('supplier_payment_list')
        
    context = {
        'suppliers': suppliers,
        'page_title': 'Record Supplier Payment',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/payment_form.html', context)


@transaction.atomic
def supplier_payment_delete(request, pk):
    from wholesaleApp.models import SupplierPayment
    from wholesaleApp.views.security_helpers import has_feature_access, log_activity
    if not has_feature_access(request.user, 'supplier_payment_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Supplier Payments.")
        return redirect('supplier_payment_list')
    
    payment = get_object_or_404(SupplierPayment, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(payment.payment_date):
        messages.error(request, "Action Denied: This payment falls within a closed Financial Year and cannot be deleted.")
        return redirect('supplier_payment_list')
    supplier = payment.supplier
    
    # Add amount back to supplier balance
    supplier.opening_balance += payment.amount
    supplier.save()
    
    log_activity(
        request,
        action='DELETE',
        model_name='SupplierPayment',
        object_id=payment.id,
        object_repr=f"Payment to {supplier.name}",
        description=f"Reverted payment of ₹{payment.amount}"
    )
    
    payment.delete()
    messages.success(request, "Supplier payment deleted and balance adjusted.")
    return redirect('supplier_payment_list')


# ==================== PURCHASE RETURNS ====================
@transaction.atomic
def purchase_return_list(request):
    from wholesaleApp.models import PurchaseReturn
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'purchase_return_view'):
        messages.error(request, "Access Denied: You do not have permission to view Purchase Returns.")
        return redirect('home')
    
    returns = PurchaseReturn.objects.all().select_related('supplier')
    context = {
        'returns': returns,
        'page_title': 'Purchase Returns',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/return_list.html', context)


@transaction.atomic
def purchase_return_create(request):
    from wholesaleApp.models import PurchaseReturn, PurchaseReturnItem, SupplierMaster, ProductMaster, ProductBatch
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    if not has_feature_access(request.user, 'purchase_return_create'):
        messages.error(request, "Access Denied: You do not have permission to create Purchase Returns.")
        return redirect('purchase_return_list')
    
    suppliers = SupplierMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        return_number = request.POST.get('return_number')
        return_date = request.POST.get('return_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(return_date):
            messages.error(request, "Action Denied: The selected return date falls within a closed Financial Year.")
            return redirect('purchase_return_list')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        remarks = request.POST.get('remarks', '')
        
        supplier = get_object_or_404(SupplierMaster, id=supplier_id)
        
        # Create return
        p_return = PurchaseReturn.objects.create(
            supplier=supplier,
            return_number=return_number,
            return_date=return_date,
            gross_amount=gross_amount,
            gst_amount=gst_amount,
            net_amount=net_amount,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Parse return items
        product_ids = request.POST.getlist('product[]')
        batches = request.POST.getlist('batch_number[]')
        expiries = request.POST.getlist('expiry_date[]')
        p_rates = request.POST.getlist('purchase_rate[]')
        quantities = request.POST.getlist('quantity[]')
        totals = request.POST.getlist('total_amount[]')
        
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_no = batches[i]
            exp_date = expiries[i]
            pr_val = Decimal(p_rates[i])
            qty = int(quantities[i])
            total_val = Decimal(totals[i])
            
            # Create Return Item
            PurchaseReturnItem.objects.create(
                purchase_return=p_return,
                product_id=prod_id,
                batch_number=batch_no,
                expiry_date=exp_date,
                purchase_rate=pr_val,
                quantity=qty,
                total_amount=total_val
            )
            
            # Deduct from Batch Inventory
            try:
                batch = ProductBatch.objects.get(
                    product_id=prod_id,
                    batch_number=batch_no,
                    expiry_date=exp_date
                )
                batch.quantity = max(0, batch.quantity - qty)
                batch.save()
            except ProductBatch.DoesNotExist:
                pass
                
        # Deduct return value from Supplier Balance (reduces our liability)
        supplier.opening_balance -= net_amount
        supplier.save()
        
        log_activity(
            request,
            action='CREATE',
            model_name='PurchaseReturn',
            object_id=p_return.id,
            object_repr=p_return.return_number,
            description=f"Created purchase return to {supplier.name} for ₹{net_amount}"
        )
        
        messages.success(request, f"Purchase Return '{return_number}' recorded successfully.")
        return redirect('purchase_return_list')
        
    context = {
        'suppliers': suppliers,
        'products': products,
        'page_title': 'New Purchase Return',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'purchase/return_form.html', context)


@transaction.atomic
def purchase_return_delete(request, pk):
    from wholesaleApp.models import PurchaseReturn, ProductBatch
    from wholesaleApp.views.security_helpers import has_feature_access, log_activity
    if not has_feature_access(request.user, 'purchase_return_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Purchase Returns.")
        return redirect('purchase_return_list')
    
    p_return = get_object_or_404(PurchaseReturn, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(p_return.return_date):
        messages.error(request, "Action Denied: This return falls within a closed Financial Year and cannot be deleted.")
        return redirect('purchase_return_list')
    supplier = p_return.supplier
    
    # Restore stock for return items
    for item in p_return.items.all():
        try:
            batch = ProductBatch.objects.get(
                product=item.product,
                batch_number=item.batch_number,
                expiry_date=item.expiry_date
            )
            batch.quantity += item.quantity
            batch.save()
        except ProductBatch.DoesNotExist:
            pass
            
    # Add amount back to supplier balance (our liability increases back)
    supplier.opening_balance += p_return.net_amount
    supplier.save()
    
    log_activity(
        request,
        action='DELETE',
        model_name='PurchaseReturn',
        object_id=p_return.id,
        object_repr=p_return.return_number,
        description=f"Deleted purchase return to {supplier.name} and restored stock"
    )
    
    p_return.delete()
    messages.success(request, "Purchase return deleted and stock restored.")
    return redirect('purchase_return_list')


# @login_required
def po_email_send(request, pk):
    """View to trigger manual sending of a PO to the supplier via email."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'po_view'):
        messages.error(request, "Access Denied: You do not have permission to access Purchase Orders.")
        return redirect('po_list')
    from wholesaleApp.utils.email_utils import send_po_email_async
    
    po = get_object_or_404(PurchaseOrder, id=pk)
    
    if not po.supplier.email or not po.supplier.email.strip():
        messages.error(request, f"Supplier '{po.supplier.name}' has no email address configured. Cannot send email.")
    else:
        send_po_email_async(po)
        messages.success(request, f"Purchase Order {po.po_number} email queued successfully in the background.")
        
    return redirect('po_list')


