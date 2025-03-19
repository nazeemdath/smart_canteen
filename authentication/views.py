from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from cart.models import CartItem

@csrf_exempt
def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")  # ✅ FIXED field name

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")  # ✅ Redirect using URL name

        # Check if username exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("signup")

        # Create user
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)
        user.save()

        messages.success(request, "Signup successful! You can now log in.")
        return redirect("user_login")  # ✅ Redirect to login page

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
