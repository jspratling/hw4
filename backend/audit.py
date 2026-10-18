"""Problem 12: append-only audit trail of the agent loop, in output/audit_trail.json.

For every chat message the agent handles, this records what happened inside the loop:
one entry when the run starts, one for each tool the agent called (time, tool name, short
inputs, short result), and one when the run stops (with the stop reason).

The file is append-only and is never wiped between runs:
- It is one JSON list, so it opens in any JSON viewer.
- New entries are added just before the closing "]". Bytes already in the file are never
  rewritten or removed, and no code in the project deletes or truncates the file.
- If the file has been edited by hand and no longer ends in "]", new entries are still added
  at the end (one per line) rather than touching what is there.

Privacy (safety rule 3): entries never include the shopper's name, email, user id, password or
payment details, only whether they were a guest or logged in.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
SHORT = 160  # characters kept from each tool input or result

# Why a run stopped.
STOP_FINAL_ANSWER = "final_answer"  # the agent returned its answer normally
STOP_LOOP_LIMIT = "loop_limit"      # it hit the 3-step loop limit (MAX_AGENT_LOOPS)
STOP_ERROR = "error"                # the model or a tool failed

_lock = threading.Lock()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _time(ts: Any) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds") if isinstance(ts, datetime) else _now()


def _short(text: str, limit: int = SHORT) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def short_args(args: Any) -> str:
    """Tool inputs as compact JSON, cut to SHORT characters."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return _short(args)
    return _short(json.dumps(args, ensure_ascii=False, separators=(", ", ": "), default=str))


def short_result(content: Any) -> str:
    """A one-line summary of what a tool returned."""
    if isinstance(content, list):
        ids = [getattr(item, "product_id", None) or (item.get("product_id") if isinstance(item, dict) else None)
               for item in content]
        ids = [i for i in ids if i]
        return _short(f"{len(content)} products: {', '.join(ids)}" if ids else f"{len(content)} items")
    if isinstance(content, BaseModel):
        data = content.model_dump()
        keep = {k: data[k] for k in ("product_id", "name", "price", "size", "quantity", "status", "total_stock")
                if k in data}
        if "sizes_in_stock" in data:
            keep["sizes_in_stock"] = data["sizes_in_stock"]
        return _short(json.dumps(keep, ensure_ascii=False, default=str))
    return _short(content)


def loop_entries(run_id: str, messages: Iterable[ModelMessage]) -> list[dict]:
    """One entry per tool call made in this run, matched with its result."""
    entries: list[dict] = []
    calls: dict[str, dict] = {}
    step = 0
    for message in messages:
        if isinstance(message, ModelResponse):
            step += 1
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    entry = {
                        "time": _time(message.timestamp),
                        "run_id": run_id,
                        "event": "tool_call",
                        "loop": step,
                        "tool": part.tool_name,
                        "args": short_args(part.args),
                        "result": None,
                    }
                    calls[part.tool_call_id] = entry
                    entries.append(entry)
        else:
            for part in getattr(message, "parts", []):
                if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id]["result"] = short_result(part.content)
                    calls[part.tool_call_id]["time"] = _time(part.timestamp)
    return entries


def record_run(
    run_id: str,
    question: str,
    shopper: str,
    started: str,
    messages: Iterable[ModelMessage],
    stop_reason: str,
    reply: str = "",
    product_ids: list[str] | None = None,
    error: str = "",
) -> list[dict]:
    """Append everything one agent run did to the audit trail. Returns the entries written."""
    messages = list(messages)
    tool_calls = loop_entries(run_id, messages)
    loops = sum(1 for m in messages if isinstance(m, ModelResponse))
    end = {
        "time": _now(),
        "run_id": run_id,
        "event": "run_end",
        "stop_reason": stop_reason,
        "loops_used": loops,
        "tools_called": [e["tool"] for e in tool_calls],
        "reply": _short(reply),
        "product_ids": product_ids or [],
    }
    if error:
        end["error"] = _short(error)
    entries = [
        {"time": started, "run_id": run_id, "event": "run_start", "question": _short(question), "shopper": shopper},
        *tool_calls,
        end,
    ]
    append_entries(entries)
    return entries


def append_entries(entries: list[dict], path: Path | None = None) -> None:
    """Add entries to the end of the JSON list without rewriting anything already there."""
    path = path or AUDIT_PATH
    if not entries:
        return
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+b") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                f.write(("[\n" + body + "\n]\n").encode("utf-8"))
                return
            # Find the closing "]" (skipping trailing spaces and newlines).
            tail_start = max(0, size - 64)
            f.seek(tail_start)
            tail = f.read()
            stripped = tail.rstrip()
            if stripped.endswith(b"]"):
                before = stripped[:-1].rstrip()
                empty_list = before.endswith(b"[")
                # "a+" always writes at the end, so cut only the closing "]" and the blank space
                # around it (never an entry), then add the new entries and close the list again.
                f.truncate(tail_start + len(before))
                f.seek(0, os.SEEK_END)
                f.write((("" if empty_list else ",") + "\n" + body + "\n]\n").encode("utf-8"))
            else:
                # Not a closed list (edited by hand?): never touch existing bytes, just add lines.
                f.write(("\n" + body + "\n").encode("utf-8"))


def read_trail(path: Path | None = None) -> list[dict]:
    """Read the whole audit trail (used by tests and for checking)."""
    path = path or AUDIT_PATH
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
