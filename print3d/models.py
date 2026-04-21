from django.db import models
from core.models import Organization

class Printer(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='printers', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="Printer Name (e.g. Bambu P1S)")
    amortization_rate_per_hour = models.FloatField(verbose_name="Machine Amortization (CZK/h)", default=25.0)

    def __str__(self):
        return f"{self.name} ({self.amortization_rate_per_hour} CZK/h)"
    
    class Meta:
        verbose_name = "Printer"
        verbose_name_plural = "Printer Fleet"

class Filament(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='filaments', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="Filament Name & Color")
    type = models.CharField(max_length=50, default="PETG", verbose_name="Material Type")
    kg_price = models.FloatField(verbose_name="Price per kg (CZK)", default=500.0)
    error_margin_multiplier = models.FloatField(
        verbose_name="Error Margin Multiplier", 
        default=1.05,
        help_text="e.g. 1.05 = +5% waste"
    )

    def __str__(self):
        return f"{self.name} ({self.type} - {self.kg_price} CZK/kg)"

    class Meta:
        verbose_name = "Filament"
        verbose_name_plural = "Filament Inventory"

class CustomOrder(models.Model):
    """Záznam o výpočtu ceny 3D tisku v angličtině"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='custom_orders', null=True, blank=True)
    project_name = models.CharField(max_length=255, verbose_name="Project Name")
    products_count = models.PositiveIntegerField(default=1, verbose_name="Products Count (Yield)")
    
    # Stroj a tisk
    printer = models.ForeignKey(Printer, on_delete=models.SET_NULL, null=True, verbose_name="Printer")
    plates_count = models.PositiveIntegerField(default=1, verbose_name="Plates Count (Changes)")
    print_time_minutes = models.PositiveIntegerField(verbose_name="Print Time (minutes)", default=60)
    
    # Materiál
    filament = models.ForeignKey(Filament, on_delete=models.SET_NULL, null=True, verbose_name="Filament")
    filament_weight_g = models.FloatField(verbose_name="Filament Weight (g) from slicer")

    # Lidská práce (v minutách)
    modeling_minutes = models.PositiveIntegerField(default=0, verbose_name="Time - 3D Modeling (min)")
    modeling_hourly_rate = models.FloatField(default=600, verbose_name="Rate - 3D Modeling (CZK/h)")
    
    operation_minutes = models.PositiveIntegerField(default=5, verbose_name="Time - Printer Operation (min)")
    operation_hourly_rate = models.FloatField(default=300, verbose_name="Rate - Printer Operation (CZK/h)")
    
    postprocessing_minutes = models.PositiveIntegerField(default=0, verbose_name="Time - Postprocessing (min)")
    postprocessing_hourly_rate = models.FloatField(default=300, verbose_name="Rate - Postprocessing (CZK/h)")
    
    packaging_minutes = models.PositiveIntegerField(default=5, verbose_name="Time - Packaging (min)")
    packaging_hourly_rate = models.FloatField(default=250, verbose_name="Rate - Packaging (CZK/h)")

    # Logistika
    DELIVERY_CHOICES = [
        ('pickup', 'Personal Pickup'),
        ('shipping', 'Shipping/Courier'),
    ]
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='shipping', verbose_name="Delivery Type")
    shipping_cost = models.FloatField(default=100.0, verbose_name="Shipping & Packaging Cost (CZK)")

    # Počítaná pole (uložená fixně pro historii)
    calculated_material_cost = models.FloatField(editable=False, default=0, verbose_name="Total Material (CZK)")
    calculated_amortization = models.FloatField(editable=False, default=0, verbose_name="Total Amortization (CZK)")
    calculated_labor_cost = models.FloatField(editable=False, default=0, verbose_name="Total Labor (CZK)")
    
    # ZISKY A MARŽE
    calculated_base_cost = models.FloatField(editable=False, default=0, verbose_name="Base Cost (0%)")
    calculated_price_100 = models.FloatField(editable=False, default=0, verbose_name="Price +100% Margin")
    calculated_price_200 = models.FloatField(editable=False, default=0, verbose_name="Price +200% Margin")
    calculated_price_350 = models.FloatField(editable=False, default=0, verbose_name="Price +350% Margin")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 1. Materiál
        self.calculated_material_cost = 0
        if self.filament:
            raw_material_cost = (self.filament.kg_price / 1000.0) * self.filament_weight_g
            self.calculated_material_cost = raw_material_cost * self.filament.error_margin_multiplier
        
        # 2. Amortizace stroje
        self.calculated_amortization = 0
        if self.printer and self.printer.amortization_rate_per_hour:
            self.calculated_amortization = (self.print_time_minutes / 60.0) * self.printer.amortization_rate_per_hour
        
        # 3. Lidská práce (minuty / 60 * sazba)
        modeling = (self.modeling_minutes / 60.0) * self.modeling_hourly_rate
        operation = (self.operation_minutes / 60.0) * self.operation_hourly_rate
        postprocessing = (self.postprocessing_minutes / 60.0) * self.postprocessing_hourly_rate
        packaging = (self.packaging_minutes / 60.0) * self.packaging_hourly_rate
        self.calculated_labor_cost = modeling + operation + postprocessing + packaging
        
        # 4. Celkem - Čistý náklad
        self.calculated_base_cost = (
            self.calculated_material_cost + 
            self.calculated_amortization + 
            self.calculated_labor_cost + 
            self.shipping_cost
        )
        
        # 5. Marže (100% zisk = * 2)
        self.calculated_price_100 = self.calculated_base_cost * 2.0
        self.calculated_price_200 = self.calculated_base_cost * 3.0
        self.calculated_price_350 = self.calculated_base_cost * 4.5
        
        super().save(*args, **kwargs)

    def __str__(self):
        import math
        return f"{self.project_name} (Cost: {math.ceil(self.calculated_base_cost)} CZK)"
    
    class Meta:
        verbose_name = "Custom Order"
        verbose_name_plural = "Custom Orders"
