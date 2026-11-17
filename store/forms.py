from django import forms

from .enrichment import enrich_product
from .models import Product


class ProductModelForm(forms.ModelForm):
    gallery_urls = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional: paste image URLs, one per line"}),
        help_text="Optional additional image URLs for the detail gallery.",
        label="Gallery image URLs",
    )

    class Meta:
        model = Product
        fields = ["sku", "name", "category", "description", "price", "stock", "image", "gallery_urls"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        gallery = self.initial.get("gallery_urls")
        if isinstance(gallery, (list, tuple)):
            self.initial["gallery_urls"] = "\n".join(str(url) for url in gallery)
        self.fields["description"].required = False
        self.fields["price"].required = False
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = f"{field.widget.attrs.get('class', '')} {css_class}".strip()

    def clean_gallery_urls(self):
        value = self.cleaned_data.get("gallery_urls")
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return value or []

    def clean(self):
        cleaned = super().clean()
        # Remember what the owner actually submitted so a blank description or
        # price is regenerated on both create and update.
        self.description_provided = bool((cleaned.get("description") or "").strip())
        self.price_provided = cleaned.get("price") is not None
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        # Enrichment lives here so every caller (views, admin, tests) gets the
        # same AI/fallback behaviour before the row is written.
        self.enhancement_report = enrich_product(
            product,
            description_provided=getattr(self, "description_provided", None),
            price_provided=getattr(self, "price_provided", None),
        )
        if commit:
            product.save()
            self.save_m2m()
        return product
