"""Pydantic / PydanticAI structured types for the Campus Customs shop agent."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator

from themes import Theme


# ---------- Agent dependencies ----------

class CustomerInfo(BaseModel):
    """Who is chatting (Problem 8). Only filled in for logged-in shoppers."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    last_viewed_product_id: str | None = None
    last_viewed_product_name: str | None = None
    last_search: str | None = None
    # Problem 9: one-line summary of their profile (usual size, favorite styles, past orders).
    profile_summary: str | None = None


class PageContext(BaseModel):
    """Where the shopper is on the website when they send a chat message (Problem 8)."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=200)
    # Filled in by the backend from the catalogue, never trusted from the browser.
    product_name: str | None = None


@dataclass
class ShopDeps:
    """What the agent and its tools need at run time: the database, who is chatting
    (None for guests) and which page they are on."""

    db_path: Path
    customer: CustomerInfo | None = None
    page: PageContext | None = None
    # Problem 8: the item a logged-in shopper last looked at or searched for, read fresh from
    # the database (price, description, sizes, stock) so the agent can recall it.
    recalled_product: "ProductDetail | None" = None
    # Problem 10: sport or field-of-study theme, so the agent talks like a coach or professional.
    theme: "Theme | None" = None


# ---------- Data the tools return ----------

LOW_STOCK_THRESHOLD = 5


class SizeStock(BaseModel):
    """Stock for one size of one product (one row of the inventory table)."""

    size: str
    quantity: int

    @computed_field
    @property
    def status(self) -> Literal["in stock", "low stock", "sold out"]:
        if self.quantity == 0:
            return "sold out"
        return "low stock" if self.quantity <= LOW_STOCK_THRESHOLD else "in stock"


class ProductSummary(BaseModel):
    """Compact search result so the model can compare many products cheaply."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    sizes_in_stock: list[str]
    total_stock: int


class TaggedProduct(ProductSummary):
    """A search result with its metadata tags (Problem 9: browse_catalogue)."""

    category: str
    brand: str
    style: str
    seasons: list[str]
    in_season: bool


class Recommendation(TaggedProduct):
    """A tailored pick for a logged-in shopper (Problem 9: recommend_for_me)."""

    reason: str
    score: float
    description: str = ""
    image_url: str = ""


class ProductDetail(BaseModel):
    """Everything the shop knows about one product, straight from the database."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    price: float
    image_url: str
    inventory: list[SizeStock]
    total_stock: int

    @computed_field
    @property
    def sizes_in_stock(self) -> list[str]:
        return [s.size for s in self.inventory if s.quantity > 0]

    @computed_field
    @property
    def sold_out_sizes(self) -> list[str]:
        return [s.size for s in self.inventory if s.quantity == 0]


class StockCheck(BaseModel):
    """Answer to "is product X in stock in size Y?"."""

    product_id: str
    name: str
    price: float
    size: str
    quantity: int
    in_stock: bool
    status: Literal["in stock", "low stock", "sold out"]
    other_sizes_in_stock: list[str]


# ---------- Agent output ----------

# Problem 12 specs, enforced in code (not just asked for in the prompt):
MAX_RESULTS = 5      # each search tool returns at most 5 products
MAX_CARDS = MAX_RESULTS  # and at most 5 product cards are shown per reply
MAX_AGENT_LOOPS = 3  # at most 3 model steps (think -> call tools -> answer) per chat message


class ShopReply(BaseModel):
    """Structured answer the agent must return."""

    reply: str = Field(
        min_length=1,
        max_length=1500,
        description="The message shown to the shopper, in plain text, in the Campus Customs voice.",
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_id values of the items to show as product cards next to the reply, "
            f"most relevant first (at most {MAX_CARDS}). Only use ids returned by the tools. "
            "Empty if none apply."
        ),
    )
    follow_up_question: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "One short question to help narrow things down (size, color, who it's for), "
            "or null if none is needed. Don't repeat it inside reply."
        ),
    )

    @field_validator("reply")
    @classmethod
    def strip_reply(cls, v: str) -> str:
        return v.strip()

    @field_validator("follow_up_question")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None

    @field_validator("product_ids")
    @classmethod
    def dedupe_and_cap(cls, v: list[str]) -> list[str]:
        # Keep order, drop duplicates and blanks, cap the number of cards.
        return [pid for pid in dict.fromkeys(p.strip() for p in v) if pid][:MAX_CARDS]


# ---------- HTTP request / response for /api/chat ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None  # Problem 8: the page the shopper is on
    theme_key: str | None = Field(default=None, max_length=40)  # Problem 10: theme already on screen


class ProductCard(BaseModel):
    """A product card shown under a chat reply. Built from the database, never from model text."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    image_url: str
    inventory: list[SizeStock]
    total_stock: int

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.total_stock > 0

    @computed_field
    @property
    def sizes_in_stock(self) -> list[str]:
        return [s.size for s in self.inventory if s.quantity > 0]

    @computed_field
    @property
    def low_stock_sizes(self) -> list[str]:
        return [s.size for s in self.inventory if 0 < s.quantity <= LOW_STOCK_THRESHOLD]


class ChatResponse(BaseModel):
    reply: str
    follow_up_question: str | None = None
    facts_verified: bool = True
    products: list[ProductCard] = []
    search_id: str | None = Field(
        default=None,
        description="Id for this search in backend/logs/search_path.jsonl (Problem 7).",
    )
    theme: "Theme | None" = Field(
        default=None,
        description="Problem 10: sport or field-of-study theme for the page banner and chat persona.",
    )
