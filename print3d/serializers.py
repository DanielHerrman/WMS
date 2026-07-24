from rest_framework import serializers
from .models import Printer, MaterialType, FilamentBrand, Filament, CustomOrder, FilamentUsageLog


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = '__all__'


class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = '__all__'


class FilamentBrandSerializer(serializers.ModelSerializer):
    material_type_name = serializers.ReadOnlyField(source='material_type.name')
    total_spools = serializers.SerializerMethodField()

    class Meta:
        model = FilamentBrand
        fields = [
            'id', 'name', 'material_type', 'material_type_name',
            'spool_size_kg', 'ean', 'photo', 'test_filament',
            'test_notes', 'price_per_kg', 'color_hex',
            'spool_weight_g', 'is_active', 'total_spools'
        ]

    def get_total_spools(self, obj):
        return obj.filaments.count()


class FilamentBrandDashboardSerializer(serializers.ModelSerializer):
    """Aggregated dashboard view grouped by FilamentBrand."""
    material_type_name = serializers.ReadOnlyField(source='material_type.name')
    total_spools = serializers.SerializerMethodField()
    stocked_count = serializers.SerializerMethodField()
    reserved_count = serializers.SerializerMethodField()
    in_use_count = serializers.SerializerMethodField()
    consumed_count = serializers.SerializerMethodField()
    discarded_count = serializers.SerializerMethodField()
    ordered_count = serializers.SerializerMethodField()
    filaments = serializers.SerializerMethodField()

    class Meta:
        model = FilamentBrand
        fields = [
            'id', 'name', 'material_type', 'material_type_name',
            'spool_size_kg', 'is_active',
            'total_spools', 'stocked_count', 'reserved_count',
            'in_use_count', 'consumed_count', 'discarded_count',
            'ordered_count', 'filaments'
        ]

    def get_total_spools(self, obj):
        return obj.filaments.count()

    def get_stocked_count(self, obj):
        return obj.filaments.filter(status='stocked').count()

    def get_reserved_count(self, obj):
        return obj.filaments.filter(status='reserved').count()

    def get_in_use_count(self, obj):
        return obj.filaments.filter(status='in_use').count()

    def get_consumed_count(self, obj):
        return obj.filaments.filter(status='consumed').count()

    def get_discarded_count(self, obj):
        return obj.filaments.filter(status='discarded').count()

    def get_ordered_count(self, obj):
        return obj.filaments.filter(status='ordered').count()

    def get_filaments(self, obj):
        filaments = obj.filaments.all()
        return FilamentListSerializer(filaments, many=True).data


class FilamentListSerializer(serializers.ModelSerializer):
    """Compact filament representation for lists/dashboard."""
    brand_name = serializers.ReadOnlyField(source='brand.name')
    material_type = serializers.ReadOnlyField(source='brand.material_type.name')
    price_per_kg = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    color_hex = serializers.ReadOnlyField(source='brand.color_hex')

    class Meta:
        model = Filament
        fields = [
            'id', 'sku', 'brand', 'brand_name', 'material_type',
            'status', 'color_hex', 'price_per_kg', 'spool_size_kg',
            'current_net_weight_g', 'qr_code', 'sku_position', 'created_at'
        ]


class FilamentSerializer(serializers.ModelSerializer):
    brand_name = serializers.ReadOnlyField(source='brand.name')
    material_type = serializers.ReadOnlyField(source='brand.material_type.name')
    material_type_id = serializers.ReadOnlyField(source='brand.material_type.id')
    organization_name = serializers.ReadOnlyField(source='organization.name')
    color_hex = serializers.ReadOnlyField(source='brand.color_hex')
    price_per_kg = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Filament
        fields = [
            'id', 'organization', 'organization_name', 'brand', 'brand_name',
            'material_type', 'material_type_id',
            'price_per_kg', 'price_per_kg_override', 'error_margin',
            'sku', 'sku_position', 'status', 'color_hex',
            'spool_size_kg', 'initial_net_weight_g', 'current_net_weight_g',
            'date_ordered', 'date_stocked', 'vacuum_sealed', 'date_opened',
            'last_dried', 'next_drying', 'diameter_checked',
            'diameter_check_date', 'diameter_result',
            'rewound', 'rewound_date', 'qr_code', 'notes', 'created_at'
        ]
        read_only_fields = ['qr_code', 'created_at', 'sku']


class CustomOrderSerializer(serializers.ModelSerializer):
    filament_sku = serializers.ReadOnlyField(source='filament.sku')

    class Meta:
        model = CustomOrder
        fields = [
            'id', 'project_name', 'products_count', 'status',
            'printer', 'plates_count', 'print_time_minutes',
            'filament', 'filament_sku', 'filament_weight_g',
            'modeling_minutes', 'modeling_hourly_rate',
            'operation_minutes', 'operation_hourly_rate',
            'postprocessing_minutes', 'postprocessing_hourly_rate',
            'packaging_minutes', 'packaging_hourly_rate',
            'delivery_type', 'shipping_cost',
            'calculated_material_cost', 'calculated_amortization',
            'calculated_labor_cost',
            'calculated_base_cost', 'calculated_price_100',
            'calculated_price_200', 'calculated_price_350',
            'created_at'
        ]
        read_only_fields = [
            'calculated_material_cost', 'calculated_amortization',
            'calculated_labor_cost',
            'calculated_base_cost', 'calculated_price_100',
            'calculated_price_200', 'calculated_price_350',
            'created_at'
        ]


class FilamentUsageLogSerializer(serializers.ModelSerializer):
    filament_sku = serializers.ReadOnlyField(source='filament.sku')
    filament_brand = serializers.ReadOnlyField(source='filament.brand.name')
    order_project = serializers.ReadOnlyField(source='custom_order.project_name')

    class Meta:
        model = FilamentUsageLog
        fields = [
            'id', 'filament', 'filament_sku', 'filament_brand',
            'custom_order', 'order_project',
            'grams_used', 'created_at', 'notes'
        ]
        read_only_fields = ['created_at']
