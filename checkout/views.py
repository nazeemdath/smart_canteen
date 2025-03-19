from django.shortcuts import render,redirect,get_object_or_404
from cart.models import CartItem
import razorpay
from django.conf import settings
from .models import Order
from cart.models import CartItem
from main.models import Product
from django.http import JsonResponse
import json
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt


def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)

    # Ensure total_price is calculated correctly
   # Ensure 'total_price' is correctly fetched
    total_cart_price = sum(item.total_price for item in cart_items if isinstance(item.total_price, (int, float)))
    print("Total Cart Price:", total_cart_price)
    # Ensure discount_amount is a number
    discount_amount = request.session.get("discount_amount", 0) or 0

    # Ensure final_total is not negative
    final_total = max(total_cart_price - discount_amount, 0)

    context = {
        "cart_items": list(cart_items),  # Convert QuerySet to a list
        "total_cart_price": total_cart_price,
        "discount_amount": discount_amount,
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

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            razorpay_order = client.order.create({
                "amount": int(total_price * 100),  # ✅ Convert to paise
                "currency": "INR",
                "payment_capture": 1
            })

            new_order.razorpay_order_id = razorpay_order["id"]
            new_order.save()

            # ✅ Render `payment.html` instead of returning JSON
            return render(request, "shop/payment.html", {
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "order_id": razorpay_order["id"],
                "amount": int(total_price * 100),  # ✅ Send amount in paise
                "currency": "INR",
                # "csrf_token": get_token(request),  # Ensure CSRF token is passed
            })

        except razorpay.errors.RazorpayError as e:
            print(f"Razorpay Error: {e}")
            return JsonResponse({"error": "Payment processing failed. Please try again."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

# def payment_success(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         order_id = data.get("order_id")
#         payment_id = data.get("payment_id")

#         try:
#             order = Order.objects.get(razorpay_order_id=order_id)
#             order.razorpay_payment_id = payment_id
#             order.status = "Paid"
#             order.save()

#             return JsonResponse({"message": "Payment successful"})
#         except Order.DoesNotExist:
#             return JsonResponse({"error": "Order not found"}, status=400)
#     return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt  # 🚨 Use only for webhook security checks (Ensure additional security)
def payment_success(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        # ✅ Parse JSON data from request body
        data = json.loads(request.body)
        order_id = data.get("order_id")
        payment_id = data.get("payment_id")

        if not order_id or not payment_id:
            return JsonResponse({"error": "Invalid payment data"}, status=400)

        # ✅ Verify payment with Razorpay API
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_details = client.payment.fetch(payment_id)

        if payment_details.get("status") != "captured":
            return JsonResponse({"error": "Payment verification failed"}, status=400)

        # ✅ Fetch and update the order
        order = get_object_or_404(Order, razorpay_order_id=order_id)
        order.status = "Completed"
        order.razorpay_payment_id = payment_id
        order.save()

        # ✅ Reduce stock for ordered products
        cart_items = CartItem.objects.filter(user=order.user)
        for item in cart_items:
            product = item.product_id  # `product` is a ForeignKey to Product model
            if product.stock >= item.quantity:
                product.stock -= item.quantity  # Reduce stock
                product.save()

        # ✅ Clear the user's cart
        cart_items.delete()

        # ✅ Generate a token
        token = f"ORD{order.id}{order.user.id:04d}"

        # ✅ Send an email confirmation
        send_mail(
            "Order Confirmation",
            f"Your order has been placed successfully!\nYour token number: {token}",
            settings.EMAIL_HOST_USER,
            [order.user.email],
            fail_silently=True,
        )

        return JsonResponse({"success": True, "message": "Payment successful!", "token": token})

    except Exception as e:
        print("Payment verification error:", e)
        return JsonResponse({"error": "Internal server error"}, status=500)

def order_confirmation(request):
    return render(request, "shop/order_confirmation.html")