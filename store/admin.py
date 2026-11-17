from django.contrib import admin

from .enrichment import enrich_product
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku", "name", "category", "price", "stock", "ai_enhanced",
        "description_origin", "price_origin", "updated_at",
    )
    list_filter = ("category", "ai_enhanced", "description_source", "price_source")
    search_fields = ("sku", "name", "description")
    readonly_fields = (
        "ai_enhanced", "ai_reasoning", "description_source", "price_source",
        "created_at", "updated_at",
    )

    @admin.display(description="Description source", ordering="description_source")
    def description_origin(self, obj):
        return obj.get_description_source_display()

    @admin.display(description="Price source", ordering="price_source")
    def price_origin(self, obj):
        return obj.get_price_source_display()

    def save_model(self, request, obj, form, change):
        enrich_product(
            obj,
            description_provided=bool((form.cleaned_data.get("description") or "").strip()),
            price_provided=form.cleaned_data.get("price") is not None,
        )
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
