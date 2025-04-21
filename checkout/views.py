from django.shortcuts import render,redirect,get_object_or_404
from cart.models import CartItem
import razorpay
from django.conf import settings
from .models import Order
from cart.models import CartItem,Coupon
from main.models import Product
from django.http import JsonResponse
import json
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django import forms
from .models import Feedback
from decimal import Decimal  
from django.contrib import messages


def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user, order__isnull=True)

    # ✅ If cart is empty, return zero values
    if not cart_items.exists():
        request.session.pop("discount_amount", None)
        request.session.pop("coupon_code", None)
        request.session.pop("final_total", None)
        request.session.modified = True  
        return render(request, "shop/checkout.html", {
            "cart_items": [],
            "total_cart_price": 0,
            "discount_amount": 0,
            "final_total": 0
        })

    # ✅ Stock validation check
    for item in cart_items:
        if item.product_id.stock < item.quantity:
            messages.warning(request, f"Sorry, only {item.product_id.stock} item(s) left for '{item.product_id.name}'. Please update your cart.")
            return redirect("cart:cart")  # 🔁 Redirect to cart page if stock insufficient

    # ✅ Calculate subtotal per item
    for item in cart_items:
        item.subtotal = Decimal(item.price) * item.quantity  

    # ✅ Calculate total cart price (before discount)
    total_cart_price = sum(item.subtotal for item in cart_items)  

    # ✅ Retrieve discount details
    discount_amount = Decimal(request.session.get("discount_amount", 0))
    applied_coupon = request.session.get("coupon_code")

    # ✅ Initialize discount calculation
    total_discount = Decimal(0)

    if applied_coupon:
        try:
            coupon = Coupon.objects.get(code=applied_coupon)
            for item in cart_items:
                if item.product_id in coupon.products.all():
                    # ✅ Apply discount proportionally based on quantity
                    item_discount = (item.subtotal * Decimal(coupon.discount_percentage)) / Decimal(100)
                    item.discounted_price = max(item.subtotal - item_discount, Decimal(0))
                    total_discount += item_discount  
                else:
                    item.discounted_price = item.subtotal  

        except Coupon.DoesNotExist:
            request.session.pop("discount_amount", None)
            request.session.pop("coupon_code", None)
            discount_amount = Decimal(0)

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
        order.status = "paid"
        order.razorpay_payment_id = payment_id
        order.save()

        # ✅ Reduce stock for ordered products
        cart_items = CartItem.objects.filter(user=order.user)
        for item in cart_items:
            product = item.product_id  # `product` is a ForeignKey to Product model
            if product.stock >= item.quantity:
                product.stock -= item.quantity  # Reduce stock
                product.save()
            item.order = order  # ✅ Link cart item to this order
            item.save()

            
     
        
     # ✅ Clear the coupon discount session data
        request.session.pop("discount_amount", None)
        request.session.pop("coupon_code", None)
        request.session.pop("final_total", None)
        request.session.modified = True  # Ensure session updates

        # ✅ Generate a token
        token = f"ORD{order.id}{order.user.id:04d}"
        request.session["order_token"] = token
        order.token_number = token  # ✅ Save it in the Order table
        order.save()
        

        # ✅ Send an email confirmation
        send_mail(
            "Order Confirmation",
            f"Your order has been placed successfully!\nYour token number: {token}",
            settings.EMAIL_HOST_USER,
            [order.user.email],
            fail_silently=True,
        )

        return JsonResponse({"success": True, "message": "Payment successful!",})

    except Exception as e:
        print("Payment verification error:", e)
        return JsonResponse({"error": "Internal server error"}, status=500)

def order_confirmation(request):
    token = request.session.get("order_token", "N/A")  # Retrieve token     
    return render(request, "shop/order_confirmation.html",{"order_token": token})


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'comment']



@login_required
def submit_feedback(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if feedback already exists for this order
    if Feedback.objects.filter(order=order).exists():
        return redirect("profile")  # Redirect if feedback already submitted

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.order = order
            feedback.save()
            return redirect("profile")  # Redirect after successful submission
    else:
        form = FeedbackForm()

    return render(request, "shop/feedback_form.html", {"form": form, "order": order})



def testimonials(request):
    feedbacks = list(Feedback.objects.all())  # Convert QuerySet to a list
    print("Feedbacks:", feedbacks)  # Debugging
    return render(request, "index.html", {"feedbacks": feedbacks})

