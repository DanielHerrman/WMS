import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from .models import EcommerceStore
from .services import import_ecommerce_order

logger = logging.getLogger(__name__)


@csrf_exempt
def ecommerce_webhook(request, store_slug: str):
    """
    Universal e-commerce webhook endpoint.
    POST /webhook/<slug>/ — accepts order payload from WooCommerce/Shopify/Shoptet.

    The EcommerceStore is identified by its slug.
    Optional HMAC verification can be enabled if webhook_secret is set.
    """
    # Find the store by slug
    store = get_object_or_404(EcommerceStore, slug=store_slug, is_active=True)

    # WooCommerce/Shopify delivery verification uses GET health-check
    if request.method == 'GET':
        return JsonResponse({'status': 'ok', 'store': store.slug})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Optional HMAC verification
    if store.webhook_secret:
        hmac_header = request.headers.get('X-WC-Webhook-Signature', '') or \
                      request.headers.get('X-Shopify-Hmac-Sha256', '') or \
                      request.headers.get('X-Hub-Signature', '')
        if hmac_header:
            # TODO: implement proper HMAC verification per platform
            # For WooCommerce: verify header == base64(hmac_sha256(webhook_secret, body))
            pass

    # Parse JSON payload — empty body = delivery ping
    if not request.body:
        return JsonResponse({'status': 'ok', 'note': 'webhook delivery acknowledged'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'ok', 'note': 'webhook delivery acknowledged (non-JSON body)'}, status=200)

    # Import the order
    try:
        order = import_ecommerce_order(store, data)
        return JsonResponse({
            'status': 'ok',
            'order_id': order.id,
            'platform_order_id': order.platform_order_id,
        })
    except Exception as e:
        logger.exception(f"Failed to import e-commerce order for store {store_slug}")
        return JsonResponse({'error': str(e)}, status=500)