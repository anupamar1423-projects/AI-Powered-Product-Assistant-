# Run locally and deploy to Hugging Face

This guide covers the Windows local setup and the Hugging Face **Docker Space** that serves Django at `/` and Streamlit at `/studio/`.

## Deployment status (read this first)

The project has been run and verified locally on Windows: Django checks, migrations, the 13-test suite, the storefront, Admin, the Streamlit catalog, and fallback chat all work.

The Docker image was **not built and the Space was not deployed from the development machine**, because Docker and Nginx are not installed there. The Dockerfile, startup script, and proxy configuration are provided and internally checked, but a live Space URL is only valid after **you** create the Space and see it reach **Running**. Do not claim cloud deployment succeeded until that happens.

---

## A. Run locally from VS Code Command Prompt

### 1. Prepare the folder

1. Extract the ZIP to a normal folder, for example `C:\Users\YOUR-NAME\Documents\AI-Powered-Product-Assistant`.
2. Open the folder in VS Code. It must contain `manage.py`, `requirements.txt`, and `run_project.bat`.
3. Install Python 3.12 if needed. During installation enable **Add python.exe to PATH**.
4. In VS Code choose **Terminal → New Terminal**, then select **Command Prompt** from the terminal-profile dropdown.

Check the interpreter:

```cmd
py --list
```

### 2. One-command start

```cmd
run_project.bat
```

On the first run the script:

1. Finds Python 3.11+ (prefers 3.14, 3.13, 3.12, then 3.11).
2. Creates `.venv` and installs `requirements.txt`.
3. Copies `.env.example` to `.env` if needed.
4. Runs `prepare_local_env`, which writes a local `SECRET_KEY`, Streamlit API token, Streamlit creator password, and Django admin password into `.env` and prints the two passwords.
5. Runs migrations, seeds the 16 demo products, creates the service user and admin, and starts Django and Streamlit in separate windows.
6. Opens the Django and Streamlit URLs.

Open:

- Django: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>
- Streamlit: <http://127.0.0.1:8501/>

Keep both Command Prompt windows open. Use `run_project.bat --no-browser` to suppress tabs.

### 3. Manual commands

If the batch file cannot be used, run these exactly from a Command Prompt in the project folder:

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

Second Command Prompt:

```cmd
.venv\Scripts\activate
python -m streamlit run streamlit_app\app.py
```

### 4. AI with Ollama or Hugging Face

For Ollama:

```cmd
ollama pull llama3.2
ollama list
```

Keep these values in `.env`:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

For Hugging Face, put a private token only in `.env`:

```env
AI_PROVIDER=huggingface
HF_API_TOKEN=your_private_token
HF_TEXT_MODEL=meta-llama/Llama-3.2-3B-Instruct
HF_INFERENCE_PROVIDER=auto
```

Restart Django after changing `.env`. With no provider or token, product generation and chat still work through the offline fallback, marked **Offline fallback (not AI)**.

### 5. Local checks

```cmd
.venv\Scripts\activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test store -v 2
```

Expected: no system-check issues, no migration drift, and all tests passing.

---

## B. Deploy Django + Streamlit in one Hugging Face Docker Space

### Architecture

```text
Browser
  |
  | HTTPS :443 (Hugging Face ingress)
  v
Container port 7860
  |
  +-- Nginx
        +-- /          -> Gunicorn / Django at 127.0.0.1:8000
        +-- /studio/   -> Streamlit at 127.0.0.1:8501/studio/
        +-- /media/    -> /data/media
        +-- /static/   -> Django/WhiteNoise
```

- Django owns `/`, `/admin/`, `/api/`, and the storefront.
- Streamlit is available only under `/studio/`.
- Nginx preserves the `/studio/` prefix because Streamlit is started with `--server.baseUrlPath=studio`. The proxy target is `http://127.0.0.1:8501/studio/`; adding another `studio` would produce `/studio/studio/`.
- Both processes use the same environment and the same Django database.
- The startup script waits for Django and Streamlit health checks before exposing Nginx on port 7860.
- If Django or Streamlit dies, the startup script exits and the container restarts/fails visibly instead of serving a half-working site.

### 1. Create the Space

1. Sign in to Hugging Face.
2. Create a new **Docker** Space.
3. Choose the free hardware initially. Hardware and storage availability can change, so follow the options shown by Hugging Face.
4. The included `README.md` front matter already declares:

```yaml
sdk: docker
app_port: 7860
```

Do not change `app_port` unless you also change the Nginx `listen` port and `PORT` environment value.

### 2. Push the source

Create an empty Space repository, then clone it locally:

```cmd
git clone https://huggingface.co/spaces/YOUR-HF-USERNAME/YOUR-SPACE-NAME
```

Copy the **contents** of the project folder into the cloned Space folder. In File Explorer, enable hidden items and include:

- `Dockerfile`, `requirements.txt`, `manage.py`, `README.md`, `DEPLOYMENT_GUIDE.md`
- `config`, `store`, `streamlit_app`, `templates`, `static`, `deploy`
- `.dockerignore`, `.gitignore`, `.gitattributes`, `.env.example`

Do **not** copy:

- `.env`
- `.venv`, `.venv-test`, or any virtual environment
- `db.sqlite3`
- `media/`, `staticfiles/`
- `outputs/`, `work/`, `agent_snapshot.json`
- the original project `.git` folder

Keep the `.git` folder created by the Space clone.

Commit and push from the Space clone folder:

```cmd
git add .
git commit -m "Deploy AI Product Assistant"
git push
```

If Git asks for credentials, use a Hugging Face access token with write access. You can also upload files through the Space's **Files** tab, but Git is easier for a full project.

### 3. Variables versus Secrets

Hugging Face exposes two configuration lists:

| Kind | Visibility | Use it for |
| --- | --- | --- |
| **Variables** | Visible with the Space configuration; treat as public | Non-sensitive switches such as model names, provider names, usernames, hosts |
| **Secrets** | Hidden value; not shown in the UI or logs | Passwords, API tokens, `SECRET_KEY`, database URLs containing passwords |

Never put a private token in a Variable, the Dockerfile, `README.md`, `.env.example`, source code, or a screenshot.

Open **Space → Settings → Variables and secrets** and add the following.

#### Required/recommended Secrets

| Name | Example / how to produce it | Why |
| --- | --- | --- |
| `SECRET_KEY` | Run `py -3 -c "import secrets; print(secrets.token_urlsafe(64))"` | Django signing key. If omitted, `start.sh` generates an ephemeral key and sessions reset on restart. |
| `STREAMLIT_API_TOKEN` | Run `py -3 -c "import secrets; print(secrets.token_urlsafe(32))"` | Authenticates Streamlit write requests to Django. If omitted, an ephemeral token is generated each boot. |
| `STREAMLIT_CREATOR_PASSWORD` | A password you choose | Unlocks the Streamlit **AI Product Creator** tab. If omitted, the creator stays locked. |
| `DEPLOY_ADMIN_PASSWORD` | A strong password you choose | Creates/synchronizes the Django Admin login on every boot. If omitted, `/admin/` has no password login (the service account has an unusable password). |
| `HF_API_TOKEN` | Hugging Face token with Inference Providers access | Enables real AI descriptions, prices, chat, and image generation. Without it, the app uses the clearly labelled offline fallback. |

Optional Secret:

| Name | Use |
| --- | --- |
| `DATABASE_URL` | Full PostgreSQL URL, for example `postgresql://user:password@host:5432/dbname`. It contains a password, so it must be a Secret. |

#### Variables

| Name | Value |
| --- | --- |
| `AI_PROVIDER` | `huggingface` |
| `ALLOWED_HOSTS` | `.hf.space,localhost,127.0.0.1` |
| `STREAMLIT_API_USER` | `storeadmin` |
| `DEPLOY_ADMIN_USERNAME` | `storeadmin` |
| `DEPLOY_ADMIN_EMAIL` | Your email address |
| `HF_TEXT_MODEL` | `meta-llama/Llama-3.2-3B-Instruct` |
| `HF_INFERENCE_PROVIDER` | `auto` |
| `HF_MAX_TOKENS` | `260` |
| `AI_TIMEOUT_SECONDS` | `30` |

The Dockerfile already supplies these defaults, so you only need to override them if you change the design:

```text
DEBUG=False
DB_ENGINE=sqlite
SQLITE_PATH=/data/db.sqlite3
MEDIA_ROOT=/data/media
DJANGO_BASE_URL=http://127.0.0.1:8000
DEPLOY_ADMIN_USERNAME=storeadmin
STREAMLIT_API_USER=storeadmin
GUNICORN_WORKERS=2
```

Important behavior:

- `DEPLOY_ADMIN_PASSWORD` is the source of truth. `bootstrap_deploy_admin` resets the admin password to the Secret on every container start.
- `STREAMLIT_API_USER` must be an active staff user. The bootstrap command creates it with an unusable password if it does not exist.
- If you change `DEPLOY_ADMIN_USERNAME`, either set `STREAMLIT_API_USER` to that same staff username or keep a separate staff service account.
- For a custom domain, add that hostname to `ALLOWED_HOSTS` and its HTTPS origin to `CSRF_TRUSTED_ORIGINS`.
- Do not set `OLLAMA_BASE_URL=localhost` on the Space. Ollama on your PC is not reachable inside the container; use Hugging Face or the offline fallback.

Save the settings. The Space rebuilds/restarts.

### 4. What happens at startup

`deploy/start.sh` runs:

1. Creates `/data/media` and the SQLite directory.
2. Uses `SECRET_KEY` and `STREAMLIT_API_TOKEN` from Secrets; generates ephemeral values only if they are missing (with warnings).
3. `python manage.py migrate --noinput`
4. `python manage.py seed_data` (idempotent; curated demo copy is **not** replaced by AI)
5. `python manage.py bootstrap_deploy_admin` (service user and admin)
6. `python manage.py collectstatic --noinput`
7. Starts Gunicorn on `127.0.0.1:8000`.
8. Starts Streamlit on `127.0.0.1:8501` with base path `studio`.
9. Polls `http://127.0.0.1:8000/api/products/` and `http://127.0.0.1:8501/studio/_stcore/health` until both are ready.
10. Starts Nginx on port 7860.

If either app fails to become ready within about two minutes, the script prints an error and exits. Check the Space **Logs** tab.

### 5. Verify the deployment

Only after the Space status is **Running**:

1. Open `https://YOUR-SPACE-SUBDOMAIN.hf.space/`.
   - Expect the Aster & Oak sign-in/landing page.
2. Sign in with `storeadmin` and the `DEPLOY_ADMIN_PASSWORD` Secret.
3. Open `/admin/` and confirm the 16 products exist with source columns.
4. Open `/studio/`.
   - Expect **Product Catalog**, **AI Product Creator**, and **Grounded AI Chat**.
   - Images should render from the bundled files.
5. Unlock the creator with `STREAMLIT_CREATOR_PASSWORD`, create a test product with a blank description and price, and confirm the success/warning text says either **AI generated** or **offline fallback (not AI)**. Delete the test product afterwards if desired.
6. Ask the chat a catalog question. Confirm the answer is grounded and the source caption is shown.
7. Restart the Space and check whether data persisted. Without persistent `/data` storage, SQLite and uploads can be lost.

Do not state that deployment succeeded based only on a successful build. Confirm the Space is Running and these pages load.

### 6. Persistence

The default SQLite database is `/data/db.sqlite3` and uploads are `/data/media/`.

Hugging Face Docker Spaces use ephemeral storage unless persistent storage is attached. On a free ephemeral Space:

- The catalog reseeds on restart.
- Admin-created products can disappear.
- Uploaded photos can disappear.
- The bundled demo photos still work because they are inside the image/static files.

For durability, attach read/write persistent storage at `/data` if your Space plan supports it, or set a reachable PostgreSQL `DATABASE_URL`. Hugging Face's storage and hardware offerings change, so use the current Space settings rather than assuming a free tier includes persistence.

For PostgreSQL, set the whole URL as a **Secret**:

```text
postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

`config/settings.py` reads `DATABASE_URL`, supports SSL mode, and uses `psycopg[binary]`. Database tables are created by `migrate`; demo products are seeded by `seed_data`. Uploaded product photos still use the local filesystem unless you also externalize media storage.

### 7. AI on the Space

`AI_PROVIDER=huggingface` means blank descriptions/prices and chat call Hugging Face Inference Providers. The token is read from `HF_API_TOKEN` or `HUGGINGFACEHUB_API_TOKEN`.

- If the token is absent, invalid, the model is unavailable, or the request times out, the app uses the offline fallback.
- The persisted `description_source` / `price_source` will be `fallback`, and the UI will say **Offline fallback (not AI)**.
- `ai_enhanced` is only true for a real AI provider result.
- Choose a text model your token/provider can actually serve. `HF_TEXT_MODEL` and `HF_INFERENCE_PROVIDER` are Variables because they are not secret.
- `HF_API_TOKEN` is a Secret because it grants access.
- Never put the token in `streamlit_app/app.py`, `Dockerfile`, `.env.example`, or the README.

The Streamlit app reads the same environment variables inside the container. `DJANGO_BASE_URL` points to the internal Gunicorn address, not the public URL.

### 8. Optional local Docker test

If Docker Desktop is available on your machine, you can test the image locally. Do not reuse your local `.env`, which contains local secrets and `DEBUG=True`.

```cmd
docker build -t ai-product-assistant .
docker run --rm -p 7860:7860 ^
  -e DEBUG=False ^
  -e SECRET_KEY=replace-with-a-long-random-value ^
  -e STREAMLIT_API_TOKEN=replace-with-a-random-token ^
  -e STREAMLIT_CREATOR_PASSWORD=replace-with-a-password ^
  -e DEPLOY_ADMIN_USERNAME=storeadmin ^
  -e DEPLOY_ADMIN_PASSWORD=replace-with-a-password ^
  -e ALLOWED_HOSTS=localhost,127.0.0.1 ^
  -e AI_PROVIDER=offline ^
  ai-product-assistant
```

Then open <http://127.0.0.1:7860/> and <http://127.0.0.1:7860/studio/>. These are placeholder values for a local test only; do not commit them.

Docker was not installed on the development machine, so this repository's image has not been built there.

---

## C. Troubleshooting

### Local Windows

| Problem | Fix |
| --- | --- |
| Python is not found | Install Python 3.12+ with PATH enabled, reopen the terminal, verify `py --list`. |
| `run_project.bat` stops while creating `.venv` | Delete `.venv`, confirm the interpreter version, and rerun. |
| `pip install` fails while building Pillow/psycopg | Use Python 3.12/3.13/3.14 and a current pip; run `python -m pip install --upgrade pip` inside `.venv`. |
| `No module named django` | Activate `.venv` (`\.venv\Scripts\activate`) and install requirements. |
| `SECRET_KEY is required` | Run `python manage.py prepare_local_env` or add `SECRET_KEY` to `.env`. |
| Migrations fail with a PostgreSQL password error | Fix `.env`, or switch to `DB_ENGINE=sqlite` and leave `DATABASE_URL` blank. |
| Ollama says port 11434 is already in use | Ollama is already running; do not start a second server. |
| AI is always fallback | Check provider settings and test with the one-line Python command in README. A fallback label is correct when AI is unavailable. |
| Streamlit cannot reach Django | Django must be running at `DJANGO_BASE_URL` (default `http://127.0.0.1:8000`). |
| Admin password forgotten | Set `DEPLOY_ADMIN_PASSWORD` in `.env`, run `bootstrap_deploy_admin`, or use `changepassword`. |

### Space build and runtime

| Problem | Fix |
| --- | --- |
| Build fails installing packages | Open **Logs → Build** and read the first error. Confirm `requirements.txt` was uploaded and the Space is a Docker Space. |
| Build succeeds but status is not Running | Check **Logs → Container**. Missing `SECRET_KEY` used to be fatal; the startup script now generates an ephemeral key with a warning, so look for the real startup error. |
| `DisallowedHost` | Add `.hf.space` and any custom domain to `ALLOWED_HOSTS`, then restart. |
| `/studio/` returns 404 or blank page | Confirm Streamlit started with `--server.baseUrlPath=studio` and Nginx proxies `/studio/` to `http://127.0.0.1:8501/studio/`; check the health URL `/studio/_stcore/health`. |
| `/studio` redirects repeatedly | Keep the exact `location = /studio { return 301 /studio/; }` rule and let Streamlit own `/studio/`. |
| Static CSS/JS returns 404 | `collectstatic` must run before Gunicorn; WhiteNoise serves `/static/`. Check the Docker startup log. |
| Uploaded images return 404 | Nginx serves `/media/` from `/data/media/`; confirm `MEDIA_ROOT=/data/media` and the uploaded file exists. |
| `CSRF verification failed` after custom domain | Add the HTTPS origin to `CSRF_TRUSTED_ORIGINS` and include the host in `ALLOWED_HOSTS`. |
| Admin password changes revert after restart | This is intentional: `DEPLOY_ADMIN_PASSWORD` is reapplied on every boot. |
| Streamlit creator says the token is missing or 401/403 | Set `STREAMLIT_API_TOKEN` as a Space Secret, use the same value in the container, and set `STREAMLIT_API_USER` to an active staff username. |
| AI always fallback on the Space | Verify `HF_API_TOKEN`, `HF_TEXT_MODEL`, and provider availability. Check container logs for the AI warning. |
| Data disappears after restart | Free Space storage is ephemeral. Attach `/data` persistent storage or use PostgreSQL; uploaded media needs persistent storage too. |
| `database is locked` under writes | SQLite with multiple Gunicorn workers can lock. Set `GUNICORN_WORKERS=1` as a Space Variable, or move to PostgreSQL. |
| `/admin/` login is impossible | Set `DEPLOY_ADMIN_PASSWORD` and `DEPLOY_ADMIN_USERNAME`, restart, then use those credentials. |
| Space logs show ephemeral SECRET_KEY/token warnings | Add the corresponding Space Secrets for stable sessions and API auth. |

### Optional Streamlit Community Cloud

Community Cloud hosts Streamlit only. It needs a publicly reachable Django API, which this project already exposes. In the Community Cloud app's Secrets:

```toml
DJANGO_BASE_URL = "https://YOUR-DJANGO-HOST"
STREAMLIT_API_TOKEN = "same-token-as-django"
STREAMLIT_CREATOR_PASSWORD = "private-password"
```

The Django host must run with the same `STREAMLIT_API_TOKEN` and an active staff `STREAMLIT_API_USER`. This is a separate architecture from the single Docker Space and is not required for the assignment.

---

## D. Submission checklist

- Submit the complete source ZIP, excluding `.env`, virtual environments, local databases, media/static output, and generated images/artifacts.
- If you deploy, submit the Space URL only after it reaches **Running** and you have opened `/` and `/studio/`.
- Include screenshots of the storefront, product detail, management page, Admin product list, Streamlit catalog, a generated product's AI/fallback label, and catalog chat.
- State the configured AI provider and be explicit that fallback output is rule-based and not AI.
- Never include secrets, `.env`, tokens, or passwords in the ZIP, screenshots, or README.
