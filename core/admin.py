from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Client, Product, ProductionDetails

@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ('name', 'contact_email')

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('sku', 'name', 'client', 'weight_g', 'is_packaging')
    list_filter = ('client', 'is_packaging', 'is_3d_print_material')
    search_fields = ('sku', 'name')

@admin.register(ProductionDetails)
class ProductionDetailsAdmin(ModelAdmin):
    pass