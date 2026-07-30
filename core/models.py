from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    """
    Organization/Company model - top-level entity for multi-tenant data isolation.
    All core business objects belong to an organization.
    """
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


class UserProfile(models.Model):
    """Extends Django User with organization membership for multi-tenant isolation."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name="Organization"
    )

    def __str__(self):
        return f"{self.user.username} → {self.organization.name}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class Client(models.Model):
    """Majitel zboží (pro tvých 30+ logistických klientů)"""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='clients',
        verbose_name="Organization"
    )
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Product(models.Model):
    """Univerzální skladová karta (SKU)"""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Organization"
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    ean = models.CharField(max_length=13, blank=True, null=True)
    
    # Fyzické parametry (pro logistiku a roboty)
    weight_g = models.PositiveIntegerField(help_text="Hmotnost v gramech", default=0)
    width_mm = models.PositiveIntegerField(default=0)
    height_mm = models.PositiveIntegerField(default=0)
    depth_mm = models.PositiveIntegerField(default=0)
    
    # Modulární příznaky
    is_3d_print_material = models.BooleanField(default=False)
    is_textile = models.BooleanField(default=False)
    
    # Obalový materiál (BOM - tvůj příklad s knížkou)
    default_packaging = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'is_packaging': True}, related_name='used_as_packaging'
    )
    is_packaging = models.BooleanField(default=False, help_text="Je toto samo o sobě krabice/fólie?")
    is_purchased = models.BooleanField(
        default=False,
        help_text="Nakupovaný produkt — nevzniká výrobní zakázka, pouze skladová položka"
    )

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"


class EcommerceStore(models.Model):
    """Připojený e-shop (WooCommerce, Shopify, Shoptet...) s credentials."""
    PLATFORM_CHOICES = [
        ('woocommerce', 'WooCommerce'),
        ('shopify', 'Shopify'),
        ('shoptet', 'Shoptet'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='ecommerce_stores',
        verbose_name="Organization"
    )
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    name = models.CharField(max_length=255, help_text="Např. 'Hlavní eshop', 'B2B shop'")
    slug = models.SlugField(unique=True, help_text="Používá se v URL webhooku: /webhook/<slug>/")
    base_url = models.URLField(help_text="Např. https://shop.example.com")
    api_key = models.CharField(max_length=255, help_text="Consumer Key / API Key")
    api_secret = models.CharField(max_length=255, help_text="Consumer Secret / API Secret")
    webhook_secret = models.CharField(
        max_length=255, blank=True,
        help_text="Tajný klíč pro HMAC ověření webhooku (nepovinné)"
    )
    is_active = models.BooleanField(default=True)
    meta = models.JSONField(
        default=dict, blank=True,
        help_text="Platform-specific nastavení (např. shopify_store_name)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.name} ({self.slug})"

    class Meta:
        verbose_name = "E-commerce Store"
        verbose_name_plural = "E-commerce Stores"
        ordering = ['organization', 'platform', 'name']


class ProductComponent(models.Model):
    """
    Bill of Materials — definuje z jakých komponent se skládá produkt.
    Každá komponenta s is_manufactured=True automaticky generuje ProductionOrder.
    """
    parent_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='component_requirements'
    )
    component = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='used_as_component'
    )
    quantity = models.PositiveIntegerField(default=1, help_text="Kolik kusů komponenty na 1 hotový produkt")
    is_manufactured = models.BooleanField(
        default=True,
        help_text="True = vytvoří se ProductionOrder; False = jen vyskladnění ze skladu"
    )
    material_type = models.ForeignKey(
        'print3d.MaterialType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    filament_brand = models.ForeignKey(
        'print3d.FilamentBrand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    weight_grams = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hmotnost filamentu v gramech"
    )
    sku_position = models.CharField(
        max_length=100,
        blank=True,
        help_text="Pozice ve skladu (např. R3-P2)"
    )
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.parent_product.sku} ← [{self.quantity}x] {self.component.sku}"

    class Meta:
        verbose_name = "Product Component (BOM)"
        verbose_name_plural = "Product Components (BOM)"
        ordering = ['parent_product', 'sort_order']
        unique_together = [['parent_product', 'component']]


class EcommerceOrder(models.Model):
    """Importovaná objednávka z e-shopu (platform-agnostic)."""
    store = models.ForeignKey(
        EcommerceStore,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='ecommerce_orders',
        verbose_name="Organization"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecommerce_orders'
    )
    platform_order_id = models.BigIntegerField(help_text="ID objednávky v externím systému")
    status = models.CharField(max_length=100, blank=True)
    # Billing
    billing_first_name = models.CharField(max_length=255, blank=True)
    billing_last_name = models.CharField(max_length=255, blank=True)
    billing_email = models.EmailField(blank=True)
    billing_phone = models.CharField(max_length=50, blank=True)
    billing_address_1 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=255, blank=True)
    billing_postcode = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    # Shipping
    shipping_first_name = models.CharField(max_length=255, blank=True)
    shipping_last_name = models.CharField(max_length=255, blank=True)
    shipping_address_1 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=255, blank=True)
    shipping_postcode = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)
    shipping_method = models.CharField(max_length=255, blank=True)
    # Finance
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='CZK')
    # Meta
    payment_method = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    raw_data = models.JSONField(
        default=dict, blank=True,
        help_text="Kompletní payload z e-shopu"
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.platform_order_id} [{self.store.name}]"

    class Meta:
        verbose_name = "E-commerce Order"
        verbose_name_plural = "E-commerce Orders"
        ordering = ['-imported_at']
        unique_together = [['store', 'platform_order_id']]


class OrderItem(models.Model):
    """Položka importované objednávky."""
    ecommerce_order = models.ForeignKey(
        EcommerceOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    ecommerce_item_id = models.BigIntegerField(help_text="ID položky v externím systému")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        help_text="Produkt ve WMS (podle SKU)"
    )
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    raw_data = models.JSONField(
        default=dict, blank=True,
        help_text="Kompletní data položky z e-shopu"
    )

    def __str__(self):
        return f"[{self.sku}] {self.product_name} × {self.quantity}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        unique_together = [['ecommerce_order', 'ecommerce_item_id']]


class ProductionStepTemplate(models.Model):
    """Šablona kroků pro výrobní workflow."""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='step_templates',
        verbose_name="Organization"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    step_number = models.PositiveIntegerField()
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='step_templates',
        help_text="Specifické pro produkt (None = univerzální)"
    )
    material_type = models.ForeignKey(
        'print3d.MaterialType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Specifické pro typ materiálu (None = univerzální)"
    )
    media_url = models.URLField(blank=True, help_text="Obrázek nebo video instrukce")
    is_required = models.BooleanField(default=True)

    def __str__(self):
        scope = []
        if self.product:
            scope.append(self.product.sku)
        if self.material_type:
            scope.append(str(self.material_type))
        scope_str = " / ".join(scope) if scope else "univerzální"
        return f"#{self.step_number} {self.name} ({scope_str})"

    class Meta:
        verbose_name = "Production Step Template"
        verbose_name_plural = "Production Step Templates"
        ordering = ['step_number']


class ProductionOrder(models.Model):
    """Výrobní zakázka."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('qc', 'Quality Control'),
        ('packed', 'Packed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='production_orders',
        verbose_name="Organization"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='production_orders'
    )
    quantity = models.PositiveIntegerField()
    quantity_completed = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    # Vazby na zdroj
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_orders'
    )
    custom_order = models.ForeignKey(
        'print3d.CustomOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_orders'
    )
    ecommerce_order = models.ForeignKey(
        EcommerceOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_orders'
    )
    # Přiřazení
    assigned_printer = models.ForeignKey(
        'print3d.Printer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    assigned_operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )
    assigned_filament = models.ForeignKey(
        'print3d.Filament',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_orders',
        verbose_name="Assigned Filament"
    )
    qr_hash = models.CharField(max_length=50, unique=True, default='PO-')
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        import secrets
        if not self.qr_hash or self.qr_hash == 'PO-':
            self.qr_hash = 'PO-' + secrets.token_hex(12).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PO #{self.pk} — [{self.product.sku}] × {self.quantity}"

    class Meta:
        verbose_name = "Production Order"
        verbose_name_plural = "Production Orders"
        ordering = ['-created_at']


class ProductionStep(models.Model):
    """Konkrétní krok výrobní zakázky."""
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    step_number = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    is_required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_steps'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PO #{self.production_order_id} Step #{self.step_number}: {self.name}"

    class Meta:
        verbose_name = "Production Step"
        verbose_name_plural = "Production Steps"
        ordering = ['production_order', 'step_number']


class ProductionDetails(models.Model):
    """Specifická data pro 3D tisk a Textil (80% focus)"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='production')
    color_name = models.CharField(max_length=50, blank=True)
    material_type = models.CharField(max_length=50, blank=True, help_text="PLA, PETG, Bavlna...")
    filament_weight_g = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Hmotnost filamentu v gramech (min. 0 g)"
    )

    def __str__(self):
        if self.product_id:
            return f"{self.product.name} — {self.material_type or 'No material'}"
        return f"ProductionDetails #{self.pk}"

    class Meta:
        verbose_name_plural = "Production details"

