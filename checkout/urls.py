from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .import views




urlpatterns = [
    path("checkout/", views.checkout,name="checkout"),
    path("initiate-payment/", views.initiate_payment, name="initiate_payment"),
    path("payment-success/", views.payment_success, name="payment_success"),
    path("order-confirmation/", views.order_confirmation, name="order-confirmation"),
    path("feedback/<int:order_id>/", views.submit_feedback, name="submit_feedback"),
    path("testimonials/", views.testimonials, name="testimonials"),
]
