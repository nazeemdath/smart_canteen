from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views


urlpatterns=[
    # path('', views.samp, name='samp'),
    path('base', views.about),
    path('shop', views.shop,name='shop' ),
    path('',views.index, name='index'),
    path("search/", views.search_products, name="search_products"),
    path('subscription_plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription_success/', views.subscription_success, name='subscription_success'),
    path("claim-meal/<int:meal_id>/", views.claim_meal, name="claim_meal"),
    path("health/", views.health_dashboard, name="health_dashboard"),
    path('save-subscription/', views.save_subscription, name='save_subscription'),
   
    
]
