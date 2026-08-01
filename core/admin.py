from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
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
    list_display = ('__str__', 'organization', 'store', 'status', 'is_paid',
                    'billing_email', 'total', 'currency', 'imported_at')
    list_filter = ('organization', 'store', 'status', 'is_paid', 'currency', 'imported_at')
    search_fields = ('platform_order_id', 'billing_email', 'billing_first_name',
                     'billing_last_name', 'shipping_first_name', 'shipping_last_name')
    readonly_fields = ('imported_at', 'date_paid', 'raw_data_download_link')
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
            'fields': ('subtotal', 'shipping_total', 'total', 'currency', 'payment_method',
                       'is_paid', 'date_paid')
        }),
        ('Notes & Timestamps', {
            'fields': ('notes', 'imported_at')
        }),
        ('RAW Data', {
            'fields': ('raw_data_download_link', 'raw_data'),
            'classes': ('collapse',),
            'description': 'Kompletní JSON payload z e-shopu. Pro stažení klikněte na tlačítko výše.'
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/download-raw/',
                self.admin_site.admin_view(self.download_raw_view),
                name='core_ecommerceorder_download_raw',
            ),
        ]
        return custom_urls + urls

    def download_raw_view(self, request, object_id):
        import json
        obj = get_object_or_404(EcommerceOrder, pk=object_id)
        response = HttpResponse(
            json.dumps(obj.raw_data, indent=2, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="order_{obj.platform_order_id}_raw.json"'
        )
        return response

    @admin.display(description="📥 RAW Data")
    def raw_data_download_link(self, obj):
        if not obj.pk:
            return "-"
        url = f"{obj.pk}/download-raw/"
        return mark_safe(
            f'<a class="button" href="{url}" style="display:inline-flex;align-items:center;gap:4px;">'
            f'📥 Stáhnout RAW data (JSON)</a>'
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
                    'assigned_printer', 'assigned_filament', 'deadline', 'created_at')
    list_filter = ('status', 'organization')
    search_fields = ('product__sku', 'product__name', 'qr_hash')
    autocomplete_fields = ('product', 'custom_order', 'ecommerce_order',
                           'assigned_printer', 'assigned_filament', 'assigned_operator')
    readonly_fields = ('qr_hash', 'created_at', 'updated_at')
    inlines = [ProductionStepInline]

    def get_fieldsets(self, request, obj=None):
        # Dynamicky zobraz jen relevantní source field podle typu objednávky
        source_fields = ['order_item', 'custom_order', 'ecommerce_order']
        if obj is not None:
            if obj.custom_order_id:
                source_fields = ['custom_order']
            elif obj.ecommerce_order_id:
                source_fields = ['ecommerce_order', 'order_item']

        return (
            (None, {
                'fields': ('organization', 'product', 'quantity', 'quantity_completed', 'status')
            }),
            ('Source', {
                'fields': tuple(source_fields)
            }),
            ('Assignment', {
                'fields': ('assigned_printer', 'assigned_filament', 'assigned_operator', 'deadline')
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


# ============================================================
# USER ADMIN (custom – with UserProfile inline)
# ============================================================

class UserProfileInline(StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "Organization Membership"
    verbose_name_plural = "Organization Membership"
    max_num = 1
    min_num = 1
    fields = ('organization',)


# Unregister default User admin first
if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff',
                    'is_active', 'date_joined', 'organization_name')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'groups', 'profile__organization')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')
    inlines = [UserProfileInline]
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    readonly_fields = ('last_login', 'date_joined')

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        # Auto-assign new users to the "Klient" group
        if is_new:
            try:
                client_group = Group.objects.get(name='Klient')
                obj.groups.add(client_group)
            except Group.DoesNotExist:
                pass

    @admin.display(description="Organization", ordering='profile__organization__name')
    def organization_name(self, obj):
        try:
            return obj.profile.organization.name
        except (AttributeError, UserProfile.DoesNotExist):
            return "-"

    def has_add_permission(self, request):
        return True
