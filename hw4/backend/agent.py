"""Campus Customs shop assistant: loads the prompt, wires model + tools, runs one chat turn."""

import time

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.usage import UsageLimits

import audit
import tools
from models import ChatTurn, ShopReply

PROMPT_PATH = tools.BACKEND_DIR / "prompts" / "prompt.md"
MAX_REQUESTS = 8  # model calls per shopper message (tool calls + final answer)


def shopper_context(deps: tools.ShopDeps) -> str:
    """Who is chatting, written into the instructions for every run."""
    c = deps.customer
    if c is None:
        return ("## Current shopper\nA guest (not logged in). Their chat is not saved. "
                "You don't know their name.")
    return (
        "## Current shopper\n"
        f"Logged in as {c.first_name} {c.last_name} ({c.email}), a member since {c.created_at[:10]}. "
        "Their earlier chats with you are saved and included above, so you can refer back to them. "
        "Call get_customer_profile for account details."
    )


def page_context(deps: tools.ShopDeps) -> str:
    """Where the shopper is on the site, so "this", "these", or "the first one" resolve."""
    p = deps.page
    if p is None:
        return ""
    if p.page == "product":
        return (
            "## Current page\n"
            f"The shopper is looking at the product page for {p.product_name} "
            f"(product_id: {p.product_id}). \"This\", \"it\", or \"this one\" means that product "
            "unless they say otherwise. Look it up with a tool before answering about it."
        )
    if p.page == "products" and p.visible_product_ids:
        ids = ", ".join(p.visible_product_ids)
        return (
            "## Current page\n"
            "The shopper is on the Products page, viewing the chat search results you showed, in "
            f"this order: {ids}. \"These\", \"any of them\", or \"the second one\" refer to that list."
        )
    return f"## Current page\nThe shopper is on the {p.page} page."


def build_agent() -> Agent[tools.ShopDeps, ShopReply]:
    agent = Agent(
        tools.make_model(),
        deps_type=tools.ShopDeps,
        output_type=ShopReply,
        tools=tools.TOOLS,
    )

    # Read on every run (not once at startup) so prompt.md edits apply without a restart;
    # uvicorn --reload only watches .py files.
    @agent.instructions
    def system_prompt() -> str:
        return PROMPT_PATH.read_text()

    @agent.instructions
    def runtime_context(ctx: RunContext[tools.ShopDeps]) -> str:
        return "\n\n".join(s for s in (shopper_context(ctx.deps), page_context(ctx.deps)) if s)

    return agent


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Rebuild a guest's earlier turns from the widget so the agent remembers this conversation."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def is_content_filter_error(exc: Exception) -> bool:
    """Azure (behind Portkey) rejects jailbreak-style or unsafe prompts with a 400 content_filter."""
    return isinstance(exc, ModelHTTPError) and exc.status_code == 400 and "content_filter" in str(exc.body)


# When the model gets stuck (e.g. keeps retrying a tool), answer politely instead of erroring.
RECOVERED_REPLY = ShopReply(
    message="Sorry, I got a little tangled up there. Could you ask that another way? "
    "I can help with styles, sizes, stock, and prices."
)

FILTERED_REPLY = ShopReply(
    message="Sorry, I can't help with that. I'm here to help you find Yale gear from Campus Customs. "
    "What are you shopping for today?"
)


async def chat(agent: Agent[tools.ShopDeps, ShopReply], message: str,
               history: list[ModelMessage], deps: tools.ShopDeps,
               entry: dict | None = None) -> ShopReply:
    """Run one chat turn. If `entry` is given, the agent loop is recorded in the audit trail
    (steps, tool calls, stop reason, timing) whether the run succeeds or fails."""
    entry = entry if entry is not None else {}
    started = time.perf_counter()
    run = None
    try:
        async with agent.iter(
            message,
            deps=deps,
            message_history=history,
            usage_limits=UsageLimits(request_limit=MAX_REQUESTS),
        ) as run:
            async for _node in run:
                pass
        entry["stop_reason"] = "final_result"
        return run.result.output
    except ModelHTTPError as exc:
        if is_content_filter_error(exc):
            entry["stop_reason"] = "content_filter"
            return FILTERED_REPLY
        entry["stop_reason"], entry["error"] = "error", f"ModelHTTPError {exc.status_code}"
        raise
    except UsageLimitExceeded:
        entry["stop_reason"] = "usage_limit"
        raise
    except UnexpectedModelBehavior as exc:
        entry["stop_reason"], entry["error"] = "recovered", f"UnexpectedModelBehavior: {str(exc)[:120]}"
        return RECOVERED_REPLY
    except Exception as exc:
        entry["stop_reason"], entry["error"] = "error", type(exc).__name__
        raise
    finally:
        if run is not None:
            entry["steps"] = audit.steps_from(run.new_messages())
            usage = run.usage
            entry.update(model_requests=usage.requests, input_tokens=usage.input_tokens,
                         output_tokens=usage.output_tokens)
        else:
            entry.setdefault("steps", [])
        entry["duration_s"] = round(time.perf_counter() - started, 2)
