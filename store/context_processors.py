from .models import Cart
from django.db.models import Sum

def cart_renderer(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(customer=request.user)
        cart_count = cart_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return {
            'cart_items': cart_items,
            'cart_count': cart_count,
            'total_price' : total_price
        }
    return {
        'cart_items': [],
        'cart_count': 0,
        'total_price' : 0
    }

def notification_context(request):
    if request.user.is_authenticated:
        notifs = request.user.notifications.all()[:5]
        count = request.user.notifications.filter(is_read=False).count()
        return {
            'user_notifications': notifs,
            'unread_notifications_count': count
        }
    return {}