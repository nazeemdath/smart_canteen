from django.test import TestCase, Client
from django.urls import reverse
from authentication.models import CustomUser
from authentication.forms import SignUpForm, LoginForm


class AuthenticationModelAndFormTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_custom_user(self):
        user = CustomUser.objects.create_user(
            username="student_john",
            email="john@example.com",
            password="StrongPassword123!",
            role="student"
        )
        self.assertEqual(user.username, "student_john")
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.role, "student")
        self.assertTrue(user.check_password("StrongPassword123!"))

    def test_signup_form_valid(self):
        form_data = {
            "username": "faculty_jane",
            "email": "jane@example.com",
            "role": "faculty",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        form = SignUpForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "faculty_jane")
        self.assertEqual(user.role, "faculty")

    def test_signup_form_password_mismatch(self):
        form_data = {
            "username": "user1",
            "email": "user1@example.com",
            "role": "student",
            "password": "Password123!",
            "confirm_password": "Mismatch123!"
        }
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_signup_form_duplicate_email(self):
        CustomUser.objects.create_user(
            username="existing_user",
            email="duplicate@example.com",
            password="Password123!",
            role="student"
        )
        form_data = {
            "username": "new_user",
            "email": "duplicate@example.com",
            "role": "student",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class AuthenticationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="TestPassword123!",
            role="student"
        )

    def test_signup_get(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/signup.html")

    def test_signup_post_success(self):
        response = self.client.post(reverse("signup"), {
            "username": "bob",
            "email": "bob@example.com",
            "role": "student",
            "password": "BobPassword123!",
            "confirm_password": "BobPassword123!"
        })
        self.assertRedirects(response, reverse("user_login"))
        self.assertTrue(CustomUser.objects.filter(username="bob").exists())

    def test_login_success(self):
        response = self.client.post(reverse("user_login"), {
            "username": "alice",
            "password": "TestPassword123!"
        })
        self.assertRedirects(response, "/")

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse("user_login"), {
            "username": "alice",
            "password": "WrongPassword!"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid login credentials")

    def test_logout(self):
        self.client.login(username="alice", password="TestPassword123!")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, "/")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("user_login"), response.url)

    def test_profile_authenticated(self):
        self.client.login(username="alice", password="TestPassword123!")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")
