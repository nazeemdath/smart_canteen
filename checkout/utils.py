# checkout/utils.py
import json
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from main.models import WebPushSubscription
from .models import Order

logger = logging.getLogger(__name__)


def send_push_notification(user, title, body=None):
    from pywebpush import webpush, WebPushException

    subscriptions = WebPushSubscription.objects.filter(user=user)
    order = user.order_set.last()
    order_id = order.id if order else "N/A"

    payload = {
        "title": title,
        "body": body or f"Your order #{order_id} is ready for pickup!",
    }

    vapid_settings = getattr(settings, "WEBPUSH_SETTINGS", {})
    vapid_private_key = vapid_settings.get("VAPID_PRIVATE_KEY") or getattr(settings, "VAPID_PRIVATE_KEY", "")
    admin_email = vapid_settings.get("VAPID_ADMIN_EMAIL") or getattr(settings, "VAPID_ADMIN_EMAIL", "") or settings.EMAIL_HOST_USER or "admin@example.com"

    if not vapid_private_key:
        logger.warning("VAPID_PRIVATE_KEY is not configured; skipping push notification.")
        return

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(payload),
                vapid_private_key=vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{admin_email}",
                },
            )
        except WebPushException as ex:
            logger.error("Error sending push notification to %s: %s", subscription.endpoint, repr(ex))


@receiver(post_save, sender=Order)
def send_order_ready_email(sender, instance, created, **kwargs):
    if not created and instance.status in ("ready", "Ready for Pickup"):
        subject = "Your Order is Ready!"
        message = f"Hi {instance.user.username}, your order #{instance.id} is ready for pickup."
        recipient = instance.user.email
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER

        if recipient:
            send_mail(
                subject,
                message,
                from_email,
                [recipient],
                fail_silently=True,
            )