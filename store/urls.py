from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.welcome, name='welcome'), 
    path("home/", views.homepage, name='homepage'), 
    path('login/', auth_views.LoginView.as_view(template_name='login.html',extra_context={'user_type': 'Customer'}), name='login'),
    path('admin-login/', auth_views.LoginView.as_view(template_name='login.html',extra_context={'user_type': 'Admin'}), name='admin_login'),
    path('redirect/', views.login_redirect, name='login_redirect'),
    path("register", views.signup, name='register'),
    path('logout/', views.logout_view, name='logout'),

    
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout',views.checkout,name='checkout'),
    path('payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('orders/', views.order_history, name='order_history'),
    path('profile/', views.profile_page, name='profile'),

    path('dashboard/', views.admin_panel, name='admin_panel'),
    path('admin-panel/inventory/', views.inventory_list, name='inventory_list'),
    path('admin-panel/inventory/add/', views.manage_product, name='add_product'),
    path('admin-panel/inventory/edit/<slug:slug>/', views.manage_product, name='edit_product'),
    path('admin-panel/inventory/delete/<slug:slug>/', views.manage_product, name='delete_product'),
    path('admin-panel/verify-receipt/', views.pending_receipts_list, name='pending_receipts_list'),
    path('admin-panel/verify-receipt/<int:order_id>/', views.verify_receipt, name='verify_receipt'),
    path('admin-panel/manage-order/', views.manage_orders, name='manage_orders'),
    path('admin-panel/manage-order/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('admin-panel/reports/', views.sales_report_page, name='sales_report_page'),
    path('admin-panel/reports/download/', views.generate_pdf_report, name='generate_pdf_report'),

    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]