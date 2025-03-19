from django.shortcuts import render, redirect, get_object_or_404
from main.models import Product  # Assuming you have a product app
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.models import CartItem,Coupon




def cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    
    for item in cart_items:
        item.subtotal = item.price * item.quantity  # ✅ Calculate subtotal per row

    total_cart_price = sum(item.subtotal for item in cart_items)  # ✅ Total cart price

    # ✅ Check if there's a discount applied
    discount_amount = request.session.get("discount_amount", 0)
    final_total = total_cart_price - discount_amount

    context = {
        'cart_items': cart_items,
        'total_cart_price': total_cart_price,
        'discount_amount': discount_amount,
        'final_total': final_total,
    }
    return render(request, 'shop/cart.html', context)


@login_required(login_url='/user_login/') 
def cartadd(request, product_id): 
    cart = request.session.get('cart', {})

    # Fetch product or return error
    product = get_object_or_404(Product, id=product_id)

    # Update session cart
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

    # **Save to CartItem model**
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product_id=product,
        defaults={'name': product.name, 'price': product.price, 'quantity': 1, 'image_url': product.image.url if product.image else ""}
    )
    print(request.user)
    # If item already exists, update the quantity
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f"{product.name} added to cart!")
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
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()

    return redirect('cart:cart')  # Redirect to cart page



def update(request, item_id):
    if request.method == "POST":
        new_quantity = int(request.POST.get("quantity", 1))

        # ✅ Get the cart item
        cart_item = get_object_or_404(CartItem, id=item_id)
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
        cart_items = CartItem.objects.filter(user=user)  # ✅ Get all cart items

        if not cart_items.exists():
            messages.error(request, "❌ Your cart is empty.")
            return redirect("cart")

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)

            # ✅ Check if the coupon is valid for the user's role
            if coupon.valid_for == user.role:
                discount_percentage = coupon.discount_percentage / 100
                total_price = sum(item.total_price for item in cart_items)  # ✅ Total cart price

                discount_amount = total_price * discount_percentage  # ✅ Calculate discount
                final_total = total_price - discount_amount  # ✅ New total after discount

                # ✅ Store coupon in session (since CartItem doesn't have a total field)
                request.session["discount_amount"] = discount_amount
                request.session["coupon_code"] = coupon.code

                messages.success(
                    request,
                    f"🎉 '{coupon_code}' applied! You saved ${discount_amount:.2f}."
                )
            else:
                messages.error(request, "❌ This coupon is not valid for your role.")
        
        except Coupon.DoesNotExist:
            messages.error(request, "❌ Invalid coupon code.")

    return redirect("cart:cart")