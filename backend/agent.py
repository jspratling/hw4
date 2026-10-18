"""Agent entry point: wires the model, system prompt, tools and output type together."""

import os
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
from db import DB_PATH
from models import MAX_AGENT_LOOPS, ChatTurn, ShopDeps, ShopReply
from tools import SHOP_TOOLS

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

load_dotenv(BACKEND_DIR / ".env")

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
# Any OpenAI 5.6 / 6 series model available through Portkey; override with AGENT_MODEL in .env.
DEFAULT_MODEL = "gpt-6-luna"


class AgentNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_agent() -> Agent[ShopDeps, ShopReply]:
    api_key = os.environ.get("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentNotConfigured("PORTKEY_API_KEY is missing from backend/.env")

    # Portkey is OpenAI-compatible; it authenticates with its own header.
    client = AsyncOpenAI(
        api_key="portkey",
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    # The Responses API (/v1/responses) supports tool calls together with reasoning.
    model = OpenAIResponsesModel(
        os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
        provider=OpenAIProvider(openai_client=client),
    )
    agent = Agent(
        model,
        deps_type=ShopDeps,
        output_type=ShopReply,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=SHOP_TOOLS,
        retries=2,
    )

    # Problem 8: code adds who is chatting and which page they are on to every run.
    @agent.instructions
    def who_and_where(ctx: RunContext[ShopDeps]) -> str:
        return customer_context(ctx.deps)

    return agent


def _clean(text: str, limit: int = 200) -> str:
    """Browser-supplied text goes into the instructions as plain data on one line."""
    return " ".join(text.split())[:limit].replace('"', "'")


def customer_context(deps: ShopDeps) -> str:
    """The "who and where" section added to the agent's instructions for each message."""
    lines = ["## Who is chatting and where they are (filled in by the website for this message)", ""]
    c = deps.customer
    if c:
        lines.append(f"- Logged-in customer: {c.first_name} {c.last_name}, email {c.email}. "
                     "Their chat is saved, and earlier turns above are from their past visits.")
        lines.append(f"- Greet them by first name ({c.first_name}) when it fits. Only mention their "
                     "email if they ask which account they are logged in with.")
        if c.last_viewed_product_id:
            lines.append(f"- Last product they looked at: {c.last_viewed_product_name} "
                         f"(product_id {c.last_viewed_product_id}).")
        if c.last_search:
            lines.append(f'- Their last search in the chat was: "{_clean(c.last_search)}".')
        if c.profile_summary:
            lines.append(f"- Their shopping profile (from orders, views and chats): {c.profile_summary} "
                         "For recommendations, call recommend_for_me.")
        lines.append("- If they ask for more styles like their last search, or for similar items, call "
                     "search_products with the words, garment type and colors from that search or product, "
                     "and show items they have not just seen.")
        r = deps.recalled_product
        if r:
            sold_out = ", ".join(r.sold_out_sizes) or "none"
            in_stock = ", ".join(f"{s.size} ({s.quantity})" for s in r.inventory if s.quantity > 0) or "none"
            lines.append(f"- Item to recall from their last visit (read from the database just now): "
                         f"{r.name} (product_id {r.product_id}), ${r.price:.2f}. Description: {r.description} "
                         f"Sizes in stock (quantity): {in_stock}. Sold out sizes: {sold_out}. "
                         f"{'In stock' if r.total_stock > 0 else 'Sold out in every size'}.")
            lines.append("- When they come back or ask about it, recall this item by name with its price, "
                         "description, sizes and stock. Call get_product_details or check_stock again "
                         "before quoting it later in the chat, because stock changes.")
    else:
        lines.append("- A guest who is not logged in. You don't know their name or email and must not ask. "
                     "Their chat is not saved; if they want it saved, they can log in.")
    t = deps.theme
    if t:
        lines.append(f"- Persona for this conversation: you are {t.persona}, a {t.persona_role} who helps at "
                     f"Campus Customs ({t.label} theme). {t.voice} Keep every fact from the tools, keep "
                     "replies short, and if asked, say you are Campus Customs' automated assistant.")
    p = deps.page
    if p and p.product_id and p.product_name:
        lines.append(f"- They are on the product page for {p.product_name} (product_id {p.product_id}). "
                     'When they say "this", "it", "this one" or "this shirt", they mean this product: '
                     "look it up with get_product_details using that product_id before answering.")
    elif p:
        lines.append(f'- They are on the "{_clean(p.path, 100)}" page of the website, not a product page.')
    return "\n".join(lines)


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Convert the website's chat turns into PydanticAI message history."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def ask_shop_agent(
    message: str, history: list[ChatTurn], deps: ShopDeps | None = None
) -> tuple[ShopReply, list[ModelMessage]]:
    """Run the agent. Returns its reply plus this turn's messages (including tool results),
    which the after-chat fact check uses. deps carries the customer and page (Problem 8).

    Problem 12: the agent loop is limited to MAX_AGENT_LOOPS (3) model requests per message.
    If it needs more, it stops and the shopper gets an honest reply with no made-up facts.
    Every run is added to the append-only audit trail (output/audit_trail.json)."""
    deps = deps or ShopDeps(db_path=DB_PATH)
    past = to_message_history(history)
    run_id, started = audit.new_run_id(), audit._now()
    shopper = "logged_in" if deps.customer else "guest"
    new_messages: list[ModelMessage] = []
    try:
        async with get_agent().iter(
            message,
            deps=deps,
            message_history=past,
            usage_limits=UsageLimits(request_limit=MAX_AGENT_LOOPS),
        ) as run:
            try:
                async for _node in run:
                    pass
            except UsageLimitExceeded:
                new_messages = run.all_messages()[len(past):]
                answer = ShopReply(reply=LOOP_LIMIT_REPLY)
                audit.record_run(run_id, message, shopper, started, new_messages, audit.STOP_LOOP_LIMIT,
                                 answer.reply)
                return answer, new_messages
            except Exception:
                new_messages = run.all_messages()[len(past):]  # keep the tool calls made before the error
                raise
            new_messages = run.all_messages()[len(past):]
            assert run.result is not None
            answer = run.result.output
    except Exception as exc:
        audit.record_run(run_id, message, shopper, started, new_messages, audit.STOP_ERROR,
                         error=f"{type(exc).__name__}: {exc}")
        raise
    audit.record_run(run_id, message, shopper, started, new_messages, audit.STOP_FINAL_ANSWER,
                     answer.reply, answer.product_ids)
    return answer, run.result.new_messages()


LOOP_LIMIT_REPLY = (
    "Sorry, I couldn't finish looking that up. Could you ask about one item or one kind of item "
    "at a time? For example: \"Do you have navy hoodies in size M?\""
)
