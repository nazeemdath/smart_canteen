from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

@csrf_exempt
def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        role = request.POST.get("role")  # Get role from form
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
       

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("signup")

        # Create user with role
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)
        user.save()

        messages.success(request, "Signup successful! You can now log in.")
        return redirect("login")  # Redirect to login page

    return render(request, "authentication/login.html")

@csrf_exempt
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("/")  # Redirect to main.html
        else:
            messages.error(request, "Invalid username or password")
            return redirect("login")

    return render(request, "authentication/login.html")  # Render login page

@login_required
def main_page(request):
    return render(request, "main.html")  # Main page after login


def logout_view(request):
    logout(request)  # Logs out the user
    return redirect('/')  # Redirect to the homepage (or any other page)
