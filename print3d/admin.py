from django.contrib import admin
from unfold.admin import ModelAdmin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import get_object_or_404
import math
from .models import CustomOrder, Printer, Filament

@admin.register(Printer)
class PrinterAdmin(ModelAdmin):
    list_display = ('name', 'amortization_rate_per_hour')
    search_fields = ('name',)

@admin.register(Filament)
class FilamentAdmin(ModelAdmin):
    list_display = ('name', 'type', 'kg_price', 'error_margin_multiplier')
    list_filter = ('type',)
    search_fields = ('name',)

@admin.action(description="Export Selected Orders to TXT")
def export_estimation_to_txt(modeladmin, request, queryset):
    import io
    output = io.StringIO()
    for obj in queryset:
        output.write(f"--- Order: {obj.project_name} ---\n")
        output.write(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        printer_name = obj.printer.name if obj.printer else 'Unknown Printer'
        output.write(f"Printer: {printer_name} | Plates: {obj.plates_count} | Print Time: {obj.print_time_minutes} min\n")
        output.write(f"Yield: {obj.products_count} products\n")
        fil_name = obj.filament.name if obj.filament else 'Unknown Filament'
        output.write(f"Material [{fil_name}]: {obj.filament_weight_g}g => {obj.calculated_material_cost:.2f} CZK incl. waste\n")
        output.write(f"Machine Amortization: {obj.calculated_amortization:.2f} CZK\n")
        output.write(f"Labor: Modeling {obj.modeling_minutes}m, Operation {obj.operation_minutes}m, Postproc. {obj.postprocessing_minutes}m, Packaging {obj.packaging_minutes}m => Total {obj.calculated_labor_cost:.2f} CZK\n")
        output.write(f"Shipping: {obj.shipping_cost:.2f} CZK ({obj.get_delivery_type_display()})\n")
        output.write(f"=====================================\n")
        output.write(f"BASE COST: {math.ceil(obj.calculated_base_cost)} CZK ({math.ceil(obj.calculated_base_cost / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +100% Margin: {math.ceil(obj.calculated_price_100)} CZK ({math.ceil(obj.calculated_price_100 / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +200% Margin: {math.ceil(obj.calculated_price_200)} CZK ({math.ceil(obj.calculated_price_200 / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +350% Margin: {math.ceil(obj.calculated_price_350)} CZK ({math.ceil(obj.calculated_price_350 / obj.products_count)} CZK / pc)\n\n")
        
    response = HttpResponse(output.getvalue(), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="3d_print_orders.txt"'
    return response

@admin.register(CustomOrder)
class CustomOrderAdmin(ModelAdmin):
    list_display = ('project_name', 'printer', 'products_count', 'display_base_cost', 'display_price_100', 'display_price_200', 'display_price_350', 'created_at')
    list_filter = ('printer', 'filament', 'delivery_type')
    search_fields = ('project_name',)
    actions = [export_estimation_to_txt]
    
    readonly_fields = (
        'financial_summary_cards',
        'calculated_material_cost', 
        'calculated_amortization', 
        'calculated_labor_cost', 
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/export-txt/', self.admin_site.admin_view(self.export_single_txt), name='customorder_export_txt'),
        ]
        return custom_urls + urls

    def export_single_txt(self, request, object_id):
        obj = get_object_or_404(CustomOrder, pk=object_id)
        import io
        output = io.StringIO()
        output.write(f"--- Order: {obj.project_name} ---\n")
        output.write(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        printer_name = obj.printer.name if obj.printer else 'Unknown Printer'
        output.write(f"Printer: {printer_name} | Plates: {obj.plates_count} | Print Time: {obj.print_time_minutes} min\n")
        output.write(f"Yield: {obj.products_count} products\n")
        fil_name = obj.filament.name if obj.filament else 'Unknown Filament'
        output.write(f"Material [{fil_name}]: {obj.filament_weight_g}g => {obj.calculated_material_cost:.2f} CZK incl. waste\n")
        output.write(f"Machine Amortization: {obj.calculated_amortization:.2f} CZK\n")
        output.write(f"Labor: Modeling {obj.modeling_minutes}m, Operation {obj.operation_minutes}m, Postproc. {obj.postprocessing_minutes}m, Packaging {obj.packaging_minutes}m => Total {obj.calculated_labor_cost:.2f} CZK\n")
        output.write(f"Shipping: {obj.shipping_cost:.2f} CZK ({obj.get_delivery_type_display()})\n")
        output.write(f"=====================================\n")
        output.write(f"BASE COST: {math.ceil(obj.calculated_base_cost)} CZK ({math.ceil(obj.calculated_base_cost / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +100% Margin: {math.ceil(obj.calculated_price_100)} CZK ({math.ceil(obj.calculated_price_100 / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +200% Margin: {math.ceil(obj.calculated_price_200)} CZK ({math.ceil(obj.calculated_price_200 / obj.products_count)} CZK / pc)\n")
        output.write(f"Price +350% Margin: {math.ceil(obj.calculated_price_350)} CZK ({math.ceil(obj.calculated_price_350 / obj.products_count)} CZK / pc)\n\n")
        
        response = HttpResponse(output.getvalue(), content_type='text/plain; charset=utf-8')
        safe_name = "".join(c if c.isalnum() else "_" for c in obj.project_name)
        if not safe_name:
            safe_name = "kalkulace"
        response['Content-Disposition'] = f'attachment; filename="{safe_name}.txt"'
        return response

    @admin.display(description="Cost (0%)")
    def display_base_cost(self, obj):
        return f"{math.ceil(obj.calculated_base_cost)} CZK"
        
    @admin.display(description="+100% Margin")
    def display_price_100(self, obj):
        return f"{math.ceil(obj.calculated_price_100)} CZK"

    @admin.display(description="+200% Margin")
    def display_price_200(self, obj):
        return f"{math.ceil(obj.calculated_price_200)} CZK"

    @admin.display(description="+350% Margin")
    def display_price_350(self, obj):
        return f"{math.ceil(obj.calculated_price_350)} CZK"

    @admin.display(description="FINANCIAL SUMMARY")
    def financial_summary_cards(self, obj):
        if not obj.pk:
            return mark_safe("<div style='color: #6b7280; font-style: italic; padding: 1rem;'>Save the record to calculate margins.</div>")
        
        c_base = math.ceil(obj.calculated_base_cost)
        c_100 = math.ceil(obj.calculated_price_100)
        c_200 = math.ceil(obj.calculated_price_200)
        c_350 = math.ceil(obj.calculated_price_350)
        
        return mark_safe(f'''
        <div class="flex flex-row flex-wrap gap-4 w-full">
            <div class="flex-1 min-w-[200px] p-4 bg-gray-50 border border-gray-200 rounded-lg shadow-sm">
                <span class="text-xs font-semibold text-gray-500 uppercase">Base Cost (0%)</span>
                <div class="mt-1 text-2xl font-bold text-gray-900">{c_base} CZK</div>
                <div class="text-xs text-gray-500 mt-1">({math.ceil(c_base / obj.products_count)} CZK / pc)</div>
            </div>
            <div class="flex-1 min-w-[200px] p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm">
                <span class="text-xs font-semibold text-blue-600 uppercase">Price +100% Margin</span>
                <div class="mt-1 text-2xl font-bold text-blue-900">{c_100} CZK</div>
                <div class="text-xs text-blue-500 mt-1">({math.ceil(c_100 / obj.products_count)} CZK / pc)</div>
            </div>
            <div class="flex-1 min-w-[200px] p-4 bg-green-50 border border-green-200 rounded-lg shadow-sm">
                <span class="text-xs font-semibold text-green-600 uppercase">Price +200% Margin</span>
                <div class="mt-1 text-2xl font-bold text-green-900">{c_200} CZK</div>
                <div class="text-xs text-green-500 mt-1">({math.ceil(c_200 / obj.products_count)} CZK / pc)</div>
            </div>
            <div class="flex-1 min-w-[200px] p-4 bg-purple-50 border border-purple-200 rounded-lg shadow-sm">
                <span class="text-xs font-semibold text-purple-600 uppercase">Price +350% Margin</span>
                <div class="mt-1 text-2xl font-bold text-purple-900">{c_350} CZK</div>
                <div class="text-xs text-purple-500 mt-1">({math.ceil(c_350 / obj.products_count)} CZK / pc)</div>
            </div>
        </div>
        <div class="mt-4 mb-4">
            <a href="../export-txt/" style="display: inline-flex; align-items: center; background-color: #2563eb; color: #ffffff; padding: 0.6rem 1.2rem; border-radius: 0.375rem; text-decoration: none; font-size: 0.875rem; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <svg style="margin-right: 0.5rem; width: 1.25rem; height: 1.25rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                Print / Export TXT
            </a>
        </div>
        ''')

    fieldsets = (
        (None, {
            "fields": ("financial_summary_cards",)
        }),
        ("Basic Info", {
            "fields": ("project_name", "products_count", "printer")
        }),
        ("Material Consumption", {
            "fields": (
                "filament", 
                "filament_weight_g", 
                "calculated_material_cost"
            )
        }),
        ("Machine & Production", {
            "fields": (
                "plates_count", 
                "print_time_minutes", 
                "calculated_amortization"
            )
        }),
        ("Labor", {
            "fields": (
                ("modeling_minutes", "modeling_hourly_rate"),
                ("operation_minutes", "operation_hourly_rate"),
                ("postprocessing_minutes", "postprocessing_hourly_rate"),
                ("packaging_minutes", "packaging_hourly_rate"),
                "calculated_labor_cost"
            )
        }),
        ("Logistics & Final", {
            "fields": (
                "delivery_type", 
                "shipping_cost"
            )
        })
    )
