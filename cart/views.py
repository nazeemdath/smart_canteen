from django.shortcuts import render, redirect, get_object_or_404
from main.models import Product  # Assuming you have a product app
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.models import CartItem,Coupon
from django.utils.timezone import now
from checkout.models import Order
from decimal import Decimal


@login_required
def cart(request):
    # ✅ Only include items not linked to any order
    cart_items = CartItem.objects.filter(user=request.user, order__isnull=True)

    if not cart_items.exists():
        request.session.pop("discount_amount", None)
        request.session.pop("coupon_code", None)
        request.session.pop("final_total", None)
        request.session.modified = True  # Ensure session updates
        return render(request, 'shop/cart.html', {'cart_items': [], 'total_cart_price': 0, 'discount_amount': 0, 'final_total': 0})


    # ✅ Calculate subtotal per item
    for item in cart_items:
        item.subtotal = Decimal(item.price) * item.quantity  # Ensure Decimal

    # ✅ Calculate total cart price (before discount)
    total_cart_price = sum(item.subtotal for item in cart_items)  

    # ✅ Retrieve discount amount from session (Convert to Decimal)
    discount_amount = Decimal(request.session.get("discount_amount", 0))
    applied_coupon = request.session.get("coupon_code")  # ✅ Correct session key

    # ✅ Initialize discount calculation
    total_discount = Decimal(0)

    if applied_coupon:
        try:
            # ✅ Get the coupon details
            coupon = Coupon.objects.get(code=applied_coupon)

            # ✅ Apply discount **only** to eligible products
            for item in cart_items:
                if item.product_id in coupon.products.all():
                    # ✅ Apply proportional discount
                    item_discount = item.subtotal * (Decimal(coupon.discount_percentage) / Decimal(100))
                    item.discounted_price = max(item.subtotal - item_discount, Decimal(0))
                    total_discount += item_discount  # Accumulate total discount
                else:
                    item.discounted_price = item.subtotal  # Keep original price for other products

        except Coupon.DoesNotExist:
            # ✅ If coupon is invalid, remove it from the session
            request.session.pop("discount_amount", None)
            request.session.pop("coupon_code", None)
            discount_amount = Decimal(0)

    # ✅ Ensure total discount does not exceed total price
    total_discount = min(total_discount, total_cart_price)

    # ✅ Final total after applying the discount
    final_total = max(total_cart_price - total_discount, Decimal(0))

    # ✅ Store the final total in session (convert Decimal to float)
    request.session["final_total"] = float(final_total)
    request.session.modified = True  # Ensure session updates

    context = {
        'cart_items': cart_items,
        'total_cart_price': total_cart_price,
        'discount_amount': total_discount,  # Show actual applied discount
        'final_total': final_total,
    }

    return render(request, 'shop/cart.html', context)



@login_required(login_url='/user_login/')
def cartadd(request, product_id): 
    cart = request.session.get('cart', {})

    # ✅ Fetch product
    product = get_object_or_404(Product, id=product_id)

    # ✅ Update session cart (optional if you’re still using it)
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {
            'id': str(product.id),  
            'name': product.name,
            'price': float(product.price),
            'quantity': 1,
            'image_url': product.image.url if product.image else "",  
        }

    request.session['cart'] = cart
    request.session.modified = True  

    # ✅ Check if CartItem exists for this user and product (not yet ordered)
    existing_item = CartItem.objects.filter(
        user=request.user,
        product_id_id=product.id,  # ✅ important fix
        order__isnull=True
    ).first()

    if existing_item:
        existing_item.quantity += 1
        existing_item.save()
    else:
        CartItem.objects.create(
            user=request.user,
            product_id_id=product.id,  # ✅ create using actual FK id
            quantity=1,
            price=product.price,
            name=product.name,
            image_url=product.image.url if product.image else "",
        )

    messages.success(request, f"{product.name} added to cart!",extra_tags="cart")
    return redirect('cart:cart')
def delete(request, item_id):
    """
    Remove a specific item from the cart (both session and database).
    """
    cart_data = request.session.get('cart', {})  # Get cart from session

    # Remove from session
    if str(item_id) in cart_data:
        del cart_data[str(item_id)]
        request.session['cart'] = cart_data
        request.session.modified = True

    # Remove from database
    cart_item = get_object_or_404(CartItem, id=item_id,user=request.user)
    cart_item.delete()
    remaining_items = CartItem.objects.filter(user=request.user).exists()

    if not remaining_items:
        # If no items left in cart, remove the discount from session
        if 'discount_amount' in request.session:
            del request.session['discount_amount']
            request.session.modified = True  # Mark session as updated

    return redirect('cart:cart')  # Redirect to cart page



def update(request, item_id):
    if request.method == "POST":
        new_quantity = int(request.POST.get("quantity", 1))

        # ✅ Get the cart item
        cart_item = get_object_or_404(CartItem, id=item_id,user=request.user)
        product = cart_item.product_id  # ForeignKey to Product

        # ✅ Check if requested quantity is within available stock
        if new_quantity > product.stock:
            messages.error(request, f"Only {product.stock} items available in stock.")
            return redirect("cart:cart")  # Redirect to cart page with error message

        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            cart_item.delete()  # Remove item if quantity is 0

        return redirect("cart:cart")  # Redirect to cart page

    return redirect("cart:cart")

def apply_coupon(request): 
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip().upper()
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        if not cart_items.exists():
            messages.error(request, "❌ Your cart is empty.")
            return redirect("cart:cart")

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)

            # ✅ Only apply to eligible products
            applicable_items = [item for item in cart_items if item.product_id in coupon.products.all()]

            if not applicable_items:
                messages.error(request, "⚠️ This coupon is not applicable to any product in your cart.")
                return redirect("cart:cart")

            # ✅ Validate coupon dates
            if not (coupon.valid_from <= now() <= coupon.valid_to):
                messages.error(request, "⏳ Coupon has expired.")
                return redirect("cart:cart")

            # ✅ Validate user role
            if coupon.valid_for != user.role:
                messages.error(request, "🚫 Coupon not valid for your role.")
                return redirect("cart:cart")

            # ✅ Convert discount percentage to Decimal
            discount_percentage = Decimal(coupon.discount_percentage) / Decimal(100)

            total_discount = Decimal(0)

            for item in applicable_items:
                if item.subtotal is None:
                    item.subtotal = Decimal(item.price) * item.quantity  # ✅ Ensure Decimal type
                    item.save()

                item_discount = item.subtotal * discount_percentage  # ✅ Both are Decimal now
                item.discounted_price = max(item.subtotal - item_discount, Decimal(0))
                item.save()

                total_discount += item_discount

            # ✅ Update session values
            total_price = sum(item.subtotal for item in cart_items)  # ✅ Ensure Decimal
            final_total = max(total_price - total_discount, Decimal(0))

            request.session["discount_amount"] = float(total_discount)  # Convert Decimal to float
            request.session["coupon_code"] = coupon.code
            request.session["final_total"] = float(final_total)  # Convert Decimal to float
            request.session.modified = True  

            messages.success(request, f"🎉 '{coupon_code}' applied! You saved ₹{total_discount:.2f}.")
        
        except Coupon.DoesNotExist:
            messages.error(request, "❌ Invalid coupon code.")

    return redirect("cart:cart")
@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        "order": order,
        "status":order.status
    }
    return render(request,'shop/track_order.html', context)

def cart_count(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)  # Adjust based on your Cart model
        return {"cart_count": cart_items.count()}
    return {"cart_count": 0}  # Default for unauthenticated users
