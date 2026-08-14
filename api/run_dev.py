"""Local (non-Docker) Windows dev entrypoint.

uvicorn's CLI (`uvicorn app.main:app`) hard-codes asyncio.ProactorEventLoop on
Windows whenever it isn't running a reload/multi-worker subprocess
(uvicorn/loops/asyncio.py: `if sys.platform == "win32" and not use_subprocess:
return asyncio.ProactorEventLoop`), which overrides any event loop policy set
beforehand. psycopg's async driver explicitly rejects ProactorEventLoop. Driving
Server.serve() ourselves under asyncio.run(..., loop_factory=SelectorEventLoop)
sidesteps uvicorn's own Windows-forcing asyncio_run() wrapper entirely.

Not needed in Docker - the container runs the regular `uvicorn app.main:app` CLI
command on Linux, which never hits this branch.
"""

import asyncio
import sys

import uvicorn


async def _serve() -> None:
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000, reload=False)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(_serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(_serve())
