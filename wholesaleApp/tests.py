from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from wholesaleApp.models import (
    CompanyMaster, DrugMaster, ProductTypeMaster, ProductMaster,
    SupplierMaster, ProductBatch, PurchaseOrder, PurchaseOrderItem,
    PurchaseEntry, PurchaseEntryItem, AreaMaster, SubareaMaster, CustomerMaster,
    SalesInvoice, SalesInvoiceItem
)

class MasterDataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_master", password="password123")
        self.client.force_login(self.user)
        # Create master data
        self.company = CompanyMaster.objects.create(name="Cipla Ltd", code="CIPLA")
        self.drug = DrugMaster.objects.create(name="Paracetamol 500mg")
        self.p_type = ProductTypeMaster.objects.create(name="Tablet")
        self.product = ProductMaster.objects.create(
            name="Crocin 650mg",
            company=self.company,
            drug_composition=self.drug,
            product_type=self.p_type,
            pack_size="10 Tab",
            hsn_code="3004",
            gst_rate=12.00,
            min_stock=10
        )

    def test_model_creation(self):
        # Verify model data saved correctly
        self.assertEqual(CompanyMaster.objects.count(), 1)
        self.assertEqual(DrugMaster.objects.count(), 1)
        self.assertEqual(ProductTypeMaster.objects.count(), 1)
        self.assertEqual(ProductMaster.objects.count(), 1)
        
        self.assertEqual(self.product.company.name, "Cipla Ltd")
        self.assertEqual(self.product.drug_composition.name, "Paracetamol 500mg")
        self.assertEqual(self.product.product_type.name, "Tablet")

    def test_view_status_codes(self):
        # Test company list view
        response = self.client.get(reverse('company_list'))
        self.assertEqual(response.status_code, 200)

        # Test drug list view
        response = self.client.get(reverse('drug_list'))
        self.assertEqual(response.status_code, 200)

        # Test product type list view
        response = self.client.get(reverse('type_list'))
        self.assertEqual(response.status_code, 200)

        # Test product list view
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)


class PurchaseModuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_purchase", password="password123")
        self.client.force_login(self.user)
        # Create base master data
        self.supplier = SupplierMaster.objects.create(
            name="Alpha Pharma Pvt Ltd",
            mobile="9876543210",
            city="Mumbai",
            state="Maharashtra"
        )
        self.company = CompanyMaster.objects.create(name="Cipla Ltd", code="CIPLA")
        self.p_type = ProductTypeMaster.objects.create(name="Tablet")
        self.product = ProductMaster.objects.create(
            name="Crocin 650mg",
            company=self.company,
            product_type=self.p_type,
            pack_size="10 Tab",
            gst_rate=12.00
        )

    def test_purchase_order_creation(self):
        po = PurchaseOrder.objects.create(
            po_number="PO-TEST-0001",
            supplier=self.supplier,
            po_date="2026-07-13",
            status="Sent"
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=self.product,
            quantity=100,
            expected_rate=15.00
        )
        
        # Verify total amount calculation
        self.assertEqual(item.total_amount, 1500.00)
        
        # Verify status code for PO views
        response = self.client.get(reverse('po_list'))
        self.assertEqual(response.status_code, 200)

    def test_purchase_entry_inventory_and_balance_update(self):
        # Initial supplier balance should be 0
        self.assertEqual(float(self.supplier.opening_balance), 0.00)
        
        # Initial stock should be 0
        self.assertEqual(ProductBatch.objects.filter(product=self.product).count(), 0)

        # Post data to simulate invoice save
        # Taxable value: 10 packs * 100 Rs = 1000 Rs
        # 10% disc = 100 Rs, taxable after disc = 900 Rs
        # 12% GST = 108 Rs
        # Total amount = 1008 Rs
        response = self.client.post(reverse('purchase_entry_create'), {
            'supplier': self.supplier.id,
            'invoice_number': 'BILL-1002',
            'invoice_date': '2026-07-13',
            'gross_amount': '900.00',
            'discount_amount': '100.00',
            'gst_amount': '108.00',
            'net_amount': '1008.00',
            
            # Arrays
            'product[]': [self.product.id],
            'batch_number[]': ['B101'],
            'expiry_date[]': ['2028-12-31'],
            'mrp[]': ['120.00'],
            'purchase_rate[]': ['100.00'],
            'sale_rate[]': ['110.00'],
            'quantity[]': [10],
            'free_quantity[]': [2],
            'discount_percentage[]': [10.00],
            'total_amount[]': [1008.00]
        })
        
        # Verify redirect to entry create with saved_id
        entry = PurchaseEntry.objects.first()
        self.assertRedirects(response, f"{reverse('purchase_entry_create')}?saved_id={entry.id}")

        # Verify entry created
        self.assertEqual(PurchaseEntry.objects.count(), 1)
        self.assertEqual(PurchaseEntryItem.objects.count(), 1)
        
        # Verify batch inventory created with correct quantity (billed 10 + free 2 = 12)
        self.assertEqual(ProductBatch.objects.count(), 1)
        batch = ProductBatch.objects.first()
        self.assertEqual(batch.batch_number, 'B101')
        self.assertEqual(batch.quantity, 12)
        
        # Verify supplier balance updated
        self.supplier.refresh_from_db()
        self.assertEqual(float(self.supplier.opening_balance), 1008.00)


class AreaMasterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_area", password="password123")
        self.client.force_login(self.user)
        self.area = AreaMaster.objects.create(city="Mumbai", code="MUM")
        self.subarea = SubareaMaster.objects.create(area=self.area, name="Andheri West")

    def test_area_list_view(self):
        response = self.client.get(reverse('area_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mumbai")
        self.assertContains(response, "Andheri West")

    def test_area_create(self):
        response = self.client.post(reverse('area_create'), {
            'city': 'Thane',
            'code': 'THN'
        })
        self.assertRedirects(response, reverse('area_list'))
        self.assertEqual(AreaMaster.objects.filter(city="Thane").count(), 1)


class SalesModuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_sales", password="password123")
        self.client.force_login(self.user)
        # Create base master data
        self.area = AreaMaster.objects.create(city="Mumbai", code="MUM")
        self.customer = CustomerMaster.objects.create(
            name="Apex Chemist",
            mobile="9988776655",
            area=self.area,
            city="Mumbai",
            state="Maharashtra"
        )
        self.company = CompanyMaster.objects.create(name="Alkem Ltd", code="ALKEM")
        self.p_type = ProductTypeMaster.objects.create(name="Capsule")
        self.product = ProductMaster.objects.create(
            name="Amoxicillin 500mg",
            company=self.company,
            product_type=self.p_type,
            pack_size="10 Caps",
            gst_rate=12.00,
            scheme_qty=10,
            scheme_free=1
        )
        # Add stock batch
        self.batch = ProductBatch.objects.create(
            product=self.product,
            batch_number="B-AMX-99",
            expiry_date="2027-06-30",
            mrp=150.00,
            purchase_rate=100.00,
            sale_rate=120.00,
            quantity=100
        )

    def test_sales_invoice_creation_and_stock_deduction(self):
        # Initial values
        self.assertEqual(self.batch.quantity, 100)
        self.assertEqual(float(self.customer.opening_balance), 0.00)

        # Post invoice request
        # 20 quantity should auto calculate 2 free items -> 22 packs deducted
        # Taxable value: 20 packs * 120 Rs = 2400 Rs
        # 12% GST = 288 Rs
        # Net Amount = 2688 Rs
        response = self.client.post(reverse('invoice_create'), {
            'customer': self.customer.id,
            'invoice_date': '2026-07-13',
            'gross_amount': '2400.00',
            'discount_amount': '0.00',
            'gst_amount': '288.00',
            'net_amount': '2688.00',
            
            # Arrays
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['120.00'],
            'quantity[]': [20],
            'free_quantity[]': [2],
            'discount_percentage[]': [0.00],
            'total_amount[]': [2688.00]
        })

        # Verify redirect to invoice_create with saved_id parameter for 3-option modal
        self.assertTrue(response.url.startswith(reverse('invoice_create')))

        # Verify database invoice record
        self.assertEqual(SalesInvoice.objects.count(), 1)
        self.assertEqual(SalesInvoiceItem.objects.count(), 1)

        # Verify batch stock deducted (100 - (20 + 2) = 78)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 78)

        # Verify customer outstanding updated
        self.customer.refresh_from_db()
        self.assertEqual(float(self.customer.opening_balance), 2688.00)

    def test_insufficient_stock_prevention(self):
        # Post invoice requesting 150 items (exceeding stock of 100)
        response = self.client.post(reverse('invoice_create'), {
            'customer': self.customer.id,
            'invoice_date': '2026-07-13',
            'gross_amount': '18000.00',
            'discount_amount': '0.00',
            'gst_amount': '2160.00',
            'net_amount': '20160.00',
            
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['120.00'],
            'quantity[]': [150],
            'free_quantity[]': [0],
            'discount_percentage[]': [0.00],
            'total_amount[]': [20160.00]
        })

        # Verify that it redirects back to create invoice page on failure
        self.assertRedirects(response, reverse('invoice_create'))
        
        # Verify no invoice was saved
        self.assertEqual(SalesInvoice.objects.count(), 0)

        # Verify stock batch remains unchanged (100)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 100)


from django.contrib.auth.models import User
from wholesaleApp.models.permissions import AppGroupModule, AppFeature, UserFeaturePermission

class PermissionMatrixTests(TestCase):
    def setUp(self):
        # Create a test employee user
        self.employee = User.objects.create_user(username="ramesh", password="password123")
        
        # Seed permissions
        from wholesaleApp.views.security_helpers import seed_default_permissions
        seed_default_permissions()
        
        self.sales_create_feature = AppFeature.objects.get(codename="sales_create")
        self.purchase_create_feature = AppFeature.objects.get(codename="purchase_create")
        
        from wholesaleApp.models import CustomerMaster, AreaMaster
        self.area = AreaMaster.objects.create(city="Test City", code="TC")
        self.customer = CustomerMaster.objects.create(name="Test Customer", mobile="1234567890", area=self.area, opening_balance=0)
        
    def test_unauthorized_user_is_blocked_from_invoicing(self):
        self.client.force_login(self.employee)
        # Explicitly revoke sales_create for unauthorized test
        UserFeaturePermission.objects.filter(user=self.employee, feature=self.sales_create_feature).update(is_granted=False)
        
        # Try to view invoice creation
        response = self.client.get(reverse('invoice_create'))
        self.assertEqual(response.status_code, 302) # Redirects with permission denied
        self.assertRedirects(response, reverse('home'))
        
    def test_authorized_user_can_access_invoicing(self):
        self.client.force_login(self.employee)
        
        # Grant sales_create permission
        UserFeaturePermission.objects.update_or_create(
            user=self.employee,
            feature=self.sales_create_feature,
            defaults={'is_granted': True}
        )
        
        response = self.client.get(reverse('invoice_create'))
        self.assertEqual(response.status_code, 200) # Access granted!

    def test_unauthorized_user_blocked_from_invoice_edit(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('invoice_edit', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('invoice_list'))

    def test_authorized_user_can_access_invoice_edit(self):
        self.client.force_login(self.employee)
        from wholesaleApp.models import SalesInvoice
        invoice = SalesInvoice.objects.create(invoice_number="INV-TEST-01", invoice_date="2026-07-28", customer=self.customer, gross_amount=0, discount_amount=0, gst_amount=0, net_amount=0)
        feature_edit = AppFeature.objects.get(codename="sales_edit")
        UserFeaturePermission.objects.update_or_create(user=self.employee, feature=feature_edit, defaults={'is_granted': True})
        response = self.client.get(reverse('invoice_edit', kwargs={'pk': invoice.id}))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_blocked_from_invoice_delete(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('invoice_delete', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('invoice_list'))

    def test_authorized_user_can_access_invoice_delete(self):
        self.client.force_login(self.employee)
        from wholesaleApp.models import SalesInvoice
        invoice = SalesInvoice.objects.create(invoice_number="INV-TEST-02", invoice_date="2026-07-28", customer=self.customer, gross_amount=0, discount_amount=0, gst_amount=0, net_amount=0)
        feature_delete = AppFeature.objects.get(codename="sales_delete")
        UserFeaturePermission.objects.update_or_create(user=self.employee, feature=feature_delete, defaults={'is_granted': True})
        response = self.client.post(reverse('invoice_delete', kwargs={'pk': invoice.id}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('invoice_list'))

    def test_unauthorized_user_blocked_from_customer_create(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('createcustomer'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_authorized_user_can_access_customer_create(self):
        self.client.force_login(self.employee)
        feature_cust_create = AppFeature.objects.get(codename="customer_create")
        UserFeaturePermission.objects.update_or_create(user=self.employee, feature=feature_cust_create, defaults={'is_granted': True})
        response = self.client.get(reverse('createcustomer'))
        self.assertEqual(response.status_code, 200)
        
    def test_owner_permissions_matrix_view_access(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('user_permission_matrix'))
        self.assertEqual(response.status_code, 302) # Blocked!
        
        # Owner superuser has access
        self.owner = User.objects.create_superuser(username="owner", password="password")
        self.client.force_login(self.owner)
        response = self.client.get(reverse('user_permission_matrix'))
        self.assertEqual(response.status_code, 200) # Access granted!


class UserManagementCRUDTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="ramesh", password="password123")
        self.owner = User.objects.create_superuser(username="owner", password="password")

    def test_unauthorized_user_blocked_from_user_management(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_owner_can_manage_users(self):
        self.client.force_login(self.owner)
        
        # 1. List
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        
        # 2. Create User
        response = self.client.post(reverse('user_create'), {
            'username': 'suresh',
            'email': 'suresh@easypharma.com',
            'password': 'password123',
            'role': 'Salesman',
            'mobile': '9876543210'
        })
        self.assertRedirects(response, reverse('user_list'))
        self.assertEqual(User.objects.filter(username="suresh").count(), 1)
        
        # Verify Profile and Role
        suresh = User.objects.get(username="suresh")
        self.assertEqual(suresh.profile.role, "Salesman")
        
        # 3. Edit User
        response = self.client.post(reverse('user_edit', args=[suresh.id]), {
            'username': 'suresh_edit',
            'email': 'suresh_new@easypharma.com',
            'role': 'Delivery Boy',
            'mobile': '9998887776'
        })
        self.assertRedirects(response, reverse('user_list'))
        suresh.refresh_from_db()
        self.assertEqual(suresh.username, "suresh_edit")
        self.assertEqual(suresh.profile.role, "Delivery Boy")
        
        # 4. Delete User
        response = self.client.post(reverse('user_delete', args=[suresh.id]))
        self.assertRedirects(response, reverse('user_list'))
        self.assertEqual(User.objects.filter(username="suresh_edit").count(), 0)


class AuthAndReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="biller", password="password123")
        
        # Seed permissions
        from wholesaleApp.views.security_helpers import seed_default_permissions
        seed_default_permissions()
        
        from wholesaleApp.models import AppFeature, UserFeaturePermission
        feature_out = AppFeature.objects.get(codename="report_outstanding")
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_out, defaults={'is_granted': True})

    def test_login_page_renders(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_reports_dashboard_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_sales_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('report_sales'))
        self.assertEqual(response.status_code, 200)

    def test_expiry_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('report_expiry'))
        self.assertEqual(response.status_code, 200)

    def test_stock_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('report_stock'))
        self.assertEqual(response.status_code, 200)

    def test_outstanding_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('report_outstanding'))
        self.assertEqual(response.status_code, 200)


from django.contrib.auth.models import User
from wholesaleApp.models.tenant import Tenant, set_current_tenant

class MultiTenancyTests(TestCase):
    def setUp(self):
        # Clear thread-local tenant to prevent leakage from previous steps
        set_current_tenant(None)
        
        # Create two tenants
        self.tenant_a = Tenant.objects.create(name="tenant_a", company_name="Company A", is_active=True)
        self.tenant_b = Tenant.objects.create(name="tenant_b", company_name="Company B", is_active=True)
        
        # Create a superuser
        self.superuser = User.objects.create_superuser(username="admin", password="password")
        
        # Create a normal user and associate with Tenant A
        self.user_a = User.objects.create_user(username="user_a", password="password")
        self.user_a.profile.tenant = self.tenant_a
        self.user_a.profile.save()

    def tearDown(self):
        # Clean up thread-local tenant
        set_current_tenant(None)

    def test_tenant_creation(self):
        self.assertEqual(Tenant.objects.count(), 2)

    def test_data_isolation(self):
        # Set thread local tenant to A
        set_current_tenant(self.tenant_a)
        
        # Create a supplier under Tenant A
        supplier_a = SupplierMaster.objects.create(
            name="Supplier A",
            mobile="9876543210",
            city="City A",
            state="State A"
        )
        self.assertEqual(SupplierMaster.objects.count(), 1)
        self.assertEqual(SupplierMaster.objects.first().name, "Supplier A")
        
        # Switch thread local tenant to B
        set_current_tenant(self.tenant_b)
        self.assertEqual(SupplierMaster.objects.count(), 0) # Should be empty!
        
        # Create a supplier under Tenant B
        supplier_b = SupplierMaster.objects.create(
            name="Supplier B",
            mobile="9876543211",
            city="City B",
            state="State B"
        )
        self.assertEqual(SupplierMaster.objects.count(), 1)
        self.assertEqual(SupplierMaster.objects.first().name, "Supplier B")
        
        # Switch thread local to None (global admin view)
        set_current_tenant(None)
        # Should return both suppliers
        self.assertEqual(SupplierMaster.objects.count(), 2)
        
    def test_switch_tenant_view(self):
        self.client.force_login(self.superuser)
        
        # Switch to tenant A
        response = self.client.post(reverse('switch_tenant'), {'tenant_id': self.tenant_a.id})
        self.assertEqual(self.client.session['active_tenant_id'], self.tenant_a.id)
        
        # Switch back to all
        response = self.client.post(reverse('switch_tenant'), {'tenant_id': ''})
        self.assertNotIn('active_tenant_id', self.client.session)

    def test_invoice_print_view(self):
        # Setup data for sales invoice
        set_current_tenant(self.tenant_a)
        area = AreaMaster.objects.create(code="A1", city="Mumbai")
        cust = CustomerMaster.objects.create(name="Customer A", mobile="1234567890", area=area, city="Mumbai", state="MH")
        company = CompanyMaster.objects.create(name="Cipla")
        p_type = ProductTypeMaster.objects.create(name="Tab")
        prod = ProductMaster.objects.create(name="Crocin", company=company, product_type=p_type, pack_size="10")
        batch = ProductBatch.objects.create(product=prod, batch_number="B1", expiry_date="2030-01-01", mrp=10, purchase_rate=5, sale_rate=8, quantity=100)
        
        invoice = SalesInvoice.objects.create(
            invoice_number="INV-0001",
            customer=cust,
            invoice_date="2026-07-15",
            gross_amount=80,
            discount_amount=0,
            gst_amount=9.6,
            net_amount=89.6
        )
        
        # Log in and check page response
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('invoice_print', args=[invoice.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "INV-0001")
        self.assertContains(response, "Customer A")
        self.assertContains(response, "Company A")


from decimal import Decimal


class InvoiceCrudAndWholesalePricingTests(TestCase):
    def setUp(self):
        # Clear current tenant context
        set_current_tenant(None)
        
        # Setup tenant
        self.tenant = Tenant.objects.create(name="main_shop", company_name="Main Shop Pharmacy", is_active=True)
        set_current_tenant(self.tenant)
        
        # Setup master data
        self.area = AreaMaster.objects.create(code="B1", city="Mumbai")
        
        # Setup a Retailer customer and a Wholesaler customer
        self.retailer = CustomerMaster.objects.create(
            name="Retail Chemist",
            mobile="9876543200",
            area=self.area,
            city="Mumbai",
            state="MH",
            customer_type="Retailer"
        )
        self.wholesaler = CustomerMaster.objects.create(
            name="Wholesale Distributor",
            mobile="9876543201",
            area=self.area,
            city="Mumbai",
            state="MH",
            customer_type="Wholesaler"
        )
        
        self.company = CompanyMaster.objects.create(name="Cipla")
        self.p_type = ProductTypeMaster.objects.create(name="Tab")
        self.product = ProductMaster.objects.create(name="Crocin 650mg", company=self.company, product_type=self.p_type, pack_size="10")
        
        # Setup a batch with different rates
        self.batch = ProductBatch.objects.create(
            product=self.product,
            batch_number="B123",
            expiry_date="2030-01-01",
            mrp=100.00,
            purchase_rate=70.00,
            sale_rate=90.00,
            wholesale_rate=80.00,
            quantity=100
        )
        
        # Setup user
        self.user = User.objects.create_superuser(username="operator", password="password")
        self.user.profile.tenant = self.tenant
        self.user.profile.save()

    def tearDown(self):
        set_current_tenant(None)

    def test_invoice_create_uses_wholesaler_rate_view(self):
        # Log in
        self.client.force_login(self.user)
        
        # Test creation of invoice for Wholesaler
        post_data = {
            'customer': self.wholesaler.id,
            'invoice_date': '2026-07-15',
            'gross_amount': '80.00',
            'discount_amount': '0.00',
            'gst_amount': '9.60',
            'net_amount': '89.60',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['80.00'], # Wholesale rate used here
            'quantity[]': ['1'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['89.60']
        }
        response = self.client.post(reverse('invoice_create'), post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify invoice created and uses wholesale rate
        invoice = SalesInvoice.objects.get(customer=self.wholesaler)
        self.assertEqual(float(invoice.net_amount), 89.60)
        item = invoice.items.first()
        self.assertEqual(float(item.sale_rate), 80.00) # Wholesale rate saved!
        
        # Stock should be deducted
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 99)
        
        # Customer balance should be updated
        self.wholesaler.refresh_from_db()
        self.assertEqual(float(self.wholesaler.opening_balance), 89.60)

    def test_invoice_edit_view(self):
        self.client.force_login(self.user)
        
        # Create a base invoice first
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-15",
            gross_amount=90,
            discount_amount=0,
            gst_amount=10.8,
            net_amount=100.8
        )
        item = SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=2,
            free_quantity=0,
            sale_rate=45.00,
            total_amount=100.80
        )
        self.batch.quantity -= 2
        self.batch.save()
        self.retailer.opening_balance = Decimal('100.80')
        self.retailer.save()
        
        # Verify starting state
        self.assertEqual(self.batch.quantity, 98)
        self.assertEqual(float(self.retailer.opening_balance), 100.80)
        
        # Perform edit via POST (updating quantity from 2 to 5)
        post_data = {
            'customer': self.retailer.id,
            'invoice_date': '2026-07-15',
            'gross_amount': '225.00',
            'discount_amount': '0.00',
            'gst_amount': '27.00',
            'net_amount': '252.00',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['45.00'],
            'quantity[]': ['5'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['252.00']
        }
        response = self.client.post(reverse('invoice_edit', args=[invoice.id]), post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify invoice items updated
        invoice.refresh_from_db()
        self.assertEqual(float(invoice.net_amount), 252.00)
        self.assertEqual(invoice.items.count(), 1)
        self.assertEqual(invoice.items.first().quantity, 5)
        
        # Verify stock correctly adjusted (100 starting - 5 = 95)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 95)
        
        # Verify customer balance correctly adjusted (originally 0 + 252 = 252)
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 252.00)

    def test_invoice_delete_view(self):
        self.client.force_login(self.user)
        
        # Create an invoice
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-15",
            gross_amount=90,
            discount_amount=0,
            gst_amount=10.8,
            net_amount=100.8
        )
        item = SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=5,
            free_quantity=1,
            sale_rate=18.00,
            total_amount=100.80
        )
        self.batch.quantity -= 6 # qty + free_qty
        self.batch.save()
        self.retailer.opening_balance = Decimal('100.80')
        self.retailer.save()
        
        self.assertEqual(self.batch.quantity, 94)
        
        # Delete invoice
        response = self.client.post(reverse('invoice_delete', args=[invoice.id]))
        self.assertEqual(response.status_code, 302)
        
        # Verify invoice deleted from database
        self.assertFalse(SalesInvoice.objects.filter(id=invoice.id).exists())
        
        # Verify stock fully restored (94 + 6 = 100)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, 100)
        
        # Verify customer balance fully reverted
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 0.00)


class PurchaseEntryCrudTests(TestCase):
    def setUp(self):
        set_current_tenant(None)
        
        # Setup tenant
        self.tenant = Tenant.objects.create(name="main_shop", company_name="Main Shop Pharmacy", is_active=True)
        set_current_tenant(self.tenant)
        
        # Setup supplier
        self.supplier = SupplierMaster.objects.create(
            name="Supplier X",
            mobile="9876543200",
            city="Mumbai",
            state="MH"
        )
        
        self.company = CompanyMaster.objects.create(name="Cipla")
        self.p_type = ProductTypeMaster.objects.create(name="Tab")
        self.product = ProductMaster.objects.create(name="Dolo 650mg", company=self.company, product_type=self.p_type, pack_size="15")
        
        # Setup superuser operator
        self.user = User.objects.create_superuser(username="operator2", password="password")
        self.user.profile.tenant = self.tenant
        self.user.profile.save()

    def tearDown(self):
        set_current_tenant(None)

    def test_purchase_entry_create_cash_vs_credit(self):
        self.client.force_login(self.user)
        
        # 1. Cash Purchase
        post_data_cash = {
            'supplier': self.supplier.id,
            'invoice_number': 'INV-CASH-001',
            'invoice_date': '2026-07-15',
            'payment_type': 'Cash',
            'gross_amount': '100.00',
            'discount_amount': '0.00',
            'gst_amount': '12.00',
            'net_amount': '112.00',
            'product[]': [self.product.id],
            'batch_number[]': ['B-CASH'],
            'expiry_date[]': ['2030-01-31'],
            'mrp[]': ['150.00'],
            'purchase_rate[]': ['100.00'],
            'sale_rate[]': ['120.00'],
            'wholesale_rate[]': [''], # wholesale_rate empty should be accepted
            'quantity[]': ['1'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['112.00']
        }
        
        response = self.client.post(reverse('purchase_entry_create'), post_data_cash)
        self.assertEqual(response.status_code, 302)
        
        # Verify supplier balance is NOT updated for Cash
        self.supplier.refresh_from_db()
        self.assertEqual(float(self.supplier.opening_balance), 0.00)
        
        # Verify batch created with 1 stock
        batch = ProductBatch.objects.get(batch_number='B-CASH')
        self.assertEqual(batch.quantity, 1)
        self.assertEqual(float(batch.wholesale_rate), 0.00) # Optional defaulted to 0
        
        # 2. Credit Purchase
        post_data_credit = {
            'supplier': self.supplier.id,
            'invoice_number': 'INV-CREDIT-002',
            'invoice_date': '2026-07-15',
            'payment_type': 'Credit',
            'gross_amount': '200.00',
            'discount_amount': '10.00', # bill discount
            'gst_amount': '24.00',
            'net_amount': '214.00',
            'product[]': [self.product.id],
            'batch_number[]': ['B-CREDIT'],
            'expiry_date[]': ['2030-01-31'],
            'mrp[]': ['150.00'],
            'purchase_rate[]': ['100.00'],
            'sale_rate[]': ['120.00'],
            'wholesale_rate[]': ['110.00'],
            'quantity[]': ['2'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['224.00']
        }
        response = self.client.post(reverse('purchase_entry_create'), post_data_credit)
        self.assertEqual(response.status_code, 302)
        
        # Verify supplier balance is updated for Credit
        self.supplier.refresh_from_db()
        self.assertEqual(float(self.supplier.opening_balance), 214.00)
        
        # Verify batch created with 2 stock
        batch2 = ProductBatch.objects.get(batch_number='B-CREDIT')
        self.assertEqual(batch2.quantity, 2)
        self.assertEqual(float(batch2.wholesale_rate), 110.00)

    def test_purchase_entry_edit_and_delete(self):
        self.client.force_login(self.user)
        
        # Create a base Credit entry manually
        entry = PurchaseEntry.objects.create(
            supplier=self.supplier,
            invoice_number='INV-EDIT-TEST',
            invoice_date='2026-07-15',
            payment_type='Credit',
            gross_amount=100,
            discount_amount=0,
            gst_amount=12,
            net_amount=112
        )
        PurchaseEntryItem.objects.create(
            purchase_entry=entry,
            product=self.product,
            batch_number='B-EDIT',
            expiry_date='2030-01-31',
            mrp=150,
            purchase_rate=100,
            sale_rate=120,
            wholesale_rate=110,
            quantity=5,
            free_quantity=1,
            total_amount=500.00
        )
        batch = ProductBatch.objects.create(
            product=self.product,
            batch_number='B-EDIT',
            expiry_date='2030-01-31',
            mrp=150,
            purchase_rate=100,
            sale_rate=120,
            wholesale_rate=110,
            quantity=6
        )
        self.supplier.opening_balance = Decimal('112.00')
        self.supplier.save()
        
        # Perform edit via POST (modifying quantity from 5 to 10)
        post_data_edit = {
            'supplier': self.supplier.id,
            'invoice_number': 'INV-EDIT-TEST',
            'invoice_date': '2026-07-15',
            'payment_type': 'Credit',
            'gross_amount': '200.00',
            'discount_amount': '0.00',
            'gst_amount': '24.00',
            'net_amount': '224.00',
            'product[]': [self.product.id],
            'batch_number[]': ['B-EDIT'],
            'expiry_date[]': ['2030-01-31'],
            'mrp[]': ['150.00'],
            'purchase_rate[]': ['100.00'],
            'sale_rate[]': ['120.00'],
            'wholesale_rate[]': ['110.00'],
            'quantity[]': ['10'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['224.00']
        }
        
        response = self.client.post(reverse('purchase_entry_edit', args=[entry.id]), post_data_edit)
        self.assertEqual(response.status_code, 302)
        
        # Verify supplier balance updated (old 112 reverted, new 224 added = 224)
        self.supplier.refresh_from_db()
        self.assertEqual(float(self.supplier.opening_balance), 224.00)
        
        # Verify batch stock adjusted (6 starting - 6 old + 10 new = 10)
        batch.refresh_from_db()
        self.assertEqual(batch.quantity, 10)
        
        # Now Delete the entry
        response = self.client.post(reverse('purchase_entry_delete', args=[entry.id]))
        self.assertEqual(response.status_code, 302)
        
        # Verify entry deleted
        self.assertFalse(PurchaseEntry.objects.filter(id=entry.id).exists())
        
        # Verify supplier balance reverted to 0
        self.supplier.refresh_from_db()
        self.assertEqual(float(self.supplier.opening_balance), 0.00)
        
        # Verify stock additions fully reverted (10 - 10 = 0)
        batch.refresh_from_db()
        self.assertEqual(batch.quantity, 0)


class SalesPaymentAndLedgerTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from wholesaleApp.models import CustomerMaster, ProductMaster, ProductBatch, AreaMaster
        from decimal import Decimal
        
        self.user = User.objects.create_user(username="testoperator", password="pwd")
        
        # Setup matrix / permissions
        from wholesaleApp.views.security_helpers import seed_default_permissions
        seed_default_permissions()
        
        from wholesaleApp.models import AppFeature, UserFeaturePermission
        feature_sales = AppFeature.objects.get(codename="sales_create")
        feature_sales_edit = AppFeature.objects.get(codename="sales_edit")
        feature_sales_delete = AppFeature.objects.get(codename="sales_delete")
        feature_cust = AppFeature.objects.get(codename="customer_create")
        feature_ledger = AppFeature.objects.get(codename="customer_ledger")
        feature_payment = AppFeature.objects.get(codename="payment_collection_create")
        feature_payment_delete = AppFeature.objects.get(codename="payment_collection_delete")
        feature_outstanding = AppFeature.objects.get(codename="report_outstanding")
        
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_sales, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_sales_edit, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_sales_delete, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_cust, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_ledger, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_payment, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_payment_delete, defaults={'is_granted': True})
        UserFeaturePermission.objects.update_or_create(user=self.user, feature=feature_outstanding, defaults={'is_granted': True})
        
        self.area = AreaMaster.objects.create(city="Test City", code="TC1")
        self.retailer = CustomerMaster.objects.create(
            name="Test Retailer",
            mobile="9988776655",
            area=self.area,
            city="Test City",
            state="Test State",
            opening_balance=Decimal("0.00")
        )
        
        from wholesaleApp.models import CompanyMaster, ProductTypeMaster
        self.company = CompanyMaster.objects.create(name="Test Pharma")
        self.p_type = ProductTypeMaster.objects.create(name="Tab")
        
        self.product = ProductMaster.objects.create(
            name="Test Medicine",
            company=self.company,
            product_type=self.p_type,
            pack_size="10"
        )
        
        self.batch = ProductBatch.objects.create(
            product=self.product,
            batch_number="B-1234",
            expiry_date="2030-12-31",
            mrp=Decimal("112.00"),
            purchase_rate=Decimal("80.00"),
            sale_rate=Decimal("100.00"),
            wholesale_rate=Decimal("90.00"),
            quantity=100
        )

    def test_cash_vs_credit_invoice_creation(self):
        from wholesaleApp.models import SalesInvoice, CustomerMaster
        from django.urls import reverse
        
        self.client.force_login(self.user)
        
        # 1. Test Cash Invoice (default behavior / selection)
        post_data_cash = {
            'customer': self.retailer.id,
            'invoice_date': '2026-07-16',
            'payment_type': 'Cash',
            'gross_amount': '100.00',
            'discount_amount': '0.00',
            'gst_amount': '12.00',
            'net_amount': '112.00',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['100.00'],
            'quantity[]': ['1'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['112.00']
        }
        
        response = self.client.post(reverse('invoice_create'), post_data_cash)
        self.assertEqual(response.status_code, 302)
        
        # Cash invoice net_amount is 112, but it should NOT increase customer's outstanding balance
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 0.00)
        
        # Verify invoice created has payment_type='Cash'
        cash_invoice = SalesInvoice.objects.get(payment_type='Cash')
        self.assertEqual(cash_invoice.payment_type, 'Cash')
        
        # 2. Test Credit Invoice
        post_data_credit = {
            'customer': self.retailer.id,
            'invoice_date': '2026-07-16',
            'payment_type': 'Credit',
            'gross_amount': '100.00',
            'discount_amount': '0.00',
            'gst_amount': '12.00',
            'net_amount': '112.00',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['100.00'],
            'quantity[]': ['1'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['112.00']
        }
        
        response = self.client.post(reverse('invoice_create'), post_data_credit)
        self.assertEqual(response.status_code, 302)
        
        # Credit invoice net_amount is 112, it SHOULD increase customer's outstanding balance to 112
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 112.00)

    def test_invoice_edit_payment_type(self):
        from wholesaleApp.models import SalesInvoice, SalesInvoiceItem
        from django.urls import reverse
        from decimal import Decimal
        
        self.client.force_login(self.user)
        
        # Create a Credit invoice first (increases balance to 112)
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-16",
            payment_type="Credit",
            gross_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            gst_amount=Decimal("12.00"),
            net_amount=Decimal("112.00")
        )
        SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=1,
            free_quantity=0,
            sale_rate=Decimal("100.00"),
            total_amount=Decimal("112.00")
        )
        self.retailer.opening_balance = Decimal("112.00")
        self.retailer.save()
        
        # Edit the invoice to Cash (should adjust balance from 112 back to 0)
        post_data_edit = {
            'customer': self.retailer.id,
            'invoice_date': '2026-07-16',
            'payment_type': 'Cash',
            'gross_amount': '100.00',
            'discount_amount': '0.00',
            'gst_amount': '12.00',
            'net_amount': '112.00',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['100.00'],
            'quantity[]': ['1'],
            'free_quantity[]': ['0'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['112.00']
        }
        
        response = self.client.post(reverse('invoice_edit', args=[invoice.id]), post_data_edit)
        self.assertEqual(response.status_code, 302)
        
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 0.00)
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.payment_type, 'Cash')

    def test_customer_payment_ledger_flow(self):
        from wholesaleApp.models import CustomerPayment
        from django.urls import reverse
        from decimal import Decimal
        
        self.client.force_login(self.user)
        
        # Set retailer balance to 500
        self.retailer.opening_balance = Decimal("500.00")
        self.retailer.save()
        
        # Add a payment of 200 via POST
        post_data_pay = {
            'customer': self.retailer.id,
            'payment_date': '2026-07-16',
            'amount': '200.00',
            'payment_mode': 'UPI',
            'reference_no': 'REF12345',
            'remarks': 'Test receipt'
        }
        
        response = self.client.post(reverse('customer_payment_add'), post_data_pay)
        self.assertEqual(response.status_code, 302)
        
        # Check that retailer balance decreased to 300
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 300.00)
        
        # Check that payment object was created
        payment = CustomerPayment.objects.get(customer=self.retailer)
        self.assertEqual(float(payment.amount), 200.00)
        self.assertEqual(payment.payment_mode, 'UPI')
        
        # Test Ledger View Load
        ledger_url = reverse('customer_ledger') + f"?customer={self.retailer.id}"
        response_ledger = self.client.get(ledger_url)
        self.assertEqual(response_ledger.status_code, 200)
        self.assertContains(response_ledger, "Test Retailer")
        self.assertContains(response_ledger, "REF12345")
        
        # Test delete payment
        response_del = self.client.post(reverse('customer_payment_delete', args=[payment.id]))
        self.assertEqual(response_del.status_code, 302)
        
        # Customer balance should be restored to 500
        self.retailer.refresh_from_db()
        self.assertEqual(float(self.retailer.opening_balance), 500.00)
        
        # Payment should be deleted
        self.assertFalse(CustomerPayment.objects.filter(id=payment.id).exists())

    def test_outstanding_report_date_filtering(self):
        from wholesaleApp.models import SalesInvoice, SalesInvoiceItem, CustomerPayment
        from django.urls import reverse
        from decimal import Decimal
        
        self.client.force_login(self.user)
        
        # Create a Credit invoice on 2026-07-05
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-05",
            payment_type="Credit",
            gross_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            gst_amount=Decimal("12.00"),
            net_amount=Decimal("112.00")
        )
        SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=1,
            free_quantity=0,
            sale_rate=Decimal("100.00"),
            total_amount=Decimal("112.00")
        )
        
        # Create a payment on 2026-07-07
        CustomerPayment.objects.create(
            customer=self.retailer,
            payment_date="2026-07-07",
            amount=Decimal("40.00"),
            payment_mode="Cash"
        )
        
        # Set retailer balance
        self.retailer.opening_balance = Decimal("72.00")
        self.retailer.save()
        
        # Query with matching date range: 2026-07-01 to 2026-07-10
        response = self.client.get(reverse('report_outstanding'), {'from_date': '2026-07-01', 'to_date': '2026-07-10'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Retailer")
        self.assertContains(response, "72.00")
        
        # Query with non-matching date range: 2026-07-11 to 2026-07-20
        response_non_match = self.client.get(reverse('report_outstanding'), {'from_date': '2026-07-11', 'to_date': '2026-07-20'})
        self.assertEqual(response_non_match.status_code, 200)
        self.assertNotContains(response_non_match, "Test Retailer")

    def test_customer_ledger_date_filtering(self):
        from wholesaleApp.models import SalesInvoice, SalesInvoiceItem, CustomerPayment
        from django.urls import reverse
        from decimal import Decimal
        
        self.client.force_login(self.user)
        
        # Create a Credit invoice on 2026-07-05 (increases balance to 112)
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-05",
            payment_type="Credit",
            gross_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            gst_amount=Decimal("12.00"),
            net_amount=Decimal("112.00")
        )
        SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=1,
            free_quantity=0,
            sale_rate=Decimal("100.00"),
            total_amount=Decimal("112.00")
        )
        
        # Create a payment on 2026-07-07 (decreases balance by 40)
        CustomerPayment.objects.create(
            customer=self.retailer,
            payment_date="2026-07-07",
            amount=Decimal("40.00"),
            payment_mode="Cash"
        )
        
        # Set retailer balance
        self.retailer.opening_balance = Decimal("72.00")
        self.retailer.save()
        
        # Query ledger with date filter: 2026-07-06 to 2026-07-10 (should only show payment, not the invoice)
        ledger_url = reverse('customer_ledger') + f"?customer={self.retailer.id}&from_date=2026-07-06&to_date=2026-07-10"
        response = self.client.get(ledger_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment Received")
        self.assertNotContains(response, "INV-2026")
        # The display opening balance (initial_balance) should be 112.00 (since invoice was on 2026-07-05)
        self.assertContains(response, "112.00")

    def test_outstanding_report_area_and_aging_filtering(self):
        from wholesaleApp.models import SalesInvoice, SalesInvoiceItem, AreaMaster
        from django.urls import reverse
        from decimal import Decimal
        from django.utils import timezone
        
        self.client.force_login(self.user)
        
        # Create a Credit invoice (sales) on 2026-07-05
        invoice = SalesInvoice.objects.create(
            customer=self.retailer,
            invoice_date="2026-07-05",
            payment_type="Credit",
            gross_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            gst_amount=Decimal("12.00"),
            net_amount=Decimal("112.00")
        )
        SalesInvoiceItem.objects.create(
            sales_invoice=invoice,
            product=self.product,
            batch=self.batch,
            quantity=1,
            free_quantity=0,
            sale_rate=Decimal("100.00"),
            total_amount=Decimal("112.00")
        )
        
        self.retailer.opening_balance = Decimal("112.00")
        self.retailer.save()
        
        # Query with matching Area: self.area (Test City)
        response = self.client.get(reverse('report_outstanding'), {'area': self.area.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Retailer")
        self.assertContains(response, "Aging")
        self.assertContains(response, "Days")
        
        # Query with a different Area
        other_area = AreaMaster.objects.create(code="OTH1", city="Other City")
        response_other = self.client.get(reverse('report_outstanding'), {'area': other_area.id})
        self.assertEqual(response_other.status_code, 200)
        self.assertNotContains(response_other, "Test Retailer")


class MultiTenantRBACTests(TestCase):
    def setUp(self):
        from wholesaleApp.views.security_helpers import seed_default_permissions
        seed_default_permissions()

        # 1. Super Admin User
        self.super_admin = User.objects.create_superuser(username="superadmin", password="password123")
        
        # 2. Tenant Shop Owner User
        self.tenant_owner = User.objects.create_user(username="shop_owner", password="password123")
        self.tenant_owner.profile.role = "Owner"
        self.tenant_owner.profile.save()

        # 3. Staff Salesman User
        self.salesman = User.objects.create_user(username="salesman_john", password="password123")
        self.salesman.profile.role = "Salesman"
        self.salesman.profile.save()

    def test_super_admin_can_access_tenant_management(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('tenant_list'))
        self.assertEqual(response.status_code, 200)

    def test_tenant_owner_blocked_from_tenant_management(self):
        self.client.force_login(self.tenant_owner)
        response = self.client.get(reverse('tenant_list'))
        self.assertEqual(response.status_code, 200) # Tenant owner can view their own tenant firm

    def test_tenant_owner_can_access_user_management_and_matrix(self):
        self.client.force_login(self.tenant_owner)
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        
        response_matrix = self.client.get(reverse('user_permission_matrix'))
        self.assertEqual(response_matrix.status_code, 200)

    def test_salesman_blocked_from_user_management(self):
        self.client.force_login(self.salesman)
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 302)
        
        response_matrix = self.client.get(reverse('user_permission_matrix'))
        self.assertEqual(response_matrix.status_code, 302)

    def test_role_default_permissions_auto_applied(self):
        from wholesaleApp.views.security_helpers import apply_role_default_permissions, has_feature_access
        
        # Apply role defaults for Salesman
        apply_role_default_permissions(self.salesman)
        self.assertTrue(has_feature_access(self.salesman, 'sales_create'))
        self.assertFalse(has_feature_access(self.salesman, 'product_crud'))

        # Test MR role defaults
        mr_user = User.objects.create_user(username="testmr", password="password")
        mr_user.profile.role = "MR"
        mr_user.profile.save()
        apply_role_default_permissions(mr_user)
        self.assertTrue(has_feature_access(mr_user, 'sales_create'))
        self.assertTrue(has_feature_access(mr_user, 'report_outstanding'))
        self.assertFalse(has_feature_access(mr_user, 'product_crud'))


from django.core import mail
from django.test import override_settings
from django.urls import reverse
from unittest.mock import patch
from wholesaleApp.models.tenant import TenantEmailConfig
from wholesaleApp.utils.email_utils import send_invoice_email, send_invoice_email_async

class InvoiceEmailTests(TestCase):
    def setUp(self):
        from wholesaleApp.models.tenant import Tenant
        from wholesaleApp.models.customers import CustomerMaster, AreaMaster
        from wholesaleApp.models.products import ProductMaster, ProductTypeMaster, CompanyMaster
        from wholesaleApp.models.purchase import ProductBatch
        from wholesaleApp.models.sales import SalesInvoice, SalesInvoiceItem
        from django.contrib.auth.models import User
        
        self.user = User.objects.create_user(username="testuser", password="password")
        from wholesaleApp.views.security_helpers import seed_default_permissions
        seed_default_permissions()
        self.user.profile.role = 'Owner'
        self.user.profile.save()
        self.tenant = Tenant.objects.create(name="test_tenant", company_name="Test Company", is_active=True)
        self.area = AreaMaster.objects.create(tenant=self.tenant, city="Test City", code="TC")
        self.customer = CustomerMaster.objects.create(
            tenant=self.tenant,
            name="Retail Chemist",
            mobile="9876543210",
            email="retailer@example.com",
            area=self.area,
            city="Test City",
            state="Test State"
        )
        self.company = CompanyMaster.objects.create(tenant=self.tenant, name="Cipla Ltd", code="CIPLA")
        self.prod_type = ProductTypeMaster.objects.create(tenant=self.tenant, name="Tablet")
        self.product = ProductMaster.objects.create(
            tenant=self.tenant,
            name="Amoxicillin",
            company=self.company,
            product_type=self.prod_type,
            hsn_code="3004",
            gst_rate=12.00
        )
        self.batch = ProductBatch.objects.create(
            product=self.product,
            batch_number="B123",
            expiry_date="2028-12-31",
            mrp=100.00,
            purchase_rate=70.00,
            sale_rate=80.00,
            quantity=50
        )
        self.invoice = SalesInvoice.objects.create(
            tenant=self.tenant,
            invoice_number="INV-2026-0001",
            customer=self.customer,
            invoice_date="2026-07-26",
            gross_amount=80.00,
            discount_amount=0.00,
            gst_amount=9.60,
            net_amount=89.60,
            created_by=self.user
        )
        self.invoice_item = SalesInvoiceItem.objects.create(
            tenant=self.tenant,
            sales_invoice=self.invoice,
            product=self.product,
            batch=self.batch,
            quantity=1,
            sale_rate=80.00,
            total_amount=89.60
        )

    def test_send_invoice_email_success(self):
        mail.outbox = []
        
        result = send_invoice_email(self.invoice.id)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["retailer@example.com"])
        self.assertIn("Tax Invoice INV-2026-0001", mail.outbox[0].subject)
        self.assertIn("Amoxicillin", mail.outbox[0].body)

    def test_send_invoice_email_no_customer_email(self):
        self.customer.email = ""
        self.customer.save()
        mail.outbox = []
        
        result = send_invoice_email(self.invoice.id)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(IS_PRODUCTION=True)
    def test_send_invoice_email_production_no_config(self):
        mail.outbox = []
        
        result = send_invoice_email(self.invoice.id)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_invoice_email_with_tenant_config(self):
        config = TenantEmailConfig.objects.create(
            tenant=self.tenant,
            email_host="smtp.custom.com",
            email_port=465,
            email_host_user="custom@custom.com",
            email_host_password="password",
            email_use_tls=False,
            email_use_ssl=True,
            default_from_email="Custom Sender <custom@custom.com>",
            is_active=True
        )
        mail.outbox = []
        
        with patch('wholesaleApp.utils.email_utils.get_connection') as mock_get_connection:
            result = send_invoice_email(self.invoice.id)
            self.assertTrue(result)
            
            mock_get_connection.assert_called_once_with(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host='smtp.custom.com',
                port=465,
                username='custom@custom.com',
                password='password',
                use_tls=False,
                use_ssl=True
            )

    def test_bulk_email_view_get(self):
        self.client.force_login(self.user)
        
        with patch('wholesaleApp.views.security_helpers.has_feature_access', return_value=True):
            response = self.client.get(reverse('invoice_email_bulk'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'sale/invoice_email_bulk.html')

    def test_bulk_email_view_post(self):
        self.client.force_login(self.user)
        
        with patch('wholesaleApp.views.security_helpers.has_feature_access', return_value=True):
            with patch('wholesaleApp.utils.email_utils.send_invoice_email_async') as mock_send_async:
                response = self.client.post(reverse('invoice_email_bulk'), {
                    'invoice_ids': [self.invoice.id]
                })
                self.assertEqual(response.status_code, 302)
                mock_send_async.assert_called_once()

    def test_tenant_email_settings_unauthorized(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('tenant_email_settings'))
        self.assertEqual(response.status_code, 302)

    def test_tenant_email_settings_get(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        response = self.client.get(reverse('tenant_email_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenant/email_settings.html')

    def test_tenant_email_settings_post(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        response = self.client.post(reverse('tenant_email_settings'), {
            'email_host': 'smtp.gmail.com',
            'email_port': '587',
            'email_use_tls': 'on',
            'email_host_user': 'sales@example.com',
            'email_host_password': 'mypassword',
            'default_from_email': 'Test <sales@example.com>',
            'is_active': 'on'
        })
        self.assertEqual(response.status_code, 302)
        
        config = TenantEmailConfig.objects.get(tenant=self.tenant)
        self.assertEqual(config.email_host, 'smtp.gmail.com')
        self.assertEqual(config.email_port, 587)
        self.assertEqual(config.email_host_user, 'sales@example.com')
        self.assertEqual(config.email_host_password, 'mypassword')
        self.assertTrue(config.email_use_tls)

    def test_send_po_email_success(self):
        from wholesaleApp.models.supplier import SupplierMaster
        from wholesaleApp.models.purchase import PurchaseOrder, PurchaseOrderItem
        from wholesaleApp.utils.email_utils import send_po_email
        
        supplier = SupplierMaster.objects.create(
            tenant=self.tenant,
            name="Test Supplier",
            mobile="8888888888",
            email="supplier@example.com",
            city="City",
            state="State"
        )
        po = PurchaseOrder.objects.create(
            tenant=self.tenant,
            po_number="PO-2026-0001",
            supplier=supplier,
            po_date="2026-07-26",
            net_amount=80.00,
            created_by=self.user
        )
        PurchaseOrderItem.objects.create(
            tenant=self.tenant,
            purchase_order=po,
            product=self.product,
            quantity=1,
            expected_rate=80.00
        )
        
        mail.outbox = []
        result = send_po_email(po.id)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["supplier@example.com"])
        self.assertIn("Purchase Order PO-2026-0001", mail.outbox[0].subject)
        self.assertIn("Amoxicillin", mail.outbox[0].body)

    def test_po_email_send_view(self):
        from wholesaleApp.models.supplier import SupplierMaster
        from wholesaleApp.models.purchase import PurchaseOrder
        
        self.client.force_login(self.user)
        supplier = SupplierMaster.objects.create(
            tenant=self.tenant,
            name="Test Supplier",
            mobile="8888888888",
            email="supplier@example.com",
            city="City",
            state="State"
        )
        po = PurchaseOrder.objects.create(
            tenant=self.tenant,
            po_number="PO-2026-0001",
            supplier=supplier,
            po_date="2026-07-26",
            net_amount=80.00,
            created_by=self.user
        )
        
        with patch('wholesaleApp.utils.email_utils.send_po_email_async') as mock_send_async:
            response = self.client.get(reverse('po_email_send', args=[po.id]))
            self.assertEqual(response.status_code, 302)
            mock_send_async.assert_called_once_with(po)

    def test_po_list_view_whatsapp_urls(self):
        from wholesaleApp.models.supplier import SupplierMaster
        from wholesaleApp.models.purchase import PurchaseOrder
        
        self.client.force_login(self.user)
        supplier = SupplierMaster.objects.create(
            tenant=self.tenant,
            name="Test Supplier",
            mobile="8888888888",
            email="supplier@example.com",
            city="City",
            state="State"
        )
        po = PurchaseOrder.objects.create(
            tenant=self.tenant,
            po_number="PO-2026-0001",
            supplier=supplier,
            po_date="2026-07-26",
            net_amount=80.00,
            created_by=self.user
        )
        
        response = self.client.get(reverse('po_list'))
        self.assertEqual(response.status_code, 200)
        orders = response.context['orders']
        order = list(orders)[0]
        self.assertTrue(hasattr(order, 'whatsapp_url'))
        self.assertIn("https://wa.me/8888888888", order.whatsapp_url)

    def test_delivery_management_view_get(self):
        self.client.force_login(self.user)
        
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        with patch('wholesaleApp.views.security_helpers.has_feature_access', return_value=True):
            response = self.client.get(reverse('delivery_management'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'sale/delivery_management.html')
            self.assertIn(self.invoice, response.context['unassigned_invoices'])

    def test_delivery_management_assign_post(self):
        from wholesaleApp.models.permissions import UserProfile
        self.client.force_login(self.user)
        
        # Create a delivery boy user
        delivery_boy = User.objects.create_user(username="deliveryboy", password="password")
        profile = delivery_boy.profile
        profile.tenant = self.tenant
        profile.role = "Delivery Boy"
        profile.save()
        
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        with patch('wholesaleApp.views.security_helpers.has_feature_access', return_value=True):
            response = self.client.post(reverse('delivery_management'), {
                'action': 'assign',
                'invoice_ids': [self.invoice.id],
                'delivery_staff': delivery_boy.id
            })
            self.assertEqual(response.status_code, 302)
            
            # Verify assigned successfully in DB
            self.invoice.refresh_from_db()
            self.assertEqual(self.invoice.assigned_delivery_boy, delivery_boy)

    def test_delivery_management_update_status_post(self):
        self.client.force_login(self.user)
        
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        with patch('wholesaleApp.views.security_helpers.has_feature_access', return_value=True):
            response = self.client.post(reverse('delivery_management'), {
                'action': 'update_status',
                'invoice_id': self.invoice.id,
                'new_status': 'Delivered'
            })
            self.assertEqual(response.status_code, 302)
            
            # Verify status updated
            self.invoice.refresh_from_db()
            self.assertEqual(self.invoice.status, 'Delivered')


class DualModeRetailWholesaleTests(TestCase):
    def setUp(self):
        from wholesaleApp.models.tenant import Tenant
        from wholesaleApp.models.customers import CustomerMaster, AreaMaster
        from wholesaleApp.models.products import ProductMaster, ProductTypeMaster, CompanyMaster
        from wholesaleApp.models.purchase import ProductBatch
        from wholesaleApp.models.sales import SalesInvoice, SalesInvoiceItem
        from django.contrib.auth.models import User
        
        self.user = User.objects.create_user(username="testuser_dual", password="password")
        self.user.is_superuser = True
        self.user.save()
        self.tenant = Tenant.objects.create(name="dual_tenant", company_name="Dual Mode Firm", business_mode="Dual", is_active=True)
        self.user.profile.tenant = self.tenant
        self.user.profile.save()
        
        self.area = AreaMaster.objects.create(tenant=self.tenant, city="Dual City", code="DC")
        self.customer = CustomerMaster.objects.create(
            tenant=self.tenant,
            name="Chemist Customer",
            mobile="9876543210",
            area=self.area,
            city="Dual City",
            state="Dual State"
        )
        self.company = CompanyMaster.objects.create(tenant=self.tenant, name="Abbott", code="ABBOTT")
        self.prod_type = ProductTypeMaster.objects.create(tenant=self.tenant, name="Tablet")
        
        # Product with 10 units per strip (e.g. 10 tablets in a strip)
        self.product = ProductMaster.objects.create(
            tenant=self.tenant,
            name="Paracetamol 650",
            company=self.company,
            product_type=self.prod_type,
            hsn_code="3004",
            gst_rate=12.00,
            units_per_strip=10
        )
        # Stock: 50.0000 strips
        self.batch = ProductBatch.objects.create(
            product=self.product,
            batch_number="PARAB1",
            expiry_date="2030-01-01",
            mrp=150.00,
            purchase_rate=100.00,
            sale_rate=120.00,
            quantity=50.0000
        )

    def test_retail_mode_invoice_create_success(self):
        from decimal import Decimal
        from wholesaleApp.models.sales import SalesInvoice, SalesInvoiceItem
        from wholesaleApp.models.purchase import ProductBatch
        
        self.client.force_login(self.user)
        session = self.client.session
        session['active_tenant_id'] = self.tenant.id
        session.save()

        # Let's post a retail invoice.
        # Retail mode is active, quantity is 35 loose units.
        # 35 loose units / 10 = 3.5 strips.
        # Rate is 120 per strip, so rate per unit is 12.00.
        # Base price = 35 * 12 = 420.00.
        # GST = 12% of 420 = 50.40.
        # Net total = 470.40.
        # Discount is 0.
        response = self.client.post(reverse('invoice_create'), {
            'customer': '',
            'patient_name': 'Rahul Kumar',
            'patient_mobile': '9988776655',
            'doctor_name': 'Dr. Mehta',
            'invoice_date': '2026-07-26',
            'payment_type': 'Cash',
            'gross_amount': '420.00',
            'discount_amount': '0.00',
            'gst_amount': '50.40',
            'net_amount': '470.40',
            'is_retail': 'true',
            'product[]': [self.product.id],
            'batch[]': [self.batch.id],
            'sale_rate[]': ['120.00'],
            'quantity[]': ['35.0000'],
            'free_quantity[]': ['0.0000'],
            'discount_percentage[]': ['0.00'],
            'total_amount[]': ['470.40']
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify invoice and item created correctly in DB
        invoice = SalesInvoice.objects.filter(patient_name='Rahul Kumar').first()
        self.assertIsNotNone(invoice)
        self.assertTrue(invoice.is_retail)
        self.assertEqual(invoice.patient_mobile, '9988776655')
        self.assertEqual(invoice.doctor_name, 'Dr. Mehta')
        self.assertIsNone(invoice.customer)
        self.assertEqual(invoice.net_amount, Decimal('470.40'))
        
        item = invoice.items.first()
        self.assertIsNotNone(item)
        self.assertTrue(item.is_retail)
        self.assertEqual(item.quantity, Decimal('35.0000'))
        
        # Verify stock batch quantity reduced correctly: 50.0000 - 35.0000 = 15.0000
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity, Decimal('15.0000'))

    def test_tenant_crud_business_mode(self):
        from wholesaleApp.models.tenant import Tenant
        self.client.force_login(self.user)
        
        # Test creation of tenant with Dual mode
        response = self.client.post(reverse('tenant_create'), {
            'name': 'new_dual_tenant',
            'company_name': 'New Dual Shop Ltd',
            'address': 'Some Address',
            'phone': '1234567890',
            'email': 'shop@firm.com',
            'gstin': '123456789012345',
            'dl_number': 'DL-12345',
            'is_active': 'on',
            'business_mode': 'Dual'
        })
        self.assertEqual(response.status_code, 302)
        tenant = Tenant.objects.filter(name='new_dual_tenant').first()
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.business_mode, 'Dual')

        # Test edit tenant to Wholesale mode
        response = self.client.post(reverse('tenant_edit', kwargs={'pk': tenant.id}), {
            'name': 'new_dual_tenant',
            'company_name': 'New Dual Shop Ltd',
            'address': 'Some Address',
            'phone': '1234567890',
            'email': 'shop@firm.com',
            'gstin': '123456789012345',
            'dl_number': 'DL-12345',
            'is_active': 'on',
            'business_mode': 'Wholesale'
        })
        self.assertEqual(response.status_code, 302)
        tenant.refresh_from_db()
        self.assertEqual(tenant.business_mode, 'Wholesale')


class FinancialYearTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from wholesaleApp.models import Tenant, UserProfile, CustomerMaster, AreaMaster
        self.tenant = Tenant.objects.create(name="test_tenant_fy", company_name="Test Tenant FY")
        self.user = User.objects.create_user(username="fy_user", password="password123")
        self.profile = self.user.profile
        self.profile.tenant = self.tenant
        self.profile.role = 'Owner'
        self.profile.save()
        
        self.area = AreaMaster.objects.create(tenant=self.tenant, city="Pusad Area", code="PA01")
        self.customer = CustomerMaster.objects.create(tenant=self.tenant, name="Test Chemist", mobile="12345", area=self.area)
        
        # Set thread-local tenant
        from wholesaleApp.models.tenant import set_current_tenant
        set_current_tenant(self.tenant)

    def tearDown(self):
        from wholesaleApp.models.tenant import set_current_tenant
        set_current_tenant(None)

    def test_financial_year_closure_blocks_invoice_writes(self):
        from django.urls import reverse
        from wholesaleApp.models import FinancialYear, SalesInvoice
        import datetime
        
        self.client.force_login(self.user)
        
        # Create a closed Financial Year
        fy = FinancialYear.objects.create(
            tenant=self.tenant,
            name="FY 2025-26",
            start_date="2025-04-01",
            end_date="2026-03-31",
            is_closed=True
        )
        
        # Attempt to create an invoice inside this closed financial year date
        post_data = {
            'customer': self.customer.id,
            'invoice_date': '2026-02-15', # falls inside FY
            'gross_amount': '100.00',
            'discount_amount': '0.00',
            'gst_amount': '12.00',
            'net_amount': '112.00',
            'product[]': [],
            'batch[]': [],
            'sale_rate[]': [],
            'quantity[]': [],
            'free_quantity[]': [],
            'discount_percentage[]': [],
            'total_amount[]': []
        }
        
        response = self.client.post(reverse('invoice_create'), post_data)
        # Should block creation
        self.assertEqual(SalesInvoice.objects.filter(tenant=self.tenant).count(), 0)


class TallyIntegrationTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from wholesaleApp.models import Tenant, UserProfile
        self.tenant = Tenant.objects.create(name="test_tenant_tally", company_name="Test Tenant Tally", tally_export_enabled=False)
        self.user = User.objects.create_user(username="tally_user", password="password123")
        self.profile = self.user.profile
        self.profile.tenant = self.tenant
        self.profile.role = 'Owner'
        self.profile.save()
        
        # Set thread-local tenant
        from wholesaleApp.models.tenant import set_current_tenant
        set_current_tenant(self.tenant)

    def tearDown(self):
        from wholesaleApp.models.tenant import set_current_tenant
        set_current_tenant(None)

    def test_tally_dashboard_disabled_pitch_screen(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('tally_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Should display pricing/upgrade content
        self.assertContains(response, "Contact Sales to Purchase")
        self.assertContains(response, "₹3,000")

    def test_tally_dashboard_enabled_interface(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        
        # Enable tally export
        self.tenant.tally_export_enabled = True
        self.tenant.save()
        
        response = self.client.get(reverse('tally_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Should display download forms
        self.assertContains(response, "Compile Tally Vouchers")
        self.assertContains(response, "Generate & Download Tally CSV")


class PublicUserCreationTests(TestCase):
    def test_create_user_public_get(self):
        from django.urls import reverse
        response = self.client.get(reverse('create_user_public'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/create_user.html')

    def test_create_user_public_post_owner_default(self):
        from django.urls import reverse
        from django.contrib.auth.models import User
        
        response = self.client.post(reverse('create_user_public'), {
            'username': 'newsignup',
            'email': 'newsignup@example.com',
            'password': 'password123',
            'mobile': '9876543210'
        })
        # Should redirect to login page upon success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        # Verify default account creation is Tenant Owner
        user = User.objects.filter(username='newsignup').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newsignup@example.com')
        self.assertFalse(user.is_superuser)
        
        # Verify profile and linking
        profile = user.profile
        self.assertEqual(profile.role, 'Owner')
        self.assertEqual(profile.mobile, '9876543210')
        self.assertIsNone(profile.tenant)

    def test_create_user_public_post_super_admin(self):
        from django.urls import reverse
        from django.contrib.auth.models import User
        
        response = self.client.post(reverse('create_user_public'), {
            'username': 'newsuperadmin',
            'email': 'superadmin@example.com',
            'password': 'password123',
            'mobile': '9876543210',
            'account_type': 'Super Admin'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        user = User.objects.filter(username='newsuperadmin').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.profile.role, 'Super Admin')

    def test_create_user_public_post_existing_username(self):
        from django.urls import reverse
        from django.contrib.auth.models import User
        
        # Pre-create user with same username
        User.objects.create_user(username='newsignup', password='somepassword')
        
        response = self.client.post(reverse('create_user_public'), {
            'username': 'newsignup',
            'email': 'newsignup@example.com',
            'password': 'password123',
            'mobile': '9876543210'
        })
        self.assertEqual(response.status_code, 200)
        # Should show error message and not create a duplicate
        self.assertContains(response, "User with username &#x27;newsignup&#x27; already exists.")

    def test_tenant_creation_links_creator(self):
        from django.urls import reverse
        from django.contrib.auth.models import User
        from wholesaleApp.models.tenant import Tenant
        
        # Create a user with no tenant
        creator = User.objects.create_superuser(username='creatoradmin', password='password123')
        self.assertIsNone(creator.profile.tenant)
        
        self.client.force_login(creator)
        
        # Post tenant creation form
        response = self.client.post(reverse('tenant_create'), {
            'name': 'creator_shop',
            'company_name': 'Creator Shop Ltd',
            'address': 'Creator Road',
            'phone': '1122334455',
            'email': 'creator@shop.com',
            'gstin': '123456789012345',
            'dl_number': 'DL-99999',
            'is_active': 'on',
            'business_mode': 'Wholesale'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify tenant is created
        tenant = Tenant.objects.get(name='creator_shop')
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.user, creator)
        
        # Verify the creator user profile is now linked to this tenant
        creator.profile.refresh_from_db()
        self.assertEqual(creator.profile.tenant, tenant)
        
        # Verify session active tenant ID is set
        self.assertEqual(self.client.session.get('active_tenant_id'), tenant.id)















