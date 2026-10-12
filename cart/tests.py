from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from datetime import timedelta

from authentication.models import CustomUser
from main.models import Product
from cart.models import CartItem, Coupon


class CartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = CustomUser.objects.create_user(
            username="student_user",
            email="student@test.com",
            password="Password123!",
            role="student"
        )
        self.faculty = CustomUser.objects.create_user(
            username="faculty_user",
            email="faculty@test.com",
            password="Password123!",
            role="faculty"
        )
        self.product = Product.objects.create(
            name="Veg Sandwich",
            price=50.00,
            stock=10,
            calories=250
        )

    def test_cartadd_view(self):
        self.client.login(username="student_user", password="Password123!")
        response = self.client.get(reverse("cart:cartadd", args=[self.product.id]))
        self.assertRedirects(response, reverse("cart:cart"))

        item = CartItem.objects.filter(user=self.student, product_id=self.product).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 1)

        # Add again -> quantity increments
        self.client.get(reverse("cart:cartadd", args=[self.product.id]))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_cart_update_within_stock(self):
        self.client.login(username="student_user", password="Password123!")
        cart_item = CartItem.objects.create(
            user=self.student,
            product_id=self.product,
            quantity=1,
            price=self.product.price,
            name=self.product.name
        )
        response = self.client.post(
            reverse("cart:update", args=[cart_item.id]),
            {"quantity": 3}
        )
        self.assertRedirects(response, reverse("cart:cart"))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

    def test_cart_update_exceeds_stock(self):
        self.client.login(username="student_user", password="Password123!")
        cart_item = CartItem.objects.create(
            user=self.student,
            product_id=self.product,
            quantity=1,
            price=self.product.price,
            name=self.product.name
        )
        response = self.client.post(
            reverse("cart:update", args=[cart_item.id]),
            {"quantity": 50}  # stock is 10
        )
        self.assertRedirects(response, reverse("cart:cart"))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)  # should not change

    def test_cart_delete(self):
        self.client.login(username="student_user", password="Password123!")
        cart_item = CartItem.objects.create(
            user=self.student,
            product_id=self.product,
            quantity=1,
            price=self.product.price,
            name=self.product.name
        )
        response = self.client.get(reverse("cart:delete", args=[cart_item.id]))
        self.assertRedirects(response, reverse("cart:cart"))
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_coupon_applied_successfully(self):
        self.client.login(username="student_user", password="Password123!")
        cart_item = CartItem.objects.create(
            user=self.student,
            product_id=self.product,
            quantity=2,
            price=Decimal("50.00"),
            name=self.product.name
        )
        coupon = Coupon.objects.create(
            code="STUDENT20",
            discount_percentage=20,
            valid_from=now() - timedelta(days=1),
            valid_to=now() + timedelta(days=5),
            valid_for="student",
            active=True
        )
        coupon.products.add(self.product)

        response = self.client.post(
            reverse("cart:apply_coupon"),
            {"coupon_code": "STUDENT20"}
        )
        self.assertRedirects(response, reverse("cart:cart"))
        cart_item.refresh_from_db()
        # Subtotal: 100, 20% discount = 20, discounted_price = 80
        self.assertEqual(cart_item.discounted_price, Decimal("80.00"))

    def test_coupon_wrong_role_rejected(self):
        self.client.login(username="faculty_user", password="Password123!")
        CartItem.objects.create(
            user=self.faculty,
            product_id=self.product,
            quantity=1,
            price=Decimal("50.00"),
            name=self.product.name
        )
        coupon = Coupon.objects.create(
            code="STUDENTONLY",
            discount_percentage=10,
            valid_from=now() - timedelta(days=1),
            valid_to=now() + timedelta(days=5),
            valid_for="student",
            active=True
        )
        coupon.products.add(self.product)

        response = self.client.post(
            reverse("cart:apply_coupon"),
            {"coupon_code": "STUDENTONLY"}
        )
        self.assertRedirects(response, reverse("cart:cart"))
        session = self.client.session
        self.assertNotIn("coupon_code", session)
