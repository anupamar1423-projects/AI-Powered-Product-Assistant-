"""Regression tests for AI provenance, product forms, API, and catalog chat."""
from decimal import Decimal
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .ai_service import ProductAIAssistant
from .forms import ProductModelForm
from .models import Product
from .provenance import ContentSource
from .python_core_utils import parse_price


class FakeAIAssistant:
    provider_label = "Fake AI (test)"

    def description(self, name, category, attributes=""):
        return f"The {name} is a test-generated description for {category} use.", ContentSource.OLLAMA

    def price(self, name, category, attributes=""):
        return Decimal("4321.00"), ContentSource.OLLAMA


class ParsePriceTests(TestCase):
    def test_currency_marked_values_are_preferred(self):
        self.assertEqual(parse_price("Estimate: INR 1,299.00"), Decimal("1299.00"))
        self.assertEqual(parse_price("About ₹ 899 for this item"), Decimal("899.00"))
        self.assertEqual(parse_price("2499 rupees"), Decimal("2499.00"))

    def test_model_or_token_numbers_are_not_prices(self):
        with self.assertRaises(ValueError):
            parse_price("llama3.2 generated this in 12 tokens")

    def test_price_above_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_price("INR 99999999")


class ProductFormTests(TestCase):
    def product_data(self, **overrides):
        data = {
            "sku": "TEST-FORM-1",
            "name": "Test Desk Lamp",
            "category": "furniture_office",
            "description": "",
            "price": "",
            "stock": "5",
            "gallery_urls": "https://example.com/a.jpg\nhttps://example.com/b.jpg",
        }
        data.update(overrides)
        return data

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_blank_description_and_price_are_generated_before_save(self):
        form = ProductModelForm(data=self.product_data())
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()

        self.assertTrue(product.pk)
        self.assertIn("test-generated", product.description)
        self.assertEqual(product.price, Decimal("4321.00"))
        self.assertEqual(product.description_source, ContentSource.OLLAMA)
        self.assertEqual(product.price_source, ContentSource.OLLAMA)
        self.assertTrue(product.ai_enhanced)
        self.assertIn("AI-generated via Fake AI (test)", product.ai_reasoning)
        self.assertEqual(product.gallery_urls, ["https://example.com/a.jpg", "https://example.com/b.jpg"])
        self.assertEqual(form.enhancement_report.ai_fields[0].source, ContentSource.OLLAMA)

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_owner_values_are_kept(self):
        form = ProductModelForm(
            data=self.product_data(description="Owner-written copy.", price="1499.00")
        )
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()

        self.assertEqual(product.description, "Owner-written copy.")
        self.assertEqual(product.price, Decimal("1499.00"))
        self.assertEqual(product.description_source, ContentSource.OWNER)
        self.assertEqual(product.price_source, ContentSource.OWNER)
        self.assertFalse(product.ai_enhanced)
        self.assertFalse(form.enhancement_report.generated)

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_blank_update_regenerates_missing_fields(self):
        product = Product.objects.create(
            sku="TEST-UPDATE-1",
            name="Test Chair",
            category="furniture_office",
            description="Old copy",
            price=Decimal("500.00"),
            stock=2,
        )
        form = ProductModelForm(
            data=self.product_data(
                sku=product.sku,
                name=product.name,
                category=product.category,
                description="",
                price="",
                stock="2",
                gallery_urls="",
            ),
            instance=product,
        )
        self.assertTrue(form.is_valid(), form.errors)

        updated = form.save()

        self.assertIn("test-generated", updated.description)
        self.assertEqual(updated.price, Decimal("4321.00"))
        self.assertTrue(updated.ai_enhanced)


class ProductViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="test-pass-123")

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_management_form_saves_and_announces_ai(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("product_create"),
            {
                "sku": "TEST-VIEW-1",
                "name": "Test Speaker",
                "category": "electronics",
                "description": "",
                "price": "",
                "stock": "3",
                "gallery_urls": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        product = Product.objects.get(sku="TEST-VIEW-1")
        self.assertEqual(product.created_by, self.user)
        self.assertTrue(product.ai_enhanced)
        self.assertContains(response, "AI generated: description, price")

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_update_with_supplied_values_keeps_owner_sources(self):
        product = Product.objects.create(
            sku="TEST-VIEW-2",
            name="Test Watch",
            category="fashion_sports",
            description="Original",
            price=Decimal("1000"),
            stock=1,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("product_update", args=[product.pk]),
            {
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "description": "Owner revised copy",
                "price": "1200.00",
                "stock": "4",
                "gallery_urls": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.description, "Owner revised copy")
        self.assertEqual(product.description_source, ContentSource.OWNER)
        self.assertFalse(product.ai_enhanced)


class CatalogAPITests(TestCase):
    def setUp(self):
        self.service_user = get_user_model().objects.create_user(
            "studio-test", password="unused", is_staff=True
        )
        self.token = "test-streamlit-token"

    @patch("store.enrichment.ProductAIAssistant", FakeAIAssistant)
    def test_token_authenticated_create_reports_ai_provenance(self):
        with patch.dict(
            os.environ,
            {"STREAMLIT_API_TOKEN": self.token, "STREAMLIT_API_USER": self.service_user.username},
        ):
            response = self.client.post(
                "/api/products/",
                data={
                    "sku": "TEST-API-1",
                    "name": "API Test Camera",
                    "category": "electronics",
                    "description": "",
                    "stock": 2,
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {self.token}",
            )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertTrue(payload["ai_enhanced"])
        self.assertEqual(payload["description_source"], ContentSource.OLLAMA)
        self.assertEqual(payload["description_source_label"], "AI · Ollama")
        self.assertIn("AI-generated", payload["ai_reasoning"])

    def test_anonymous_read_is_allowed(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"AI_PROVIDER": "offline"})
    def test_chat_fallback_is_labeled_not_ai(self):
        Product.objects.create(
            sku="TEST-CHAT-1",
            name="Budget Headphones",
            category="electronics",
            description="Affordable wired headphones.",
            price=Decimal("1999.00"),
            stock=6,
        )
        response = self.client.post(
            "/api/assistant/chat/",
            data={"question": "Which headphones are cheapest?"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ai_generated"])
        self.assertEqual(payload["source"], ContentSource.FALLBACK)
        self.assertIn("not AI", payload["source_label"])


class AIFallbackTests(TestCase):
    def test_offline_provider_never_claims_ai(self):
        assistant = ProductAIAssistant(provider="offline")
        description, description_source = assistant.description("Quiet Lamp", "furniture_office")
        price, price_source = assistant.price("Quiet Lamp", "furniture_office")

        self.assertTrue(description)
        self.assertEqual(description_source, ContentSource.FALLBACK)
        self.assertEqual(price_source, ContentSource.FALLBACK)
        self.assertFalse(ProductAIAssistant(provider="offline").provider_source)

    @patch.dict(os.environ, {"AI_PROVIDER": "offline"})
    def test_home_page_marks_fallback_products_as_draft(self):
        Product.objects.create(
            sku="TEST-DRAFT-1",
            name="Offline Draft Lamp",
            category="furniture_office",
            description="Fallback description",
            price=Decimal("1999.00"),
            stock=1,
            description_source=ContentSource.FALLBACK,
            price_source=ContentSource.FALLBACK,
        )
        user = get_user_model().objects.create_user("viewer", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "OFFLINE DRAFT")
