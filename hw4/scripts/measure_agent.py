"""Measure how hard the agent works on filtered shopping questions (model calls, tool calls, time).

From hw4/:
    venv/bin/python scripts/measure_agent.py before     # or: after
Appends results to output/usability_measurements.json.
"""

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW4 / "backend"))

from pydantic_ai.messages import ModelResponse, ToolCallPart  # noqa: E402

import agent as shop_agent  # noqa: E402
import tools  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

QUESTIONS = [
    "Do you have hoodies under $60 in stock in medium?",
    "Any navy crewnecks in XL?",
    "What's the cheapest quarter-zip you have in stock in small?",
    "Show me gray t-shirts in XXL.",
]
RUNS = 2  # per question; model timing varies run to run
OUT = HW4 / "output" / "usability_measurements.json"


async def measure(agent, question: str) -> dict:
    start = time.perf_counter()
    result = await agent.run(
        question,
        deps=tools.ShopDeps(),
        usage_limits=UsageLimits(request_limit=15),  # generous so "before" isn't cut off
    )
    seconds = time.perf_counter() - start
    calls = [p.tool_name for m in result.all_messages() if isinstance(m, ModelResponse)
             for p in m.parts if isinstance(p, ToolCallPart)]
    usage = result.usage
    return {
        "model_requests": usage.requests,
        "tool_calls": len([c for c in calls if c != "final_result"]),
        "tools_used": sorted(set(c for c in calls if c != "final_result")),
        "input_tokens": usage.input_tokens,
        "seconds": round(seconds, 1),
        "reply": result.output.message[:160],
    }


async def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    agent = shop_agent.build_agent()
    rows = []
    for q in QUESTIONS:
        runs = [await measure(agent, q) for _ in range(RUNS)]
        row = {
            "question": q,
            "model_requests": statistics.mean(r["model_requests"] for r in runs),
            "tool_calls": statistics.mean(r["tool_calls"] for r in runs),
            "input_tokens": round(statistics.mean(r["input_tokens"] for r in runs)),
            "seconds": round(statistics.mean(r["seconds"] for r in runs), 1),
            "tools_used": sorted({t for r in runs for t in r["tools_used"]}),
            "sample_reply": runs[0]["reply"],
        }
        rows.append(row)
        print(f"{q[:55]:57} req={row['model_requests']:<4} tools={row['tool_calls']:<4} "
              f"tokens={row['input_tokens']:<6} {row['seconds']}s")
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    data[label] = rows
    OUT.write_text(json.dumps(data, indent=2))
    print(f"saved '{label}' to {OUT.relative_to(HW4)}")


if __name__ == "__main__":
    asyncio.run(main())
