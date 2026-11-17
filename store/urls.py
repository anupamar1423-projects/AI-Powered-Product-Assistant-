from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="store/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("home/", views.home, name="home"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("manage/", views.manage_products, name="manage"),
    path("manage/new/", views.product_create, name="product_create"),
    path("manage/<int:pk>/edit/", views.product_update, name="product_update"),
    path("manage/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("assistant/chat/", views.catalog_chat, name="catalog_chat"),
    path("product/<int:pk>/loyalty-quote/", views.loyalty_quote, name="loyalty_quote"),
]
