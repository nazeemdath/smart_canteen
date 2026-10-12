import json
import logging
from decimal import Decimal

import razorpay
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from cart.models import CartItem, Coupon
from main.models import Product
from .models import Feedback, Order

logger = logging.getLogger(__name__)


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user, order__isnull=True)

    # If cart is empty, return zero values
    if not cart_items.exists():
        request.session.pop("discount_amount", None)
        request.session.pop("coupon_code", None)
        request.session.pop("final_total", None)
        request.session.modified = True
        return render(
            request,
            "shop/checkout.html",
            {
                "cart_items": [],
                "total_cart_price": 0,
                "discount_amount": 0,
                "final_total": 0,
            },
        )

    # Stock validation check
    for item in cart_items:
        if item.product_id.stock < item.quantity:
            messages.warning(
                request,
                f"Sorry, only {item.product_id.stock} item(s) left for '{item.product_id.name}'. Please update your cart.",
            )
            return redirect("cart:cart")

    # Calculate subtotal per item
    for item in cart_items:
        item.subtotal = Decimal(item.price) * item.quantity

    # Calculate total cart price (before discount)
    total_cart_price = sum(item.subtotal for item in cart_items)

    # Retrieve discount details
    discount_amount = Decimal(str(request.session.get("discount_amount", 0)))
    applied_coupon = request.session.get("coupon_code")

    total_discount = Decimal(0)

    if applied_coupon:
        try:
            coupon = Coupon.objects.get(code=applied_coupon, active=True)
            for item in cart_items:
                if item.product_id in coupon.products.all():
                    item_discount = (item.subtotal * Decimal(coupon.discount_percentage)) / Decimal(100)
                    item.discounted_price = max(item.subtotal - item_discount, Decimal(0))
                    total_discount += item_discount
                else:
                    item.discounted_price = item.subtotal
        except Coupon.DoesNotExist:
            request.session.pop("discount_amount", None)
            request.session.pop("coupon_code", None)
            total_discount = Decimal(0)

    total_discount = min(total_discount, total_cart_price)
    final_total = max(total_cart_price - total_discount, Decimal(0))

    request.session["discount_amount"] = float(total_discount)
    request.session["final_total"] = float(final_total)
    request.session.modified = True

    context = {
        "cart_items": cart_items,
        "total_cart_price": total_cart_price,
        "discount_amount": total_discount,
        "final_total": final_total,
    }

    return render(request, "shop/checkout.html", context)


@login_required
def initiate_payment(request):
    if request.method == "POST":
        total_price = request.POST.get("total_cart_price", "0")

        try:
            total_price = float(total_price)
        except ValueError:
            return JsonResponse({"error": "Invalid total price"}, status=400)

        if total_price < 1:
            return JsonResponse({"error": "Order amount must be at least ₹1"}, status=400)

        new_order = Order.objects.create(
            user=request.user,
            order_total=total_price,
            status="Pending",
        )

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID or "rzp_test_placeholder", settings.RAZORPAY_KEY_SECRET or "rzp_secret_placeholder")
        )

        try:
            razorpay_order = client.order.create({
                "amount": int(total_price * 100),  # Convert to paise
                "currency": "INR",
                "payment_capture": 1,
            })

            new_order.razorpay_order_id = razorpay_order["id"]
            new_order.save()

            return render(
                request,
                "shop/payment.html",
                {
                    "razorpay_key": settings.RAZORPAY_KEY_ID,
                    "order_id": razorpay_order["id"],
                    "amount": int(total_price * 100),
                    "currency": "INR",
                },
            )

        except razorpay.errors.RazorpayError as e:
            logger.error("Razorpay Error: %s", repr(e))
            return JsonResponse({"error": "Payment processing failed. Please try again."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def payment_success(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get("order_id")
        payment_id = data.get("payment_id")

        if not order_id or not payment_id:
            return JsonResponse({"error": "Invalid payment data"}, status=400)

        # Verify payment with Razorpay API
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID or "rzp_test_placeholder", settings.RAZORPAY_KEY_SECRET or "rzp_secret_placeholder")
        )
        payment_details = client.payment.fetch(payment_id)

        if payment_details.get("status") != "captured":
            return JsonResponse({"error": "Payment verification failed"}, status=400)

        order = get_object_or_404(Order, razorpay_order_id=order_id)

        # Ensure user ownership if request is authenticated
        if request.user.is_authenticated and order.user != request.user:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        order.status = "Paid"
        order.razorpay_payment_id = payment_id
        order.save()

        # Reduce stock for ordered products
        cart_items = CartItem.objects.filter(user=order.user, order__isnull=True)
        for item in cart_items:
            product = item.product_id
            if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()
            item.order = order
            item.save()

        # Clear coupon discount session data
        request.session.pop("discount_amount", None)
        request.session.pop("coupon_code", None)
        request.session.pop("final_total", None)
        request.session.modified = True

        token = f"ORD{order.id}{order.user.id:04d}"
        request.session["order_token"] = token
        order.token_number = token
        order.save()

        # Send confirmation email
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        if order.user.email:
            send_mail(
                "Order Confirmation",
                f"Your order has been placed successfully!\nYour token number: {token}",
                from_email,
                [order.user.email],
                fail_silently=True,
            )

        return JsonResponse({"success": True, "message": "Payment successful!"})

    except Exception as e:
        logger.error("Payment verification error: %s", repr(e))
        return JsonResponse({"error": "Internal server error"}, status=500)


def order_confirmation(request):
    token = request.session.get("order_token", "N/A")
    return render(request, "shop/order_confirmation.html", {"order_token": token})


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["rating", "comment"]


@login_required
def submit_feedback(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if Feedback.objects.filter(order=order).exists():
        return redirect("profile")

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.order = order
            feedback.save()
            return redirect("profile")
    else:
        form = FeedbackForm()

    return render(request, "shop/feedback_form.html", {"form": form, "order": order})


def testimonials(request):
    feedbacks = Feedback.objects.all().order_by("-created_at")
    return render(request, "index.html", {"feedbacks": feedbacks})
