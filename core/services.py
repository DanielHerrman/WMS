"""
Core business services for e-commerce import and production workflow.
"""
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Product, EcommerceStore, EcommerceOrder, OrderItem,
    ProductComponent, ProductionStepTemplate,
    ProductionOrder, ProductionStep,
)


@transaction.atomic
def import_ecommerce_order(store: EcommerceStore, data: dict) -> EcommerceOrder:
    """
    Import e-commerce order and create ProductionOrders based on BOM logic.

    1. Creates EcommerceOrder + OrderItems
    2. For each OrderItem:
       a. Finds Product by SKU
       b. If product.is_purchased → skip (warehouse only)
       c. If product has BOM (ProductComponent):
          For each is_manufactured=True component:
            quantity = component.quantity × order_item.quantity
            Create ProductionOrder
       d. If product has no BOM and is_purchased=False:
          Create 1 ProductionOrder with quantity = order_item.quantity
    3. For each ProductionOrder, generate ProductionSteps from ProductionStepTemplate
       Priority: product-specific → material_type-specific → universal

    Args:
        store: EcommerceStore instance
        data: Raw webhook payload from the e-commerce platform (WooCommerce format expected)

    Returns:
        EcommerceOrder instance
    """
    # Determine platform_order_id from data
    platform_order_id = data.get('id')
    if not platform_order_id:
        raise ValueError("Missing order ID in webhook data")

    # Parse billing/shipping from WooCommerce-style payload
    billing = data.get('billing', {})
    shipping = data.get('shipping', {})
    shipping_lines = data.get('shipping_lines', [])
    shipping_method = shipping_lines[0].get('method_title', '') if shipping_lines else ''

    # Determine client from the first matching product
    client = None

    # Create EcommerceOrder
    order = EcommerceOrder.objects.create(
        store=store,
        organization=store.organization,
        platform_order_id=platform_order_id,
        status=data.get('status', ''),
        billing_first_name=billing.get('first_name', ''),
        billing_last_name=billing.get('last_name', ''),
        billing_email=billing.get('email', ''),
        billing_phone=billing.get('phone', ''),
        billing_address_1=billing.get('address_1', ''),
        billing_city=billing.get('city', ''),
        billing_postcode=billing.get('postcode', ''),
        billing_country=billing.get('country', ''),
        shipping_first_name=shipping.get('first_name', ''),
        shipping_last_name=shipping.get('last_name', ''),
        shipping_address_1=shipping.get('address_1', ''),
        shipping_city=shipping.get('city', ''),
        shipping_postcode=shipping.get('postcode', ''),
        shipping_country=shipping.get('country', ''),
        shipping_method=shipping_method,
        subtotal=data.get('subtotal', '0'),
        shipping_total=data.get('shipping_total', '0'),
        total=data.get('total', '0'),
        currency=data.get('currency', 'CZK'),
        payment_method=data.get('payment_method_title', ''),
        notes=data.get('customer_note', ''),
        raw_data=data,
    )

    # Create OrderItems and ProductionOrders
    line_items = data.get('line_items', [])
    for item_data in line_items:
        item_id = item_data.get('id')
        sku = item_data.get('sku', '')
        product_name = item_data.get('name', '')
        quantity = item_data.get('quantity', 1)
        unit_price = item_data.get('price', 0)
        subtotal = item_data.get('subtotal', 0)

        # Try to find product by SKU
        product = None
        if sku:
            try:
                product = Product.objects.get(sku=sku)
            except Product.DoesNotExist:
                product = None

        # Determine client from the first matched product
        if product and not client:
            client = product.client
            order.client = client
            order.save(update_fields=['client'])

        # Create OrderItem
        order_item = OrderItem.objects.create(
            ecommerce_order=order,
            ecommerce_item_id=item_id,
            product=product,
            product_name=product_name,
            sku=sku,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
            raw_data=item_data,
        )

        # --- Create ProductionOrders ---
        if not product:
            continue  # Skip items without matched product

        if product.is_purchased:
            continue  # Purchased items → no production, warehouse only

        # Check if product has BOM
        components = ProductComponent.objects.filter(
            parent_product=product,
            is_manufactured=True
        )

        if components.exists():
            # BOM-based: create ProductionOrder for each manufactured component
            for comp in components:
                po_quantity = comp.quantity * quantity
                po = ProductionOrder.objects.create(
                    organization=store.organization,
                    product=comp.component,
                    quantity=po_quantity,
                    order_item=order_item,
                    ecommerce_order=order,
                    status='queued',
                )
                _generate_steps(po, comp.component, comp.material_type)
        else:
            # No BOM → single ProductionOrder for the product itself
            po = ProductionOrder.objects.create(
                organization=store.organization,
                product=product,
                quantity=quantity,
                order_item=order_item,
                ecommerce_order=order,
                status='queued',
            )
            _generate_steps(po, product, None)

    return order


def _generate_steps(
    production_order: ProductionOrder,
    product: Product,
    material_type=None
):
    """
    Generate ProductionSteps for a ProductionOrder from ProductionStepTemplate.

    Priority:
    1. Templates matching both product AND material_type (highest specificity)
    2. Templates matching only product
    3. Templates matching only material_type
    4. Universal templates (product=None, material_type=None)

    If multiple templates match the same step_number, the most specific one wins.
    """
    from print3d.models import MaterialType as Print3dMaterialType

    # Collect templates in priority order
    templates_by_step = {}

    # 1. Universal templates first (lowest priority)
    universal = ProductionStepTemplate.objects.filter(
        organization=production_order.organization,
        product__isnull=True,
        material_type__isnull=True,
    )
    for t in universal:
        templates_by_step.setdefault(t.step_number, t)

    # 2. Material-type specific (overrides universal)
    if material_type:
        mt_templates = ProductionStepTemplate.objects.filter(
            organization=production_order.organization,
            product__isnull=True,
            material_type=material_type,
        )
        for t in mt_templates:
            templates_by_step[t.step_number] = t

    # 3. Product specific (overrides material-type)
    product_templates = ProductionStepTemplate.objects.filter(
        organization=production_order.organization,
        product=product,
        material_type__isnull=True,
    )
    for t in product_templates:
        templates_by_step[t.step_number] = t

    # 4. Both product AND material_type (highest priority)
    if material_type:
        both_templates = ProductionStepTemplate.objects.filter(
            organization=production_order.organization,
            product=product,
            material_type=material_type,
        )
        for t in both_templates:
            templates_by_step[t.step_number] = t  # Override all

    # Create steps from collected templates
    for step_number in sorted(templates_by_step):
        template = templates_by_step[step_number]
        ProductionStep.objects.create(
            production_order=production_order,
            step_number=template.step_number,
            name=template.name,
            description=template.description,
            media_url=template.media_url,
            is_required=template.is_required,
        )


def complete_step(step_id: int, user: User) -> ProductionStep:
    """
    Mark a ProductionStep as completed.

    If the step is the "3D tisk" step (name contains "3D" or step_number=2)
    and the parent ProductionOrder has an assigned filament linked to a B2B
    CustomOrder, a FilamentUsageLog is automatically created.

    Args:
        step_id: ProductionStep PK
        user: User completing the step

    Returns:
        Updated ProductionStep

    Raises:
        ProductionStep.DoesNotExist
    """
    from print3d.models import FilamentUsageLog

    step = ProductionStep.objects.select_related(
        'production_order__custom_order'
    ).get(pk=step_id)

    if step.is_completed:
        return step

    step.is_completed = True
    step.completed_by = user
    step.completed_at = timezone.now()
    step.save(update_fields=['is_completed', 'completed_by', 'completed_at'])

    # ── Auto-deduct filament if this is the "3D tisk" step ──
    is_print_step = (
        '3D' in step.name.upper() or step.step_number == 2
    )

    if is_print_step:
        try:
            po = step.production_order
            b2b = po.custom_order
            if (
                po.assigned_filament
                and b2b
                and b2b.filament_weight_g is not None
                and float(b2b.filament_weight_g) > 0
            ):
                FilamentUsageLog.objects.create(
                    filament=po.assigned_filament,
                    custom_order=b2b,
                    grams_used=float(b2b.filament_weight_g),
                    notes=(
                        f"Auto-deducted from ProductionOrder #{po.pk} "
                        f"step '{step.name}'"
                    ),
                )
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(
                "Failed to create FilamentUsageLog on step completion "
                "step_id=%s",
                step_id,
            )

    return step


@transaction.atomic
def complete_unit(production_order_id: int, user: User) -> ProductionOrder:
    """
    Increment quantity_completed on a ProductionOrder.
    When quantity_completed >= quantity, auto-transition status to 'qc'.

    Args:
        production_order_id: ProductionOrder PK
        user: User completing the unit

    Returns:
        Updated ProductionOrder

    Raises:
        ProductionOrder.DoesNotExist
    """
    po = ProductionOrder.objects.select_for_update().get(pk=production_order_id)
    po.quantity_completed += 1

    if po.quantity_completed >= po.quantity:
        po.status = 'qc'

    po.save(update_fields=['quantity_completed', 'status', 'updated_at'])
    return po