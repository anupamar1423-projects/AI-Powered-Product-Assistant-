import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Product", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("sku", models.CharField(db_index=True, max_length=32, unique=True)),
            ("name", models.CharField(db_index=True, max_length=180)),
            ("category", models.CharField(choices=[("electronics", "Electronics"), ("home_appliances", "Home Appliances"), ("fashion_sports", "Fashion & Sports"), ("furniture_office", "Furniture & Office")], db_index=True, max_length=32)),
            ("description", models.TextField(blank=True)),
            ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)])),
            ("stock", models.PositiveIntegerField(default=0)),
            ("image", models.ImageField(blank=True, upload_to="products/%Y/%m/")),
            ("gallery_urls", models.JSONField(blank=True, default=list, help_text="Optional additional image URLs for the detail gallery")),
            ("ai_enhanced", models.BooleanField(default=False)),
            ("ai_reasoning", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering":["category","name"]}),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["category","name"], name="store_produ_categor_a94bb0_idx")),
    ]
