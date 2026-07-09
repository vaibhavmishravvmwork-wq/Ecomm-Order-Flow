from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from PIL import Image, ImageDraw, ImageFont

from store.models import CartItem, Order, OrderItem, Product, ProductImage, ReturnRequest


class Command(BaseCommand):
    help = "Seed demo accounts, products, orders, carts, and return requests."

    def handle(self, *args, **options):
        with transaction.atomic():
            admin = self._ensure_user("admin@orderflow.com", "admin123", is_staff=True, is_superuser=True, first_name="Admin", last_name="User")
            customer1 = self._ensure_user("customer1@orderflow.com", "customer123", first_name="Alex", last_name="Morgan")
            customer2 = self._ensure_user("customer2@orderflow.com", "customer123", first_name="Jordan", last_name="Lee")

            products = self._ensure_products()
            self._attach_images(products)
            self._ensure_cart_items(customer1, customer2, products)
            self._ensure_orders_and_returns(customer1, customer2, products)

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))

    def _ensure_user(self, email, password, **extra):
        user, created = User.objects.get_or_create(email=email, defaults={"username": email.split("@")[0], **extra})
        if created:
            user.set_password(password)
        else:
            for key, value in extra.items():
                setattr(user, key, value)
            user.set_password(password)
        user.save()
        return user

    def _ensure_products(self):
        catalog = [
            ("ProFlow Ultra Hub", "Warehouse Tools", Decimal("299.00"), 84, "A multi-port logistics hub built for high-velocity operations."),
            ("Quantum MX Keyboard", "Electronics", Decimal("189.00"), 126, "Mechanical keyboard with fast response and durable switches."),
            ("UltraFlow 34\" Monitor", "Electronics", Decimal("649.00"), 40, "Wide curved display for operations and analytics."),
            ("ProDock Thunderbolt 4", "Accessories", Decimal("299.00"), 34, "Dual 4K support docking station with power delivery."),
            ("Titan-Lift Semi-Auto Jack", "Warehouse Tools", Decimal("1250.00"), 12, "Heavy lifting support for warehouse teams."),
            ("Armor-Pack Multi-Size Crate", "Shipping Supplies", Decimal("85.00"), 190, "Industrial-grade shipping crate for secure transport."),
        ]
        products = []
        for name, category, price, stock, description in catalog:
            product, _ = Product.objects.get_or_create(name=name, defaults={"category": category, "price": price, "stock_quantity": stock, "description": description, "is_active": True})
            product.category = category
            product.price = price
            product.stock_quantity = stock
            product.description = description
            product.is_active = True
            product.save()
            products.append(product)
        return products

    def _attach_images(self, products):
        palette = ["0b6a99", "104e8b", "1f9d55", "d97706", "7c3aed", "c2410c"]
        for index, product in enumerate(products):
            if product.images.exists():
                continue
            image = self._generate_image(product.name, palette[index % len(palette)])
            filename = f"demo-{product.id}-{index}.png"
            product.images.create(image=ContentFile(image, name=filename), is_primary=True, display_order=0)

    def _generate_image(self, label, color):
        size = (1200, 900)
        image = Image.new("RGB", size, f"#{color}")
        draw = ImageDraw.Draw(image)
        accent = Image.new("RGB", size, "#eef4fb")
        image.paste(accent, (0, 0))
        draw.rounded_rectangle((80, 80, 1120, 820), radius=48, fill=f"#{color}")
        draw.text((120, 140), "OrderFlow", fill="white", font=ImageFont.load_default())
        draw.text((120, 220), label, fill="white", font=ImageFont.load_default())
        draw.text((120, 290), "Demo product image", fill="white", font=ImageFont.load_default())
        output = Path("temp-demo.png")
        image.save(output)
        data = output.read_bytes()
        output.unlink(missing_ok=True)
        return data

    def _ensure_cart_items(self, customer1, customer2, products):
        CartItem.objects.filter(user__in=[customer1, customer2]).delete()
        CartItem.objects.create(user=customer1, product=products[0], quantity=2)
        CartItem.objects.create(user=customer1, product=products[1], quantity=1)
        CartItem.objects.create(user=customer2, product=products[2], quantity=1)
        CartItem.objects.create(user=customer2, product=products[5], quantity=3)

    def _ensure_orders_and_returns(self, customer1, customer2, products):
        if not Order.objects.exists():
            order1 = Order.objects.create(user=customer1, shipping_address="123 Logistics Ave\nChicago, IL 60601", total_amount=Decimal("1097.00"), status=Order.Status.DELIVERED)
            oi1 = OrderItem.objects.create(order=order1, product=products[0], quantity=1, price_at_purchase=products[0].price)
            oi2 = OrderItem.objects.create(order=order1, product=products[3], quantity=1, price_at_purchase=products[3].price)
            order1.total_amount = oi1.subtotal + oi2.subtotal
            order1.save(update_fields=["total_amount"])

            order2 = Order.objects.create(user=customer2, shipping_address="77 Harbor Road\nBrooklyn, NY 11201", total_amount=Decimal("934.00"), status=Order.Status.SHIPPED)
            OrderItem.objects.create(order=order2, product=products[2], quantity=1, price_at_purchase=products[2].price)
            OrderItem.objects.create(order=order2, product=products[5], quantity=2, price_at_purchase=products[5].price)

        delivered_item = OrderItem.objects.filter(order__user=customer1, order__status=Order.Status.DELIVERED).first()
        if delivered_item and not hasattr(delivered_item, "return_request"):
            ReturnRequest.objects.create(
                order_item=delivered_item,
                user=customer1,
                reason=ReturnRequest.Reason.DAMAGED_PRODUCT,
                description="Outer packaging arrived damaged during transit.",
                status=ReturnRequest.Status.APPROVED,
            )
