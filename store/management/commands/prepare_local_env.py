"""Create the local .env with generated secrets for a one-command Windows setup."""
from pathlib import Path
import re
import secrets
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key

KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
INSECURE_SECRETS = {"", "replace-with-a-long-random-secret", "dev-only-change-this-secret-key"}


class Command(BaseCommand):
    help = "Create/update the local .env with generated local-only credentials."

    def add_arguments(self, parser):
        parser.add_argument("--rotate", action="store_true", help="Replace the local Streamlit API token and creator password.")

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        env_path = base_dir / ".env"
        example_path = base_dir / ".env.example"

        if not env_path.exists():
            if example_path.exists():
                shutil.copyfile(example_path, env_path)
                self.stdout.write("Created .env from .env.example.")
            else:
                env_path.write_text("DEBUG=True\n", encoding="utf-8")
                self.stdout.write("Created a minimal .env.")

        lines = env_path.read_text(encoding="utf-8").splitlines()
        generated_password = ""
        generated_admin_password = ""

        secret = _value(lines, "SECRET_KEY")
        if secret in INSECURE_SECRETS:
            _set(lines, "SECRET_KEY", get_random_secret_key())

        if options["rotate"] or not _value(lines, "STREAMLIT_API_TOKEN"):
            _set(lines, "STREAMLIT_API_TOKEN", secrets.token_urlsafe(32))

        current_password = _value(lines, "STREAMLIT_CREATOR_PASSWORD")
        if options["rotate"] or not current_password:
            generated_password = secrets.token_urlsafe(9)
            _set(lines, "STREAMLIT_CREATOR_PASSWORD", generated_password)

        if not _value(lines, "STREAMLIT_API_USER"):
            _set(lines, "STREAMLIT_API_USER", "studio")
        if not _value(lines, "DJANGO_BASE_URL"):
            _set(lines, "DJANGO_BASE_URL", "http://127.0.0.1:8000")
        if _value(lines, "DEPLOY_ADMIN_USERNAME") and not _value(lines, "DEPLOY_ADMIN_PASSWORD"):
            generated_admin_password = secrets.token_urlsafe(9)
            _set(lines, "DEPLOY_ADMIN_PASSWORD", generated_admin_password)
        if not _value(lines, "AI_PROVIDER"):
            _set(lines, "AI_PROVIDER", "ollama")
        if not _value(lines, "OLLAMA_MODEL"):
            _set(lines, "OLLAMA_MODEL", "llama3.2")

        env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Local environment ready: {env_path}"))
        if generated_password:
            self.stdout.write(self.style.WARNING(f"Streamlit creator password: {generated_password}"))
            self.stdout.write("This password is stored only in the local .env file.")
        else:
            self.stdout.write("Streamlit creator password is already set in .env.")
        self.stdout.write(f"Streamlit API user: {_value(lines, 'STREAMLIT_API_USER')}")
        if generated_admin_password:
            self.stdout.write(self.style.WARNING(
                f"Django admin: {_value(lines, 'DEPLOY_ADMIN_USERNAME')} / {generated_admin_password}"
            ))
            self.stdout.write("This admin password is stored only in the local .env file.")
        self.stdout.write("Run this command with --rotate to replace the local Streamlit token and password.")


def _value(lines, key):
    for line in lines:
        match = KEY_RE.match(line)
        if match and match.group(1) == key:
            raw = match.group(2).strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                return raw[1:-1]
            return raw
    return ""


def _set(lines, key, value):
    for index, line in enumerate(lines):
        match = KEY_RE.match(line)
        if match and match.group(1) == key:
            lines[index] = f"{key}={value}"
            return
    lines.append(f"{key}={value}")
