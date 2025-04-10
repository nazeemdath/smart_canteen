from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns=[
    path('signup', views.signup, name='signup'),
    path('user_login/', views.user_login, name='user_login'),
    path('logut_view', views.logout_view, name='logout_view'),
    path("profile/", views.profile, name="profile"),


]
