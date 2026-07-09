from django.contrib import admin

from .models import CartItem, Order, OrderItem, Product, ProductImage, ReturnRequest


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock_quantity", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description", "category")
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "shipping_address")
    inlines = [OrderItemInline]


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order_item", "user", "status", "requested_at")
    list_filter = ("status", "reason")


admin.site.register(ProductImage)
admin.site.register(CartItem)
admin.site.register(OrderItem)
