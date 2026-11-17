import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure the configured service account and deployment admin exist."

    def handle(self, *args, **options):
        user_model = get_user_model()
        service_username = os.getenv("STREAMLIT_API_USER", "").strip()
        token_configured = bool(os.getenv("STREAMLIT_API_TOKEN", "").strip())

        if service_username:
            service_user, created = user_model.objects.get_or_create(
                username=service_username,
                defaults={"is_staff": True, "is_active": True},
            )
            changed = created
            if created:
                service_user.set_unusable_password()
            if not service_user.is_staff:
                service_user.is_staff = True
                changed = True
            if not service_user.is_active:
                service_user.is_active = True
                changed = True
            if changed:
                service_user.save()
            self.stdout.write(f"API service user {'created' if created else 'ready'}: {service_username}")
            if not token_configured:
                self.stdout.write(self.style.WARNING("STREAMLIT_API_TOKEN is empty; the Streamlit creator API will reject writes."))

        admin_username = os.getenv("DEPLOY_ADMIN_USERNAME", "").strip()
        admin_password = os.getenv("DEPLOY_ADMIN_PASSWORD", "")
        admin_email = os.getenv("DEPLOY_ADMIN_EMAIL", "").strip()
        if not admin_username or not admin_password:
            self.stdout.write("Deployment admin not configured; set DEPLOY_ADMIN_USERNAME and DEPLOY_ADMIN_PASSWORD to create one.")
            return

        admin, created = user_model.objects.get_or_create(
            username=admin_username,
            defaults={"email": admin_email, "is_staff": True, "is_superuser": True, "is_active": True},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        if admin_email:
            admin.email = admin_email
        # The Space secret is the source of truth so a restarted container can
        # always be recovered; changes made in the admin UI are reset on boot.
        admin.set_password(admin_password)
        admin.save()
        self.stdout.write(f"Deployment admin {'created' if created else 'password synchronized'}: {admin_username}")
