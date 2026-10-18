"""Problem 11: bug found by the live app check.

"What hoodies do you have?" sometimes returned nothing, because the agent searched
query="hoodies" and the keyword match needed the exact word. Plurals now match.

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_app_check.py -v
Reads campus_customs.db read-only. No API key needed.
"""

import sys
import types
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import db  # noqa: E402
import tools  # noqa: E402
from models import ShopDeps  # noqa: E402


def ctx():
    return types.SimpleNamespace(deps=ShopDeps(db_path=db.DB_PATH))


def test_failing_live_search_now_finds_hoodies():
    # The exact inputs the agent sent on the failed try (backend/logs/search_path.jsonl).
    results = tools.search_products(ctx(), query="hoodies", garment_type="hoodie", limit=8, in_stock_only=True)
    assert len(results) == 5  # Problem 12 caps results at 5
    assert all("hood" in p.garment_type.lower() for p in results)


def test_plural_keywords_match_singular_names():
    for plural, singular in [("hoodies", "hoodie"), ("crewnecks", "crewneck"), ("jackets", "jacket")]:
        plural_ids = {p.product_id for p in tools.search_products(ctx(), query=plural)}
        singular_ids = {p.product_id for p in tools.search_products(ctx(), query=singular)}
        assert plural_ids and plural_ids == singular_ids, plural


def test_keyword_helper():
    assert tools._keyword_in("hoodies", "basic hoodie big yale")
    assert tools._keyword_in("t", "t-shirt")
    assert not tools._keyword_in("harvard", "yale hoodie")
