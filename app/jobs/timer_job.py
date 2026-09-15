import asyncio
from typing import Any, Dict

from app.jobs.context import JobContext
from app.jobs.registry import job


@job(domain="demo", type="timer", max_attempts=3)
async def run_timer(payload: Dict[str, Any], ctx: JobContext) -> Dict[str, Any]:
    """Count up to payload["seconds"], one second at a time."""
    seconds = payload["seconds"]
    elapsed = ctx.state.get("elapsed_seconds", 0)  # resume after a worker crash

    while elapsed < seconds:
        await ctx.check_cancelled()
        await asyncio.sleep(1)
        elapsed += 1
        await ctx.save_state({"elapsed_seconds": elapsed})
        await ctx.progress(elapsed / seconds * 100, f"{elapsed}/{seconds}")

    return {"elapsed_seconds": elapsed}
