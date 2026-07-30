import uuid
import logging
from datetime import date
from decimal import Decimal

from django.db import models
from core.models import Organization

logger = logging.getLogger(__name__)


class Printer(models.Model):
    """3D printer model."""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='printers',
        verbose_name="Organization"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Printer Name (e.g. Bambu P1S)"
    )
    amortization_rate_per_hour = models.FloatField(
        verbose_name="Machine Amortization (CZK/h)",
        default=25.0
    )

    def __str__(self):
        return f"{self.name} ({self.amortization_rate_per_hour} CZK/h)"

    class Meta:
        verbose_name = "Printer"
        verbose_name_plural = "Printer Fleet"


class MaterialType(models.Model):
    """Material type definition with recommended settings."""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='material_types',
        verbose_name="Organization"
    )
    name = models.CharField(max_length=50, verbose_name="Material Name")
    description = models.TextField(blank=True, verbose_name="Description")
    recommended_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Recommended Settings",
        help_text="JSON: nozzle_temp, bed_temp, speed, cooling, etc."
    )
    default_error_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        verbose_name="Default Error Margin (%)",
        help_text="Default waste/spillage percentage for new spools"
    )
    default_drying_interval_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Default Drying Interval (days)",
        help_text="For future automatic drying reminders"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Material Type"
        verbose_name_plural = "Material Types"
        ordering = ['name']


class FilamentBrand(models.Model):
    """Brand + batch specification shared across all spools of the same type and size."""
    SPOOL_SIZE_CHOICES = [
        (0.5, '0.5 kg'),
        (1.0, '1.0 kg'),
        (2.5, '2.5 kg'),
        (5.0, '5.0 kg'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='filament_brands',
        verbose_name="Organization"
    )
    name = models.CharField(max_length=100, verbose_name="Brand Name")
    material_type = models.ForeignKey(
        MaterialType,
        on_delete=models.PROTECT,
        related_name='brands',
        verbose_name="Material Type"
    )
    spool_size_kg = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=SPOOL_SIZE_CHOICES,
        verbose_name="Spool Size (kg)"
    )
    ean = models.CharField(
        max_length=13,
        unique=True,
        null=True,
        blank=True,
        verbose_name="EAN Code"
    )
    photo = models.URLField(
        null=True,
        blank=True,
        verbose_name="Photo URL"
    )
    test_filament = models.OneToOneField(
        'Filament',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brand_test_for',
        verbose_name="Test Filament",
        help_text="Reference to a tested spool of this brand"
    )
    test_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Test Notes",
        help_text="Temperature tower, print settings, results"
    )
    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        verbose_name="Price per kg (CZK)"
    )
    color_hex = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        verbose_name="Color (HEX)",
        help_text="e.g. #FF5733"
    )
    spool_weight_g = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Empty Spool Weight (g)",
        help_text="Weight of the empty spool — measured once, valid for all spools of this brand"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Deactivate to archive obsolete brands"
    )

    def __str__(self):
        return f"{self.name} — {self.material_type} ({self.spool_size_kg} kg)"

    class Meta:
        verbose_name = "Filament Brand"
        verbose_name_plural = "Filament Brands"
        ordering = ['name', 'material_type__name']


class Filament(models.Model):
    """Individual filament spool."""
    STATUS_CHOICES = [
        ('ordered', 'Ordered'),
        ('stocked', 'Stocked'),
        ('reserved', 'Reserved'),
        ('in_use', 'In Use'),
        ('consumed', 'Consumed'),
        ('discarded', 'Discarded'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='filaments',
        verbose_name="Organization"
    )
    brand = models.ForeignKey(
        FilamentBrand,
        on_delete=models.PROTECT,
        related_name='filaments',
        verbose_name="Brand"
    )
    price_per_kg_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Price per kg Override (CZK)",
        help_text="Leave blank to use brand price"
    )
    error_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        verbose_name="Error Margin (%)",
        help_text="Waste/spillage percentage"
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="SKU",
        help_text="Auto-generated if left blank"
    )
    sku_position = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="SKU Position",
        help_text='e.g. "R3-P2", manually assigned shelf position'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ordered',
        verbose_name="Status"
    )
    spool_size_kg = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Spool Size (kg)",
        help_text="Pre-filled from brand"
    )
    initial_net_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Initial Net Weight (g)",
        help_text="Net filament weight upon receipt"
    )
    current_net_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Current Net Weight (g)",
        help_text="Auto-deducted from UsageLog on confirmed orders"
    )
    date_ordered = models.DateField(
        default=date.today,
        verbose_name="Date Ordered"
    )
    date_stocked = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date Stocked"
    )
    vacuum_sealed = models.BooleanField(
        default=False,
        verbose_name="Vacuum Sealed"
    )
    date_opened = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date Opened"
    )
    last_dried = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Dried"
    )
    next_drying = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Next Drying (Reminder)"
    )
    diameter_checked = models.BooleanField(
        default=False,
        verbose_name="Diameter Checked"
    )
    diameter_check_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Diameter Check Date"
    )
    diameter_result = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Diameter Result",
        help_text='e.g. "1.74 ±0.03"'
    )
    rewound = models.BooleanField(
        default=False,
        verbose_name="Rewound"
    )
    rewound_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Rewound Date"
    )
    qr_code = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        verbose_name="QR Code",
        help_text="Auto-generated unique hash/ID"
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    @property
    def price_per_kg(self):
        """Effective price — override or brand default."""
        if self.price_per_kg_override is not None:
            return self.price_per_kg_override
        if self.brand_id:
            return self.brand.price_per_kg
        return Decimal('500.00')

    def _generate_sku(self):
        """Generate unique short SKU like PLA-2507-A3."""
        import string
        import random
        today_str = date.today().strftime('%y%m')
        mat_prefix = self.brand.material_type.name[:3].upper() if self.brand_id else 'FIL'
        while True:
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
            candidate = f"{mat_prefix}-{today_str}-{suffix}"
            if not Filament.objects.filter(sku=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        # Auto-generate SKU on creation if not provided
        if not self.sku:
            self.sku = self._generate_sku()

        # Auto-generate QR code on creation
        if self.pk is None and not self.qr_code:
            self.qr_code = uuid.uuid4().hex

        # Pre-fill spool_size_kg from brand if not set
        if not self.spool_size_kg and self.brand_id:
            self.spool_size_kg = self.brand.spool_size_kg

        # Initialize current_net_weight_g from initial_net_weight_g on creation
        if self.pk is None and self.initial_net_weight_g is not None and self.current_net_weight_g is None:
            self.current_net_weight_g = self.initial_net_weight_g

        # Auto-fill weight when transitioning to stocked
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # After save: if status changed from ordered to non-ordered and no weight set, auto-fill
        if not is_new and self.status != 'ordered' and self.initial_net_weight_g is None:
            if self.brand_id:
                spool_kg = float(self.spool_size_kg or self.brand.spool_size_kg)
                spool_w = float(self.brand.spool_weight_g) if self.brand.spool_weight_g else 0
                estimated_net = max(0, spool_kg * 1000 - spool_w)
                self.initial_net_weight_g = estimated_net
                self.current_net_weight_g = estimated_net
                self.save(update_fields=['initial_net_weight_g', 'current_net_weight_g'])
        return

    def generate_qr_code(self):
        """Generate a unique QR code identifier. No-op if already set (auto-gen in save)."""
        if not self.qr_code:
            self.qr_code = uuid.uuid4().hex
            self.save(update_fields=['qr_code'])
        return self.qr_code

    def __str__(self):
        return f"[{self.sku}] {self.brand}"

    class Meta:
        verbose_name = "Filament"
        verbose_name_plural = "Filament Inventory"
        ordering = ['brand__name', 'sku']


class CustomOrder(models.Model):
    """Custom 3D print order with cost calculation."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('printing', 'In Production'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    DELIVERY_CHOICES = [
        ('pickup', 'Personal Pickup'),
        ('shipping', 'Shipping/Courier'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='custom_orders',
        verbose_name="Organization"
    )
    project_name = models.CharField(max_length=255, verbose_name="Project Name")
    products_count = models.PositiveIntegerField(default=1, verbose_name="Products Count (Yield)")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Order Status"
    )

    # Printer and print settings
    printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Printer"
    )
    plates_count = models.PositiveIntegerField(default=1, verbose_name="Plates Count (Changes)")
    print_time_minutes = models.PositiveIntegerField(
        verbose_name="Print Time (minutes)",
        default=60
    )

    # Material
    filament = models.ForeignKey(
        Filament,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Filament"
    )
    filament_weight_g = models.FloatField(verbose_name="Filament Weight (g) from slicer")

    # Labor
    modeling_minutes = models.PositiveIntegerField(default=0, verbose_name="Time - 3D Modeling (min)")
    modeling_hourly_rate = models.FloatField(default=600, verbose_name="Rate - 3D Modeling (CZK/h)")

    operation_minutes = models.PositiveIntegerField(default=5, verbose_name="Time - Printer Operation (min)")
    operation_hourly_rate = models.FloatField(default=300, verbose_name="Rate - Printer Operation (CZK/h)")

    postprocessing_minutes = models.PositiveIntegerField(default=0, verbose_name="Time - Postprocessing (min)")
    postprocessing_hourly_rate = models.FloatField(default=300, verbose_name="Rate - Postprocessing (CZK/h)")

    packaging_minutes = models.PositiveIntegerField(default=5, verbose_name="Time - Packaging (min)")
    packaging_hourly_rate = models.FloatField(default=250, verbose_name="Rate - Packaging (CZK/h)")

    # Logistics
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='shipping',
        verbose_name="Delivery Type"
    )
    shipping_cost = models.FloatField(default=100.0, verbose_name="Shipping & Packaging Cost (CZK)")

    # Calculated fields (stored for history)
    calculated_material_cost = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Total Material (CZK)"
    )
    calculated_amortization = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Total Amortization (CZK)"
    )
    calculated_labor_cost = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Total Labor (CZK)"
    )

    # Profit margins
    calculated_base_cost = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Base Cost (0%)"
    )
    calculated_price_100 = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Price +100% Margin"
    )
    calculated_price_200 = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Price +200% Margin"
    )
    calculated_price_350 = models.FloatField(
        editable=False,
        default=0,
        verbose_name="Price +350% Margin"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Track previous status for transition detection
        if self.pk:
            from django.db.models import F  # noqa: F811
            try:
                old_status = CustomOrder.objects.only('status').get(pk=self.pk).status
            except CustomOrder.DoesNotExist:
                old_status = None
        else:
            old_status = None

        # 1. Material cost
        self.calculated_material_cost = 0
        if self.filament:
            raw_material_cost = (float(self.filament.price_per_kg) / 1000.0) * self.filament_weight_g
            error_multiplier = 1.0 + (float(self.filament.error_margin) / 100.0)
            self.calculated_material_cost = raw_material_cost * error_multiplier

        # 2. Machine amortization
        self.calculated_amortization = 0
        if self.printer and self.printer.amortization_rate_per_hour:
            self.calculated_amortization = (
                self.print_time_minutes / 60.0
            ) * self.printer.amortization_rate_per_hour

        # 3. Labor
        modeling = (self.modeling_minutes / 60.0) * self.modeling_hourly_rate
        operation = (self.operation_minutes / 60.0) * self.operation_hourly_rate
        postprocessing = (self.postprocessing_minutes / 60.0) * self.postprocessing_hourly_rate
        packaging = (self.packaging_minutes / 60.0) * self.packaging_hourly_rate
        self.calculated_labor_cost = modeling + operation + postprocessing + packaging

        # 4. Base cost
        self.calculated_base_cost = (
            self.calculated_material_cost +
            self.calculated_amortization +
            self.calculated_labor_cost +
            self.shipping_cost
        )

        # 5. Margin prices
        self.calculated_price_100 = self.calculated_base_cost * 2.0
        self.calculated_price_200 = self.calculated_base_cost * 3.0
        self.calculated_price_350 = self.calculated_base_cost * 4.5

        super().save(*args, **kwargs)

        # Auto-create ProductionOrder when status transitions to 'confirmed'
        if old_status != 'confirmed' and self.status == 'confirmed':
            try:
                self._on_confirmed()
            except Exception as e:
                logger.error(
                    f"Failed to create ProductionOrder for order #{self.pk} "
                    f"({self.project_name}): {e}",
                    exc_info=True,
                )

        # Auto-create FilamentUsageLog + update filament when status transitions to 'printing'
        if old_status != 'printing' and self.status == 'printing':
            try:
                self._on_printing()
            except Exception as e:
                logger.error(
                    f"Failed to create FilamentUsageLog for order #{self.pk} "
                    f"({self.project_name}): {e}",
                    exc_info=True,
                )

    def _on_confirmed(self):
        """
        Handle status transition to 'confirmed':
        - Create a ProductionOrder linked to this B2B order
        - Clone steps from universal ProductionStepTemplate (product=None, material_type=None)

        Idempotent: if a ProductionOrder already exists for this CustomOrder, skip.
        """
        from core.models import ProductionOrder, Product, ProductionStepTemplate, ProductionStep

        # Idempotent check: skip if a ProductionOrder already linked to this B2B order
        if ProductionOrder.objects.filter(custom_order=self).exists():
            return

        # Find or create the shared B2B-CUSTOM product
        b2b_product, _ = Product.objects.get_or_create(
            sku='B2B-CUSTOM',
            defaults={
                'name': 'B2B Custom Manufacturing',
                'organization': self.organization,
                'client_id': 1,  # fallback — real client should be set later
                'is_purchased': False,
            }
        )

        # Create the ProductionOrder
        po = ProductionOrder.objects.create(
            organization=self.organization,
            product=b2b_product,
            quantity=self.products_count,
            status='queued',
            custom_order=self,
            assigned_printer=self.printer,
        )

        # Clone universal step templates (product=None, material_type=None)
        templates = ProductionStepTemplate.objects.filter(
            organization=self.organization,
            product__isnull=True,
            material_type__isnull=True,
        )

        for template in templates:
            ProductionStep.objects.create(
                production_order=po,
                step_number=template.step_number,
                name=template.name,
                description=template.description,
                media_url=template.media_url,
                is_required=template.is_required,
            )

    def _on_printing(self):
        """Handle status transition to 'printing':
        - Deduct filament weight via FilamentUsageLog
        - Set filament status to 'in_use'
        - Set filament sku_position to printer name

        Resilient: never fails on missing filament/brand data — uses defaults or skips.
        """
        if not self.filament or not self.filament_weight_g or self.filament_weight_g <= 0:
            return

        filament = self.filament
        weight_used = float(self.filament_weight_g)

        # ── 1. Create the usage log (always, regardless of weight tracking) ──
        try:
            FilamentUsageLog.objects.create(
                filament=filament,
                custom_order=self,
                grams_used=weight_used,
                notes=f"Auto-logged from printing order #{self.id}: {self.project_name}",
            )
        except Exception:
            logger.exception("FilamentUsageLog create failed — continuing")

        # ── 2. Try to deduct from current net weight (optional, best-effort) ──
        try:
            # Auto-fill weight from brand if missing
            if filament.current_net_weight_g is None:
                if filament.brand_id:
                    spool_kg = float(
                        filament.spool_size_kg
                        or getattr(filament.brand, 'spool_size_kg', None)
                        or 0
                    )
                    spool_w = float(
                        getattr(filament.brand, 'spool_weight_g', None) or 0
                    )
                    estimated = max(0, spool_kg * 1000 - spool_w)
                    filament.initial_net_weight_g = estimated
                    filament.current_net_weight_g = estimated
                else:
                    filament.current_net_weight_g = 0

            # Deduct
            filament.current_net_weight_g = max(
                0,
                float(filament.current_net_weight_g) - weight_used,
            )
            filament.status = 'in_use'
            if float(filament.current_net_weight_g) <= 0:
                filament.status = 'consumed'
                filament.current_net_weight_g = 0

            # Set sku_position to printer name
            if self.printer:
                filament.sku_position = self.printer.name

            filament.save(update_fields=['current_net_weight_g', 'status', 'sku_position'])
        except Exception:
            logger.exception("Filament weight deduction failed — log was created")

    def __str__(self):
        import math
        return f"{self.project_name} (Cost: {math.ceil(self.calculated_base_cost)} CZK)"

    class Meta:
        verbose_name = "B2B order"
        verbose_name_plural = "B2B orders"


class FilamentUsageLog(models.Model):
    """History of filament usage for confirmed orders."""
    filament = models.ForeignKey(
        Filament,
        on_delete=models.CASCADE,
        related_name='usage_logs',
        verbose_name="Filament"
    )
    custom_order = models.ForeignKey(
        CustomOrder,
        on_delete=models.CASCADE,
        related_name='filament_usage_logs',
        verbose_name="Custom Order"
    )
    grams_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Grams Used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Notes"
    )

    def __str__(self):
        return f"{self.filament.sku} — {self.grams_used}g (Order #{self.custom_order_id})"

    class Meta:
        verbose_name = "Filament Usage Log"
        verbose_name_plural = "Filament Usage Logs"
        ordering = ['-created_at']