import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_service import ProductAIAssistant
from .forms import ProductModelForm
from .models import Product
from .provenance import is_ai_source, source_label
from .python_core_utils import recursive_loyalty_discount
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name", "sku", "description"]


class CatalogChatAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        question = str(request.data.get("question", "")).strip()[:1000]
        if not question:
            return Response({"answer": "Enter a question to get started."}, status=400)
        products = list(Product.objects.all()[:100])
        answer, source = ProductAIAssistant().chat(question, products)
        return Response(_chat_payload(answer, source))


def _chat_payload(answer, source):
    return {
        "answer": answer,
        "source": source,
        "source_label": source_label(source),
        "ai_generated": is_ai_source(source),
    }


def landing(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "store/landing.html", {"signup_form": UserCreationForm()})


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "store/landing.html", {"signup_form": form, "signup_open": True})


@login_required
def home(request):
    products = Product.objects.all()
    grouped = [(value, label, products.filter(category=value)) for value, label in Product.Category.choices]
    return render(request, "store/home.html", {"grouped_products": grouped, "products": products})


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    gallery = ([product.image.url] if product.image else []) + (product.gallery_urls or [])
    return render(request, "store/product_detail.html", {"product": product, "gallery": gallery})


@login_required
def manage_products(request):
    return render(request, "store/manage.html", {"products": Product.objects.all()})


@login_required
def product_create(request):
    form = ProductModelForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.instance.created_by = request.user
        form.save()
        _announce_enhancement(request, form.enhancement_report, "Product saved.")
        return redirect("manage")
    return render(request, "store/product_form.html", {"form": form, "title": "Add product"})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductModelForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        _announce_enhancement(request, form.enhancement_report, "Product updated.")
        return redirect("manage")
    return render(request, "store/product_form.html", {"form": form, "title": "Edit product"})


def _announce_enhancement(request, report, prefix):
    ai_fields = [item.name for item in report.ai_fields]
    fallback_fields = [item.name for item in report.fallback_fields]
    if ai_fields:
        labels = sorted({source_label(item.source) for item in report.ai_fields})
        messages.success(request, f"{prefix} AI generated: {', '.join(ai_fields)} ({', '.join(labels)}).")
    if fallback_fields:
        messages.warning(
            request,
            f"{prefix} AI did not provide a usable value, so the offline fallback (not AI) generated: "
            f"{', '.join(fallback_fields)}. Review the draft before publishing.",
        )
    if not report.generated:
        messages.success(request, f"{prefix} All supplied details were kept.")


@login_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect("manage")


@login_required
@require_POST
def catalog_chat(request):
    try:
        payload = json.loads(request.body or "{}")
        question = str(payload.get("question", "")).strip()[:1000]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return render_json("Please send a valid question.", status=400)
    if not question:
        return render_json("Enter a question to get started.", status=400)
    products = list(Product.objects.all()[:100])
    answer, source = ProductAIAssistant().chat(question, products)
    return render_json(answer, source=source)


def render_json(answer, source=None, status=200):
    payload = _chat_payload(answer, source) if source else {"answer": answer}
    return JsonResponse(payload, status=status)


@login_required
@require_POST
def loyalty_quote(request, pk):
    product = get_object_or_404(Product, pk=pk)
    tier = request.POST.get("tier", "none")
    price = recursive_loyalty_discount(product.price or Decimal("0"), tier)
    return JsonResponse({"price": str(price), "tier": tier})
