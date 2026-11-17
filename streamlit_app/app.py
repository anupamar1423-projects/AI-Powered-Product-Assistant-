"""Streamlit studio that talks to Django over its REST endpoints."""
import hmac
import os
from pathlib import Path
from urllib.parse import urljoin

import requests
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
# Django loads .env itself; Streamlit needs the same file for local API tokens.
load_dotenv(BASE_DIR / ".env")


def setting(name, default=""):
    """Read regular environment variables (Docker) or Streamlit secrets."""
    value = os.getenv(name)
    if value is not None and str(value).strip() != "":
        return str(value)
    try:
        secret = st.secrets.get(name, default)
        return str(secret) if secret is not None else default
    except Exception:
        return default


st.set_page_config(page_title="Aster & Oak · Product Studio", page_icon="✦", layout="wide")

API_BASE = setting("DJANGO_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = setting("STREAMLIT_API_TOKEN")
CREATOR_PASSWORD = setting("STREAMLIT_CREATOR_PASSWORD")
PRODUCTS_URL = f"{API_BASE}/api/products/"
CHAT_URL = f"{API_BASE}/api/assistant/chat/"


def api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}


st.markdown(
    "<style>.block-container{max-width:1180px;padding-top:2rem}.hero{padding:2rem 0 1rem;border-bottom:1px solid #ddd}"
    ".muted{color:#777}</style>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='hero'><div class='muted'>ASTER &amp; OAK · MERCHANDISING STUDIO</div>"
    "<h1>Product Assistant</h1><p class='muted'>A live catalog, with a little intelligence built in.</p></div>",
    unsafe_allow_html=True,
)

catalog_tab, creator_tab, chat_tab = st.tabs(["Product Catalog", "AI Product Creator", "Grounded AI Chat"])


def fetch_products():
    response = requests.get(PRODUCTS_URL, headers=api_headers(), timeout=25)
    response.raise_for_status()
    data = response.json()
    return data.get("results", data) if isinstance(data, dict) else data


@st.cache_data(show_spinner=False, ttl="1h", max_entries=64)
def fetch_image_bytes(url):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.content


def show_image(product):
    image_url = product.get("image_url") or ""
    sku = product.get("sku", "")
    alt = f"Photo of {product.get('name') or sku or 'product'}"
    bundled = BASE_DIR / "static" / "store" / "images" / f"{sku}.jpg"
    if bundled.exists():
        st.image(str(bundled), width="stretch", alt=alt)
        return
    if image_url:
        absolute_url = image_url if image_url.startswith(("http://", "https://")) else urljoin(API_BASE + "/", image_url.lstrip("/"))
        try:
            st.image(fetch_image_bytes(absolute_url), width="stretch", alt=alt)
        except requests.RequestException:
            st.caption("Image unavailable")


def source_caption(product):
    labels = []
    if product.get("ai_enhanced"):
        labels.append("✦ AI assisted")
    if "fallback" in {product.get("description_source"), product.get("price_source")}:
        labels.append("Offline fallback (not AI)")
    if labels:
        st.caption(" · ".join(labels))
    provenance = []
    if product.get("description_source_label"):
        provenance.append(f"Description: {product['description_source_label']}")
    if product.get("price_source_label"):
        provenance.append(f"Price: {product['price_source_label']}")
    if provenance:
        st.caption(" · ".join(provenance))


def catalog():
    try:
        products = fetch_products()
    except requests.RequestException as exc:
        st.error(
            f"Cannot reach the Django API at {API_BASE}. Check DJANGO_BASE_URL and that Django is running. Details: {exc}"
        )
        return
    categories = ["All categories"] + sorted({p.get("category_label", p.get("category", "")) for p in products})
    chosen = st.selectbox("Category", categories)
    query = st.text_input("Search the live catalog", placeholder="Name, category, SKU…").strip().lower()
    visible = [p for p in products if chosen == "All categories" or p.get("category_label", p.get("category")) == chosen]
    if query:
        visible = [
            p for p in visible
            if query in " ".join(
                [p.get("name", ""), p.get("sku", ""), p.get("description", ""), p.get("category_label", "")]
            ).lower()
        ]
    if not visible:
        st.info("No products match this view yet.")
        return
    cols = st.columns(4)
    for index, product in enumerate(visible):
        with cols[index % 4]:
            show_image(product)
            st.caption(product.get("sku", ""))
            st.subheader(product.get("name", "Product"))
            st.write(product.get("description", ""))
            price = product.get("price")
            st.markdown(
                f"**₹{float(price):,.0f}** · {product.get('stock', 0)} in stock"
                if price is not None else "**Price on request**"
            )
            source_caption(product)


with catalog_tab:
    catalog()

with creator_tab:
    st.write(
        "Store owners can create catalog items here. A blank description or price is completed before saving; "
        "the result states whether AI or the offline fallback produced it."
    )
    if not CREATOR_PASSWORD:
        st.warning("Set STREAMLIT_CREATOR_PASSWORD in .env or the Space secrets to unlock product creation.")
    elif not st.session_state.get("creator_authenticated", False):
        with st.form("creator_unlock"):
            entered = st.text_input("Store owner password", type="password")
            unlock = st.form_submit_button("Unlock product creator")
        if unlock:
            if hmac.compare_digest(entered, CREATOR_PASSWORD):
                st.session_state["creator_authenticated"] = True
                st.rerun()
            st.error("That password did not match.")
    elif not API_TOKEN:
        st.error("STREAMLIT_API_TOKEN is missing. Add it to .env and restart both services.")
    else:
        with st.form("creator"):
            sku = st.text_input("SKU")
            name = st.text_input("Product name")
            category = st.selectbox(
                "Category",
                [
                    ("electronics", "Electronics"),
                    ("home_appliances", "Home Appliances"),
                    ("fashion_sports", "Fashion & Sports"),
                    ("furniture_office", "Furniture & Office"),
                ],
                format_func=lambda row: row[1],
            )
            description = st.text_area("Description (optional)")
            price = st.number_input("Price in INR (0 = let AI estimate)", min_value=0.0, step=100.0)
            stock = st.number_input("Stock", min_value=0, step=1)
            submitted = st.form_submit_button("Create with AI")
        if submitted:
            if not sku.strip() or not name.strip():
                st.error("SKU and product name are required.")
            else:
                payload = {
                    "sku": sku.strip(),
                    "name": name.strip(),
                    "category": category[0],
                    "description": description.strip(),
                    "stock": int(stock),
                }
                if price > 0:
                    payload["price"] = price
                try:
                    response = requests.post(
                        PRODUCTS_URL, json=payload, headers=api_headers(), timeout=120
                    )
                    if response.ok:
                        data = response.json()
                        fallback = "fallback" in {data.get("description_source"), data.get("price_source")}
                        if data.get("ai_enhanced"):
                            st.success(f"Created {data.get('name', name)}. AI generated at least one missing field.")
                        if fallback:
                            st.warning(
                                f"Created {data.get('name', name)}. AI did not provide a usable value; "
                                "the offline fallback (not AI) drafted the missing field(s). Review before publishing."
                            )
                        if not data.get("ai_enhanced") and not fallback:
                            st.success(f"Created {data.get('name', name)} with all supplied details.")
                        if data.get("ai_reasoning"):
                            st.caption(data["ai_reasoning"])
                        st.caption(
                            f"Description: {data.get('description_source_label', '—')} · "
                            f"Price: {data.get('price_source_label', '—')}"
                        )
                    else:
                        st.error(f"Django rejected the product ({response.status_code}): {response.text[:500]}")
                except requests.RequestException as exc:
                    st.error(f"Could not reach Django: {exc}")

with chat_tab:
    st.write("Answers are grounded in the current Django catalog and say when the catalog cannot confirm something.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for item in st.session_state.chat_history:
        role, message = item[0], item[1]
        source = item[2] if len(item) > 2 else ""
        st.chat_message(role).write(message)
        if source:
            st.caption(source)
    question = st.chat_input("Ask about a product, price or stock…")
    if question:
        st.session_state.chat_history.append(("user", question, ""))
        st.chat_message("user").write(question)
        try:
            response = requests.post(CHAT_URL, json={"question": question}, headers=api_headers(), timeout=120)
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "No answer returned.")
            source = data.get("source_label", "")
        except requests.RequestException as exc:
            answer = f"The Django assistant is unavailable at the moment: {exc}"
            source = ""
        st.session_state.chat_history.append(("assistant", answer, source))
        st.chat_message("assistant").write(answer)
        if source:
            st.caption(source)
