"""Minimal MCP server over streamable HTTP (plain JSON responses).

One server holds all swarm state. Each agent's Codex session connects with its
own bearer token, so the server knows who is calling and lists tools by role.
"""

from __future__ import annotations

import asyncio
import socket

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .tools import ToolBox
from .world import World

PROTOCOL = "2025-06-18"


class ToolServer:
    def __init__(self, world: World, toolbox: ToolBox):
        self.world = world
        self.toolbox = toolbox
        self.app = Starlette(routes=[Route("/mcp", self.handle, methods=["GET", "POST", "DELETE"])])
        self.port: int | None = None
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    async def start(self) -> None:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning",
                                lifespan="off", timeout_keep_alive=30)
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        while not self._server.started:
            await asyncio.sleep(0.02)

    async def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
            await self._task

    async def handle(self, request: Request) -> Response:
        if request.method != "POST":
            return Response(status_code=405)
        token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        agent = self.world.by_token(token) if token else None
        if agent is None:
            return Response(status_code=401)
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(_err(None, -32700, "parse error"), status_code=400)
        batch = body if isinstance(body, list) else [body]
        out = []
        for msg in batch:
            res = await self._dispatch(agent, msg)
            if res is not None:
                out.append(res)
        if not out:
            return Response(status_code=202)
        return JSONResponse(out if isinstance(body, list) else out[0])

    async def _dispatch(self, agent, msg: dict) -> dict | None:
        mid = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}
        if mid is None:  # notification
            return None
        if method == "initialize":
            return _ok(mid, {"protocolVersion": params.get("protocolVersion", PROTOCOL),
                             "capabilities": {"tools": {"listChanged": False}},
                             "serverInfo": {"name": "swarm", "version": "0.1.0"}})
        if method == "ping":
            return _ok(mid, {})
        if method == "tools/list":
            return _ok(mid, {"tools": [s.schema() for s in self.toolbox.list_for(agent)]})
        if method == "tools/call":
            text, is_err, _ = await self.toolbox.call(agent, params.get("name", ""), params.get("arguments") or {})
            return _ok(mid, {"content": [{"type": "text", "text": text}], "isError": is_err})
        if method in ("resources/list", "resources/templates/list", "prompts/list"):
            key = {"resources/list": "resources", "resources/templates/list": "resourceTemplates",
                   "prompts/list": "prompts"}[method]
            return _ok(mid, {key: []})
        return _err(mid, -32601, f"method not found: {method}")


def _ok(mid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _err(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}
