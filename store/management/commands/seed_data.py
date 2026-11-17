"""Seed a curated demo catalog without calling an AI provider during startup."""
from io import BytesIO
import os

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.templatetags.static import static

from store.models import Product
from store.provenance import ContentSource

PRODUCTS = [
    (
        "ELEC-1001", "Studio ANC Headphones", "electronics", 8999, 32,
        "wireless over-ear headphones",
        "Studio ANC Headphones are made for focused listening at home, at work, or on the move. "
        "The over-ear design pairs everyday comfort with a clean, considered look.",
    ),
    (
        "ELEC-1002", "AMOLED Fitness Watch", "electronics", 7499, 24,
        "smartwatch with AMOLED screen",
        "Keep daily activity, workouts, and notifications close at hand with this AMOLED fitness watch. "
        "Its clear display and lightweight build suit both training days and busy workdays.",
    ),
    (
        "ELEC-1003", "4K Mirrorless Camera", "electronics", 68999, 8,
        "mirrorless camera with interchangeable lens",
        "A compact mirrorless camera for creators who want detailed stills and video without a bulky kit. "
        "The interchangeable lens system makes it easy to grow from everyday shots to planned productions.",
    ),
    (
        "ELEC-1004", "Portable Bluetooth Speaker", "electronics", 3999, 41,
        "compact portable Bluetooth speaker",
        "Take room-filling sound from the kitchen to the garden with this compact Bluetooth speaker. "
        "Its portable form is designed for casual listening, travel, and shared moments.",
    ),
    (
        "HOME-2001", "Barista Espresso Machine", "home_appliances", 24999, 12,
        "stainless steel espresso machine",
        "Bring a café-style routine home with this stainless steel espresso machine. "
        "It is built for people who enjoy dialing in a daily shot without leaving the kitchen.",
    ),
    (
        "HOME-2002", "Air Purifier Pro", "home_appliances", 12999, 18,
        "tower air purifier",
        "A slim tower purifier designed to fit quietly into living rooms and bedrooms. "
        "It offers a simple way to keep everyday spaces feeling fresher.",
    ),
    (
        "HOME-2003", "Handcrafted Pour-over Set", "home_appliances", 2499, 55,
        "ceramic coffee dripper and carafe",
        "Slow down with a handcrafted pour-over set made for a deliberate morning coffee. "
        "The ceramic dripper and carafe bring a tactile, considered feel to a daily ritual.",
    ),
    (
        "HOME-2004", "Smart Induction Cooktop", "home_appliances", 5999, 20,
        "glass induction cooktop",
        "This glass induction cooktop offers responsive heat in a clean, low-profile design. "
        "It suits compact kitchens and anyone who wants straightforward everyday cooking.",
    ),
    (
        "FASH-3001", "Performance Running Shoes", "fashion_sports", 5499, 38,
        "lightweight knit running shoes",
        "Lightweight knit running shoes built for regular training and comfortable everyday wear. "
        "The streamlined shape works with both workout kits and casual outfits.",
    ),
    (
        "FASH-3002", "Technical Everyday Backpack", "fashion_sports", 3299, 46,
        "weather-resistant commuter backpack",
        "A weather-resistant commuter backpack that keeps daily essentials organized. "
        "Its technical look and practical layout move easily from the train to the office.",
    ),
    (
        "FASH-3003", "Studio Yoga Mat", "fashion_sports", 1899, 62,
        "textured premium yoga mat",
        "A textured studio mat that gives yoga and stretching sessions a steady surface. "
        "It is designed for regular practice at home or in class.",
    ),
    (
        "FASH-3004", "Classic Chronograph Watch", "fashion_sports", 8999, 15,
        "stainless steel chronograph watch",
        "A stainless steel chronograph with a classic, uncluttered presence. "
        "It is an easy choice for everyday dressing and more formal occasions.",
    ),
    (
        "FURN-4001", "Ergonomic Mesh Chair", "furniture_office", 18999, 14,
        "adjustable ergonomic mesh task chair",
        "An adjustable mesh task chair designed for long stretches at a desk. "
        "Its breathable back and supportive shape suit home offices and shared workspaces.",
    ),
    (
        "FURN-4002", "Solid Oak Writing Desk", "furniture_office", 24999, 9,
        "solid oak minimalist writing desk",
        "A solid oak writing desk with a calm, minimalist profile. "
        "The generous work surface makes room for focused writing, planning, or study.",
    ),
    (
        "FURN-4003", "Arc Task Lamp", "furniture_office", 4999, 27,
        "brushed metal adjustable desk lamp",
        "An adjustable brushed-metal task lamp that directs light exactly where it is needed. "
        "Its arc silhouette adds a quiet architectural note to a desk or reading corner.",
    ),
    (
        "FURN-4004", "Modular Bookshelf", "furniture_office", 14999, 11,
        "modular walnut bookshelf",
        "A modular walnut bookshelf that adapts to books, objects, and changing rooms. "
        "Its warm finish and clean lines bring order without feeling heavy.",
    ),
]

CURATED_NOTE = "Curated demo copy and retail price. Not AI-generated."
LEGACY_NOTE = "Seed catalog copy; price reflects demo retail positioning."


class Command(BaseCommand):
    help = "Create the 16 curated demo products (no AI calls) and optionally render photos with Hugging Face."

    def add_arguments(self, parser):
        parser.add_argument("--generate-images", action="store_true", help="Generate images with the HF Inference API (requires HF_API_TOKEN).")
        parser.add_argument("--force", action="store_true", help="Refresh seeded product copy, price, stock, and gallery URLs.")

    def handle(self, *args, **options):
        if options["generate_images"]:
            token = (os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or "").strip()
            if not token:
                raise CommandError("Set HF_API_TOKEN (or HUGGINGFACEHUB_API_TOKEN) before using --generate-images.")

        for sku, name, category, price, stock, facts, description in PRODUCTS:
            bundled_photo = static(f"store/images/{sku}.jpg")
            defaults = {
                "name": name,
                "category": category,
                "price": price,
                "stock": stock,
                "description": description,
                "description_source": ContentSource.SEED,
                "price_source": ContentSource.SEED,
                "ai_enhanced": False,
                "ai_reasoning": CURATED_NOTE,
                "gallery_urls": [bundled_photo],
            }
            product, created = Product.objects.get_or_create(sku=sku, defaults=defaults)

            if not created and options["force"]:
                for field, value in defaults.items():
                    setattr(product, field, value)
                product.save()
            elif not created and not product.gallery_urls:
                product.gallery_urls = [bundled_photo]
                product.save(update_fields=["gallery_urls"])
            elif not created and product.ai_reasoning == LEGACY_NOTE:
                # Older seed rows claimed AI enhancement even when the fallback ran.
                product.description_source = ContentSource.FALLBACK
                product.price_source = ContentSource.OWNER
                product.ai_enhanced = False
                product.ai_reasoning = "Legacy demo copy with unrecorded provenance; review before publishing."
                product.save(update_fields=["description_source", "price_source", "ai_enhanced", "ai_reasoning"])

            if options["generate_images"] and (created or options["force"] or not product.image):
                try:
                    self._generate_image(product, facts)
                    self.stdout.write(self.style.SUCCESS(f"Rendered {sku}"))
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f"Image generation skipped for {sku}: {exc}"))

            self.stdout.write(f"{'Created' if created else 'Ready'} {sku} {name}")

    def _generate_image(self, product, facts):
        from huggingface_hub import InferenceClient

        token = (os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or "").strip()
        model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
        client = InferenceClient(model=model, token=token, timeout=120)
        shots = [
            ("hero", "single hero object, clean warm-white seamless studio background, softbox key light and subtle rim light, centered commercial packshot"),
            ("macro", "tight macro detail photograph showing authentic material grain, controls, stitching and craftsmanship, dramatic soft side light"),
            ("lifestyle", "refined lived-in lifestyle scene with the product naturally in use, calm editorial interior, daylight, aspirational but believable"),
        ]
        gallery = []
        for shot, art_direction in shots:
            prompt = (
                f"Photorealistic premium ecommerce product photography, {facts}, product named {product.name}. "
                f"{art_direction}, clean composition, true-to-life texture, crisp sharp focus, realistic shadows, "
                "high-end retail campaign, square frame, no text, no logo, no watermark."
            )
            image = client.text_to_image(prompt=prompt, width=1024, height=1024, guidance_scale=3.5, num_inference_steps=4)
            image = image.resize((1600, 1600))
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=94, optimize=True)
            content = ContentFile(buffer.getvalue())
            filename = f"products/generated/{product.sku.lower()}-{shot}.jpg"
            if shot == "hero":
                product.image.save(filename, content, save=False)
            else:
                saved_name = default_storage.save(filename, content)
                gallery.append(default_storage.url(saved_name))
        product.gallery_urls = gallery
        product.save()
