"""Core Python helpers used by the catalog and AI workflows."""
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from functools import wraps
import logging
import os
import re
import time

logger = logging.getLogger("store.ai")

MAX_INR_PRICE = Decimal("10000000")


class BaseAIEngine(ABC):
    """Abstract engine contract; credentials are encapsulated by implementations."""

    def __init__(self, timeout=None):
        raw_timeout = timeout if timeout is not None else os.getenv("AI_TIMEOUT_SECONDS", "30")
        self._timeout = max(float(raw_timeout), 1.0)

    @abstractmethod
    def generate(self, prompt: str) -> str: ...


def log_ai_execution(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            logger.info("%s completed in %.3fs", fn.__name__, time.perf_counter() - started)
    return wrapper


def product_batch_generator(products, batch_size=50):
    """Yield database iterables in bounded batches."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    batch = []
    for product in products:
        batch.append(product)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def recursive_loyalty_discount(price, tier, step=0):
    """Apply a tier's total savings via bounded recursive compounding."""
    rates = {"bronze": Decimal("0.02"), "silver": Decimal("0.04"), "gold": Decimal("0.07"), "platinum": Decimal("0.10")}
    amount = Decimal(str(price))
    if amount < 0:
        raise ValueError("price cannot be negative")
    if tier not in rates:
        return amount.quantize(Decimal("0.01"))
    installments = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 5}[tier]
    if step >= installments:
        return amount.quantize(Decimal("0.01"))
    per_step = Decimal("1") - (Decimal("1") - rates[tier]) ** (Decimal("1") / Decimal(installments))
    return recursive_loyalty_discount(amount * (Decimal("1") - per_step), tier, step + 1)


_CURRENCY_PATTERNS = (
    re.compile(r"(?:₹|INR|Rs\.?)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE),
    re.compile(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:₹|INR|Rs\.?|rupees)\b", re.IGNORECASE),
)
_PLAIN_NUMBER = re.compile(r"(?<![\w.])([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{2,7})(?:\.[0-9]{1,2})?(?![\w.])")


def parse_price(text, minimum=Decimal("1")):
    """Extract a plausible INR price, preferring explicitly currency-marked numbers."""
    text = str(text or "")
    for pattern in _CURRENCY_PATTERNS:
        for raw in pattern.findall(text):
            value = _to_decimal(raw)
            if value is not None and Decimal(minimum) <= value <= MAX_INR_PRICE:
                return value.quantize(Decimal("0.01"))
    for raw in _PLAIN_NUMBER.findall(text):
        value = _to_decimal(raw)
        # Avoid picking model names or token counts when no currency is stated.
        if value is not None and Decimal("49") <= value <= MAX_INR_PRICE:
            return value.quantize(Decimal("0.01"))
    raise ValueError("No valid INR price found in the AI response")


def _to_decimal(raw):
    try:
        return Decimal(str(raw).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def normalize_names(products):
    """Example lambda map/filter operations useful to catalog consumers."""
    names = list(map(lambda p: p.name.strip(), products))
    return list(filter(lambda name: bool(name), names))
