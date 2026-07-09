from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CheckoutForm, InventoryUpdateForm, LoginForm, OrderStatusForm, ProductForm, ProfileForm, RegistrationForm, ReturnRequestForm
from .models import CartItem, Order, OrderItem, Product, ProductImage, ReturnRequest


def staff_required(view_func):
    return user_passes_test(lambda user: user.is_authenticated and user.is_staff)(view_func)


def home(request):
    featured_products = Product.objects.filter(is_active=True).prefetch_related("images")[:8]
    categories = Product.objects.filter(is_active=True).values_list("category", flat=True).distinct().order_by("category")
    return render(request, "store/home.html", {"featured_products": featured_products, "categories": categories})


def product_list(request):
    products = Product.objects.filter(is_active=True).prefetch_related("images")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query))
    if category:
        products = products.filter(category=category)
    categories = Product.objects.filter(is_active=True).values_list("category", flat=True).distinct().order_by("category")
    return render(request, "store/product_list.html", {"products": products, "categories": categories, "selected_category": category, "query": query})


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related("images"), pk=pk, is_active=True)
    return render(request, "store/product_detail.html", {"product": product})


def register(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("store:home")
    return render(request, "registration/register.html", {"form": form})


@login_required
def cart(request):
    items = CartItem.objects.filter(user=request.user).select_related("product").prefetch_related("product__images")
    subtotal = sum(item.subtotal for item in items)
    return render(request, "store/cart.html", {"items": items, "subtotal": subtotal})


@login_required
def cart_add(request, product_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    quantity = int(request.POST.get("quantity", 1))
    item, created = CartItem.objects.get_or_create(user=request.user, product=product, defaults={"quantity": quantity})
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])
    messages.success(request, f"Added {product.name} to cart.")
    return redirect(request.POST.get("next") or product.get_absolute_url())


@login_required
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    if request.method == "POST":
        quantity = max(1, int(request.POST.get("quantity", 1)))
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        messages.success(request, "Cart updated.")
    return redirect("store:cart")


@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Item removed from cart.")
    return redirect("store:cart")


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")
    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("store:product_list")

    subtotal = sum(item.subtotal for item in cart_items)
    form = CheckoutForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        shipping_address = form.cleaned_data["shipping_address"]
        with transaction.atomic():
            for item in cart_items.select_for_update():
                product = Product.objects.select_for_update().get(pk=item.product_id)
                if product.stock_quantity < item.quantity:
                    messages.error(request, f"Not enough stock for {product.name}.")
                    return redirect("store:cart")

            order = Order.objects.create(user=request.user, shipping_address=shipping_address, total_amount=Decimal("0.00"))
            total = Decimal("0.00")
            for item in cart_items:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                OrderItem.objects.create(order=order, product=product, quantity=item.quantity, price_at_purchase=product.price)
                Product.objects.filter(pk=product.pk).update(stock_quantity=F("stock_quantity") - item.quantity)
                total += product.price * item.quantity
            order.total_amount = total
            order.save(update_fields=["total_amount"])
            cart_items.delete()
        messages.success(request, "Order placed successfully.")
        return redirect("store:order_detail", pk=order.pk)

    return render(request, "store/checkout.html", {"form": form, "items": cart_items, "subtotal": subtotal})


@login_required
def orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items__product", "items__product__images")
    return render(request, "store/orders.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items__product", "items__product__images"), pk=pk)
    if order.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden()
    return render(request, "store/order_detail.html", {"order": order, "fulfillment_steps": order.fulfillment_steps()})


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == "POST" and order.is_cancellable:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        for item in order.items.select_related("product"):
            Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)
        messages.success(request, "Order cancelled.")
    return redirect("store:order_detail", pk=order.pk)


@login_required
def return_requests(request):
    requests_qs = ReturnRequest.objects.filter(user=request.user).select_related("order_item__order", "order_item__product")
    return render(request, "store/returns.html", {"return_requests": requests_qs})


@login_required
def request_return(request, order_item_id):
    order_item = get_object_or_404(OrderItem.objects.select_related("order", "product"), pk=order_item_id, order__user=request.user)
    if hasattr(order_item, "return_request"):
        messages.info(request, "A return request already exists for this item.")
        return redirect("store:return_requests")
    form = ReturnRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return_request = form.save(commit=False)
        return_request.order_item = order_item
        return_request.user = request.user
        return_request.save()
        messages.success(request, "Return request submitted.")
        return redirect("store:return_requests")
    return render(request, "store/return_request.html", {"order_item": order_item, "form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("store:profile")
    order_stats = request.user.orders.aggregate(total_orders=Count("id"), delivered=Count("id", filter=Q(status=Order.Status.DELIVERED)), cancelled=Count("id", filter=Q(status=Order.Status.CANCELLED)))
    return_stats = request.user.return_requests.aggregate(total_returns=Count("id"), approved=Count("id", filter=Q(status=ReturnRequest.Status.APPROVED)), completed=Count("id", filter=Q(status=ReturnRequest.Status.COMPLETED)))
    order_history = request.user.orders.prefetch_related("items__product")[:5]
    return_history = request.user.return_requests.select_related("order_item__product")[:5]
    return render(request, "store/profile.html", {"form": form, "order_stats": order_stats, "return_stats": return_stats, "order_history": order_history, "return_history": return_history})


def _is_staff(user):
    return user.is_authenticated and user.is_staff


@staff_required
def staff_dashboard(request):
    context = {
        "total_products": Product.objects.count(),
        "total_customers": User.objects.filter(is_staff=False).count(),
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
        "delivered_orders": Order.objects.filter(status=Order.Status.DELIVERED).count(),
        "return_requests": ReturnRequest.objects.count(),
        "low_stock_products": Product.objects.filter(stock_quantity__lte=10, is_active=True).count(),
        "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:5],
        "recent_returns": ReturnRequest.objects.select_related("user", "order_item__product")[:5],
    }
    return render(request, "staff/dashboard.html", context)


@staff_required
def staff_products(request):
    products = Product.objects.all().prefetch_related("images")
    return render(request, "staff/products.html", {"products": products})


@staff_required
def staff_product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        _save_product_images(request, product)
        messages.success(request, "Product created.")
        return redirect("store:staff_products")
    return render(request, "staff/product_form.html", {"form": form, "title": "Add Product"})


@staff_required
def staff_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        _save_product_images(request, product)
        messages.success(request, "Product updated.")
        return redirect("store:staff_products")
    return render(request, "staff/product_form.html", {"form": form, "title": "Edit Product", "product": product})


def _save_product_images(request, product):
    images = request.FILES.getlist("images")
    existing_count = product.images.count()
    for index, image in enumerate(images, start=existing_count):
        ProductImage.objects.create(product=product, image=image, is_primary=(existing_count == 0 and index == 0), display_order=index)


@staff_required
def staff_product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_active = not product.is_active
        product.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Product status updated.")
    return redirect("store:staff_products")


@staff_required
def staff_inventory(request):
    products = Product.objects.all().order_by("name")
    return render(request, "staff/inventory.html", {"products": products, "inventory_form": InventoryUpdateForm()})


@staff_required
def staff_orders(request):
    orders = Order.objects.select_related("user").prefetch_related("items__product")
    return render(request, "staff/orders.html", {"orders": orders, "status_choices": Order.Status.choices})


@staff_required
def staff_order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("user").prefetch_related("items__product"), pk=pk)
    form = OrderStatusForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        new_status = form.cleaned_data["status"]
        workflow = [Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PACKED, Order.Status.SHIPPED, Order.Status.DELIVERED]
        current_index = workflow.index(order.status) if order.status in workflow else -1
        allowed_next = {order.status}
        if current_index >= 0 and current_index < len(workflow) - 1:
            allowed_next.add(workflow[current_index + 1])
        if order.status == Order.Status.CANCELLED and new_status != Order.Status.CANCELLED:
            messages.error(request, "Cancelled orders cannot be reopened.")
        elif new_status == Order.Status.CANCELLED and order.status in {Order.Status.SHIPPED, Order.Status.DELIVERED, Order.Status.CANCELLED}:
            messages.error(request, "Orders can only be cancelled before shipment.")
        elif new_status not in allowed_next and new_status != Order.Status.CANCELLED:
            messages.error(request, "Orders must move through the fulfillment workflow one step at a time.")
        else:
            form.save()
            messages.success(request, "Order status updated.")
            return redirect("store:staff_order_detail", pk=order.pk)
    return render(request, "staff/order_detail.html", {"order": order, "form": form, "fulfillment_steps": order.fulfillment_steps()})


@staff_required
def staff_returns(request):
    return_requests = ReturnRequest.objects.select_related("user", "order_item__product", "order_item__order")
    if request.method == "POST":
        return_request = get_object_or_404(ReturnRequest, pk=request.POST.get("return_id"))
        action = request.POST.get("action")
        if action == "approve":
            return_request.status = ReturnRequest.Status.APPROVED
            return_request.processed_at = timezone.now()
            return_request.save(update_fields=["status", "processed_at"])
            messages.success(request, "Return request approved.")
        elif action == "reject":
            return_request.status = ReturnRequest.Status.REJECTED
            return_request.processed_at = timezone.now()
            return_request.save(update_fields=["status", "processed_at"])
            messages.success(request, "Return request rejected.")
        elif action == "complete" and return_request.status in {ReturnRequest.Status.APPROVED, ReturnRequest.Status.REJECTED}:
            if return_request.status == ReturnRequest.Status.APPROVED:
                product = return_request.order_item.product
                Product.objects.filter(pk=product.pk).update(stock_quantity=F("stock_quantity") + return_request.order_item.quantity)
            return_request.status = ReturnRequest.Status.COMPLETED
            return_request.processed_at = timezone.now()
            return_request.save(update_fields=["status", "processed_at"])
            messages.success(request, "Return request completed.")
        return redirect("store:staff_returns")
    return render(request, "staff/returns.html", {"return_requests": return_requests})


@staff_required
def staff_customers(request):
    customers = User.objects.filter(is_staff=False).annotate(order_count=Count("orders"), return_count=Count("return_requests"))
    return render(request, "staff/customers.html", {"customers": customers})


@staff_required
def staff_customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    orders = customer.orders.prefetch_related("items__product")
    returns = customer.return_requests.select_related("order_item__product")
    stats = {
        "total_orders": orders.count(),
        "total_spent": orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00"),
        "open_returns": returns.filter(status__in=[ReturnRequest.Status.REQUESTED, ReturnRequest.Status.APPROVED]).count(),
    }
    return render(request, "staff/customer_detail.html", {"customer": customer, "orders": orders, "returns": returns, "stats": stats})
