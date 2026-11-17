from rest_framework import serializers

from .enrichment import enrich_product
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    description_source_label = serializers.CharField(source="get_description_source_display", read_only=True)
    price_source_label = serializers.CharField(source="get_price_source_display", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "category", "category_label", "description", "price", "stock",
            "image_url", "gallery_urls", "ai_enhanced", "ai_reasoning",
            "description_source", "description_source_label", "price_source", "price_source_label",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "category_label", "image_url", "gallery_urls", "ai_enhanced", "ai_reasoning",
            "description_source", "description_source_label", "price_source", "price_source_label",
            "created_at", "updated_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        product = Product(**validated_data)
        if request and getattr(request.user, "is_authenticated", False):
            product.created_by = request.user
        enrich_product(
            product,
            description_provided=bool((validated_data.get("description") or "").strip()),
            price_provided=validated_data.get("price") is not None,
        )
        product.save()
        return product

    def update(self, instance, validated_data):
        description_provided = None
        if "description" in validated_data:
            description_provided = bool((validated_data.get("description") or "").strip())
        price_provided = None
        if "price" in validated_data:
            price_provided = validated_data.get("price") is not None

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)

        if description_provided is not None or price_provided is not None:
            enrich_product(
                instance,
                description_provided=description_provided,
                price_provided=price_provided,
            )
        instance.save()
        return instance

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        if obj.gallery_urls:
            url = obj.gallery_urls[0]
            return request.build_absolute_uri(url) if request else url
        return ""
