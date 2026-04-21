from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Organization(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    
    def __str__(self):
        org_name = self.organization.name if self.organization else "No Org"
        return f"{self.user.username} ({org_name})"
class Client(models.Model):
    """Majitel zboží (pro tvých 30+ logistických klientů)"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='clients', null=True, blank=True)
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    """Univerzální skladová karta (SKU)"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
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

class ProductionDetails(models.Model):
    """Specifická data pro 3D tisk a Textil (80% focus)"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='production')
    color_name = models.CharField(max_length=50, blank=True)
    material_type = models.CharField(max_length=50, blank=True, help_text="PLA, PETG, Bavlna...")
    filament_length_m = models.FloatField(null=True, blank=True, help_text="Délka pro 3D tisk")


@receiver(post_save, sender=User)
def create_user_profile_and_assign_group(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
        
        # Automatické přiřazení do skupiny "Základní tarif"
        from django.contrib.auth.models import Group
        try:
            default_group, _ = Group.objects.get_or_create(name='Základní tarif')
            instance.groups.add(default_group)
        except Exception:
            pass # Prestoze by melo fungovat, jistota pro pripadne db kolize pri migraci

