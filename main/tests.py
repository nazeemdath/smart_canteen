from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now

from authentication.models import CustomUser
from cart.models import CartItem
from checkout.models import Order
from main.models import (
    Product,
    MealSubscriptionPlan,
    UserSubscription,
    SubscriptionMeal,
    ClaimedMeal,
)


class MainAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="dave",
            email="dave@example.com",
            password="Password123!",
            role="student"
        )
        self.product = Product.objects.create(
            name="Chicken Biryani",
            price=120.00,
            stock=15,
            calories=650
        )
        self.plan = MealSubscriptionPlan.objects.create(
            name="monthly",
            price=2500.00,
            duration_days=30,
            meals_per_day=2,
            description="2 meals per day for 30 days"
        )

    def test_search_products_api(self):
        # Product without image should not crash
        response = self.client.get(reverse("search_products") + "?q=biryani")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["name"], "Chicken Biryani")
        self.assertEqual(data["results"][0]["image"], "")

    def test_search_empty_query(self):
        response = self.client.get(reverse("search_products") + "?q=")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])

    def test_user_subscription_save_calculation(self):
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
        )
        self.assertEqual(sub.remaining_meals, 60)  # 30 days * 2 meals
        self.assertEqual(sub.end_date, date.today() + timedelta(days=30))
        self.assertTrue(sub.is_valid())

    def test_claim_meal_without_subscription(self):
        self.client.login(username="dave", password="Password123!")
        sub_meal = SubscriptionMeal.objects.create(
            product=self.product,
            date_available=date.today(),
            is_available=True
        )
        response = self.client.get(reverse("claim_meal", args=[sub_meal.id]))
        self.assertRedirects(response, reverse("subscription_plans"))

    def test_claim_meal_success(self):
        self.client.login(username="dave", password="Password123!")
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            payment_status="active"
        )
        sub_meal = SubscriptionMeal.objects.create(
            product=self.product,
            date_available=date.today(),
            is_available=True
        )

        initial_stock = self.product.stock
        response = self.client.get(reverse("claim_meal", args=[sub_meal.id]))
        self.assertRedirects(response, reverse("order-confirmation"))

        # Verify stock decremented
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 1)

        # Verify remaining meals decremented
        sub.refresh_from_db()
        self.assertEqual(sub.remaining_meals, 59)

        # Verify ClaimedMeal record created
        self.assertTrue(ClaimedMeal.objects.filter(user_subscription=sub, meal=sub_meal).exists())

    def test_claim_meal_daily_limit(self):
        self.client.login(username="dave", password="Password123!")
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            payment_status="active"
        )
        sub_meal = SubscriptionMeal.objects.create(
            product=self.product,
            date_available=date.today(),
            is_available=True
        )

        # Claim 2 meals (the daily limit)
        self.client.get(reverse("claim_meal", args=[sub_meal.id]))
        self.client.get(reverse("claim_meal", args=[sub_meal.id]))

        # Third claim should be rejected
        response = self.client.get(reverse("claim_meal", args=[sub_meal.id]))
        self.assertRedirects(response, reverse("subscription_plans"))
        self.assertEqual(ClaimedMeal.objects.filter(user_subscription=sub).count(), 2)

    def test_health_dashboard(self):
        self.client.login(username="dave", password="Password123!")
        order = Order.objects.create(
            user=self.user,
            order_total=120.00,
            status="Paid"
        )
        CartItem.objects.create(
            user=self.user,
            product_id=self.product,
            quantity=2,
            price=120.00,
            name=self.product.name,
            order=order
        )

        response = self.client.get(reverse("health_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "health_dashboard.html")
        # 2 quantity * 650 calories = 1300
        daily_calories = response.context["daily_calories"]
        self.assertTrue(len(daily_calories) > 0)
        self.assertEqual(daily_calories[0]["total_calories"], 1300)
