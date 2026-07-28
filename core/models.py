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

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"


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

