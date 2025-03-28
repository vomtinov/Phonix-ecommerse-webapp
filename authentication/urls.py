from django.urls import path,include
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),#for login
    path('signup/', views.signup_view, name='signup'),#for sign up
    path('logout/', views.logout_view, name='logout'),#for logout
    path('otp_verification/', views.otp_verification_view, name='otp_verification'),#sign up page otp verification
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),# signup page resent otp verification view
    # path('accounts/', include('allauth.urls')),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('forgot-password_otp/', views.forgot_password_otp_verification_view, name='forgot_password_otp'),
    path('password_otp_verification/', views.forgot_password_otp_verification_view, name='password_otp_verification'),
    path('reset-otp/', views.reset_otp_view, name='reset_otp'),
]