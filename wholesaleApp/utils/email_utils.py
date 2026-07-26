import logging
import threading
from decimal import Decimal
from django.conf import settings
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from wholesaleApp.models.sales import SalesInvoice
from wholesaleApp.models.tenant import TenantEmailConfig

logger = logging.getLogger('wholesaleApp')


def send_invoice_email(invoice_id):
    """
    Sends the invoice email to the customer. 
    Retrieves SMTP configuration specific to the invoice's tenant, or falls back to global settings in development.
    """
    try:
        # Fetch the invoice with related customer and tenant
        invoice = SalesInvoice.objects.select_related('customer', 'tenant').get(id=invoice_id)
    except SalesInvoice.DoesNotExist:
        logger.error(f"Failed to send email: Invoice ID {invoice_id} not found.")
        return False

    customer = invoice.customer
    if not customer.email or not customer.email.strip():
        logger.info(f"Customer '{customer.name}' has no email address. Skipping email for invoice {invoice.invoice_number}.")
        return False

    tenant = invoice.tenant
    email_config = None
    if tenant:
        try:
            email_config = tenant.email_config
        except TenantEmailConfig.DoesNotExist:
            pass

    # Resolve email connection and sender
    if email_config and email_config.is_active:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=email_config.email_host,
            port=email_config.email_port,
            username=email_config.email_host_user,
            password=email_config.email_host_password,
            use_tls=email_config.email_use_tls,
            use_ssl=email_config.email_use_ssl,
        )
        from_email = email_config.default_from_email or email_config.email_host_user
    else:
        # Check if running in production
        is_production = getattr(settings, 'IS_PRODUCTION', False)
        if is_production:
            logger.warning(f"Production safety block: No active TenantEmailConfig for tenant '{tenant.name if tenant else 'None'}'. Skipping email sending for invoice {invoice.invoice_number}.")
            return False

        # If in development, fall back to global settings (prints to console if EMAIL_HOST_USER is empty)
        logger.info(f"Development fallback: Using default system email backend for invoice {invoice.invoice_number}.")
        connection = get_connection()
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        # Gather invoice items & details for the email template
        items = invoice.items.all().select_related('product', 'batch')
        item_details = []
        total_taxable_value = Decimal('0.00')
        total_gst_calculated = Decimal('0.00')

        for idx, item in enumerate(items, 1):
            qty = item.quantity
            rate = item.sale_rate
            disc_pct = item.discount_percentage
            gst_pct = item.product.gst_rate

            base_val = qty * rate
            disc_val = base_val * (disc_pct / Decimal('100.00'))
            taxable_val = base_val - disc_val
            gst_val = taxable_val * (gst_pct / Decimal('100.00'))

            total_taxable_value += taxable_val
            total_gst_calculated += gst_val

            item_details.append({
                'idx': idx,
                'item': item,
                'product_name': item.product.name,
                'pack_size': item.product.pack_size,
                'hsn_code': item.product.hsn_code,
                'batch_number': item.batch.batch_number,
                'qty': qty,
                'free_qty': item.free_quantity,
                'mrp': item.batch.mrp,
                'rate': rate,
                'disc_pct': disc_pct,
                'gst_pct': gst_pct,
                'amount': item.total_amount
            })

        # Build email body using HTML template
        context = {
            'invoice': invoice,
            'customer': customer,
            'tenant': tenant,
            'item_details': item_details,
            'total_taxable_value': total_taxable_value,
            'total_gst_calculated': total_gst_calculated,
            'cgst_total': total_gst_calculated / Decimal('2.00'),
            'sgst_total': total_gst_calculated / Decimal('2.00'),
        }

        subject = f"Tax Invoice {invoice.invoice_number} - {tenant.company_name if tenant else 'easyPharma'}"
        html_content = render_to_string('emails/invoice_email.html', context)
        text_content = strip_tags(html_content)

        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[customer.email.strip()],
            connection=connection,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Email sent successfully for invoice {invoice.invoice_number} to {customer.email.strip()}.")
        return True

    except Exception as e:
        logger.exception(f"Exception occurred while sending email for invoice {invoice.invoice_number}: {str(e)}")
        return False


def send_invoice_email_async(invoice):
    """
    Spawns a background thread to send the invoice email, 
    preventing UI delay for the operator.
    Runs synchronously during unit testing to avoid SQLite database locking.
    """
    if not invoice or not invoice.id:
        return
    
    import sys
    # Check if running within a test execution
    is_testing = 'test' in sys.argv or any('test' in arg for arg in sys.argv)
    
    if is_testing:
        send_invoice_email(invoice.id)
    else:
        # We pass the ID to avoid thread-safety issues with django objects
        thread = threading.Thread(
            target=send_invoice_email,
            args=(invoice.id,),
            name=f"EmailThread-Invoice-{invoice.id}"
        )
        thread.daemon = True
        thread.start()


def send_po_email(po_id):
    """
    Sends the Purchase Order email to the supplier.
    Retrieves SMTP configuration specific to the PO's tenant, or falls back to global settings in development.
    """
    from wholesaleApp.models.purchase import PurchaseOrder
    try:
        po = PurchaseOrder.objects.select_related('supplier', 'tenant').get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        logger.error(f"Failed to send email: PO ID {po_id} not found.")
        return False

    supplier = po.supplier
    if not supplier.email or not supplier.email.strip():
        logger.info(f"Supplier '{supplier.name}' has no email address. Skipping PO email for PO {po.po_number}.")
        return False

    tenant = po.tenant
    email_config = None
    if tenant:
        try:
            email_config = tenant.email_config
        except TenantEmailConfig.DoesNotExist:
            pass

    if email_config and email_config.is_active:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=email_config.email_host,
            port=email_config.email_port,
            username=email_config.email_host_user,
            password=email_config.email_host_password,
            use_tls=email_config.email_use_tls,
            use_ssl=email_config.email_use_ssl,
        )
        from_email = email_config.default_from_email or email_config.email_host_user
    else:
        is_production = getattr(settings, 'IS_PRODUCTION', False)
        if is_production:
            logger.warning(f"Production safety block: No active TenantEmailConfig for tenant. Skipping PO email for PO {po.po_number}.")
            return False
        connection = get_connection()
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        items = po.items.all().select_related('product')
        item_details = []
        for idx, item in enumerate(items, 1):
            item_details.append({
                'idx': idx,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'expected_rate': item.expected_rate,
                'total_amount': item.total_amount
            })

        context = {
            'po': po,
            'supplier': supplier,
            'tenant': tenant,
            'item_details': item_details,
        }

        subject = f"Purchase Order {po.po_number} - {tenant.company_name if tenant else 'easyPharma'}"
        html_content = render_to_string('emails/po_email.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[supplier.email.strip()],
            connection=connection,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"PO Email sent successfully for PO {po.po_number} to {supplier.email.strip()}.")
        return True
    except Exception as e:
        logger.exception(f"Exception occurred while sending PO email for PO {po.po_number}: {str(e)}")
        return False


def send_po_email_async(po):
    """
    Spawns a background thread to send the Purchase Order email, 
    preventing UI delay for the operator.
    Runs synchronously during unit testing to avoid SQLite database locking.
    """
    if not po or not po.id:
        return
    
    import sys
    is_testing = 'test' in sys.argv or any('test' in arg for arg in sys.argv)
    
    if is_testing:
        send_po_email(po.id)
    else:
        thread = threading.Thread(
            target=send_po_email,
            args=(po.id,),
            name=f"EmailThread-PO-{po.id}"
        )
        thread.daemon = True
        thread.start()

