"""Automatic checks that keep the shop agent honest.

1. verify_chat_reply   - runs after every customer chat. Every price, stock count and
                         product card in the agent's reply must match what the tools
                         actually read from the database during that conversation turn.
2. check_inventory     - inventory consistency check. Meant to run after every purchase;
                         the shop has no purchase flow yet, so it runs at startup and hourly.
3. run_tool_checks     - hourly health test. Runs every agent tool against every product and
                         compares the answers with direct SQL reads of campus_customs.db.

Results are logged and appended to backend/logs/checks.jsonl.
"""

import json
import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_core import to_jsonable_python

import tools
from models import ShopDeps, ShopReply

logger = logging.getLogger("campus_customs.checks")

LOG_PATH = Path(__file__).resolve().parent / "logs" / "checks.jsonl"
EXPECTED_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


class CheckReport(BaseModel):
    check: str
    passed: bool
    ran_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    duration_ms: int = 0
    checked: int = 0
    issues: list[str] = []
    detail: dict[str, Any] = {}


def record(report: CheckReport) -> CheckReport:
    """Log a report and append it to logs/checks.jsonl."""
    level = logging.INFO if report.passed else logging.WARNING
    logger.log(level, "%s %s (%d checked, %d issues)", report.check,
               "PASSED" if report.passed else "FAILED", report.checked, len(report.issues))
    for issue in report.issues[:20]:
        logger.log(level, "  - %s", issue)
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(report.model_dump_json() + "\n")
    except OSError:
        logger.exception("Could not write %s", LOG_PATH)
    return report


# ---------------------------------------------------------------------------
# 1. After every customer interaction
# ---------------------------------------------------------------------------

PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
QUANTITY_RE = re.compile(
    r"\b(\d{1,4})\s+(?:\w+\s+){0,2}?(?:left|in stock|available|remaining|units?)\b", re.IGNORECASE
)
SOLD_OUT_RE = re.compile(r"\bsold[\s-]out\b|\bout of stock\b", re.IGNORECASE)


def _walk(value: Any) -> Iterable[dict]:
    """Yield every dict inside nested tool results."""
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)


def facts_from_messages(messages: list[ModelMessage]) -> dict[str, set]:
    """Collect the product ids, prices and quantities the tools returned in this run."""
    facts: dict[str, set] = {"product_ids": set(), "prices": set(), "quantities": set(), "sold_out": set()}
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, ToolReturnPart):
                continue
            for d in _walk(to_jsonable_python(part.content)):
                if "product_id" in d:
                    facts["product_ids"].add(d["product_id"])
                if isinstance(d.get("price"), (int, float)):
                    facts["prices"].add(round(float(d["price"]), 2))
                for key in ("quantity", "total_stock"):
                    if isinstance(d.get(key), int):
                        facts["quantities"].add(d[key])
                if d.get("quantity") == 0 or d.get("in_stock") is False or d.get("total_stock") == 0:
                    facts["sold_out"].add(d.get("product_id") or d.get("size") or "?")
    return facts


def verify_chat_reply(answer: ShopReply, messages: list[ModelMessage], question: str = "") -> CheckReport:
    """Check that the reply only states facts the database tools actually returned."""
    start = time.perf_counter()
    facts = facts_from_messages(messages)
    issues: list[str] = []
    text = f"{answer.reply} {answer.follow_up_question or ''}"

    prices = [round(float(p.replace(",", "")), 2) for p in PRICE_RE.findall(text)]
    for price in prices:
        if price not in facts["prices"]:
            issues.append(f"Reply quotes ${price:.2f}, which no tool returned from the database.")

    quantities = [int(q) for q in QUANTITY_RE.findall(text)]
    for qty in quantities:
        if qty not in facts["quantities"]:
            issues.append(f"Reply states a stock count of {qty}, which no tool returned.")

    for pid in answer.product_ids:
        if pid not in facts["product_ids"]:
            issues.append(f"Product card '{pid}' was not returned by any tool in this conversation turn.")

    if SOLD_OUT_RE.search(answer.reply) and not facts["sold_out"]:
        issues.append("Reply says something is sold out, but no tool returned a sold-out size.")

    if (prices or quantities) and not any(facts.values()):
        issues.append("Reply gives prices or stock without looking anything up in the database.")

    return CheckReport(
        check="chat_reply_facts",
        passed=not issues,
        duration_ms=int((time.perf_counter() - start) * 1000),
        checked=len(prices) + len(quantities) + len(answer.product_ids),
        issues=issues,
        detail={"question": question[:200], "prices_quoted": prices, "quantities_quoted": quantities,
                "cards": answer.product_ids},
    )


# ---------------------------------------------------------------------------
# 2. Inventory consistency (run after every purchase)
# ---------------------------------------------------------------------------

def check_inventory(db_path: Path) -> CheckReport:
    """Make sure the inventory table is complete and sensible."""
    start = time.perf_counter()
    issues: list[str] = []
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        products = {r[0] for r in conn.execute("SELECT product_id FROM catalogue")}
        rows = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    finally:
        conn.close()

    sizes_by_product: dict[str, set[str]] = {}
    for pid, size, qty in rows:
        if pid not in products:
            issues.append(f"Inventory row for unknown product '{pid}'.")
        if size not in EXPECTED_SIZES:
            issues.append(f"{pid}: unexpected size '{size}'.")
        if not isinstance(qty, int) or qty < 0:
            issues.append(f"{pid} {size}: invalid quantity {qty!r}.")
        sizes_by_product.setdefault(pid, set()).add(size)

    for pid in sorted(products):
        missing = [s for s in EXPECTED_SIZES if s not in sizes_by_product.get(pid, set())]
        if missing:
            issues.append(f"{pid}: no inventory row for size(s) {', '.join(missing)}.")

    return CheckReport(
        check="inventory_consistency",
        passed=not issues,
        duration_ms=int((time.perf_counter() - start) * 1000),
        checked=len(rows),
        issues=issues,
        detail={"products": len(products), "inventory_rows": len(rows),
                "sold_out_rows": sum(1 for _, _, q in rows if q == 0),
                "units_in_stock": sum(q for _, _, q in rows if isinstance(q, int) and q > 0)},
    )


# ---------------------------------------------------------------------------
# 3. Hourly tool health test
# ---------------------------------------------------------------------------

def run_tool_checks(db_path: Path) -> CheckReport:
    """Run every agent tool against every product and compare with direct SQL."""
    start = time.perf_counter()
    issues: list[str] = []
    checked = 0
    ctx = SimpleNamespace(deps=ShopDeps(db_path=Path(db_path)))

    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        catalogue = {r["product_id"]: r for r in conn.execute("SELECT * FROM catalogue")}
        stock = {(r["product_id"], r["size"]): r["quantity"]
                 for r in conn.execute("SELECT product_id, size, quantity FROM inventory")}
    finally:
        conn.close()

    for pid, row in catalogue.items():
        try:
            detail = tools.get_product_details(ctx, pid)
        except Exception as exc:  # a tool must never crash
            issues.append(f"get_product_details('{pid}') raised {type(exc).__name__}: {exc}")
            continue
        checked += 1
        if isinstance(detail, str):
            issues.append(f"get_product_details('{pid}') could not find a product that exists.")
            continue
        if detail.price != row["price"]:
            issues.append(f"{pid}: tool price {detail.price} != database {row['price']}.")
        if detail.description != row["description"]:
            issues.append(f"{pid}: tool description differs from the database.")
        if detail.colors != json.loads(row["colors"]):
            issues.append(f"{pid}: tool colors differ from the database.")
        expected_total = sum(q for (p, _), q in stock.items() if p == pid)
        if detail.total_stock != expected_total:
            issues.append(f"{pid}: tool total_stock {detail.total_stock} != database {expected_total}.")

        for size in EXPECTED_SIZES:
            if (pid, size) not in stock:
                continue
            try:
                result = tools.check_stock(ctx, pid, size)
            except Exception as exc:
                issues.append(f"check_stock('{pid}', '{size}') raised {type(exc).__name__}: {exc}")
                continue
            checked += 1
            expected = stock[(pid, size)]
            if isinstance(result, str):
                issues.append(f"check_stock('{pid}', '{size}') returned an error: {result}")
            elif result.quantity != expected or result.in_stock != (expected > 0):
                issues.append(f"{pid} {size}: tool says {result.quantity}, database says {expected}.")

    # Unknown inputs must be handled politely, not crash.
    for label, call in [
        ("get_product_details(unknown id)", lambda: tools.get_product_details(ctx, "no-such-product")),
        ("check_stock(unknown size)", lambda: tools.check_stock(ctx, next(iter(catalogue)), "XXXL")),
        ("check_stock(size word)", lambda: tools.check_stock(ctx, next(iter(catalogue)), "medium")),
    ]:
        checked += 1
        try:
            result = call()
            if label == "check_stock(size word)" and (isinstance(result, str) or result.size != "M"):
                issues.append(f"{label}: 'medium' was not understood as M.")
            elif label != "check_stock(size word)" and not isinstance(result, str):
                issues.append(f"{label}: expected a 'not found' message.")
        except Exception as exc:
            issues.append(f"{label} raised {type(exc).__name__}: {exc}")

    # search_products: every result must be real and respect the filters.
    searches = [
        {"garment_type": "hoodie"},
        {"color": "navy", "max_price": 70},
        {"query": "hockey"},
        {"size": "L", "in_stock_only": True},
    ]
    for args in searches:
        checked += 1
        try:
            results = tools.search_products(ctx, **args)
        except Exception as exc:
            issues.append(f"search_products({args}) raised {type(exc).__name__}: {exc}")
            continue
        if not results:
            issues.append(f"search_products({args}) returned nothing.")
        for r in results:
            db = catalogue.get(r.product_id)
            if db is None:
                issues.append(f"search_products({args}) returned unknown product '{r.product_id}'.")
                continue
            if r.price != db["price"]:
                issues.append(f"search_products: {r.product_id} price {r.price} != database {db['price']}.")
            if "max_price" in args and r.price > args["max_price"]:
                issues.append(f"search_products({args}): {r.product_id} is over the max price.")
            if args.get("size") and args["size"] not in r.sizes_in_stock:
                issues.append(f"search_products({args}): {r.product_id} is not in stock in {args['size']}.")

    return CheckReport(
        check="tool_health",
        passed=not issues,
        duration_ms=int((time.perf_counter() - start) * 1000),
        checked=checked,
        issues=issues,
        detail={"products": len(catalogue), "size_rows": len(stock)},
    )
