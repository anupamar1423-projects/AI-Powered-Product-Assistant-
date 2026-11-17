from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .provenance import ContentSource


class Product(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Electronics"
        HOME = "home_appliances", "Home Appliances"
        FASHION = "fashion_sports", "Fashion & Sports"
        FURNITURE = "furniture_office", "Furniture & Office"

    sku = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=180, db_index=True)
    category = models.CharField(max_length=32, choices=Category.choices, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank to let the configured AI provider estimate an INR price.",
    )
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True)
    gallery_urls = models.JSONField(default=list, blank=True, help_text="Optional additional image URLs for the detail gallery")
    ai_enhanced = models.BooleanField(default=False, help_text="True only when a real AI provider generated at least one field.")
    ai_reasoning = models.TextField(blank=True)
    description_source = models.CharField(max_length=16, choices=ContentSource.choices, default=ContentSource.OWNER)
    price_source = models.CharField(max_length=16, choices=ContentSource.choices, default=ContentSource.OWNER)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [models.Index(fields=["category", "name"], name="store_product_cat_name_idx")]

    def __str__(self):
        return f"{self.sku} · {self.name}"

    @property
    def has_fallback_content(self):
        return ContentSource.FALLBACK in {self.description_source, self.price_source}
