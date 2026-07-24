from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PrinterViewSet,
    MaterialTypeViewSet,
    FilamentBrandViewSet,
    FilamentViewSet,
    CustomOrderViewSet,
    FilamentUsageLogViewSet,
)

router = DefaultRouter()
router.register(r'printers', PrinterViewSet)
router.register(r'material-types', MaterialTypeViewSet)
router.register(r'filament-brands', FilamentBrandViewSet)
router.register(r'filaments', FilamentViewSet)
router.register(r'custom-orders', CustomOrderViewSet)
router.register(r'usage-logs', FilamentUsageLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]