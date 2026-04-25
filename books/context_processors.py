def cart_count(request):
    """Add cart count to all templates"""
    cart = request.session.get('cart', {})
    
    # Ensure cart is a dictionary
    if isinstance(cart, list):
        cart = {}
    
    count = sum(cart.values())
    
    return {'cart_count': count}