import logging
from django import forms
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .email_verification import send_verification_email, email_delivery_error
logger = logging.getLogger(__name__)


from .models import *
from .forms import *
import io
from datetime import timedelta
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db.models import Sum, Avg, Count, F, Q
from django.db.models.functions import ExtractWeekDay
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404


# Create your views here.
def welcome(request):
    return render (request,"welcome.html")

def get_products(category, sort='default'):
    products = Product.objects.filter(
        category__iexact=category
    ).annotate(
        avg_rating=Avg('feedbacks__rating'),
        review_count=Count(
            'feedbacks',
            distinct=True
        ),
        total_sold=Sum(
            'orderitem__quantity',
            filter=Q(
                orderitem__order__payment_status='VERIFIED'
            )
        )
    )

    if sort == 'best_seller':
        products = products.order_by(
            '-total_sold',
            '-avg_rating'
        )

    elif sort == 'top_rating':
        products = products.order_by(
            '-avg_rating',
            '-review_count'
        )

    elif sort == 'price_low':
        products = products.order_by('price')

    elif sort == 'price_high':
        products = products.order_by('-price')

    return products

def homepage(request):
    sort = request.GET.get('sort', 'default')

    context = {
        'bawal': get_products('bawal', sort),
        'shawl': get_products('shawl', sort),
        'current_sort': sort,
    }

    return render(request, 'homepage.html', context)

def filter_products(request):
    sort = request.GET.get('sort', 'default')

    context = {
        'bawal': get_products('bawal', sort),
        'shawl': get_products('shawl', sort),
    }

    return render(request, 'product_grid.html', context)

def is_cust(user):
    return user.groups.filter(name='Customer').exists()

@login_required
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.annotate(
            avg_rating=Avg('feedbacks__rating'),
            review_count=Count('feedbacks')
        ),
        slug=slug
    )

    feedbacks = product.feedbacks.all().order_by('-created_at')
    
    context = {
        'product': product,
        'feedbacks': feedbacks,
    }
    return render(request, 'product_detail.html', context)

def login_redirect(request):
    if request.user.groups.filter(name='Customer').exists():
        return redirect('homepage')
    elif request.user.groups.filter(name='Admin').exists():
        return redirect('admin_panel')
    else:
        return redirect('login')

def logout_view(request):
    if request.user.groups.filter(name='Admin').exists():
        destination = 'admin_login'
    else:
        destination = 'homepage'
    
    logout(request)
    return redirect(destination)

def signup(request):

    if request.method == 'POST':

        form = CustomerSignupForm(request.POST)

        if form.is_valid():

            try:
                with transaction.atomic():

                    # Create User without immediately activating it.
                    user = form.save(commit=False)

                    user.set_password(
                        form.cleaned_data['password']
                    )

                    user.first_name = form.cleaned_data['full_name']
                    user.email = form.cleaned_data['email'].strip().lower()

                    # IMPORTANT:
                    # Customer cannot login until email is verified.
                    user.is_active = False

                    user.save()

                    # Create Customer profile.
                    Customer.objects.create(
                        user=user,
                        phone=form.cleaned_data['phone']
                    )

                    # Create/get Customer group.
                    group, _ = Group.objects.get_or_create(
                        name='Customer'
                    )

                    user.groups.add(group)

                    # Send verification email.
                    send_verification_email(
                        request,
                        user
                    )

                    messages.success(
                        request,
                        "Registration successful! "
                        "A verification email has been sent to "
                        f"{user.email}. Please check your inbox."
                    )

                    return redirect('login')

            except Group.DoesNotExist:

                messages.error(
                    request,
                    "User group configuration error. "
                    "Please contact admin."
                )

            except DatabaseError:

                messages.error(
                    request,
                    "A database error occurred. "
                    "Please try again later."
                )

            except Exception as e:

                logger.exception(
                    "Customer signup verification email failed"
                )

                messages.error(
                    request,
                    email_delivery_error(e)
                )

    else:
        form = CustomerSignupForm()

    return render(
        request,
        'customer/signup.html',
        {'form': form}
    )


def verify_email(request, uidb64, token):
    """
    Verify customer's email address.

    If the token is valid, the user's is_active field is changed
    from False to True.
    """

    try:
        uid = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(pk=uid)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):
        user = None

    if user is not None and default_token_generator.check_token(
        user,
        token
    ):
        if user.is_active:
            messages.info(
                request,
                "Your email has already been verified. You can login."
            )
        else:
            user.is_active = True
            user.save(
                update_fields=['is_active']
            )

            messages.success(
                request,
                "Your email has been verified successfully! "
                "You can now login."
            )

        return redirect('login')

    messages.error(
        request,
        "The verification link is invalid or has expired."
    )

    return redirect('login')


def resend_verification(request):
    if request.method == 'POST':
        form = forms.Form(request.POST)
        form.fields['email'] = forms.EmailField()
        if form.is_valid():
            user = User.objects.filter(
                email__iexact=form.cleaned_data['email'], is_active=False,
                customer__isnull=False,
            ).first()
            if user and cache.add(f'verification-resend-{user.pk}', True, 60):
                try:
                    send_verification_email(request, user)
                except Exception:
                    cache.delete(f'verification-resend-{user.pk}')
                    logger.exception('Verification resend failed')
                    messages.error(request, 'Email delivery is temporarily unavailable. Please try again later.')
                    return redirect('login')
            messages.info(request, 'If this email belongs to an unverified account, a verification link has been sent. Check your inbox and spam folder. Please wait a minute before requesting another link.')
        else:
            messages.error(request, 'Please enter a valid email address.')
    return redirect('login')


@login_required
@user_passes_test(is_cust, login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(customer=request.user, product=product)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    cart_items = Cart.objects.filter(customer=request.user)

    cart_count = sum(item.quantity for item in cart_items)
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    html = render_to_string('cart_dropdown_content.html', {
        'cart_items': cart_items,
        'cart_count': cart_count,
        'total_price': total_price, 
    }, request=request) 
    
    return JsonResponse({
        'status': 'success', 
        'total_items': cart_count,
        'cart_html': html
    })


@login_required
def update_cart(request, cart_id, action):
    item = get_object_or_404(Cart, id=cart_id, customer=request.user)
    
    if action == 'increment':
        item.quantity += 1
        item.save()
    elif action == 'decrement':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    elif action == 'remove':
        item.delete()

    cart_items = Cart.objects.filter(customer=request.user)
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    cart_count = cart_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    html = render_to_string('cart_dropdown_content.html', {
        'cart_items': cart_items,
        'cart_count': cart_count,
        'total_price': total_price,
        'user': request.user 
    }, request=request)

    return JsonResponse({
        'status': 'success',
        'total_items': cart_count,
        'cart_html': html
    })


@login_required
def checkout(request):
    cart_items = Cart.objects.filter(customer=request.user)
    if not cart_items:
        return redirect('homepage')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                form.save_customer_data(request.user)

                state = request.POST.get('state')
                shipping_fee = 15.00 if state in ["Sabah", "Sarawak"] else 5.00
                final_total = float(total_price) + shipping_fee

                order = Order.objects.create(
                    customer=request.user,
                    total_price=final_total,
                    payment_status='UNVERIFIED',
                    order_status='PENDING',
                    admin_note=f"Shipping to {state}. Base: RM{total_price} + Ship: RM{shipping_fee}"
                )

                for item in cart_items:
                    if item.product.stock < item.quantity:
                        return render(request, 'customer/checkout.html', {
                            'form': form, 'cart_items': cart_items, 'total_price': total_price,
                            'error': f"Sorry, {item.product.name} just went out of stock."
                        })

                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_at_purchase=item.product.price
                    )
                    
                    item.product.stock -= item.quantity
                    item.product.save()

                cart_items.delete()

                return redirect('payment_page', order_id=order.id)
    else:
        try:
            customer = request.user.customer 
            initial_data = {
                'full_name': f"{request.user.first_name} {request.user.last_name}",
                'phone': customer.phone,
                'address': customer.address,
            }
        except:
            initial_data = {'full_name': request.user.get_full_name()}
            
        form = CheckoutForm(initial=initial_data)

    return render(request, 'customer/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price
    })

@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if request.method == 'POST' and request.FILES.get('receipt'):
        order.receipt = request.FILES['receipt']
        order.status = 'Pending'
        order.save()
        return redirect('payment_success', order_id=order.id)

    return render(request, 'customer/payment.html', {'order': order})

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'customer/payment_success.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user, payment_status='UNVERIFIED')
    
    with transaction.atomic():
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        order.delete()
        
    messages.info(request, "Order successfully cancelled. Your items are back in stock.")
    return redirect('homepage')

@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).order_by('-created_at').prefetch_related('items__product')
    
    return render(request, 'customer/order_history.html', {'orders': orders})

@login_required
def profile_page(request):
    # Ensure the customer profile exists
    customer = get_object_or_404(Customer, user=request.user)
    
    if request.method == 'POST':
        # Pass both instances so the form knows who is requesting the update
        form = ProfileUpdateForm(
            request.POST, 
            instance=request.user, 
            customer_instance=customer
        )
        
        if form.is_valid():
            # 1. Update User Model
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['full_name']
            user.email = form.cleaned_data['email']
            user.save()
            
            # 2. Update Customer Model
            customer.phone = form.cleaned_data['phone']
            customer.address = form.cleaned_data['address']
            customer.save()
            
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileUpdateForm(instance=request.user, customer_instance=customer)
    
    return render(request, 'customer/profile.html', {'form': form})

############################ customer submit feedback #########################

@login_required
def submit_feedback(request, order_id):
    item = get_object_or_404(OrderItem, id=order_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message') or request.POST.get('comment')
        rating_val = request.POST.get('rating', 5)
        
        if message_text and message_text.strip():
            Feedback.objects.create(
                customer=request.user,
                order_item=item,
                product=item.product,
                rating=int(rating_val),
                message=message_text.strip(),
                category='product'
            )
            messages.success(request, "Feedback submitted successfully!")
        else:
            messages.error(request, "Feedback cannot be empty.")
            
    return redirect('order_history')

@login_required
def submit_all_feedback(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == 'POST':
        submitted_count = 0

        for item in order.items.all():
            if hasattr(item, 'feedback') or item.feedback_set.exists():
                continue

            rating_val = request.POST.get(f'rating_{item.id}')
            message_text = request.POST.get(f'message_{item.id}', '').strip()

            if message_text or rating_val:
                Feedback.objects.create(
                    customer=request.user,
                    order_item=item,
                    product=item.product,
                    rating=int(rating_val) if rating_val else 5,
                    message=message_text if message_text else "No written comment.",
                    category='product'
                )
                submitted_count += 1

        if submitted_count > 0:
            messages.success(request, f"Successfully submitted {submitted_count} review(s)!")
        else:
            messages.warning(request, "No new reviews were filled in.")

    return redirect('order_history')

@login_required
def view_feedback(request):
    if not request.user.is_staff:
        return redirect('homepage')
    feedbacks = Feedback.objects.all().order_by('-created_at')
    return render(request, 'admin/view_feedback.html', {'feedbacks': feedbacks})

@login_required
def edit_user_feedback(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    if feedback.customer != request.user:
        messages.error(request, "You can only edit your own feedback.")
        return redirect('order_history')
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        rating_val = request.POST.get('rating')
        
        if message_text:
            feedback.message = message_text.strip()
        if rating_val:
            feedback.rating = int(rating_val)
            
        feedback.save()
        messages.success(request, "Feedback updated successfully!")
        return redirect('order_history')
            
    return render(request, 'customer/edit_feedback.html', {
        'feedback': feedback,
        'item': feedback.order_item  
    })

@login_required
def delete_user_feedback(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    if feedback.customer == request.user:
        feedback.delete()
        messages.success(request, "Feedback deleted successfully!")
    else:
        messages.error(request, "You can only delete your own feedback.")
    return redirect('order_history')

#### end of customer submit feedback


#ADMIN VIEWS
def is_admin(user):
    return user.groups.filter(name='Admin').exists() or user.is_superuser

@login_required
@user_passes_test(is_admin, login_url='admin_login')
def admin_panel(request):
    unverified_payments = Order.objects.filter(payment_status='UNVERIFIED').count()
    pending_orders = Order.objects.filter(order_status='PENDING',payment_status='VERIFIED').count()

    customer = User.objects.filter(groups="1").count()

    low_stock_threshold = 5
    low_stock_items = Product.objects.filter(stock__lt=low_stock_threshold).count()

    now = timezone.now()

    month_revenue = Order.objects.filter(
        payment_status='VERIFIED',
        created_at__year=now.year,
        created_at__month=now.month
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    context = {
        'unverified_payments': unverified_payments,
        'low_stock_count': low_stock_items,
        'month_revenue': month_revenue,
        'pending_orders' : pending_orders,
        'cust': customer
    }
    return render(request, 'admin/admin_panel.html', context)


@login_required
def inventory_list(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'admin/inventory_list.html', {'products': products})

@login_required
def manage_product(request, slug=None):
    instance = get_object_or_404(Product, slug=slug) if slug else None
    
    if request.method == 'POST':
        if 'delete_product' in request.POST and instance:
            product_name = instance.name
            instance.delete()
            messages.success(request, f"Product '{product_name}' deleted successfully.")
            return redirect('inventory_list')

        form = ProductForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Product saved successfully.")
            return redirect('inventory_list')
    else:
        form = ProductForm(instance=instance)
        
    return render(request, 'admin/product_form.html', {
        'form': form,
        'edit_mode': instance is not None
    })

@login_required
def verify_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note')
        
        if action == 'approve':
            order.payment_status = 'VERIFIED'
            order.admin_note = admin_note
            order.save()
            messages.success(request, f"Payment for Order #{order.id} approved.")
            Notification.objects.create(
                user=order.customer,
                message=f"Your payment for Order #{order.id} has been verified! Thank you."
            )
            return redirect('pending_receipts_list')
            
        elif action == 'reject':
            order.payment_status = 'REJECTED'
            order.admin_note = admin_note
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            order.save()
            messages.error(request, f"Payment for Order #{order.id} rejected.")
            Notification.objects.create(
                user=order.customer,
                message=f"Your payment for Order #{order.id} is rejected. See further details on order history."
            )
            return redirect('pending_receipts_list')

    return render(request, 'admin/verify_receipt.html', {'order': order})

@login_required
def pending_receipts_list(request):
    orders = Order.objects.filter(payment_status='UNVERIFIED').exclude(receipt='').select_related('customer').order_by('-created_at')
    
    return render(request, 'admin/pending_receipts.html', {
        'orders': orders
    })

@login_required
def manage_orders(request):
    base_orders = Order.objects.filter(payment_status='VERIFIED').prefetch_related('items__product')

    context = {
        'pending_orders': base_orders.filter(order_status='PENDING'),
        'packed_orders': base_orders.filter(order_status='PACKED'),
        'shipped_orders': base_orders.filter(order_status='SHIPPED'),
    }
    return render(request, 'admin/manage_orders.html', context)

@login_required
def update_order_status(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)

        order.admin_note = request.POST.get('admin_note', order.admin_note)
        new_status = request.POST.get('new_status')
        
        if new_status in dict(Order.ORDER_STATUS):
            order.order_status = new_status
            order.save()
            messages.success(request, f"Order #{order.id} updated.")

            status_messages = {
                "PACKED": f"Your package for Order #{order.id} is packed and ready to ship!",
                "SHIPPED": f"Your package for Order #{order.id} has been shipped out! Tracking number is in order details",
                "DELIVERED": f"Yay! Your package for Order #{order.id} has been delivered!",
            }

            if new_status in status_messages:
                Notification.objects.create(
                    user=order.customer,
                    message=status_messages[new_status]
                )
        
        return redirect('manage_orders')

def sales_report_page(request):
    return render(request, 'admin/sales_report_selector.html')

def generate_pdf_report(request):
    report_type = request.GET.get('report_type', 'weekly') 
    
    now = timezone.now()
    
    if report_type == 'monthly':
        start_date = now - timedelta(days=30)
        title = "Monthly Sales Report"
    else:
        start_date = now - timedelta(days=7)
        title = "Weekly Sales Report"

    orders = Order.objects.filter(
        payment_status='VERIFIED',
        created_at__gte=start_date
    ).order_by('-created_at')

    total_revenue = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    order_count = orders.count()

    top_products = OrderItem.objects.filter(order__in=orders) \
        .values('product__name') \
        .annotate(total_qty=Sum('quantity')) \
        .order_by('-total_qty')[:5] 
    
    avg_order_value = orders.aggregate(Avg('total_price'))['total_price__avg'] or 0
    busiest_day_num = orders.annotate(weekday=ExtractWeekDay('created_at')) \
                            .values('weekday') \
                            .annotate(count=Count('id')) \
                            .order_by('-count').first()
    
    days = {1:'Sunday', 2:'Monday', 3:'Tuesday', 4:'Wednesday', 5:'Thursday', 6:'Friday', 7:'Saturday'}
    busiest_day = days.get(busiest_day_num['weekday']) if busiest_day_num else "N/A"

    context = {
        'title': title,
        'orders': orders,
        'total_revenue': total_revenue,
        'order_count': order_count,
        'generated_at': now,
        'top_products': top_products,
        'avg_order_value': round(avg_order_value, 2),
        'busiest_day': busiest_day,
        'report_type': report_type.title() if report_type else "Report",
    }

    try:
        template = get_template('admin/sales_report_pdf.html')
        html = template.render(context)
        result = io.BytesIO()
        
        pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"HAJAZ_Report_{report_type}_{now.strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except Exception as e:
        return HttpResponse(f"System Error: {str(e)}", status=500)
    
    return HttpResponse("Error generating PDF", status=400)

@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)