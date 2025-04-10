from cart.models import CartItem

# create context processor so ur cart can work on all pages

def cart(request):
    #return.the default data from iur cart
    return {'cart': request.session.get('cart', {})}
def cart_count(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, order__isnull=True)
        return {"cart_count": cart_items.count()}
    return {"cart_count": 0}  # Default when user is not logged in