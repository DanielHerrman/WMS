from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Organization, UserProfile, Client, Product, ProductionDetails


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
                # Superuser: pre-fill from profile but allow choosing any org
                if not obj:
                    form.base_fields['organization'].initial = getattr(
                        request.user.profile, 'organization', None
                    )
                form.base_fields['organization'].help_text = (
                    'Select the organization this record belongs to.'
                )
            else:
                # Regular user: locked to their own organization
                form.base_fields['organization'].initial = getattr(
                    request.user.profile, 'organization', None
                )
                form.base_fields['organization'].disabled = True
                form.base_fields['organization'].help_text = (
                    'Automatically set to your organization.'
                )
        return form


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


@admin.register(Product)
class ProductAdmin(OrganizationAdminMixin, ModelAdmin):
    list_display = ('sku', 'name', 'organization', 'client', 'weight_g', 'is_packaging')
    list_filter = ('organization', 'client', 'is_packaging', 'is_3d_print_material')
    search_fields = ('sku', 'name')


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
        # filament_weight_g is only relevant for 3D print materials
        if obj is None or (obj.product and obj.product.is_3d_print_material):
            fieldsets.append(
                ('Filament', {
                    'fields': ('filament_weight_g',),
                    'description': 'Hmotnost filamentu — relevantní pouze pro 3D tiskové materiály.'
                })
            )
        return fieldsets
