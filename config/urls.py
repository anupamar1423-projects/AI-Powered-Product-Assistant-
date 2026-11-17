from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from store.views import CatalogChatAPIView, ProductViewSet

admin.site.site_header = "Aster & Oak Administration"
admin.site.site_title = "Aster & Oak Admin"
admin.site.index_title = "Store management"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product-api")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/assistant/chat/", CatalogChatAPIView.as_view(), name="api_catalog_chat"),
    path("api/", include(router.urls)),
    path(
        "login/",
        LoginView.as_view(
            template_name="store/login.html",
            redirect_authenticated_user=True,
            extra_context={"signup_form": UserCreationForm()},
        ),
        name="login",
    ),
    path("", include("store.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
