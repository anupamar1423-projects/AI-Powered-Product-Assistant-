---
title: AI-Powered Product Assistant
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
---

# AI-Powered Product Assistant

A Django + Streamlit catalog application for an assignment-ready product assistant. Django provides the storefront, authentication, product management, REST API, and Admin. Streamlit provides the product catalog, AI Product Creator, and catalog-grounded chat. The same catalog is used by both.

The AI integration is deliberately transparent. A real Ollama or Hugging Face result is labelled **AI · Ollama** or **AI · Hugging Face**. When a provider is missing, slow, or returns unusable output, the rule-based safety net is labelled **Offline fallback (not AI)** and `ai_enhanced` stays `false`. The fallback is never presented as AI output.

## What is included

- Django `Product` model with SKU, name, category, description, optional price, stock, image, gallery URLs, AI metadata, and timestamps.
- `ProductModelForm`: a blank description or price is filled **before the row is saved** on create and update.
- Ollama (`llama3.2`) and Hugging Face Inference Providers support, with prompts for descriptions and INR prices.
- Catalog-grounded chat that answers from current database rows, not invented facts.
- Offline fallback for descriptions, prices, and chat when AI cannot be used.
- Per-field provenance columns (`description_source`, `price_source`), `ai_enhanced`, and a human-readable `ai_reasoning` summary.
- Django login/signup, storefront, product detail, management dashboard, Admin, and DRF REST API.
- Streamlit **Product Catalog**, **AI Product Creator**, and **Grounded AI Chat** tabs.
- 16 locally bundled demo photos for the four assignment categories.
- SQLite for zero-password local/demo use, with PostgreSQL support through `DATABASE_URL` or `DB_ENGINE=postgresql`.
- One-command Windows setup via `run_project.bat`.
- One Docker Space for Hugging Face: Django at `/`, Streamlit at `/studio/`, Nginx reverse proxy.

## Requirements

- Windows 10/11 for the one-command setup, or any OS for the manual Django/Streamlit commands.
- Python 3.11 or newer. Python 3.12, 3.13, and 3.14 are all supported by `requirements.txt`; 3.12 is the tested Docker version.
- VS Code is optional; the commands below use a **Command Prompt** terminal.
- Docker is only needed if you build the container locally. It is not installed or required for the Windows setup.

## Run on Windows with one command

1. Extract the project ZIP to a normal folder, for example `C:\Users\YOUR-NAME\Documents\AI-Powered-Product-Assistant`.
2. Open that folder in VS Code.
3. Select **Terminal → New Terminal**. If the terminal profile is PowerShell, open the dropdown and choose **Command Prompt**.
4. Run:

```cmd
run_project.bat
```

The first run creates `.venv`, installs `requirements.txt`, creates `.env`, generates local-only secrets, applies migrations, seeds the 16 demo products, creates the API service user and local admin, and opens Django and Streamlit in two separate Command Prompt windows.

The script prints two local credentials and also saves them in `.env`:

- A Django Admin login (`storeadmin` by default).
- A Streamlit Product Creator password.

`.env` is excluded from Git and from the submission ZIP. Do not copy it into the Space or a public repository.

Open:

| Service | URL |
| --- | --- |
| Django storefront | <http://127.0.0.1:8000/> |
| Django Admin | <http://127.0.0.1:8000/admin/> |
| Streamlit studio | <http://127.0.0.1:8501/> |
| REST API | <http://127.0.0.1:8000/api/products/> |

Keep both server windows open. Stop them with `Ctrl+C` in each window.

Useful flags:

```cmd
run_project.bat --no-browser
run_project.bat --skip-install
```

`--no-browser` does not open tabs. `--skip-install` skips `pip install`; it fails if a required package is missing.

## Manual setup (exact Windows CMD commands)

Use these commands if you do not want the batch file, or if you need to debug setup step by step. Run them from the project folder in a Command Prompt:

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python manage.py prepare_local_env
python manage.py migrate
python manage.py seed_data
python manage.py bootstrap_deploy_admin
python manage.py runserver
```

Open a **second** Command Prompt in the same folder for Streamlit:

```cmd
.venv\Scripts\activate
python -m streamlit run streamlit_app\app.py
```

If `py -3.12` is not available, use `py -3.13`, `py -3.14`, or `python -m venv .venv` with a Python 3.11+ interpreter.

To use a different local admin password, change `DEPLOY_ADMIN_PASSWORD` in `.env` and run `python manage.py bootstrap_deploy_admin` again. The command synchronizes the configured admin password on every startup.

## Turn on AI

The selected provider is controlled by `AI_PROVIDER` in `.env`. With no working provider, the app still runs and clearly labels offline drafts.

### Option A: Ollama (local, recommended for `llama3.2`)

1. Install Ollama for Windows.
2. In a Command Prompt, pull the model once:

```cmd
ollama pull llama3.2
ollama list
```

3. Confirm `.env` contains:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

4. Restart the Django server. Ollama normally runs as a background service; do not start a second `ollama serve` if port `11434` is already in use.

Test the provider from the project folder:

```cmd
.venv\Scripts\activate
python -c "from store.ai_service import ProductAIAssistant; a=ProductAIAssistant(); print(a.description('Test Lamp','furniture_office')); print(a.price('Test Lamp','furniture_office'))"
```

A successful result prints text plus `ollama`. If Ollama is not running, the same command returns the `fallback` source instead of claiming AI success.

### Option B: Hugging Face Inference Providers

1. Create a Hugging Face token with Inference Providers permission.
2. Put the token **only** in `.env` (never in source, README, screenshots, or Dockerfile):

```env
AI_PROVIDER=huggingface
HF_API_TOKEN=your_private_token
HF_TEXT_MODEL=meta-llama/Llama-3.2-3B-Instruct
HF_INFERENCE_PROVIDER=auto
```

3. Restart the Django server.

If the token, provider, or model is unavailable, the request falls back to offline rules and is labelled that way. `HF_API_TOKEN` is server-side only; it is never sent to the browser or Streamlit.

### Option C: Offline only

```env
AI_PROVIDER=offline
```

This is useful for a deterministic demo with no network. The product form still completes blank fields, but every generated field is marked **Offline fallback (not AI)**.

### How generation works

- The Django form detects whether description and price were actually supplied.
- Blank description and/or price triggers `store/enrichment.py` before `save()`.
- A real provider value is stored with `description_source` or `price_source` set to `ollama` / `huggingface`; `ai_enhanced` becomes `true`.
- A provider failure or unusable response is stored as `fallback`; `ai_enhanced` stays `false`.
- The UI, API, Streamlit captions, management table, and Admin list all show the same provenance.
- Existing owner-supplied values are never silently replaced by AI.

## Database

SQLite is the default and needs no password:

```env
DB_ENGINE=sqlite
SQLITE_PATH=db.sqlite3
```

For PostgreSQL, either use a URL:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

or individual values:

```env
DB_ENGINE=postgresql
DB_NAME=product_assistant
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

The project uses `psycopg[binary]` (psycopg 3), which supports Python 3.14; `psycopg2-binary` does not. Keep database passwords in `.env` or platform secrets.

## Tests and checks

Run these before submission:

```cmd
.venv\Scripts\activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test store -v 2
```

The tests cover form filling, owner-supplied preservation, AI versus fallback labels, view messages, token-authenticated API creation, price parsing, and fallback chat.

## Deploying to Hugging Face

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for the full Docker Space walkthrough, including the difference between **Variables** and **Secrets**, persistent storage, the `/studio/` proxy, and troubleshooting.

Short version:

1. Create a **Docker** Space. The README front matter sets `sdk: docker` and `app_port: 7860`.
2. Push the project files, excluding `.env`, `.venv*`, `db.sqlite3`, `media/`, `staticfiles/`, and generated outputs.
3. Add Secrets: `SECRET_KEY`, `STREAMLIT_API_TOKEN`, `STREAMLIT_CREATOR_PASSWORD`, `DEPLOY_ADMIN_PASSWORD`, and optionally `HF_API_TOKEN`.
4. Add Variables: `AI_PROVIDER=huggingface`, `ALLOWED_HOSTS=.hf.space,localhost,127.0.0.1`, `STREAMLIT_API_USER=storeadmin`, `DEPLOY_ADMIN_USERNAME=storeadmin`.
5. Wait for the Space to report **Running**, then open `/` and `/studio/`.

The Docker image was **not built or deployed from this machine** because Docker is not installed here. The Space steps are prepared and locally validated where possible, but a successful cloud deployment must be confirmed in your own Hugging Face account. Do not submit a Space URL until you have seen it reach **Running**.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `'python' is not recognized` or `'py' is not recognized` | Install Python 3.12+ with **Add python.exe to PATH**, reopen Command Prompt/VS Code, then run `py --list` and `run_project.bat` again. |
| `run_project.bat` says the existing `.venv` uses an unsupported Python | Delete the `.venv` folder and run the batch file again. |
| `ModuleNotFoundError: django` or `streamlit` | Activate `.venv` and run `python -m pip install -r requirements.txt`. |
| `SECRET_KEY is required when DEBUG=False` | Run `python manage.py prepare_local_env`, or add a long random `SECRET_KEY` to `.env`. |
| Port 8000 or 8501 already in use | Stop the old server with `Ctrl+C`, or run `netstat -ano | findstr :8000` and end the listed process. |
| Streamlit starts but shows a connection error | Start Django first, confirm <http://127.0.0.1:8000/api/products/> returns JSON, and check `DJANGO_BASE_URL` in `.env`. |
| Streamlit creator says the API token is missing | Run `python manage.py prepare_local_env` and restart both servers. |
| Creator returns `401`/`403` | The token must match in Django and Streamlit, and `STREAMLIT_API_USER` must be an active staff user. Run `python manage.py bootstrap_deploy_admin`. |
| Ollama returns connection errors | Start/open Ollama, run `ollama list`, and confirm `OLLAMA_BASE_URL=http://localhost:11434`. If the model is missing, run `ollama pull llama3.2`. |
| Hugging Face returns `401`, `403`, or model unavailable | Check the token, Inference Providers access, and `HF_TEXT_MODEL`. The app will fall back without claiming AI; switch models or fix the token to restore AI. |
| Admin password was lost | Set a new `DEPLOY_ADMIN_PASSWORD` in `.env` and run `python manage.py bootstrap_deploy_admin`, or run `python manage.py changepassword storeadmin`. |
| `DisallowedHost` in a Space | Add `.hf.space` to the Space variable `ALLOWED_HOSTS`, or use the Dockerfile default, and restart. |
| `/studio/` is blank or assets 404 in a Space | Confirm Nginx preserves the prefix (`proxy_pass http://127.0.0.1:8501/studio/;`) and Streamlit uses `--server.baseUrlPath=studio`. Do not add a second `studio` segment. |
| Product form fields overlap or are cramped | Fixed in this version by applying Bootstrap `form-control`/`form-select` classes to all form widgets. Hard-refresh the browser after updating. |
| Mobile product detail is clipped | Fixed by removing the negative Bootstrap row gutter inside `.detail-info` at narrow widths. Hard-refresh if CSS is cached. |
| Images are missing after a Space restart | The free Space filesystem is ephemeral. Attach persistent `/data` storage or use an external database/media host; see the deployment guide. |

## Project layout

```text
config/                 Django settings and URLs
store/
  models.py             Product model and provenance fields
  forms.py              ProductModelForm; fill happens before save
  enrichment.py         Shared AI/fill/provenance pipeline
  ai_service.py         Ollama, Hugging Face, offline rules, chat
  provenance.py         ContentSource choices and labels
  views.py              Storefront, management, chat, loyalty API
  serializers.py        DRF API with provenance output
  admin.py              Django Admin with AI/source columns
  python_core_utils.py  Syllabus examples and price parsing
  tests.py              Regression tests
  management/commands/  seed, local environment, deployment bootstrap
streamlit_app/app.py    Streamlit catalog, creator, chat
templates/              Django templates
static/store/           CSS, JS, and 16 bundled demo photos
deploy/                 start.sh and nginx.conf for the Space
Dockerfile              Docker Space image
run_project.bat         Windows one-command setup
DEPLOYMENT_GUIDE.md     Hugging Face walkthrough and troubleshooting
IMAGE_CREDITS.md        Unsplash photo sources and license note
```

## Security notes

- `.env`, `.venv*`, `db.sqlite3`, `media/`, `staticfiles/`, and generated ZIPs are ignored by Git and Docker.
- Tokens and passwords are read from environment variables / `.env` / Streamlit secrets. No real credential is committed.
- Streamlit writes use a bearer token checked by a custom DRF authentication class and are bound to an active staff user.
- Run `python manage.py check --deploy` with production settings before a real public launch. The Docker Space is a demo configuration, not a hardened production deployment.

## Photo credits

The bundled demo photos are representative category images, not manufacturer-verified photos of the exact fictional SKUs. See [IMAGE_CREDITS.md](IMAGE_CREDITS.md) for the Unsplash source IDs and license note. Replace them with owner-supplied product photos before real retail use.
