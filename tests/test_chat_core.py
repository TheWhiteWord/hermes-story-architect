import asyncio
import tempfile
from pathlib import Path

from story_architect.chat.fake_backend import FakeBackend
from story_architect.chat.service import ChatService
from story_architect.chat import store


def proj(tmp):
    p = Path(tmp) / "proj"
    (p / ".story").mkdir(parents=True)
    return p


def test_new_conversation(tmp_path):
    p = proj(tmp_path)
    svc = ChatService(FakeBackend(replies=["hi"]))
    cid = svc.create_conversation(p, title="t")
    async def run():
        events = []
        async for e in svc.send(p, cid, "hello", {}):
            events.append(e)
        return events
    evs = asyncio.get_event_loop().run_until_complete(run())
    conv = store.get_conversation(p, cid)
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][1]["role"] == "assistant"
    assert conv["messages"][1]["text"] == "hi"
    assert conv["messages"][1]["status"] == "complete"


def test_multiturn(tmp_path):
    p = proj(tmp_path)
    fb = FakeBackend(replies=["r1"])
    svc = ChatService(fb)
    cid = svc.create_conversation(p)
    asyncio.get_event_loop().run_until_complete(_collect(svc, p, cid, "q1"))
    fb.replies = ["r2"]
    asyncio.get_event_loop().run_until_complete(_collect(svc, p, cid, "q2"))
    conv = store.get_conversation(p, cid)
    assert len(conv["messages"]) == 4


async def _collect(svc, p, cid, text):
    async for _ in svc.send(p, cid, text, {}):
        pass


def test_reload_from_disk(tmp_path):
    p = proj(tmp_path)
    svc = ChatService(FakeBackend(replies=["x"]))
    cid = svc.create_conversation(p)
    asyncio.get_event_loop().run_until_complete(_collect(svc, p, cid, "q"))
    # reopen
    conv = store.get_conversation(p, cid)
    assert conv["messages"][1]["text"] == "x"


def test_two_projects_isolated(tmp_path):
    p1 = proj(tmp_path / "a")
    p2 = proj(tmp_path / "b")
    # create distinct dirs
    (tmp_path / "a" / "proj" / ".story").mkdir(parents=True, exist_ok=True)
    (tmp_path / "b" / "proj" / ".story").mkdir(parents=True, exist_ok=True)
    svc = ChatService(FakeBackend(replies=["x"]))
    c1 = svc.create_conversation(p1)
    c2 = svc.create_conversation(p2)
    assert store.list_conversations(p1) and store.list_conversations(p2)
    assert store.list_conversations(p1)[0]["id"] == c1


def test_backend_error(tmp_path):
    p = proj(tmp_path)
    svc = ChatService(FakeBackend(replies=[], error="boom"))
    cid = svc.create_conversation(p)
    async def run():
        evs = []
        async for e in svc.send(p, cid, "q", {}):
            evs.append(e)
        return evs
    evs = asyncio.get_event_loop().run_until_complete(run())
    conv = store.get_conversation(p, cid)
    assert conv["messages"][1]["status"] == "error"


def test_cancellation_midstream(tmp_path):
    p = proj(tmp_path)
    # backend that yields slowly
    class Slow:
        async def send(self, messages, context, bs):
            import asyncio
            for i in range(5):
                await asyncio.sleep(0.05)
                from story_architect.chat.events import TextDelta
                yield TextDelta(text="a")
            from story_architect.chat.events import Done
            yield Done(backend_state=None)
    svc = ChatService(Slow())
    cid = svc.create_conversation(p)
    async def run():
        gen = svc.send(p, cid, "q", {})
        await gen.__anext__()
        await gen.aclose()
    asyncio.get_event_loop().run_until_complete(run())
    conv = store.get_conversation(p, cid)
    assert conv["messages"][1]["status"] in ("cancelled", "streaming", "complete")
