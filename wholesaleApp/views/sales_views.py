from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from decimal import Decimal
import datetime
from wholesaleApp.models import (
    CustomerMaster,
    ProductMaster,
    ProductBatch,
    SalesInvoice,
    SalesInvoiceItem
)

# ==================== AJAX API ENDPOINTS ====================
@login_required
def get_product_batches(request, pk):
    """API endpoint to get active batches with stock for a selected product in FEFO order."""
    from django.core.cache import cache
    cache_key = f"product_batches_{pk}"
    data = cache.get(cache_key)
    
    if data is None:
        batches = ProductBatch.objects.filter(product_id=pk, quantity__gt=0).select_related('product').order_by('expiry_date')
        data = []
        for b in batches:
            # Format MM/YY for display mask and YYYY-MM-DD for form submit
            exp_mask = b.expiry_date.strftime('%m/%y') if b.expiry_date else ''
            exp_real = b.expiry_date.strftime('%Y-%m-%d') if b.expiry_date else ''
            data.append({
                'id': b.id,
                'batch_number': b.batch_number,
                'expiry_mask': exp_mask,
                'expiry_real': exp_real,
                'mrp': float(b.mrp),
                'purchase_rate': float(b.purchase_rate),
                'sale_rate': float(b.sale_rate),
                'wholesale_rate': float(b.wholesale_rate),
                'quantity': float(b.quantity),
                'units_per_strip': b.product.units_per_strip
            })
        cache.set(cache_key, data, timeout=60)
    return JsonResponse(data, safe=False)


# ==================== SALES BILLING VIEWS ====================
@login_required
def invoice_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not (has_feature_access(request.user, 'sales_view') or has_feature_access(request.user, 'sales_reprint')):
        messages.error(request, "Access Denied: You do not have permission to view Sales Invoices.")
        return redirect('home')
        
    invoices = SalesInvoice.objects.all().select_related('customer').order_by('-invoice_date', '-id')
    print_invoice_id = request.session.pop('print_invoice_id', None)
    context = {
        'invoices': invoices,
        'page_title': 'Sales Invoices (Retail Bills)',
        'user_perms': get_user_permissions_context(request.user),
        'print_invoice_id': print_invoice_id
    }
    return render(request, 'sale/invoice_list.html', context)

@login_required
@transaction.atomic
def invoice_create(request):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'sales_create'):
        messages.error(request, "Access Denied: You do not have permission to create Sale Bills.")
        return redirect('home')
        
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        if not customer_id:
            customer_id = None
            
        patient_name = request.POST.get('patient_name', '').strip() or None
        patient_mobile = request.POST.get('patient_mobile', '').strip() or None
        doctor_name = request.POST.get('doctor_name', '').strip() or None
        
        invoice_date = request.POST.get('invoice_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(invoice_date):
            messages.error(request, "Action Denied: The selected invoice date falls within a closed Financial Year.")
            return redirect('invoice_create')
        payment_type = request.POST.get('payment_type', 'Credit')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        discount_amount = Decimal(request.POST.get('discount_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        
        # Extract item arrays
        product_ids = request.POST.getlist('product[]')
        batch_ids = request.POST.getlist('batch[]')
        sale_rates = request.POST.getlist('sale_rate[]')
        quantities = request.POST.getlist('quantity[]')
        free_quantities = request.POST.getlist('free_quantity[]')
        discounts = request.POST.getlist('discount_percentage[]')
        totals = request.POST.getlist('total_amount[]')
        
        is_retail = request.POST.get('is_retail') == 'true' or request.POST.get('is_retail') == '1' or request.POST.get('is_retail') == 'on'

        # 1. Pre-validate stock availability for all items to avoid rollback errors
        for i in range(len(product_ids)):
            batch_id = batch_ids[i]
            qty = Decimal(quantities[i])
            free_qty = Decimal(free_quantities[i]) if free_quantities[i] else Decimal('0.0000')
            total_requested = qty + free_qty
            
            batch = get_object_or_404(ProductBatch, id=batch_id)
            if batch.quantity < total_requested:
                messages.error(request, f"Insufficient stock for {batch.product.name} (Batch: {batch.batch_number}). Available: {batch.quantity}, Requested: {total_requested}")
                return redirect('invoice_create')
        
        # Parse invoice_date to datetime.date object for calculations
        if isinstance(invoice_date, str):
            parsed_date = datetime.datetime.strptime(invoice_date, '%Y-%m-%d').date()
        else:
            parsed_date = invoice_date

        # Generate Invoice Number (I-[tenant_id][FY]-0001) for GST compliance
        from wholesaleApp.models.tenant import get_current_tenant, Tenant
        tenant = get_current_tenant()
        if not tenant:
            tenant = Tenant.objects.filter(is_active=True).first()
        
        if parsed_date.month < 4:
            fy_start_year = parsed_date.year - 1
        else:
            fy_start_year = parsed_date.year
        fy_end_year = fy_start_year + 1
        
        start_yy = str(fy_start_year)[-2:]
        end_yy = str(fy_end_year)[-2:]
        fy_str = f"{start_yy}{end_yy}"
        
        tenant_id_val = tenant.id if tenant else 1
        prefix = f"I-{tenant_id_val}{fy_str}-"
        
        fy_start_date = datetime.date(fy_start_year, 4, 1)
        fy_end_date = datetime.date(fy_end_year, 3, 31)
        
        # Count existing invoices for this tenant within the same financial year
        count = SalesInvoice.objects.filter(
            tenant=tenant,
            invoice_date__range=[fy_start_date, fy_end_date]
        ).count()
        next_id = count + 1
        
        while True:
            invoice_number = f"{prefix}{next_id:04d}"
            # Check unique_together collision across this tenant
            if not SalesInvoice.objects.filter(tenant=tenant, invoice_number=invoice_number).exists():
                break
            next_id += 1
        
        # 2. Create Sales Invoice
        invoice = SalesInvoice.objects.create(
            invoice_number=invoice_number,
            customer_id=customer_id,
            patient_name=patient_name,
            patient_mobile=patient_mobile,
            doctor_name=doctor_name,
            invoice_date=invoice_date,
            payment_type=payment_type,
            gross_amount=gross_amount,
            discount_amount=discount_amount,
            gst_amount=gst_amount,
            net_amount=net_amount,
            is_retail=is_retail,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # 3. Create items and deduct stock
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_id = batch_ids[i]
            s_rate = Decimal(sale_rates[i])
            qty = Decimal(quantities[i])
            free_qty = Decimal(free_quantities[i]) if free_quantities[i] else Decimal('0.0000')
            disc_pct = Decimal(discounts[i]) if discounts[i] else Decimal('0.00')
            total_val = Decimal(totals[i])
            
            batch = ProductBatch.objects.get(id=batch_id)
            total_requested = qty + free_qty
            
            # Create Sales Invoice Item
            SalesInvoiceItem.objects.create(
                sales_invoice=invoice,
                product_id=prod_id,
                batch=batch,
                quantity=qty,
                free_quantity=free_qty,
                sale_rate=s_rate,
                discount_percentage=disc_pct,
                total_amount=total_val,
                is_retail=is_retail
            )
            
            # Deduct Batch Inventory stock
            batch.quantity -= total_requested
            batch.save()
            
        # Invalidate Redis/LocMem batch cache for affected products
        from django.core.cache import cache
        for pid in product_ids:
            cache.delete(f"product_batches_{pid}")
            
        # 4. Update Customer Outstanding Balance (Accounts Receivable)
        if payment_type == 'Credit' and customer_id:
            customer = CustomerMaster.objects.get(id=customer_id)
            customer.opening_balance += invoice.net_amount
            customer.save()
        
        # 5. Trigger email notification to the customer (retailer)
        from wholesaleApp.utils.email_utils import send_invoice_email_async
        send_invoice_email_async(invoice)
        
        messages.success(request, f"Sales Invoice {invoice_number} saved successfully.")
        request.session['print_invoice_id'] = invoice.id
        return redirect(f"/sales/invoice/create/?saved_id={invoice.id}")
        
    saved_invoice = None
    saved_id = request.GET.get('saved_id')
    if saved_id:
        saved_invoice = SalesInvoice.objects.filter(id=saved_id).select_related('customer').first()

    context = {
        'customers': customers,
        'products': products,
        'page_title': 'Create Sales Invoice (Bill)',
        'saved_invoice': saved_invoice,
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/invoice_form.html', context)


def get_product_last_purchase_rate(request, pk):
    """API endpoint to get the actual last purchase rate and detailed past purchase history for a selected product."""
    from wholesaleApp.views.security_helpers import has_feature_access
    if not (has_feature_access(request.user, 'view_margins') or has_feature_access(request.user, 'purchase_list') or has_feature_access(request.user, 'purchase_create')):
        return JsonResponse({'error': 'Permission Denied'}, status=403)

    from wholesaleApp.models.purchase import PurchaseEntryItem, ProductBatch
    
    items = PurchaseEntryItem.objects.filter(product_id=pk).select_related('purchase_entry__supplier').order_by('-purchase_entry__invoice_date', '-id')[:10]
    
    history = []
    last_rate = 0.00

    if items.exists():
        last_rate = float(items[0].purchase_rate)
        for item in items:
            exp_str = item.expiry_date.strftime('%m/%y') if item.expiry_date else '-'
            date_str = item.purchase_entry.invoice_date.strftime('%d-%m-%Y') if (item.purchase_entry and item.purchase_entry.invoice_date) else '-'
            supp_name = item.purchase_entry.supplier.name if (item.purchase_entry and item.purchase_entry.supplier) else '-'
            inv_no = item.purchase_entry.invoice_number if item.purchase_entry else '-'

            history.append({
                'date': date_str,
                'invoice_number': inv_no,
                'supplier_name': supp_name,
                'batch': item.batch_number or '-',
                'expiry': exp_str,
                'quantity': item.quantity,
                'free_quantity': item.free_quantity,
                'purchase_rate': float(item.purchase_rate),
                'mrp': float(item.mrp),
                'total_amount': float(item.total_amount)
            })
    else:
        batches = ProductBatch.objects.filter(product_id=pk).order_by('-id')[:5]
        if batches.exists():
            last_rate = float(batches[0].purchase_rate)
            for batch in batches:
                exp_str = batch.expiry_date.strftime('%m/%y') if batch.expiry_date else '-'
                history.append({
                    'date': 'Stock Batch',
                    'invoice_number': '-',
                    'supplier_name': '-',
                    'batch': batch.batch_number or '-',
                    'expiry': exp_str,
                    'quantity': batch.quantity,
                    'free_quantity': 0,
                    'purchase_rate': float(batch.purchase_rate),
                    'mrp': float(batch.mrp) if batch.mrp else 0.00,
                    'total_amount': float(batch.purchase_rate * batch.quantity)
                })

    return JsonResponse({
        'product_id': pk,
        'last_purchase_rate': last_rate,
        'history': history
    })


def number_to_words(number):
    """Simple helper to convert a number to Indian currency format words."""
    try:
        number = int(round(number))
        if number == 0:
            return "Rupees Zero Only"
        
        words = []
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                 "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        def helper(n):
            if n < 20:
                return units[n]
            elif n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
            elif n < 1000:
                return units[n // 100] + " Hundred" + (" and " + helper(n % 100) if n % 100 != 0 else "")
            
        # Break into crores, lakhs, thousands, hundreds
        crore = number // 10000000
        number %= 10000000
        lakh = number // 100000
        number %= 100000
        thousand = number // 1000
        number %= 1000
        
        if crore:
            words.append(helper(crore) + " Crore")
        if lakh:
            words.append(helper(lakh) + " Lakh")
        if thousand:
            words.append(helper(thousand) + " Thousand")
        if number:
            words.append(helper(number))
            
        return "Rupees " + " ".join(words) + " Only"
    except Exception:
        return ""


@login_required
def invoice_print(request, pk):
    """View to render the printable invoice styled for A4 half-page (A5 landscape)."""
    # Fetch invoice, filtering by tenant is handled automatically by the custom TenantManager
    invoice = get_object_or_404(SalesInvoice, id=pk)
    items = invoice.items.all().select_related('product', 'batch')
    
    # Identify tenant details to print.
    # Fallback to the invoice's own tenant if request.tenant is None (Admin mode)
    print_tenant = request.tenant or invoice.tenant
    
    # Calculate invoice items breakdown
    item_details = []
    total_taxable_value = 0
    total_gst_calculated = 0
    
    for idx, item in enumerate(items, 1):
        qty = item.quantity
        rate = item.sale_rate
        disc_pct = item.discount_percentage
        gst_pct = item.product.gst_rate
        
        if item.is_retail:
            base_val = qty * (rate / Decimal(item.product.units_per_strip or 1))
        else:
            base_val = qty * rate
        disc_val = base_val * (disc_pct / 100)
        taxable_val = base_val - disc_val
        gst_val = taxable_val * (gst_pct / 100)
        
        total_taxable_value += taxable_val
        total_gst_calculated += gst_val
        
        # Calculate split taxes (CGST and SGST are 50% each of total GST for local sales)
        cgst_pct = gst_pct / 2
        sgst_pct = gst_pct / 2
        cgst_val = gst_val / 2
        sgst_val = gst_val / 2
        
        item_details.append({
            'idx': idx,
            'item': item,
            'product_name': item.product.name,
            'pack_size': item.product.pack_size,
            'hsn_code': item.product.hsn_code,
            'batch_number': item.batch.batch_number,
            'expiry_mask': item.batch.expiry_date.strftime('%m/%y') if item.batch.expiry_date else '—',
            'qty': qty,
            'free_qty': item.free_quantity,
            'mrp': item.batch.mrp,
            'rate': rate,
            'disc_pct': disc_pct,
            'gst_pct': gst_pct,
            'cgst_pct': cgst_pct,
            'sgst_pct': sgst_pct,
            'cgst_val': cgst_val,
            'sgst_val': sgst_val,
            'amount': item.total_amount
        })
        
    net_amount_words = number_to_words(invoice.net_amount)
    
    # ===== OUTSTANDING BALANCE WITH AGING =====
    outstanding_balance = Decimal('0.00')
    aging_0_30 = Decimal('0.00')
    aging_31_60 = Decimal('0.00')
    aging_61_90 = Decimal('0.00')
    aging_90_plus = Decimal('0.00')
    pending_bills = []
    
    customer = invoice.customer
    if customer and not invoice.is_retail:
        outstanding_balance = customer.opening_balance or Decimal('0.00')
        
        # Fetch all unpaid Credit invoices for this customer to calculate aging
        today = datetime.date.today()
        credit_invoices = SalesInvoice.objects.filter(
            customer=customer,
            payment_type='Credit'
        ).order_by('invoice_date')
        
        # Calculate payments received for this customer
        from wholesaleApp.models.customers import CustomerPayment
        total_payments = CustomerPayment.objects.filter(
            customer=customer
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Build aging from invoices — distribute payments FIFO (oldest first)
        remaining_payment = total_payments
        for inv in credit_invoices:
            inv_amount = inv.net_amount
            if remaining_payment >= inv_amount:
                remaining_payment -= inv_amount
                continue  # Fully paid, skip
            
            pending_amount = inv_amount - remaining_payment
            remaining_payment = Decimal('0.00')
            
            days_old = (today - inv.invoice_date).days
            if days_old < 0:
                days_old = 0
            
            if days_old <= 30:
                aging_0_30 += pending_amount
            elif days_old <= 60:
                aging_31_60 += pending_amount
            elif days_old <= 90:
                aging_61_90 += pending_amount
            else:
                aging_90_plus += pending_amount
            
            pending_bills.append({
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date,
                'amount': pending_amount,
                'days_old': days_old
            })
    
    # ===== QR CODE DATA =====
    qr_items_list = []
    for det in item_details:
        qr_items_list.append(f"{det['product_name']} x {det['qty']}")
    qr_items_str = ', '.join(qr_items_list)
    
    qr_data = (
        f"Invoice: {invoice.invoice_number}\n"
        f"Date: {invoice.invoice_date.strftime('%d-%m-%Y')}\n"
    )
    if customer:
        qr_data += f"Customer: {customer.name}\n"
    qr_data += (
        f"Items: {qr_items_str}\n"
        f"Total: Rs.{invoice.net_amount}"
    )
    
    context = {
        'invoice': invoice,
        'customer': customer,
        'tenant': print_tenant,
        'item_details': item_details,
        'total_taxable_value': total_taxable_value,
        'total_gst_calculated': total_gst_calculated,
        'cgst_total': total_gst_calculated / 2,
        'sgst_total': total_gst_calculated / 2,
        'net_amount_words': net_amount_words,
        # Outstanding balance & aging
        'outstanding_balance': outstanding_balance,
        'aging_0_30': aging_0_30,
        'aging_31_60': aging_31_60,
        'aging_61_90': aging_61_90,
        'aging_90_plus': aging_90_plus,
        'pending_bills': pending_bills,
        # QR Code
        'qr_data': qr_data,
    }
    return render(request, 'sale/invoice_print.html', context)


@login_required
@transaction.atomic
def invoice_edit(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'sales_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Sale Bills.")
        return redirect('invoice_list')
        
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(invoice.invoice_date):
        messages.error(request, "Action Denied: This invoice falls within a closed Financial Year and cannot be modified.")
        return redirect('invoice_list')
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        if not customer_id:
            customer_id = None
            
        patient_name = request.POST.get('patient_name', '').strip() or None
        patient_mobile = request.POST.get('patient_mobile', '').strip() or None
        doctor_name = request.POST.get('doctor_name', '').strip() or None
        
        invoice_date = request.POST.get('invoice_date')
        if is_date_in_closed_fy(invoice_date):
            messages.error(request, "Action Denied: The selected invoice date falls within a closed Financial Year.")
            return redirect('invoice_list')
        payment_type = request.POST.get('payment_type', 'Credit')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        discount_amount = Decimal(request.POST.get('discount_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        is_retail = request.POST.get('is_retail') == 'true' or request.POST.get('is_retail') == '1' or request.POST.get('is_retail') == 'on'
        
        # Extract item arrays from POST
        product_ids = request.POST.getlist('product[]')
        batch_ids = request.POST.getlist('batch[]')
        sale_rates = request.POST.getlist('sale_rate[]')
        quantities = request.POST.getlist('quantity[]')
        free_quantities = request.POST.getlist('free_quantity[]')
        discounts = request.POST.getlist('discount_percentage[]')
        totals = request.POST.getlist('total_amount[]')
        
        # 1. Temporarily restore all old stock quantities to calculate inventory correctly
        old_items = list(invoice.items.all().select_related('batch'))
        for item in old_items:
            batch = item.batch
            batch.quantity += (item.quantity + item.free_quantity)
            batch.save()
            
        # 2. Check if new items have sufficient stock
        for i in range(len(product_ids)):
            batch_id = batch_ids[i]
            qty = Decimal(quantities[i])
            free_qty = Decimal(free_quantities[i]) if free_quantities[i] else Decimal('0.0000')
            
            batch = ProductBatch.objects.get(id=batch_id)
            if batch.quantity < (qty + free_qty):
                # Rollback temporary stock changes by restoring them back to old state
                for old_item in old_items:
                    obatch = old_item.batch
                    obatch.quantity -= (old_item.quantity + old_item.free_quantity)
                    obatch.save()
                messages.error(request, f"Insufficient stock for batch {batch.batch_number}! Available: {batch.quantity}")
                return redirect('invoice_edit', pk=pk)
                
        # 3. Update customer outstanding balance: revert old net amount
        if invoice.payment_type == 'Credit' and invoice.customer:
            old_customer = invoice.customer
            old_customer.opening_balance -= invoice.net_amount
            old_customer.save()
        
        # 4. Delete old invoice items
        invoice.items.all().delete()
        
        # 5. Save updated invoice headers
        invoice.customer_id = customer_id
        invoice.patient_name = patient_name
        invoice.patient_mobile = patient_mobile
        invoice.doctor_name = doctor_name
        invoice.invoice_date = invoice_date
        invoice.payment_type = payment_type
        invoice.gross_amount = gross_amount
        invoice.discount_amount = discount_amount
        invoice.gst_amount = gst_amount
        invoice.net_amount = net_amount
        invoice.is_retail = is_retail
        invoice.save()
        
        # 6. Save new items and deduct stock
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_id = batch_ids[i]
            s_rate = Decimal(sale_rates[i])
            qty = Decimal(quantities[i])
            free_qty = Decimal(free_quantities[i]) if free_quantities[i] else Decimal('0.0000')
            disc_pct = Decimal(discounts[i]) if discounts[i] else Decimal('0.00')
            total_val = Decimal(totals[i])
            
            batch = ProductBatch.objects.get(id=batch_id)
            SalesInvoiceItem.objects.create(
                sales_invoice=invoice,
                product_id=prod_id,
                batch=batch,
                quantity=qty,
                free_quantity=free_qty,
                sale_rate=s_rate,
                discount_percentage=disc_pct,
                total_amount=total_val,
                is_retail=is_retail
            )
            # Deduct stock
            batch.quantity -= (qty + free_qty)
            batch.save()
            
        # 7. Apply new invoice net amount to customer balance
        if payment_type == 'Credit' and invoice.customer:
            new_customer = invoice.customer
            new_customer.opening_balance += invoice.net_amount
            new_customer.save()
        
        # 8. Trigger email notification to the customer (retailer)
        from wholesaleApp.utils.email_utils import send_invoice_email_async
        send_invoice_email_async(invoice)
        
        messages.success(request, f"Invoice {invoice.invoice_number} updated successfully!")
        request.session['print_invoice_id'] = invoice.id
        return redirect('invoice_list')
        
    context = {
        'invoice': invoice,
        'customers': customers,
        'products': products,
        'page_title': f'Edit Sales Invoice {invoice.invoice_number}',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/invoice_edit.html', context)


@login_required
@transaction.atomic
def invoice_delete(request, pk):
    from wholesaleApp.views.security_helpers import has_feature_access
    if not has_feature_access(request.user, 'sales_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete/cancel Sale Bills.")
        return redirect('invoice_list')
        
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(invoice.invoice_date):
        messages.error(request, "Action Denied: This invoice falls within a closed Financial Year and cannot be deleted.")
        return redirect('invoice_list')
    
    # 1. Restore inventory stock
    for item in invoice.items.all().select_related('batch'):
        batch = item.batch
        batch.quantity += (item.quantity + item.free_quantity)
        batch.save()
        
    # 2. Subtract from customer outstanding balance
    if invoice.payment_type == 'Credit':
        customer = invoice.customer
        customer.opening_balance -= invoice.net_amount
        customer.save()
    
    # 3. Delete the invoice
    invoice_number = invoice.invoice_number
    invoice.delete()
    
    messages.success(request, f"Invoice {invoice_number} has been deleted successfully, stock restored and customer balance reverted.")
    return redirect('invoice_list')


# ==================== SALES RETURNS ====================
@transaction.atomic
def sales_return_list(request):
    from wholesaleApp.models import SalesReturn
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context
    if not has_feature_access(request.user, 'sales_return_view'):
        messages.error(request, "Access Denied: You do not have permission to view Sales Returns.")
        return redirect('home')
        
    returns = SalesReturn.objects.all().select_related('customer')
    context = {
        'returns': returns,
        'page_title': 'Sales Returns',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/return_list.html', context)


@transaction.atomic
def sales_return_create(request):
    from wholesaleApp.models import SalesReturn, SalesReturnItem, CustomerMaster, ProductMaster, ProductBatch
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    if not has_feature_access(request.user, 'sales_return_create'):
        messages.error(request, "Access Denied: You do not have permission to create Sales Returns.")
        return redirect('sales_return_list')
    
    customers = CustomerMaster.objects.filter(status=True, is_deleted=False)
    products = ProductMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        return_number = request.POST.get('return_number')
        return_date = request.POST.get('return_date')
        from wholesaleApp.models.financial_year import is_date_in_closed_fy
        if is_date_in_closed_fy(return_date):
            messages.error(request, "Action Denied: The selected return date falls within a closed Financial Year.")
            return redirect('sales_return_list')
        gross_amount = Decimal(request.POST.get('gross_amount', 0))
        gst_amount = Decimal(request.POST.get('gst_amount', 0))
        net_amount = Decimal(request.POST.get('net_amount', 0))
        remarks = request.POST.get('remarks', '')
        
        customer = get_object_or_404(CustomerMaster, id=customer_id)
        
        # Create return
        s_return = SalesReturn.objects.create(
            customer=customer,
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
        batch_ids = request.POST.getlist('batch[]')
        sale_rates = request.POST.getlist('sale_rate[]')
        quantities = request.POST.getlist('quantity[]')
        totals = request.POST.getlist('total_amount[]')
        
        for i in range(len(product_ids)):
            prod_id = product_ids[i]
            batch_id = batch_ids[i]
            s_rate = Decimal(sale_rates[i])
            qty = int(quantities[i])
            total_val = Decimal(totals[i])
            
            batch = get_object_or_404(ProductBatch, id=batch_id)
            
            # Create Sales Return Item
            SalesReturnItem.objects.create(
                sales_return=s_return,
                product_id=prod_id,
                batch=batch,
                sale_rate=s_rate,
                quantity=qty,
                total_amount=total_val
            )
            
            # Restore stock (add back to inventory)
            batch.quantity += qty
            batch.save()
            
        # Deduct return value from Customer Balance (reduces their outstanding dues)
        customer.opening_balance -= net_amount
        customer.save()
        
        log_activity(
            request,
            action='CREATE',
            model_name='SalesReturn',
            object_id=s_return.id,
            object_repr=s_return.return_number,
            description=f"Recorded sales return from {customer.name} for ₹{net_amount}"
        )
        
        messages.success(request, f"Sales Return '{return_number}' recorded successfully.")
        return redirect('sales_return_list')
        
    context = {
        'customers': customers,
        'products': products,
        'page_title': 'New Sales Return',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/return_form.html', context)


@transaction.atomic
def sales_return_delete(request, pk):
    from wholesaleApp.models import SalesReturn, ProductBatch
    from wholesaleApp.views.security_helpers import has_feature_access, log_activity
    if not has_feature_access(request.user, 'sales_return_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Sales Returns.")
        return redirect('sales_return_list')
    
    s_return = get_object_or_404(SalesReturn, pk=pk)
    from wholesaleApp.models.financial_year import is_date_in_closed_fy
    if is_date_in_closed_fy(s_return.return_date):
        messages.error(request, "Action Denied: This return falls within a closed Financial Year and cannot be deleted.")
        return redirect('sales_return_list')
    customer = s_return.customer
    
    # Revert inventory stock restoration
    for item in s_return.items.all().select_related('batch'):
        batch = item.batch
        batch.quantity = max(0, batch.quantity - item.quantity)
        batch.save()
        
    # Add amount back to customer balance (outstanding dues increase back)
    customer.opening_balance += s_return.net_amount
    customer.save()
    
    log_activity(
        request,
        action='DELETE',
        model_name='SalesReturn',
        object_id=s_return.id,
        object_repr=s_return.return_number,
        description=f"Deleted sales return from {customer.name} and adjusted stock"
    )
    
    s_return.delete()
    messages.success(request, "Sales return deleted, stock reverted and customer balance adjusted.")
    return redirect('sales_return_list')


def invoice_email_bulk(request):
    """View to filter sales invoices by date and customer, and manually trigger email notifications."""
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    
    if not has_feature_access(request.user, 'sales_view'):
        messages.error(request, "Access Denied: You do not have permission to email bills.")
        return redirect('home')

    customers = CustomerMaster.objects.filter(status=True, is_deleted=False)
    
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    customer_id = request.GET.get('customer', '')

    invoices = SalesInvoice.objects.all().select_related('customer')

    # Apply filters
    if start_date_str:
        invoices = invoices.filter(invoice_date__gte=start_date_str)
    if end_date_str:
        invoices = invoices.filter(invoice_date__lte=end_date_str)
    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)

    # Default to last 30 days if no filter applied to prevent loading too much data
    if not start_date_str and not end_date_str and not customer_id:
        today = datetime.date.today()
        thirty_days_ago = today - datetime.timedelta(days=30)
        invoices = invoices.filter(invoice_date__gte=thirty_days_ago)
        # Populate defaults for the HTML date inputs
        start_date_str = thirty_days_ago.strftime('%Y-%m-%d')
        end_date_str = today.strftime('%Y-%m-%d')

    if request.method == 'POST':
        invoice_ids = request.POST.getlist('invoice_ids')
        if not invoice_ids:
            messages.warning(request, "No invoices were selected.")
            return redirect(request.get_full_path())

        from wholesaleApp.utils.email_utils import send_invoice_email_async
        selected_invoices = SalesInvoice.objects.filter(id__in=invoice_ids).select_related('customer')
        sent_count = 0
        skipped_count = 0

        for inv in selected_invoices:
            if inv.customer.email and inv.customer.email.strip():
                send_invoice_email_async(inv)
                sent_count += 1
            else:
                skipped_count += 1

        # Log the bulk action if log_activity is available
        try:
            log_activity(
                request,
                action='BULK_EMAIL',
                model_name='SalesInvoice',
                description=f"Manually triggered bulk email queue for {sent_count} invoices (skipped {skipped_count} due to missing email address)."
            )
        except Exception:
            pass

        if sent_count > 0:
            msg = f"Successfully queued {sent_count} invoice email(s) for sending in the background."
            if skipped_count > 0:
                msg += f" {skipped_count} invoice(s) were skipped because the customer has no email address."
            messages.success(request, msg)
        else:
            messages.error(request, f"Failed to send: All {skipped_count} selected invoice(s) belong to customers with no email address.")

        return redirect(request.get_full_path())

    import urllib.parse
    ordered_invoices = invoices.order_by('-invoice_date', '-id').select_related('tenant').prefetch_related('items__product')
    for inv in ordered_invoices:
        items_list = []
        for item in inv.items.all():
            items_list.append(f"- {item.product.name}: {item.quantity} Qty @ Rs. {item.sale_rate}")
        items_text = "\n".join(items_list)
        
        tenant_name = inv.tenant.company_name if inv.tenant else "easyPharma"
        text = (
            f"Dear {inv.customer.name},\n\n"
            f"Thank you for billing with *{tenant_name}*.\n\n"
            f"Your Invoice *{inv.invoice_number}* dated *{inv.invoice_date.strftime('%d-%m-%Y')}* is ready.\n\n"
            f"*Items Billed*:\n{items_text}\n\n"
            f"*Total Payable*: *Rs. {inv.net_amount}*\n\n"
            f"We look forward to serving you again."
        )
        inv.whatsapp_url = f"https://wa.me/{inv.customer.mobile}?text={urllib.parse.quote(text)}"

    context = {
        'invoices': ordered_invoices,
        'customers': customers,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_customer': customer_id,
        'page_title': 'Bulk Email Sales Bills',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/invoice_email_bulk.html', context)


@login_required
def delivery_management(request):
    """View to track pending bills/orders, assign them to delivery boys/salesmen, and update delivery status."""
    from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
    from django.contrib.auth.models import User
    from wholesaleApp.models import AreaMaster
    
    if not has_feature_access(request.user, 'sales_view'):
        messages.error(request, "Access Denied: You do not have permission to access Delivery Management.")
        return redirect('home')

    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "No active Tenant/Firm detected.")
        return redirect('home')

    # Fetch active delivery boys, salesmen, and MRs for assignment
    delivery_staff = User.objects.filter(
        profile__tenant=tenant,
        profile__role__in=['Delivery Boy', 'Salesman', 'MR']
    ).select_related('profile')

    areas = AreaMaster.objects.all()

    # GET filters
    selected_area = request.GET.get('area', '')
    selected_staff = request.GET.get('staff', '')

    unassigned_invoices = SalesInvoice.objects.filter(status='Pending', assigned_delivery_boy__isnull=True)
    assigned_invoices = SalesInvoice.objects.filter(status='Pending', assigned_delivery_boy__isnull=False).select_related('assigned_delivery_boy')

    if selected_area:
        unassigned_invoices = unassigned_invoices.filter(customer__area_id=selected_area)
        assigned_invoices = assigned_invoices.filter(customer__area_id=selected_area)
    if selected_staff:
        assigned_invoices = assigned_invoices.filter(assigned_delivery_boy_id=selected_staff)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign':
            invoice_ids = request.POST.getlist('invoice_ids')
            staff_id = request.POST.get('delivery_staff')
            
            if invoice_ids and staff_id:
                try:
                    staff_user = User.objects.get(id=staff_id, profile__tenant=tenant)
                    SalesInvoice.objects.filter(id__in=invoice_ids).update(assigned_delivery_boy=staff_user)
                    messages.success(request, f"Successfully assigned {len(invoice_ids)} order(s) to {staff_user.username}.")
                    
                    try:
                        log_activity(
                            request,
                            action='ASSIGN_DELIVERY',
                            model_name='SalesInvoice',
                            description=f"Assigned {len(invoice_ids)} invoices to delivery user: {staff_user.username}"
                        )
                    except Exception:
                        pass
                except User.DoesNotExist:
                    messages.error(request, "Selected staff user not found or does not belong to this tenant.")
            else:
                messages.warning(request, "Please select both invoices and a staff member.")
                
        elif action == 'update_status':
            invoice_id = request.POST.get('invoice_id')
            new_status = request.POST.get('new_status')
            
            if invoice_id and new_status in ['Pending', 'Delivered', 'Cancelled']:
                try:
                    invoice = SalesInvoice.objects.get(id=invoice_id)
                    old_status = invoice.status
                    invoice.status = new_status
                    invoice.save()
                    
                    messages.success(request, f"Order {invoice.invoice_number} marked as {new_status}.")
                    
                    try:
                        log_activity(
                            request,
                            action='UPDATE_STATUS',
                            model_name='SalesInvoice',
                            object_id=invoice.id,
                            object_repr=invoice.invoice_number,
                            description=f"Updated invoice status from {old_status} to {new_status}."
                        )
                    except Exception:
                        pass
                except SalesInvoice.DoesNotExist:
                    messages.error(request, "Order not found.")
                    
        return redirect(request.get_full_path())

    context = {
        'unassigned_invoices': unassigned_invoices.order_by('invoice_date', 'id').select_related('customer__area'),
        'assigned_invoices': assigned_invoices.order_by('invoice_date', 'id').select_related('customer__area'),
        'delivery_staff': delivery_staff,
        'areas': areas,
        'selected_area': selected_area,
        'selected_staff': selected_staff,
        'page_title': 'Delivery Management',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'sale/delivery_management.html', context)



