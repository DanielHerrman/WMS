import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import Organization
from .models import (
    Printer,
    MaterialType,
    FilamentBrand,
    Filament,
    CustomOrder,
    FilamentUsageLog,
)


class MaterialTypeTests(TestCase):
    """Tests for MaterialType model."""

    def setUp(self):
        self.pla = MaterialType.objects.create(
            name='PLA',
            description='Standard PLA filament',
            recommended_settings={'nozzle_temp': 210, 'bed_temp': 60, 'speed': 80},
            default_error_margin=Decimal('5.00'),
            default_drying_interval_days=30,
        )

    def test_create_material_type(self):
        self.assertEqual(self.pla.name, 'PLA')
        self.assertEqual(self.pla.default_error_margin, Decimal('5.00'))
        self.assertIsNotNone(self.pla.recommended_settings)
        self.assertEqual(self.pla.recommended_settings['nozzle_temp'], 210)

    def test_material_type_str(self):
        self.assertEqual(str(self.pla), 'PLA')

    def test_unique_name(self):
        with self.assertRaises(Exception):
            MaterialType.objects.create(name='PLA')

    def test_optional_drying_interval(self):
        abs_material = MaterialType.objects.create(
            name='ABS',
            recommended_settings={'nozzle_temp': 250, 'bed_temp': 100},
        )
        self.assertIsNone(abs_material.default_drying_interval_days)


class FilamentBrandTests(TestCase):
    """Tests for FilamentBrand model."""

    def setUp(self):
        self.pla = MaterialType.objects.create(name='PLA')
        self.brand = FilamentBrand.objects.create(
            name='Smart Print',
            material_type=self.pla,
            spool_size_kg=Decimal('1.00'),
            spool_weight_g=Decimal('200.00'),
        )

    def test_create_brand(self):
        self.assertEqual(self.brand.name, 'Smart Print')
        self.assertEqual(self.brand.material_type, self.pla)
        self.assertEqual(self.brand.spool_size_kg, Decimal('1.00'))
        self.assertTrue(self.brand.is_active)

    def test_brand_str(self):
        expected = 'Smart Print — PLA (1.00 kg)'
        self.assertEqual(str(self.brand), expected)

    def test_unique_ean(self):
        brand2 = FilamentBrand.objects.create(
            name='Other Brand',
            material_type=self.pla,
            spool_size_kg=Decimal('2.50'),
            ean='1234567890123',
        )
        self.assertEqual(brand2.ean, '1234567890123')
        with self.assertRaises(Exception):
            FilamentBrand.objects.create(
                name='Dup',
                material_type=self.pla,
                spool_size_kg=Decimal('1.00'),
                ean='1234567890123',
            )

    def test_photo_url(self):
        self.brand.photo = 'https://example.com/photo.jpg'
        self.brand.save()
        self.assertEqual(self.brand.photo, 'https://example.com/photo.jpg')


class FilamentTests(TestCase):
    """Tests for Filament model."""

    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.pla = MaterialType.objects.create(
            name='PLA',
            default_error_margin=Decimal('5.00'),
        )
        self.brand = FilamentBrand.objects.create(
            name='Smart Print',
            material_type=self.pla,
            spool_size_kg=Decimal('1.00'),
            spool_weight_g=Decimal('200.00'),
        )

    def test_create_filament(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='White PLA',
            price_per_kg=Decimal('450.00'),
            error_margin=Decimal('5.00'),
            sku='FIL-PLA-001',
            status='ordered',
            color_hex='#FFFFFF',
            spool_size_kg=Decimal('1.00'),
            initial_net_weight_g=Decimal('1000.00'),
        )
        self.assertEqual(filament.sku, 'FIL-PLA-001')
        self.assertEqual(filament.status, 'ordered')
        self.assertEqual(filament.organization, self.org)
        self.assertEqual(filament.spool_size_kg, Decimal('1.00'))

    def test_spool_size_prefill_from_brand(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Black PLA',
            price_per_kg=Decimal('450.00'),
            sku='FIL-PLA-002',
            initial_net_weight_g=Decimal('1000.00'),
        )
        self.assertEqual(filament.spool_size_kg, Decimal('1.00'))

    def test_current_weight_initialized_on_create(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Red PLA',
            price_per_kg=Decimal('450.00'),
            sku='FIL-PLA-003',
            initial_net_weight_g=Decimal('1000.00'),
        )
        self.assertEqual(filament.current_net_weight_g, Decimal('1000.00'))

    def test_generate_qr_code(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Blue PLA',
            price_per_kg=Decimal('450.00'),
            sku='FIL-PLA-004',
            status='stocked',
        )
        self.assertIsNone(filament.qr_code)
        qr = filament.generate_qr_code()
        self.assertIsNotNone(qr)
        self.assertEqual(len(qr), 32)  # UUID4 hex is 32 chars
        filament.refresh_from_db()
        self.assertEqual(filament.qr_code, qr)

    def test_generate_qr_code_idempotent(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Green PLA',
            price_per_kg=Decimal('450.00'),
            sku='FIL-PLA-005',
            status='stocked',
        )
        qr1 = filament.generate_qr_code()
        qr2 = filament.generate_qr_code()
        self.assertEqual(qr1, qr2)

    def test_unique_sku(self):
        Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='A',
            sku='FIL-UNIQUE',
            price_per_kg=Decimal('450.00'),
        )
        with self.assertRaises(Exception):
            Filament.objects.create(
                organization=self.org,
                brand=self.brand,
                name='B',
                sku='FIL-UNIQUE',
                price_per_kg=Decimal('450.00'),
            )

    def test_filament_str(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='White PLA',
            sku='FIL-PLA-010',
            price_per_kg=Decimal('450.00'),
        )
        self.assertIn('FIL-PLA-010', str(filament))
        self.assertIn('Smart Print', str(filament))

    def test_status_choices(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Status Test',
            sku='FIL-STAT-001',
            price_per_kg=Decimal('450.00'),
        )
        self.assertEqual(filament.status, 'ordered')

        for status in ['stocked', 'reserved', 'in_use', 'consumed', 'discarded']:
            filament.status = status
            filament.save()
            filament.refresh_from_db()
            self.assertEqual(filament.status, status)

    def test_optional_fields(self):
        filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Minimal',
            sku='FIL-MIN-001',
            price_per_kg=Decimal('450.00'),
        )
        self.assertIsNone(filament.sku_position)
        self.assertIsNone(filament.color_hex)
        self.assertIsNone(filament.date_ordered)
        self.assertIsNone(filament.diameter_result)
        self.assertIsNone(filament.notes)
        self.assertFalse(filament.vacuum_sealed)
        self.assertFalse(filament.diameter_checked)
        self.assertFalse(filament.rewound)


class CustomOrderWorkflowTests(TestCase):
    """Tests for CustomOrder save logic and FilamentUsageLog creation."""

    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.pla = MaterialType.objects.create(name='PLA')
        self.brand = FilamentBrand.objects.create(
            name='Test Brand',
            material_type=self.pla,
            spool_size_kg=Decimal('1.00'),
            spool_weight_g=Decimal('200.00'),
        )
        self.filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Test Filament',
            sku='FIL-TEST-001',
            price_per_kg=Decimal('500.00'),
            status='stocked',
            initial_net_weight_g=Decimal('1000.00'),
        )
        self.printer = Printer.objects.create(
            name='Test Printer',
            amortization_rate_per_hour=30.0,
        )

    def test_create_order_pending(self):
        order = CustomOrder.objects.create(
            project_name='Test Project',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=50,
        )
        self.assertEqual(order.status, 'pending')

    def test_confirm_order_creates_usage_log(self):
        order = CustomOrder.objects.create(
            project_name='Confirmed Order',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=100,
        )
        order.status = 'confirmed'
        order.save()

        # Check usage log was created
        logs = FilamentUsageLog.objects.filter(custom_order=order)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().grams_used, Decimal('100'))

    def test_confirm_order_deducts_weight(self):
        order = CustomOrder.objects.create(
            project_name='Weight Deduct',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=100,
        )
        order.status = 'confirmed'
        order.save()

        self.filament.refresh_from_db()
        self.assertEqual(self.filament.current_net_weight_g, Decimal('900.00'))

    def test_confirm_order_consumes_filament_at_zero(self):
        order = CustomOrder.objects.create(
            project_name='Consume All',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=1000,
        )
        order.status = 'confirmed'
        order.save()

        self.filament.refresh_from_db()
        self.assertEqual(self.filament.current_net_weight_g, Decimal('0.00'))
        self.assertEqual(self.filament.status, 'consumed')

    def test_confirm_order_does_not_exceed_zero(self):
        order = CustomOrder.objects.create(
            project_name='Overconsume',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=1500,
        )
        order.status = 'confirmed'
        order.save()

        self.filament.refresh_from_db()
        self.assertEqual(self.filament.current_net_weight_g, Decimal('0.00'))
        self.assertEqual(self.filament.status, 'consumed')

    def test_no_usage_log_if_no_filament(self):
        order = CustomOrder.objects.create(
            project_name='No Filament Order',
            printer=self.printer,
            filament=None,
            filament_weight_g=100,
        )
        order.status = 'confirmed'
        order.save()

        logs = FilamentUsageLog.objects.filter(custom_order=order)
        self.assertEqual(logs.count(), 0)

    def test_no_usage_log_if_weight_zero(self):
        order = CustomOrder.objects.create(
            project_name='Zero Weight',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=0,
        )
        order.status = 'confirmed'
        order.save()

        logs = FilamentUsageLog.objects.filter(custom_order=order)
        self.assertEqual(logs.count(), 0)

    def test_material_cost_calculation(self):
        order = CustomOrder.objects.create(
            project_name='Cost Test',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=200,
        )
        # 200g * (500 CZK / 1000g) * (1 + 0.05) = 200 * 0.5 * 1.05 = 105
        self.assertAlmostEqual(order.calculated_material_cost, 105.0, places=1)

    def test_amortization_calculation(self):
        order = CustomOrder.objects.create(
            project_name='Amort Test',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=50,
            print_time_minutes=120,
        )
        # 120 min / 60 * 30 CZK/h = 60
        self.assertAlmostEqual(order.calculated_amortization, 60.0, places=1)

    def test_reconfirm_does_not_create_duplicate_logs(self):
        order = CustomOrder.objects.create(
            project_name='Reconfirm Test',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=50,
        )
        order.status = 'confirmed'
        order.save()

        self.assertEqual(FilamentUsageLog.objects.filter(custom_order=order).count(), 1)

        # Save again with same status — no new log
        order.project_name = 'Updated Name'
        order.save()

        self.assertEqual(FilamentUsageLog.objects.filter(custom_order=order).count(), 1)


class FilamentUsageLogTests(TestCase):
    """Tests for FilamentUsageLog model."""

    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.pla = MaterialType.objects.create(name='PLA')
        self.brand = FilamentBrand.objects.create(
            name='Test Brand',
            material_type=self.pla,
            spool_size_kg=Decimal('1.00'),
        )
        self.filament = Filament.objects.create(
            organization=self.org,
            brand=self.brand,
            name='Log Test',
            sku='FIL-LOG-001',
            price_per_kg=Decimal('500.00'),
            status='stocked',
            initial_net_weight_g=Decimal('1000.00'),
        )
        self.printer = Printer.objects.create(name='Test Printer')
        self.order = CustomOrder.objects.create(
            project_name='Log Order',
            printer=self.printer,
            filament=self.filament,
            filament_weight_g=75,
        )

    def test_create_usage_log_manually(self):
        log = FilamentUsageLog.objects.create(
            filament=self.filament,
            custom_order=self.order,
            grams_used=Decimal('75.00'),
            notes='Manual entry',
        )
        self.assertEqual(log.grams_used, Decimal('75.00'))
        self.assertIsNotNone(log.created_at)
        self.assertEqual(log.notes, 'Manual entry')

    def test_usage_log_str(self):
        log = FilamentUsageLog.objects.create(
            filament=self.filament,
            custom_order=self.order,
            grams_used=Decimal('75.00'),
        )
        self.assertIn('FIL-LOG-001', str(log))
        self.assertIn('75', str(log))

    def test_usage_log_ordering(self):
        log1 = FilamentUsageLog.objects.create(
            filament=self.filament,
            custom_order=self.order,
            grams_used=Decimal('10.00'),
        )
        log2 = FilamentUsageLog.objects.create(
            filament=self.filament,
            custom_order=self.order,
            grams_used=Decimal('20.00'),
        )
        logs = list(FilamentUsageLog.objects.all())
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], log1)


class PrinterTests(TestCase):
    """Tests for Printer model."""

    def test_create_printer(self):
        printer = Printer.objects.create(
            name='Bambu P1S',
            amortization_rate_per_hour=25.0,
        )
        self.assertEqual(printer.name, 'Bambu P1S')
        self.assertEqual(printer.amortization_rate_per_hour, 25.0)

    def test_printer_str(self):
        printer = Printer.objects.create(
            name='Prusa MK4',
            amortization_rate_per_hour=20.0,
        )
        self.assertIn('Prusa MK4', str(printer))
        self.assertIn('20.0', str(printer))