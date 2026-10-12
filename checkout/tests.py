from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail

from authentication.models import CustomUser
from cart.models import CartItem
from checkout.models import Order, Feedback
from main.models import Product


class CheckoutAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="emily",
            email="emily@example.com",
            password="Password123!",
            role="student"
        )
        self.product = Product.objects.create(
            name="Club Sandwich",
            price=80.00,
            stock=10,
            calories=350
        )

    def test_checkout_requires_login(self):
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("user_login"), response.url)

    def test_checkout_empty_cart(self):
        self.client.login(username="emily", password="Password123!")
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["final_total"], 0)

    def test_checkout_with_items(self):
        self.client.login(username="emily", password="Password123!")
        CartItem.objects.create(
            user=self.user,
            product_id=self.product,
            quantity=2,
            price=Decimal("80.00"),
            name=self.product.name
        )
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_cart_price"], Decimal("160.00"))
        self.assertEqual(response.context["final_total"], Decimal("160.00"))

    def test_order_status_email_change_only(self):
        # Initial creation as Pending - no email sent
        order = Order.objects.create(
            user=self.user,
            order_total=160.00,
            status="Pending"
        )
        self.assertEqual(len(mail.outbox), 0)

        # Update status to Processing - 1 email sent
        order.status = "Processing"
        order.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Your Order is Being Prepared", mail.outbox[0].subject)

        # Save again without changing status - should NOT send another email
        order.save()
        self.assertEqual(len(mail.outbox), 1)

        # Update status to Delivered - 1 more email sent
        order.status = "Delivered"
        order.save()
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Order Ready for Pickup!", mail.outbox[1].subject)

    def test_submit_feedback(self):
        self.client.login(username="emily", password="Password123!")
        order = Order.objects.create(
            user=self.user,
            order_total=80.00,
            status="Paid"
        )
        response = self.client.post(
            reverse("submit_feedback", args=[order.id]),
            {"rating": 5, "comment": "Delicious food and prompt service!"}
        )
        self.assertRedirects(response, reverse("profile"))
        self.assertTrue(Feedback.objects.filter(order=order, rating=5).exists())

    def test_submit_duplicate_feedback_redirects(self):
        self.client.login(username="emily", password="Password123!")
        order = Order.objects.create(
            user=self.user,
            order_total=80.00,
            status="Paid"
        )
        Feedback.objects.create(
            user=self.user,
            order=order,
            rating=5,
            comment="Initial feedback"
        )
        # Attempt duplicate
        response = self.client.get(reverse("submit_feedback", args=[order.id]))
        self.assertRedirects(response, reverse("profile"))
