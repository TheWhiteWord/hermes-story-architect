import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from story_architect.adapters.hermes.chat_backend import HermesChatBackend


def make_server(handler_cls):
    httpd = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port


class OkHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer key":
            self.send_response(401)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b'data: {"id":"resp1","choices":[{"delta":{"content":"hi"}}]}\n\n')
        self.wfile.write(b'event: hermes.tool.progress\n')
        self.wfile.write(b'data: {"event":"hermes.tool.progress","data":{"tool":"lookup"}}\n\n')
        self.wfile.write(b'data: {"id":"resp1","choices":[{"delta":{"content":"!"}}]}\n\n')
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *a, **k):
        pass


async def collect(b, ctx=None, state=None):
    out = []
    async for e in b.send([{"role": "user", "content": "q"}], ctx or {}, state):
        out.append(e)
    return out


def test_text_and_tool():
    httpd, port = make_server(OkHandler)
    try:
        b = HermesChatBackend(f"http://127.0.0.1:{port}", "key", model="m")
        events = asyncio.run(collect(b, {"project_slug": "s", "project_name": "N"}))
        assert [type(e).__name__ for e in events] == ["TextDelta", "ToolStarted", "TextDelta", "Done"]
        assert events[0].text == "hi"
        assert events[1].name == "lookup"
        assert events[3].backend_state == "resp1"
    finally:
        httpd.shutdown()


class AuthFailHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b"nope")

    def log_message(self, *a, **k):
        pass


def test_auth_failure():
    httpd, port = make_server(AuthFailHandler)
    try:
        b = HermesChatBackend(f"http://127.0.0.1:{port}", "key")
        events = asyncio.run(collect(b))
        assert len(events) == 1 and type(events[0]).__name__ == "Error"
    finally:
        httpd.shutdown()


def test_unreachable():
    b = HermesChatBackend("http://127.0.0.1:1", "key", timeout=1.0)
    events = asyncio.run(collect(b))
    assert len(events) == 1 and type(events[0]).__name__ == "Error"


class MalformedHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b"data: {not json}\n\n")
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n')
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *a, **k):
        pass


def test_malformed_ignored():
    httpd, port = make_server(MalformedHandler)
    try:
        b = HermesChatBackend(f"http://127.0.0.1:{port}", "key")
        events = asyncio.run(collect(b, state="prev"))
        assert any(type(e).__name__ == "TextDelta" and e.text == "ok" for e in events)
    finally:
        httpd.shutdown()


def test_continuity_roundtrip():
    httpd, port = make_server(OkHandler)
    try:
        b = HermesChatBackend(f"http://127.0.0.1:{port}", "key")
        events = asyncio.run(collect(b, state="prev"))
        done = [e for e in events if type(e).__name__ == "Done"][0]
        assert done.backend_state == "resp1"
    finally:
        httpd.shutdown()
