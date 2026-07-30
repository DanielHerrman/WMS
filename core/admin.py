from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from .models import (
    Organization, UserProfile, Client, Product, ProductionDetails,
    EcommerceStore, EcommerceOrder, OrderItem,
    ProductComponent, ProductionStepTemplate,
    ProductionOrder, ProductionStep,
)


class OrganizationAdminMixin:
    """
    Mixin for multi-tenant data isolation.
    - Filters queryset to user's organization only (superusers see all).
    - Auto-assigns organization on new objects from user's profile.
    - Hides organization field from non-superusers.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            org = request.user.profile.organization
        except (AttributeError, UserProfile.DoesNotExist):
            # Non-superuser without profile → no access
            return qs.none()
        return qs.filter(organization=org)

    def save_model(self, request, obj, form, change):
        if not change and not obj.organization_id:
            try:
                obj.organization = request.user.profile.organization
            except (AttributeError, UserProfile.DoesNotExist):
                pass
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'organization' in form.base_fields:
            if request.user.is_superuser:
                if not obj:
                    form.base_fields['organization'].initial = getattr(
                        request.user.profile, 'organization', None
                    )
                form.base_fields['organization'].help_text = (
                    'Select the organization this record belongs to.'
                )
            else:
                form.base_fields['organization'].initial = getattr(
                    request.user.profile, 'organization', None
                )
                form.base_fields['organization'].disabled = True
                form.base_fields['organization'].help_text = (
                    'Automatically set to your organization.'
                )
        return form


# ============================================================
# ORGANIZATION, USER PROFILE, CLIENT
# ============================================================

@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'organization')
    list_filter = ('organization',)
    search_fields = ('user__username', 'organization__name')
    autocomplete_fields = ('user',)


@admin.register(Client)
class ClientAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'contact_email')
    list_filter = ('organization',)
    search_fields = ('name',)


# ============================================================
# PRODUCT COMPONENT (BOM) INLINE
# ============================================================

class ProductComponentInline(StackedInline):
    model = ProductComponent
    extra = 1
    fk_name = 'parent_product'
    autocomplete_fields = ['component']
    ordering = ['sort_order']


# ============================================================
# PRODUCT
# ============================================================

@admin.register(Product)
class ProductAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('sku', 'name', 'organization', 'client', 'weight_g',
                    'is_purchased', 'is_packaging')
    list_filter = ('organization', 'client', 'is_packaging', 'is_purchased',
                   'is_3d_print_material')
    search_fields = ('sku', 'name')
    inlines = [ProductComponentInline]


# ============================================================
# PRODUCTION DETAILS
# ============================================================

@admin.register(ProductionDetails)
class ProductionDetailsAdmin(ModelAdmin):
    list_display = ('product', 'material_type', 'color_name')
    search_fields = ('product__sku', 'product__name', 'material_type')

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': ('product', 'material_type', 'color_name')
            }),
        ]
        if obj is None or (obj.product and obj.product.is_3d_print_material):
            fieldsets.append(
                ('Filament', {
                    'fields': ('filament_weight_g',),
                    'description': 'Hmotnost filamentu — relevantní pouze pro 3D tiskové materiály.'
                })
            )
        return fieldsets


# ============================================================
# E-COMMERCE STORE
# ============================================================

@admin.register(EcommerceStore)
class EcommerceStoreAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'platform', 'slug', 'is_active', 'created_at')
    list_filter = ('organization', 'platform', 'is_active')
    search_fields = ('name', 'slug', 'base_url')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('organization', 'platform', 'name', 'slug', 'base_url')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret', 'webhook_secret'),
            'description': 'API klíče pro komunikaci s e-shopem. Consumer Key/Secret u WooCommerce.'
        }),
        ('Settings', {
            'fields': ('is_active', 'meta'),
            'description': 'JSON pole pro platform-specific nastavení.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


# ============================================================
# ORDER ITEM INLINE (readonly)
# ============================================================

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('ecommerce_item_id', 'product', 'product_name', 'sku',
                       'quantity', 'unit_price', 'subtotal')
    can_delete = False
    max_num = 0
    show_change_link = True


# ============================================================
# E-COMMERCE ORDER
# ============================================================

@admin.register(EcommerceOrder)
class EcommerceOrderAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('__str__', 'organization', 'store', 'status',
                    'billing_email', 'total', 'currency', 'imported_at')
    list_filter = ('organization', 'store', 'status', 'currency', 'imported_at')
    search_fields = ('platform_order_id', 'billing_email', 'billing_first_name',
                     'billing_last_name', 'shipping_first_name', 'shipping_last_name')
    readonly_fields = ('imported_at', 'raw_data')
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('store', 'organization', 'client', 'platform_order_id', 'status')
        }),
        ('Billing', {
            'fields': ('billing_first_name', 'billing_last_name', 'billing_email',
                       'billing_phone', 'billing_address_1', 'billing_city',
                       'billing_postcode', 'billing_country')
        }),
        ('Shipping', {
            'fields': ('shipping_first_name', 'shipping_last_name', 'shipping_address_1',
                       'shipping_city', 'shipping_postcode', 'shipping_country',
                       'shipping_method')
        }),
        ('Finance', {
            'fields': ('subtotal', 'shipping_total', 'total', 'currency', 'payment_method')
        }),
        ('Meta', {
            'fields': ('notes', 'raw_data', 'imported_at')
        }),
    )

    def has_add_permission(self, request):
        return False  # Orders are imported via webhook only


# ============================================================
# PRODUCTION STEP INLINE
# ============================================================

class ProductionStepInline(TabularInline):
    model = ProductionStep
    extra = 0
    fields = ('step_number', 'name', 'is_required', 'is_completed',
              'completed_by', 'completed_at')
    readonly_fields = ('completed_by', 'completed_at')
    ordering = ['step_number']
    show_change_link = True


# ============================================================
# PRODUCTION ORDER
# ============================================================

@admin.register(ProductionOrder)
class ProductionOrderAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('__str__', 'status', 'quantity', 'quantity_completed',
                    'assigned_printer', 'deadline', 'created_at')
    list_filter = ('status', 'organization')
    search_fields = ('product__sku', 'product__name', 'qr_hash')
    autocomplete_fields = ('product', 'custom_order', 'ecommerce_order',
                           'assigned_printer', 'assigned_operator')
    readonly_fields = ('qr_hash', 'created_at', 'updated_at')
    inlines = [ProductionStepInline]
    fieldsets = (
        (None, {
            'fields': ('organization', 'product', 'quantity', 'quantity_completed', 'status')
        }),
        ('Source', {
            'fields': ('order_item', 'custom_order', 'ecommerce_order')
        }),
        ('Assignment', {
            'fields': ('assigned_printer', 'assigned_operator', 'deadline')
        }),
        ('Identifier', {
            'fields': ('qr_hash',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


# ============================================================
# PRODUCTION STEP TEMPLATE
# ============================================================

@admin.register(ProductionStepTemplate)
class ProductionStepTemplateAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'step_number', 'product',
                    'material_type', 'is_required')
    list_filter = ('organization', 'product', 'material_type', 'is_required')
    search_fields = ('name', 'description')
    autocomplete_fields = ('product', 'material_type')
    ordering = ('step_number',)
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'description', 'step_number')
        }),
        ('Scope', {
            'fields': ('product', 'material_type'),
            'description': 'Nech prázdné pro univerzální šablonu.'
        }),
        ('Media', {
            'fields': ('media_url', 'is_required'),
        }),
    )


# ============================================================
# PRODUCTION STEP (standalone – i když je inline v PO)
# ============================================================

@admin.register(ProductionStep)
class ProductionStepAdmin(ModelAdmin):
    list_display = ('production_order', 'step_number', 'name', 'is_required',
                    'is_completed', 'completed_by', 'completed_at')
    list_filter = ('is_completed', 'is_required', 'production_order__status')
    search_fields = ('name', 'production_order__product__sku', 'production_order__qr_hash')
    readonly_fields = ('completed_by', 'completed_at')
    ordering = ('production_order', 'step_number')