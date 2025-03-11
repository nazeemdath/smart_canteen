from django.shortcuts import render
from .models import Product

# Create your views here.
def samp(request):
    return render(request,'index.html')

def about(request):
    return render(request,'base.html')

def shop(request):
    products = Product.objects.all()
    cont = {'products':products}
    return render(request,'shop/shop.html', cont )