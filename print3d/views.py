from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q

from .models import Printer, MaterialType, FilamentBrand, Filament, CustomOrder, FilamentUsageLog
from .serializers import (
    PrinterSerializer,
    MaterialTypeSerializer,
    FilamentBrandSerializer,
    FilamentBrandDashboardSerializer,
    FilamentSerializer,
    FilamentListSerializer,
    CustomOrderSerializer,
    FilamentUsageLogSerializer,
)


class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'amortization_rate_per_hour']


class MaterialTypeViewSet(viewsets.ModelViewSet):
    queryset = MaterialType.objects.all()
    serializer_class = MaterialTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']


class FilamentBrandViewSet(viewsets.ModelViewSet):
    queryset = FilamentBrand.objects.all()
    serializer_class = FilamentBrandSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['material_type', 'is_active', 'spool_size_kg']
    search_fields = ['name', 'ean']
    ordering_fields = ['name', 'material_type__name', 'spool_size_kg']

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """Aggregated overview grouped by FilamentBrand with filament lists."""
        brands = FilamentBrand.objects.prefetch_related(
            'filaments'
        ).annotate(
            total_spools=Count('filaments'),
            stocked_count=Count('filaments', filter=Q(filaments__status='stocked')),
            reserved_count=Count('filaments', filter=Q(filaments__status='reserved')),
        ).order_by('name')
        serializer = FilamentBrandDashboardSerializer(brands, many=True)
        return Response(serializer.data)


class FilamentViewSet(viewsets.ModelViewSet):
    queryset = Filament.objects.select_related('brand', 'brand__material_type', 'organization').all()
    serializer_class = FilamentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'brand', 'status', 'organization',
        'vacuum_sealed', 'diameter_checked', 'rewound'
    ]
    search_fields = ['sku', 'name', 'qr_code', 'sku_position', 'brand__name']
    ordering_fields = [
        'sku', 'name', 'status', 'price_per_kg',
        'current_net_weight_g', 'created_at', 'date_opened'
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Allow filtering by material_type through brand
        material_type = self.request.query_params.get('material_type')
        if material_type:
            queryset = queryset.filter(brand__material_type_id=material_type)
        return queryset

    @action(detail=False, methods=['post'], url_path='generate-qr')
    def generate_qr(self, request):
        """Generate QR codes for selected filament IDs in 'stocked' status."""
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No IDs provided. Provide {"ids": [1, 2, 3]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        filaments = Filament.objects.filter(id__in=ids, status='stocked')
        results = []
        for filament in filaments:
            qr_code = filament.generate_qr_code()
            results.append({
                'id': filament.id,
                'sku': filament.sku,
                'name': filament.name,
                'qr_code': qr_code,
            })

        skipped = len(ids) - len(results)
        return Response({
            'generated': len(results),
            'skipped': skipped,
            'results': results,
        })

    @action(detail=True, methods=['get'], url_path='by-qr')
    def by_qr(self, request, pk=None):
        """Lookup filament by QR code."""
        filament = Filament.objects.filter(qr_code=pk).first()
        if not filament:
            return Response(
                {'error': 'Filament not found for this QR code'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(filament)
        return Response(serializer.data)


class CustomOrderViewSet(viewsets.ModelViewSet):
    queryset = CustomOrder.objects.select_related('printer', 'filament').all()
    serializer_class = CustomOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['printer', 'filament', 'status', 'delivery_type']
    search_fields = ['project_name']
    ordering_fields = ['created_at', 'project_name', 'calculated_base_cost', 'status']


class FilamentUsageLogViewSet(viewsets.ModelViewSet):
    queryset = FilamentUsageLog.objects.select_related(
        'filament', 'custom_order'
    ).all()
    serializer_class = FilamentUsageLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['filament', 'custom_order']
    search_fields = ['notes', 'filament__sku', 'custom_order__project_name']
    ordering_fields = ['created_at', 'grams_used']