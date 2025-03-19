class Cart:
    def __init__(self, request):
        self.session = request.session
        
        # Generate session key if it does not exist
        if not self.session.session_key:
            self.session.create()

        # Get the cart from session or create a new one
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}

        self.cart = cart

    def add(self, product, quantity=1):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)  # Convert to string for session storage

        if product_id in self.cart:
            self.cart[product_id]['quantity'] += quantity  # Update quantity
        else:
            self.cart[product_id] = {
                'name': product.name,
                'price': str(product.price),  # Store as string for JSON compatibility
                'quantity': quantity,
                'image_url': product.image.url if product.image else '',  # Store image URL
            }

        self.session.modified = True  # Save session changes
