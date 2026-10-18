"""Checkout: turns a shopper's cart into an order and takes the items out of inventory.

This is a class project, so no payment is collected. Prices always come from the
catalogue table (never from the browser), and stock is checked and reduced in a
single database transaction so two shoppers can't buy the last item twice.

After every purchase the inventory test runs: each purchased size must have gone
down by exactly the quantity bought, and the whole inventory table must still be
consistent (see checks.check_inventory).
"""

import logging
import sqlite3

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from auth import current_user_id
from checks import CheckReport, check_inventory, record
import db
from db import get_db

logger = logging.getLogger("campus_customs.orders")

router = APIRouter(prefix="/api")

MAX_QTY_PER_LINE = 10


def init_orders_tables() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                size TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
            );
            """
        )


class OrderLineIn(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(ge=1, le=MAX_QTY_PER_LINE)


class OrderIn(BaseModel):
    items: list[OrderLineIn] = Field(min_length=1, max_length=50)


class OrderLineOut(BaseModel):
    product_id: str
    name: str
    size: str
    quantity: int
    unit_price: float
    line_total: float


class OrderOut(BaseModel):
    order_id: int
    total: float
    created_at: str
    items: list[OrderLineOut]
    inventory_check: CheckReport | None = None


def _require_user(authorization: str | None) -> int:
    user_id = current_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Please log in to check out.")
    return user_id


def verify_purchase(expected_after: dict[tuple[str, str], int]) -> CheckReport:
    """After-purchase test: purchased sizes went down by exactly what was bought."""
    issues: list[str] = []
    with get_db() as conn:
        for (pid, size), expected in expected_after.items():
            row = conn.execute(
                "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (pid, size)
            ).fetchone()
            actual = row["quantity"] if row else None
            if actual != expected:
                issues.append(f"{pid} {size}: expected {expected} left after purchase, found {actual}.")
    table_check = check_inventory(db.DB_PATH)
    issues.extend(table_check.issues)
    return CheckReport(
        check="inventory_after_purchase",
        passed=not issues,
        checked=len(expected_after) + table_check.checked,
        issues=issues,
        detail={"purchased_sizes": len(expected_after), **table_check.detail},
    )


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def place_order(body: OrderIn, authorization: str | None = Header(default=None)) -> OrderOut:
    user_id = _require_user(authorization)

    # Combine duplicate lines (same product and size) so stock is checked on the total.
    wanted: dict[tuple[str, str], int] = {}
    for line in body.items:
        key = (line.product_id, line.size.strip().upper())
        wanted[key] = wanted.get(key, 0) + line.quantity

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")  # lock the database for this purchase
        lines: list[OrderLineOut] = []
        expected_after: dict[tuple[str, str], int] = {}
        for (pid, size), qty in wanted.items():
            row = conn.execute(
                "SELECT c.name, c.price, i.quantity FROM catalogue c "
                "JOIN inventory i ON i.product_id = c.product_id "
                "WHERE c.product_id = ? AND i.size = ?",
                (pid, size),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"{pid} in size {size} was not found.")
            if row["quantity"] < qty:
                left = row["quantity"]
                msg = (f"Sorry, {row['name']} in size {size} is sold out."
                       if left == 0 else
                       f"Only {left} of {row['name']} in size {size} left. Please lower the quantity.")
                raise HTTPException(status_code=409, detail=msg)
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND size = ?",
                (qty, pid, size),
            )
            expected_after[(pid, size)] = row["quantity"] - qty
            lines.append(OrderLineOut(
                product_id=pid, name=row["name"], size=size, quantity=qty,
                unit_price=row["price"], line_total=round(row["price"] * qty, 2),
            ))

        total = round(sum(line.line_total for line in lines), 2)
        cur = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))
        order_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, size, quantity, unit_price)"
            " VALUES (?, ?, ?, ?, ?)",
            [(order_id, l.product_id, l.size, l.quantity, l.unit_price) for l in lines],
        )
        created_at = conn.execute("SELECT created_at FROM orders WHERE id = ?", (order_id,)).fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # After-purchase inventory test.
    report = record(verify_purchase(expected_after))
    if not report.passed:
        logger.error("Inventory check failed after order %s", order_id)

    return OrderOut(order_id=order_id, total=total, created_at=created_at,
                    items=lines, inventory_check=report)


@router.get("/orders")
def my_orders(authorization: str | None = Header(default=None)) -> list[OrderOut]:
    user_id = _require_user(authorization)
    with get_db() as conn:
        orders = conn.execute(
            "SELECT id, total, created_at FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ).fetchall()
        result = []
        for o in orders:
            items = conn.execute(
                "SELECT oi.product_id, c.name, oi.size, oi.quantity, oi.unit_price "
                "FROM order_items oi JOIN catalogue c ON c.product_id = oi.product_id "
                "WHERE oi.order_id = ?",
                (o["id"],),
            ).fetchall()
            result.append(OrderOut(
                order_id=o["id"], total=o["total"], created_at=o["created_at"],
                items=[OrderLineOut(product_id=i["product_id"], name=i["name"], size=i["size"],
                                    quantity=i["quantity"], unit_price=i["unit_price"],
                                    line_total=round(i["unit_price"] * i["quantity"], 2))
                       for i in items],
            ))
    return result
