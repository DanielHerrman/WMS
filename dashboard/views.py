import base64
import io
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import Organization, UserProfile, ProductionOrder
from print3d.models import CustomOrder, FilamentUsageLog

ALLOWED_GROUPS = {'Admin', 'Obchoďák', 'Klient'}

# Safe fields for CustomOrder on dashboard — NO financial data ever
SAFE_B2B_FIELDS = [
    'id', 'project_name', 'products_count', 'status', 'printer',
    'plates_count', 'filament_weight_g', 'delivery_type', 'created_at',
]

SEKCE_NEZOBRAZUJE_CENY = (
    'Misto cen/marzi zobrazujeme jen vyrobni data.'
)


def get_visible_organizations(user):
    """
    Returns:
        None  — superuser / Admin / Obchoďák (see all organizations)
        list  — [organization] for Klient
        []    — no access (Operátor etc. — pero PermissionDenied handles this)
    """
    if user.is_superuser or user.groups.filter(name__in=['Admin', 'Obchoďák']).exists():
        return None
    try:
        return [user.profile.organization]
    except (AttributeError, UserProfile.DoesNotExist):
        return []


def dashboard_access_required(view_func):
    """
    Decorator: login_required + group membership check.
    - superuser, Admin, Obchoďák, Klient → allowed
    - Operátor (has profile but not in allowed groups) → 403
    """

    @login_required
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=ALLOWED_GROUPS).exists()):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


@dashboard_access_required
def client_dashboard(request):
    user = request.user
    orgs = get_visible_organizations(user)
    is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
    is_obchodak = user.groups.filter(name='Obchoďák').exists()
    show_all_orgs = is_admin or is_obchodak  # show org column + filter

    # ── Base querysets ──
    b2b_qs = CustomOrder.objects.select_related('organization', 'printer').prefetch_related(
        'production_orders', 'filament_usage_logs',
    )
    po_qs = ProductionOrder.objects.filter(custom_order__isnull=False)
    usage_qs = FilamentUsageLog.objects.all()

    if orgs is not None:
        b2b_qs = b2b_qs.filter(organization__in=orgs)
        po_qs = po_qs.filter(organization__in=orgs)
        usage_qs = usage_qs.filter(custom_order__organization__in=orgs)

    # ── Statistics cards ──

    # 1. Aktivní zakázky
    active_orders_count = b2b_qs.filter(status__in=['pending', 'confirmed', 'printing']).count()

    # 2. Vyrobené ks (tento měsíc)
    start_of_month = date.today().replace(day=1)
    produced_this_month = (
        po_qs.filter(
            status__in=['qc', 'packed', 'done'],
            updated_at__gte=start_of_month,
        ).aggregate(total=Sum('quantity_completed'))['total'] or 0
    )

    # 3. Průměrná doba výroby (dny) — PO status=done, finished_at použito
    dones = po_qs.filter(status='done', finished_at__isnull=False).values('created_at', 'finished_at')
    durations = []
    for d in dones:
        if d['created_at'] and d['finished_at']:
            durations.append((d['finished_at'] - d['created_at']).total_seconds())
    avg_production_days = sum(durations) / len(durations) / 86400 if durations else None

    # 4. Průměrná doba doručení — placeholder
    avg_delivery_days = None  # přijde s Fází 5

    # 5. Spotřeba materiálu (g)
    total_grams = usage_qs.aggregate(total=Sum('grams_used'))['total'] or 0
    if total_grams >= 1000:
        display_grams = f"{total_grams / 1000:.1f} kg"
    else:
        display_grams = f"{total_grams:.0f} g"

    # ── Orders list (latest 10) ──
    orders = b2b_qs.order_by('-created_at')[:10]

    # Annotate progress per order
    order_data = []
    for order in orders:
        pos = list(order.production_orders.all())
        total_qty = sum(po.quantity for po in pos)
        completed_qty = sum(po.quantity_completed for po in pos)
        progress_pct = int(completed_qty / total_qty * 100) if total_qty > 0 else 0
        order_data.append({
            'order': order,
            'total_qty': total_qty,
            'completed_qty': completed_qty,
            'progress_pct': progress_pct,
        })

    # ── Organization filter for admin/obchodak ──
    all_orgs = None
    selected_org = None
    if show_all_orgs:
        all_orgs = Organization.objects.all().order_by('name')
        selected_org_id = request.GET.get('org')
        if selected_org_id:
            selected_org = get_object_or_404(Organization, pk=selected_org_id)
            order_data = [d for d in order_data if d['order'].organization_id == selected_org.pk]

    context = {
        'active_orders_count': active_orders_count,
        'produced_this_month': produced_this_month,
        'avg_production_days': avg_production_days,
        'avg_delivery_days': avg_delivery_days,
        'total_grams': total_grams,
        'display_grams': display_grams,
        'order_data': order_data,
        'is_admin_or_obchodak': show_all_orgs,
        'all_orgs': all_orgs,
        'selected_org': selected_org,
    }
    return render(request, 'dashboard/client_dashboard.html', context)


@dashboard_access_required
def manufacturing_detail(request, pk):
    user = request.user
    orgs = get_visible_organizations(user)

    order = get_object_or_404(
        CustomOrder.objects.select_related(
            'organization', 'printer', 'filament',
        ).prefetch_related(
            'production_orders__product',
            'production_orders__steps',
            'production_orders__assigned_printer',
            'production_orders__assigned_operator',
            'filament_usage_logs',
        ),
        pk=pk,
    )

    # Scope check
    if orgs is not None and order.organization not in orgs:
        raise PermissionDenied

    pos = list(order.production_orders.all())
    total_qty = sum(po.quantity for po in pos)
    completed_qty = sum(po.quantity_completed for po in pos)
    overall_progress = int(completed_qty / total_qty * 100) if total_qty > 0 else 0

    # Per-PO data
    po_data = []
    for po in pos:
        po_progress = int(po.quantity_completed / po.quantity * 100) if po.quantity > 0 else 0
        po_data.append({
            'po': po,
            'progress_pct': po_progress,
            'steps': po.steps.order_by('step_number'),
        })

    # Material — total grams (no prices)
    total_material_grams = order.filament_usage_logs.aggregate(
        total=Sum('grams_used')
    )['total'] or 0

    # QR code (segno — local generation)
    qr_b64 = None
    if hasattr(order, 'production_orders'):
        # Use the B2B order's first PO qr_hash, or generate from CustomOrder.pk
        first_po = pos[0] if pos else None
        qr_data = first_po.qr_hash if first_po else f'B2B-{order.pk}'
        try:
            import segno
            buf = io.BytesIO()
            qr = segno.make(qr_data, micro=False)
            qr.save(buf, kind='png', scale=5)
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            pass  # segno not installed — QR will be hidden

    # Safe order dict — whitelist approach, NO financial fields
    safe_order = {field: getattr(order, field, None) for field in SAFE_B2B_FIELDS}
    safe_order['organization_name'] = order.organization.name

    context = {
        'order': safe_order,
        'raw_order': order,  # for FK access (printer.name etc.) — safe, no financials
        'pos_data': po_data,
        'total_qty': total_qty,
        'completed_qty': completed_qty,
        'overall_progress': overall_progress,
        'total_material_grams': total_material_grams,
        'qr_b64': qr_b64,
    }
    return render(request, 'dashboard/manufacturing_detail.html', context)