from django.contrib import admin

from .models import Product
admin.site.register(Product)
from.models import Customer
admin.site.register(Customer)
from.models import Admin
admin.site.register(Admin)
from.models import Cart
admin.site.register(Cart)
from.models import Order
admin.site.register(Order)
from.models import OrderItem
admin.site.register(OrderItem)
from .models import Feedback
admin.site.register(Feedback)