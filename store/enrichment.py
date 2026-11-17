"""Fill missing product fields and record exactly where each value came from."""
from dataclasses import dataclass, field as dataclass_field

from .ai_service import ProductAIAssistant
from .provenance import ContentSource, is_ai_source, source_label


@dataclass
class GeneratedField:
    name: str
    source: str


@dataclass
class EnhancementReport:
    generated: list[GeneratedField] = dataclass_field(default_factory=list)

    @property
    def ai_fields(self):
        return [item for item in self.generated if is_ai_source(item.source)]

    @property
    def fallback_fields(self):
        return [item for item in self.generated if item.source == ContentSource.FALLBACK]

    def summary(self, product, provider_label=""):
        groups = {"ai": [], "fallback": [], "owner": [], "seed": []}
        for name in ("description", "price"):
            source = getattr(product, f"{name}_source", ContentSource.OWNER)
            if is_ai_source(source):
                groups["ai"].append(f"{name} ({source_label(source)})")
            elif source == ContentSource.FALLBACK:
                groups["fallback"].append(name)
            elif source == ContentSource.SEED:
                groups["seed"].append(name)
            else:
                groups["owner"].append(name)

        parts = []
        if groups["ai"]:
            provider = f" via {provider_label}" if provider_label else ""
            parts.append("AI-generated" + provider + ": " + ", ".join(groups["ai"]) + ".")
        if groups["fallback"]:
            parts.append(
                "AI did not provide a usable value; offline rule-based fallback (not AI) generated: "
                + ", ".join(groups["fallback"]) + "."
            )
        if groups["owner"]:
            parts.append("Owner-supplied: " + ", ".join(groups["owner"]) + ".")
        if groups["seed"]:
            parts.append("Curated demo: " + ", ".join(groups["seed"]) + ".")
        return " ".join(parts) or "No product fields were generated."


def enrich_product(product, *, description_provided=None, price_provided=None, assistant=None):
    """Generate only blank fields, then recompute AI/fallback provenance.

    `description_provided` and `price_provided` let each caller say whether the
    submitted form/API payload contained a value.  When omitted, the current
    object state is used.
    """
    description = (product.description or "").strip()
    needs_description = description_provided is False or (description_provided is None and not description)
    needs_price = price_provided is False or (price_provided is None and product.price is None)
    if (needs_description or needs_price) and assistant is None:
        assistant = ProductAIAssistant()

    report = EnhancementReport()
    facts = f"SKU: {product.sku}; stock: {product.stock or 0}"

    if needs_description:
        value, source = assistant.description(product.name, product.category, facts)
        product.description = value
        product.description_source = source
        report.generated.append(GeneratedField("description", source))
    elif description_provided:
        product.description_source = ContentSource.OWNER

    if needs_price:
        value, source = assistant.price(product.name, product.category, facts)
        product.price = value
        product.price_source = source
        report.generated.append(GeneratedField("price", source))
    elif price_provided:
        product.price_source = ContentSource.OWNER

    product.ai_enhanced = is_ai_source(product.description_source) or is_ai_source(product.price_source)
    provider_label = getattr(assistant, "provider_label", "") if assistant else ""
    product.ai_reasoning = report.summary(product, provider_label)
    return report
