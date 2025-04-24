from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from cart.models import CartItem
from checkout.models import Order
import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError



@csrf_exempt
def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        flag = False

        # ✅ Password match check
        if password != confirm_password:
            messages.error(request, "Passwords do not match.", extra_tags="password_mismatch")
            flag = True

        # ✅ Username & email uniqueness check
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.", extra_tags="username_taken")
            flag = True
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already taken.", extra_tags="email_taken")
            flag = True

        # ✅ Password strength check using Django validator
        try:
            validate_password(password)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg, extra_tags="weak_password")
            flag = True

        # ✅ You can also add custom rules like:
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.", extra_tags="weak_password")
            flag = True
        if not re.search(r"[A-Z]", password):
            messages.error(request, "Password must include at least one uppercase letter.", extra_tags="weak_password")
            flag = True
        if not re.search(r"[a-z]", password):
            messages.error(request, "Password must include at least one lowercase letter.", extra_tags="weak_password")
            flag = True
        if not re.search(r"[0-9]", password):
            messages.error(request, "Password must include at least one digit.", extra_tags="weak_password")
            flag = True
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            messages.error(request, "Password must include at least one special character.", extra_tags="weak_password")
            flag = True

        if flag:
            return redirect("signup")

        # ✅ Create user
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)
        user.save()

        messages.success(request, "Signup successful! You can now log in.")
        return redirect("user_login")

    return render(request, "authentication/signup.html")


@csrf_exempt
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)

            # ✅ Sync database cart with session after login
            cart_items = CartItem.objects.filter(user=user)
            request.session['cart'] = {
                str(item.product_id): {
                    'id': str(item.product_id),
                    'name': item.name,
                    'price': item.price,
                    'quantity': item.quantity,
                    'image_url': item.image_url
                } for item in cart_items
            }

            request.session.modified = True  # Ensure session updates
            
            return redirect('/')  # Redirect to cart page after login
        else:
            messages.error(request, "Invalid login credentials")
    
    return render(request, "authentication/login.html")

@login_required
def main_page(request):
    return render(request, "main.html")  # Main page after login


def logout_view(request):
    logout(request)  # Logs out the user
    return redirect('/')  # Redirect to the homepage (or any other page)

    
@login_required
def profile(request):
    user = request.user
    last_five_orders = Order.objects.filter(user=user).order_by("-created_at")[:5]  # Get last 5 orders

    context = {
        "user": user,
        "last_five_orders": last_five_orders,
    }
    return render(request, "profile.html", context)

