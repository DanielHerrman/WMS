from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Client, Product, ProductionDetails, Organization, Profile

class MultiTenantAdminMixin:
    """Mixin pro automatické filtrování dat podle organizace uživatele"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.organization:
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def get_exclude(self, request, obj=None):
        """Skryje pole 'organization' pro všechny běžné uživatele"""
        excludes = super().get_exclude(request, obj) or []
        excludes = list(excludes)
        if not request.user.is_superuser:
            if 'organization' not in excludes:
                excludes.append('organization')
        return tuple(excludes) if excludes else None

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not change:
            if hasattr(request.user, 'profile') and request.user.profile.organization:
                obj.organization = request.user.profile.organization
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            try:
                user_org = request.user.profile.organization
                if hasattr(db_field.remote_field.model, 'organization'):
                    kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=user_org)
            except (AttributeError, Profile.DoesNotExist):
                kwargs["queryset"] = db_field.remote_field.model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ('name',)

class ProfileInline(StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Organization & Settings'

class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = (ProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Client)
class ClientAdmin(MultiTenantAdminMixin, ModelAdmin):
    list_display = ('name', 'organization', 'contact_email')
    list_filter = ('organization',)

@admin.register(Product)
class ProductAdmin(MultiTenantAdminMixin, ModelAdmin):
    list_display = ('sku', 'name', 'client', 'organization', 'weight_g', 'is_packaging')
    list_filter = ('organization', 'client', 'is_packaging', 'is_3d_print_material')
    search_fields = ('sku', 'name')

@admin.register(ProductionDetails)
class ProductionDetailsAdmin(MultiTenantAdminMixin, ModelAdmin):
    pass