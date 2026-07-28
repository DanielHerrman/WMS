"""
Tests for POD model — e-commerce import and production workflow.
"""
import json
from django.test import TestCase
from django.test import Client as TestClient
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import (
    Organization, Client, Product, ProductComponent,
    EcommerceStore, EcommerceOrder, OrderItem,
    ProductionStepTemplate, ProductionOrder, ProductionStep,
)
from core.services import (
    import_ecommerce_order, complete_step, complete_unit,
)


class EcommerceImportTests(TestCase):
    """Tests for import_ecommerce_order service."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.client = Client.objects.create(
            organization=self.org, name="Test Client"
        )
        self.user = User.objects.create_superuser("admin", "a@a.com", "pass")
        self.store = EcommerceStore.objects.create(
            organization=self.org,
            platform='woocommerce',
            name='Test Shop',
            slug='test-shop',
            base_url='https://test.shop',
            api_key='key',
            api_secret='secret',
        )

    def _wc_payload(self, order_id=123, line_items=None, **overrides):
        """Helper to build a WooCommerce-like webhook payload."""
        payload = {
            "id": order_id,
            "status": "processing",
            "currency": "CZK",
            "subtotal": "500.00",
            "shipping_total": "80.00",
            "total": "580.00",
            "payment_method_title": "Dobírka",
            "customer_note": "Test note",
            "billing": {
                "first_name": "Jan",
                "last_name": "Novák",
                "email": "jan@example.com",
                "phone": "123456789",
                "address_1": "Ulice 1",
                "city": "Praha",
                "postcode": "11000",
                "country": "CZ",
            },
            "shipping": {
                "first_name": "Jan",
                "last_name": "Novák",
                "address_1": "Ulice 1",
                "city": "Praha",
                "postcode": "11000",
                "country": "CZ",
            },
            "shipping_lines": [
                {"method_title": "Česká pošta"}
            ],
            "line_items": line_items or [],
        }
        payload.update(overrides)
        return payload

    # ----------------------------------------------------------
    # 1. Product without BOM (is_purchased=False) → 1 ProductionOrder
    # ----------------------------------------------------------
    def test_simple_product_creates_one_production_order(self):
        product = Product.objects.create(
            organization=self.org,
            client=self.client,
            sku='TEST-001',
            name='Test Product',
            is_purchased=False,
        )
        # Create a universal step template
        ProductionStepTemplate.objects.create(
            organization=self.org,
            name='Print',
            description='3D print the part',
            step_number=1,
            is_required=True,
        )

        payload = self._wc_payload(order_id=1, line_items=[{
            "id": 101,
            "sku": "TEST-001",
            "name": "Test Product",
            "quantity": 3,
            "price": "100.00",
            "subtotal": "300.00",
        }])

        order = import_ecommerce_order(self.store, payload)

        # Verify EcommerceOrder
        self.assertEqual(order.platform_order_id, 1)
        self.assertEqual(order.store, self.store)
        self.assertEqual(order.organization, self.org)
        self.assertEqual(order.client, self.client)

        # Verify 1 OrderItem
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.sku, 'TEST-001')
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.product, product)

        # Verify 1 ProductionOrder
        pos = ProductionOrder.objects.filter(ecommerce_order=order)
        self.assertEqual(pos.count(), 1)
        po = pos.first()
        self.assertEqual(po.product, product)
        self.assertEqual(po.quantity, 3)
        self.assertEqual(po.status, 'queued')
        self.assertEqual(po.organization, self.org)

        # Verify steps were generated
        self.assertEqual(po.steps.count(), 1)
        step = po.steps.first()
        self.assertEqual(step.name, 'Print')
        self.assertFalse(step.is_completed)

    # ----------------------------------------------------------
    # 2. Product with BOM → M ProductionOrders
    # ----------------------------------------------------------
    def test_bom_product_creates_multiple_production_orders(self):
        # Parent product (assembled)
        parent = Product.objects.create(
            organization=self.org, client=self.client,
            sku='ASSEMBLY', name='Assembled Product',
        )
        # Components
        comp_a = Product.objects.create(
            organization=self.org, client=self.client,
            sku='PART-A', name='Component A',
        )
        comp_b = Product.objects.create(
            organization=self.org, client=self.client,
            sku='PART-B', name='Component B',
        )
        # BOM: 2 × comp_a + 1 × comp_b per parent
        ProductComponent.objects.create(
            parent_product=parent, component=comp_a,
            quantity=2, is_manufactured=True,
        )
        ProductComponent.objects.create(
            parent_product=parent, component=comp_b,
            quantity=1, is_manufactured=True,
        )
        # Non-manufactured component (warehouse only)
        comp_packaging = Product.objects.create(
            organization=self.org, client=self.client,
            sku='BOX', name='Shipping Box',
            is_purchased=True,
        )
        ProductComponent.objects.create(
            parent_product=parent, component=comp_packaging,
            quantity=1, is_manufactured=False,
        )

        payload = self._wc_payload(order_id=2, line_items=[{
            "id": 201,
            "sku": "ASSEMBLY",
            "name": "Assembled Product",
            "quantity": 2,
            "price": "500.00",
            "subtotal": "1000.00",
        }])

        order = import_ecommerce_order(self.store, payload)

        # 2 ProductionOrders (only is_manufactured=True components)
        pos = ProductionOrder.objects.filter(ecommerce_order=order)
        self.assertEqual(pos.count(), 2)

        po_a = pos.get(product=comp_a)
        po_b = pos.get(product=comp_b)

        # comp_a: 2 × 2 = 4
        self.assertEqual(po_a.quantity, 4)
        self.assertEqual(po_b.quantity, 2)

    # ----------------------------------------------------------
    # 3. is_purchased=True → no ProductionOrder
    # ----------------------------------------------------------
    def test_purchased_product_creates_no_production_order(self):
        product = Product.objects.create(
            organization=self.org,
            client=self.client,
            sku='PURCHASED-001',
            name='Purchased Item',
            is_purchased=True,
        )

        payload = self._wc_payload(order_id=3, line_items=[{
            "id": 301,
            "sku": "PURCHASED-001",
            "name": "Purchased Item",
            "quantity": 5,
            "price": "50.00",
            "subtotal": "250.00",
        }])

        order = import_ecommerce_order(self.store, payload)

        # OrderItem exists
        self.assertEqual(order.items.count(), 1)

        # No ProductionOrders
        pos = ProductionOrder.objects.filter(ecommerce_order=order)
        self.assertEqual(pos.count(), 0)

    # ----------------------------------------------------------
    # 4. Unknown SKU → OrderItem created but no PO
    # ----------------------------------------------------------
    def test_unknown_sku_creates_order_item_no_po(self):
        payload = self._wc_payload(order_id=4, line_items=[{
            "id": 401,
            "sku": "UNKNOWN-SKU",
            "name": "Mystery Product",
            "quantity": 1,
            "price": "99.00",
            "subtotal": "99.00",
        }])

        order = import_ecommerce_order(self.store, payload)

        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertIsNone(item.product)

        pos = ProductionOrder.objects.filter(ecommerce_order=order)
        self.assertEqual(pos.count(), 0)

    # ----------------------------------------------------------
    # 5. Multiple line items → mixed behavior
    # ----------------------------------------------------------
    def test_multiple_line_items_mixed_behavior(self):
        product = Product.objects.create(
            organization=self.org, client=self.client,
            sku='SIMPLE', name='Simple Product',
        )
        purchased = Product.objects.create(
            organization=self.org, client=self.client,
            sku='PURCHASED', name='Purchased', is_purchased=True,
        )

        payload = self._wc_payload(order_id=5, line_items=[
            {"id": 501, "sku": "SIMPLE", "name": "Simple", "quantity": 2,
             "price": "100", "subtotal": "200"},
            {"id": 502, "sku": "PURCHASED", "name": "Purchased", "quantity": 3,
             "price": "50", "subtotal": "150"},
            {"id": 503, "sku": "UNKNOWN", "name": "Unknown", "quantity": 1,
             "price": "999", "subtotal": "999"},
        ])

        order = import_ecommerce_order(self.store, payload)
        self.assertEqual(order.items.count(), 3)

        # Only the simple product should have a PO
        pos = ProductionOrder.objects.filter(ecommerce_order=order)
        self.assertEqual(pos.count(), 1)
        self.assertEqual(pos.first().product, product)
        self.assertEqual(pos.first().quantity, 2)


class StepTemplatePriorityTests(TestCase):
    """Tests for ProductionStepTemplate priority logic."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.client = Client.objects.create(organization=self.org, name="C")
        self.store = EcommerceStore.objects.create(
            organization=self.org, platform='woocommerce',
            name='S', slug='s', base_url='https://s.com',
            api_key='k', api_secret='k',
        )
        self.product = Product.objects.create(
            organization=self.org, client=self.client,
            sku='P', name='Product P',
        )

    def test_template_priority_highest_specificity_wins(self):
        """Product+Material template overrides universal one with same step_number."""
        # Universal
        ProductionStepTemplate.objects.create(
            organization=self.org, name='Universal Step', step_number=1,
            is_required=True,
        )
        # Product-specific (higher priority)
        ProductionStepTemplate.objects.create(
            organization=self.org, name='Product Step', step_number=1,
            product=self.product, is_required=True,
        )

        # Create a component with BOM that references the product
        ProductComponent.objects.create(
            parent_product=self.product,
            component=self.product,
            quantity=1,
            is_manufactured=True,
        )

        payload = {
            "id": 999, "status": "p", "currency": "CZK",
            "total": "0", "subtotal": "0", "shipping_total": "0",
            "billing": {}, "shipping": {}, "shipping_lines": [],
            "line_items": [{
                "id": 1, "sku": "P", "name": "P",
                "quantity": 1, "price": "0", "subtotal": "0",
            }],
        }

        order = import_ecommerce_order(self.store, payload)
        po = ProductionOrder.objects.get(ecommerce_order=order)
        step = po.steps.first()
        # Product-specific template should win
        self.assertEqual(step.name, 'Product Step')
        self.assertEqual(po.steps.count(), 1)  # No duplicate step_number


class CompleteStepUnitTests(TestCase):
    """Tests for complete_step and complete_unit services."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.client = Client.objects.create(organization=self.org, name="C")
        self.user = User.objects.create_superuser("op", "op@x.com", "pass")
        self.product = Product.objects.create(
            organization=self.org, client=self.client,
            sku='X', name='X',
        )
        self.po = ProductionOrder.objects.create(
            organization=self.org, product=self.product,
            quantity=3, status='queued',
        )
        self.step = ProductionStep.objects.create(
            production_order=self.po, step_number=1,
            name='Test Step', is_required=True,
        )

    def test_complete_step(self):
        updated = complete_step(self.step.id, self.user)
        self.assertTrue(updated.is_completed)
        self.assertEqual(updated.completed_by, self.user)
        self.assertIsNotNone(updated.completed_at)

    def test_complete_unit_increments(self):
        po = complete_unit(self.po.id, self.user)
        self.assertEqual(po.quantity_completed, 1)
        self.assertEqual(po.status, 'queued')  # Not yet >= quantity

    def test_complete_unit_auto_qc(self):
        self.po.quantity_completed = 2
        self.po.save()
        po = complete_unit(self.po.id, self.user)
        self.assertEqual(po.quantity_completed, 3)
        self.assertEqual(po.status, 'qc')  # quantity_completed >= quantity


class WebhookEndpointTests(TestCase):
    """Integration tests for the webhook endpoint."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.client = Client.objects.create(organization=self.org, name="C")
        self.store = EcommerceStore.objects.create(
            organization=self.org, platform='woocommerce',
            name='S', slug='test-shop', base_url='https://s.com',
            api_key='k', api_secret='k',
        )
        self.product = Product.objects.create(
            organization=self.org, client=self.client,
            sku='HOOK', name='Hook Product',
        )

    def test_webhook_post_imports_order(self):
        c = TestClient()
        response = c.post(
            '/webhook/test-shop/',
            data=json.dumps({
                "id": 1001,
                "status": "processing",
                "currency": "CZK",
                "subtotal": "100",
                "shipping_total": "0",
                "total": "100",
                "billing": {},
                "shipping": {},
                "shipping_lines": [],
                "line_items": [{
                    "id": 1, "sku": "HOOK", "name": "H",
                    "quantity": 1, "price": "100", "subtotal": "100",
                }],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['platform_order_id'], 1001)

        # Verify DB objects
        self.assertTrue(EcommerceOrder.objects.filter(platform_order_id=1001).exists())
        order = EcommerceOrder.objects.get(platform_order_id=1001)
        self.assertEqual(order.store, self.store)
        self.assertTrue(ProductionOrder.objects.filter(ecommerce_order=order).exists())

    def test_webhook_get_returns_200(self):
        """GET is a health-check for WooCommerce delivery verification."""
        c = TestClient()
        response = c.get('/webhook/test-shop/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['store'], 'test-shop')

    def test_webhook_invalid_slug_returns_404(self):
        c = TestClient()
        response = c.post(
            '/webhook/nonexistent/',
            data=json.dumps({"id": 1}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_inactive_store_returns_404(self):
        self.store.is_active = False
        self.store.save()
        c = TestClient()
        response = c.post(
            '/webhook/test-shop/',
            data=json.dumps({"id": 1}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_invalid_json_returns_400(self):
        c = TestClient()
        response = c.post(
            '/webhook/test-shop/',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)