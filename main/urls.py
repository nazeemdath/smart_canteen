from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns=[
    path('', views.samp, name='samp'),
    path('base', views.about),
    path('shop', views.shop,name='shop' ),
]
