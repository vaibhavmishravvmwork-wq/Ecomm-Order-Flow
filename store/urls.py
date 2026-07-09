from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html", authentication_form=views.LoginForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("returns/", views.return_requests, name="return_requests"),
    path("returns/request/<int:order_item_id>/", views.request_return, name="request_return"),
    path("profile/", views.profile, name="profile"),
    path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/products/", views.staff_products, name="staff_products"),
    path("staff/products/new/", views.staff_product_create, name="staff_product_create"),
    path("staff/products/<int:pk>/edit/", views.staff_product_edit, name="staff_product_edit"),
    path("staff/products/<int:pk>/toggle/", views.staff_product_toggle, name="staff_product_toggle"),
    path("staff/inventory/", views.staff_inventory, name="staff_inventory"),
    path("staff/orders/", views.staff_orders, name="staff_orders"),
    path("staff/orders/<int:pk>/", views.staff_order_detail, name="staff_order_detail"),
    path("staff/returns/", views.staff_returns, name="staff_returns"),
    path("staff/customers/", views.staff_customers, name="staff_customers"),
    path("staff/customers/<int:pk>/", views.staff_customer_detail, name="staff_customer_detail"),
]
