from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from django.contrib.auth import views as auth_views

urlpatterns=[
    path('signup', views.signup, name='signup'),
    path('user_login/', views.user_login, name='user_login'),
    path('logut_view', views.logout_view, name='logout_view'),
    path("profile/", views.profile, name="profile"),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='authentication/password_reset.html'), name='password_reset'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='authentication/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),


]
