from django.contrib import admin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import get_object_or_404, redirect, render
from unfold.admin import ModelAdmin
import math

from core.admin import OrganizationAdminMixin
from .models import (
    Printer, MaterialType, FilamentBrand, Filament, CustomOrder, FilamentUsageLog
)


# ============================================================
# PRINTER
# ============================================================

@admin.register(Printer)
class PrinterAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'amortization_rate_per_hour')
    list_filter = ('organization',)
    search_fields = ('name',)


# ============================================================
# MATERIAL TYPE
# ============================================================

@admin.register(MaterialType)
class MaterialTypeAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'default_error_margin', 'default_drying_interval_days')
    list_filter = ('organization',)
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('organization',)
        }),
        ('Material Info', {
            'fields': ('name', 'description')
        }),
        ('Defaults', {
            'fields': ('default_error_margin', 'default_drying_interval_days')
        }),
        ('Recommended Settings (JSON)', {
            'fields': ('recommended_settings',),
            'description': 'Enter JSON object, e.g. {"nozzle_temp": 215, "bed_temp": 60, "speed": 80, "cooling": 100}'
        }),
    )


# ============================================================
# FILAMENT BRAND
# ============================================================

@admin.register(FilamentBrand)
class FilamentBrandAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'material_type', 'spool_size_kg', 'price_per_kg', 'color_hex_display', 'is_active')
    list_filter = ('organization', 'material_type', 'is_active', 'spool_size_kg')
    search_fields = ('name', 'ean')
    fieldsets = (
        (None, {
            'fields': ('organization',)
        }),
        ('Brand Info', {
            'fields': ('name', 'material_type', 'spool_size_kg', 'ean', 'photo')
        }),
        ('Pricing & Color', {
            'fields': ('price_per_kg', 'color_hex')
        }),
        ('Testing', {
            'fields': ('test_filament', 'test_notes')
        }),
        ('Spool Info', {
            'fields': ('spool_weight_g',),
            'description': 'Weight of the empty spool — measured once, applies to all spools of this brand.'
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    @admin.display(description="Color", ordering='color_hex')
    def color_hex_display(self, obj):
        if obj.color_hex:
            return mark_safe(
                f'<span style="display:inline-block;width:16px;height:16px;'
                f'background-color:{obj.color_hex};border:1px solid #ccc;'
                f'margin-right:6px;vertical-align:middle;"></span>'
                f'{obj.color_hex}'
            )
        return '-'


# ============================================================
# FILAMENT
# ============================================================

@admin.action(description="Generate QR codes for selected stocked spools")
def generate_qr_codes(modeladmin, request, queryset):
    stocked = queryset.filter(status='stocked')
    count = 0
    for filament in stocked:
        filament.generate_qr_code()
        count += 1
    skipped = queryset.count() - count
    msg = f"Generated QR codes for {count} spools."
    if skipped:
        msg += f" Skipped {skipped} (not in 'stocked' status)."
    modeladmin.message_user(request, msg)


@admin.action(description="Mark selected as Stocked")
def mark_as_stocked(modeladmin, request, queryset):
    updated = 0
    for filament in queryset:
        filament.status = 'stocked'
        filament.save()
        updated += 1
    modeladmin.message_user(request, f"{updated} spools marked as Stocked.")


@admin.action(description="Mark selected as Reserved")
def mark_as_reserved(modeladmin, request, queryset):
    updated = 0
    for filament in queryset:
        filament.status = 'reserved'
        filament.save()
        updated += 1
    modeladmin.message_user(request, f"{updated} spools marked as Reserved.")


@admin.action(description="Mark selected as In Use")
def mark_as_in_use(modeladmin, request, queryset):
    updated = 0
    for filament in queryset:
        filament.status = 'in_use'
        filament.save()
        updated += 1
    modeladmin.message_user(request, f"{updated} spools marked as In Use.")


@admin.action(description="Mark selected as Discarded")
def mark_as_discarded(modeladmin, request, queryset):
    updated = 0
    for filament in queryset:
        filament.status = 'discarded'
        filament.save()
        updated += 1
    modeladmin.message_user(request, f"{updated} spools marked as Discarded.")


@admin.register(Filament)
class FilamentAdmin(ModelAdmin):
    list_display = (
        'sku', 'brand', 'status_badge', 'brand_color_display',
        'weight_display', 'sku_position'
    )

    @admin.display(description="Status", ordering='status')
    def status_badge(self, obj):
        styles = {
            'ordered':   'background:#dbeafe;color:#1d4ed8;',
            'stocked':   'background:#dcfce7;color:#15803d;',
            'reserved':  'background:#fef3c7;color:#b45309;',
            'in_use':    'background:#f3e8ff;color:#7c3aed;',
            'consumed':  'background:#f3f4f6;color:#4b5563;',
            'discarded': 'background:#fee2e2;color:#b91c1c;',
        }
        s = styles.get(obj.status, 'background:#f3f4f6;color:#4b5563;')
        return mark_safe(
            f'<span style="display:inline-block;padding:2px 10px;border-radius:9999px;font-size:0.75rem;font-weight:500;{s}">'
            f'{obj.get_status_display()}'
            f'</span>'
        )
    list_filter = ('status', 'brand', 'brand__material_type', 'organization', 'vacuum_sealed')
    search_fields = ('sku', 'qr_code', 'brand__name', 'brand__material_type__name')
    readonly_fields = ('sku', 'qr_code', 'brand_price_display', 'current_net_weight_g')
    actions = [
        generate_qr_codes, mark_as_stocked, mark_as_reserved,
        mark_as_in_use, mark_as_discarded
    ]

    fieldsets = (
        (None, {
            'fields': ('organization', 'brand', 'status')
        }),
        ('Identifiers', {
            'fields': ('sku', 'sku_position', 'qr_code')
        }),
        ('Material Details', {
            'fields': ('price_per_kg_override', 'brand_price_display', 'error_margin', 'spool_size_kg')
        }),
        ('Weight Tracking', {
            'fields': ('initial_net_weight_g', 'current_net_weight_g')
        }),
        ('Dates & Status', {
            'fields': (
                'date_ordered', 'date_stocked', 'vacuum_sealed', 'date_opened',
                'last_dried', 'next_drying'
            )
        }),
        ('Quality Control', {
            'fields': (
                'diameter_checked', 'diameter_check_date', 'diameter_result',
                'rewound', 'rewound_date'
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    @admin.display(description="Color", ordering='brand__color_hex')
    def brand_color_display(self, obj):
        hex_color = obj.brand.color_hex if obj.brand else None
        if hex_color:
            return mark_safe(
                f'<span style="display:inline-block;width:16px;height:16px;'
                f'background-color:{hex_color};border:1px solid #ccc;'
                f'margin-right:6px;vertical-align:middle;"></span>'
                f'{hex_color}'
            )
        return '-'

    @admin.display(description="Brand Price/kg")
    def brand_price_display(self, obj=None):
        if obj and obj.brand_id:
            return f'{obj.brand.price_per_kg} CZK'
        return '-'

    @admin.display(description="Current Weight", ordering='current_net_weight_g')
    def weight_display(self, obj):
        if obj.status == 'ordered':
            return 'Waiting for stock'
        if obj.current_net_weight_g is None:
            return '-'
        return f'{obj.current_net_weight_g} g'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-add/',
                self.admin_site.admin_view(self.bulk_add_view),
                name='print3d_filament_bulk_add',
            ),
            path(
                'bulk-add-modal/',
                self.admin_site.admin_view(self.bulk_add_modal_view),
                name='print3d_filament_bulk_add_modal',
            ),
        ]
        return custom_urls + urls

    def bulk_add_modal_view(self, request):
        """Return modal HTML for HTMX request."""
        from core.models import Organization as Org

        if request.method == 'POST':
            brand_id = request.POST.get('brand')
            org_id = request.POST.get('organization')
            count = int(request.POST.get('count', 1))
            weight_g = request.POST.get('initial_net_weight_g') or None
            override_price = request.POST.get('price_per_kg_override') or None

            brand = get_object_or_404(FilamentBrand, pk=brand_id)
            org = get_object_or_404(Org, pk=org_id)

            created = []
            for _ in range(count):
                filament = Filament(
                    organization=org,
                    brand=brand,
                    status='ordered',
                    initial_net_weight_g=weight_g,
                    price_per_kg_override=override_price if override_price else None,
                )
                filament.save()
                created.append(filament.sku)

            self.message_user(request, f"Created {len(created)} spools: {', '.join(created)}")
            return redirect('admin:print3d_filament_changelist')

        brands = FilamentBrand.objects.filter(is_active=True).order_by('name')
        organizations = Org.objects.all().order_by('name')
        context = {
            'brands': brands,
            'organizations': organizations,
            'opts': self.model._meta,
        }
        return render(request, 'admin/print3d/filament/bulk_add_modal.html', context)

    def bulk_add_view(self, request):
        from core.models import Organization as Org

        if request.method == 'POST':
            brand_id = request.POST.get('brand')
            org_id = request.POST.get('organization')
            count = int(request.POST.get('count', 1))
            weight_g = request.POST.get('initial_net_weight_g') or None
            override_price = request.POST.get('price_per_kg_override') or None

            brand = get_object_or_404(FilamentBrand, pk=brand_id)
            org = get_object_or_404(Org, pk=org_id)

            created = []
            for _ in range(count):
                filament = Filament(
                    organization=org,
                    brand=brand,
                    status='ordered',
                    initial_net_weight_g=weight_g,
                    price_per_kg_override=override_price if override_price else None,
                )
                filament.save()
                created.append(filament.sku)

            self.message_user(request, f"Created {len(created)} spools: {', '.join(created)}")
            return redirect('admin:print3d_filament_changelist')

        brands = FilamentBrand.objects.filter(is_active=True).order_by('name')
        organizations = Org.objects.all().order_by('name')
        context = {
            'brands': brands,
            'organizations': organizations,
            'title': 'Bulk Add Filament Spools',
            'opts': self.model._meta,
        }
        return render(request, 'admin/print3d/filament/bulk_add.html', context)


# ============================================================
# CUSTOM ORDER
# ============================================================

@admin.action(description="Export Selected Orders to TXT")
def export_estimation_to_txt(modeladmin, request, queryset):
    import io
    output = io.StringIO()
    for obj in queryset:
        output.write(f"--- Order: {obj.project_name} ---\n")
        output.write(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        output.write(f"Status: {obj.get_status_display()}\n")
        printer_name = obj.printer.name if obj.printer else 'Unknown Printer'
        output.write(f"Printer: {printer_name} | Plates: {obj.plates_count} | Print Time: {obj.print_time_minutes} min\n")
        output.write(f"Yield: {obj.products_count} products\n")
        fil_name = str(obj.filament.brand) if obj.filament else 'Unknown Filament'
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
class CustomOrderAdmin(OrganizationAdminMixin, ModelAdmin):
    def save_model(self, request, obj, form, change):
        """
        Override save_model to guarantee _on_confirmed() runs even when
        Unfold admin bypasses the model's save() override.

        This is the gold-standard hook — Django admin ALWAYS calls this.
        """
        super().save_model(request, obj, form, change)

        # Trigger ProductionOrder generation on confirmed transition
        if obj.status == 'confirmed':
            try:
                obj._on_confirmed()
            except Exception:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(
                    "Admin save_model: Failed to create ProductionOrder for "
                    "CustomOrder #%s (%s)",
                    obj.pk,
                    obj.project_name,
                )

    list_display = (
        'project_name', 'organization', 'status', 'printer', 'products_count',
        'display_base_cost', 'display_price_100', 'display_price_200',
        'display_price_350', 'created_at'
    )
    list_filter = ('organization', 'status', 'printer', 'filament', 'delivery_type')
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
            path(
                '<path:object_id>/export-txt/',
                self.admin_site.admin_view(self.export_single_txt),
                name='customorder_export_txt'
            ),
        ]
        return custom_urls + urls

    def export_single_txt(self, request, object_id):
        obj = get_object_or_404(CustomOrder, pk=object_id)
        import io
        output = io.StringIO()
        output.write(f"--- Order: {obj.project_name} ---\n")
        output.write(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        output.write(f"Status: {obj.get_status_display()}\n")
        printer_name = obj.printer.name if obj.printer else 'Unknown Printer'
        output.write(f"Printer: {printer_name} | Plates: {obj.plates_count} | Print Time: {obj.print_time_minutes} min\n")
        output.write(f"Yield: {obj.products_count} products\n")
        fil_name = str(obj.filament.brand) if obj.filament else 'Unknown Filament'
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
            return mark_safe(
                "<div style='color: #6b7280; font-style: italic; padding: 1rem;'>"
                "Save the record to calculate margins.</div>"
            )

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
        ("Organization", {
            "fields": ("organization",)
        }),
        ("Basic Info", {
            "fields": ("project_name", "products_count", "printer", "status")
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


# ============================================================
# FILAMENT USAGE LOG
# ============================================================

@admin.register(FilamentUsageLog)
class FilamentUsageLogAdmin(ModelAdmin):
    list_display = ('filament', 'custom_order', 'grams_used', 'created_at')
    list_filter = ('filament', 'created_at')
    search_fields = ('filament__sku', 'custom_order__project_name', 'notes')
    readonly_fields = ('filament', 'custom_order', 'grams_used', 'created_at', 'notes')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False