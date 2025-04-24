# checkout/utils.py

from pywebpush import webpush, WebPushException
import json
from django.conf import settings
from main.models import WebPushSubscription  # adjust if it's in another app
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order


def send_push_notification(user, title, body=None):
    from pywebpush import webpush, WebPushException

    subscriptions = WebPushSubscription.objects.filter(user=user)
    order = user.order_set.last()
    order_id = order.id if order else "N/A"
    
    payload = {
        "title": title,
        "body": body or f"Your order #{order_id} is ready for pickup!",
    }

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,  # base64 format required!
                vapid_claims={
                    "sub": "mailto:nazeemdath.1@gmail.com"
                }
            )
        except WebPushException as ex:
            print(f"Error sending notification to {subscription.endpoint}: {repr(ex)}")



@receiver(post_save, sender=Order)
def send_order_ready_email(sender, instance, created, **kwargs):
    print(f"[DEBUG] Signal triggered for Order #{instance.id}")
    print(f"[DEBUG] created = {created}, status = {instance.status}")

    if not created and instance.status == 'ready':
        print(f"[DEBUG] Sending email for Order #{instance.id}")
        
        subject = 'Your Order is Ready!'
        message = f'Hi {instance.user.username}, your order #{instance.id} is ready for pickup.'
        recipient = instance.user.email
        

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    else:
        print(f"[DEBUG] No email sent. Status: {instance.status}, Created: {created}")