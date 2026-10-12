from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from cart.models import CartItem
from checkout.models import Order
from .forms import LoginForm, SignUpForm
from .models import CustomUser


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Signup successful! You can now log in.")
            return redirect("user_login")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
            return render(request, "authentication/signup.html", {"form": form})

    form = SignUpForm()
    return render(request, "authentication/signup.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)

                # Sync database cart with session after login
                cart_items = CartItem.objects.filter(user=user, order__isnull=True)
                request.session["cart"] = {
                    str(item.product_id): {
                        "id": str(item.product_id),
                        "name": item.name,
                        "price": float(item.price),
                        "quantity": item.quantity,
                        "image_url": item.image_url,
                    }
                    for item in cart_items
                }
                request.session.modified = True
                return redirect("/")
            else:
                messages.error(request, "Invalid login credentials.")
        else:
            messages.error(request, "Please enter both username and password.")

        return render(request, "authentication/login.html", {"form": form})

    form = LoginForm()
    return render(request, "authentication/login.html", {"form": form})


@login_required
def main_page(request):
    return render(request, "main.html")


def logout_view(request):
    logout(request)
    return redirect("/")


@login_required
def profile(request):
    user = request.user
    last_five_orders = Order.objects.filter(user=user).order_by("-created_at")[:5]

    context = {
        "user": user,
        "last_five_orders": last_five_orders,
    }
    return render(request, "profile.html", context)
