from .cart import Cart

# create context processor so ur cart can work on all pages

def cart(request):
    #return.the default data from iur cart
    return {'cart': request.session.get('cart', {})}