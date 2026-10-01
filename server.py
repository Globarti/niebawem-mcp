"""niebawem.fun — MCP Server v1.0.

Prawdziwe integracje: Facebook Page, Instagram (Graph API), Eventbrite, GitHub.
Każde narzędzie działa na żywym API, jeśli w env jest token; bez tokenu zwraca
jawny tryb mock (status="mock", note mówi, której zmiennej brakuje).
"""
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"
EVENTBRITE = "https://www.eventbriteapi.com/v3"
GITHUB = "https://api.github.com"
TIMEOUT = httpx.Timeout(60.0)

# Disable DNS rebinding protection - server is behind HTTPS Caddy proxy
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("niebawem-tools", transport_security=security)


def _env(*names: str) -> dict | None:
    vals = {n: os.getenv(n, "") for n in names}
    if any(not v or v.startswith("XXXX") or v.startswith("ghp_XXXX") for v in vals.values()):
        return None
    return vals


def _mock(missing: str, **extra) -> dict:
    return {"status": "mock", "note": f"Brak konfiguracji: {missing} — nic nie zostało opublikowane.", **extra}


def _err(r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = r.text[:500]
    return {"status": "error", "http_status": r.status_code, "error": body}


def _iso_local(date: str, time: str) -> str:
    """'2026-11-14', '19:00' -> '2026-11-14T19:00:00'."""
    return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------- Facebook ---

@mcp.tool()
def fb_create_post(text: str, image_url: str = "", schedule_datetime: str = "") -> dict:
    """Publikuje post na stronie Facebook niebawem.fun.

    schedule_datetime: opcjonalnie ISO 8601 (np. 2026-11-10T18:00:00+01:00) — post zaplanowany
    (10 min – 30 dni w przód). image_url: publiczny URL obrazka (wtedy post ze zdjęciem).
    """
    cfg = _env("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN")
    if not cfg:
        return _mock("FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN")
    page, token = cfg["FB_PAGE_ID"], cfg["FB_PAGE_ACCESS_TOKEN"]
    data: dict = {"access_token": token}
    if schedule_datetime:
        data["published"] = "false"
        data["scheduled_publish_time"] = int(datetime.fromisoformat(schedule_datetime).timestamp())
    if image_url:
        data.update({"url": image_url, "caption": text})
        r = httpx.post(f"{GRAPH}/{page}/photos", data=data, timeout=TIMEOUT)
    else:
        data["message"] = text
        r = httpx.post(f"{GRAPH}/{page}/feed", data=data, timeout=TIMEOUT)
    if r.status_code != 200:
        return _err(r)
    j = r.json()
    return {"status": "ok", "post_id": j.get("post_id") or j.get("id"), "scheduled": bool(schedule_datetime)}


@mcp.tool()
def fb_create_event(title: str, date: str, time: str, location: str, description: str, ticket_price: float = 0) -> dict:
    """Przygotowuje wydarzenie na stronie Facebook niebawem.fun.

    Graph API nie pozwala już tworzyć wydarzeń stron przez API, więc narzędzie publikuje
    post-zapowiedź z datą, miejscem i ceną oraz zwraca link do ręcznego kreatora wydarzeń.
    date: RRRR-MM-DD, time: GG:MM.
    """
    when = f"{date} {time}"
    price = f"Bilety: {ticket_price:.0f} zł" if ticket_price else "Wstęp wolny"
    text = f"🎙️ {title}\n📅 {when}\n📍 {location}\n🎟️ {price}\n\n{description}"
    post = fb_create_post(text)
    page = os.getenv("FB_PAGE_ID", "niebawem.impro")
    return {
        **post,
        "event_creator_url": f"https://www.facebook.com/{page}/events/create",
        "note": "Wydarzenie FB trzeba założyć ręcznie (ograniczenie Graph API); zapowiedź opublikowana jako post.",
    }


# --------------------------------------------------------------- Instagram ---

def _ig_publish(container: dict) -> dict:
    cfg = _env("IG_ACCOUNT_ID", "FB_PAGE_ACCESS_TOKEN")
    if not cfg:
        return _mock("IG_ACCOUNT_ID / FB_PAGE_ACCESS_TOKEN")
    ig, token = cfg["IG_ACCOUNT_ID"], cfg["FB_PAGE_ACCESS_TOKEN"]
    r = httpx.post(f"{GRAPH}/{ig}/media", data={**container, "access_token": token}, timeout=TIMEOUT)
    if r.status_code != 200:
        return _err(r)
    creation_id = r.json()["id"]
    # Wideo (reels) wymaga przetworzenia — czekamy na FINISHED.
    if container.get("media_type") == "REELS":
        import time
        for _ in range(60):
            s = httpx.get(f"{GRAPH}/{creation_id}", params={"fields": "status_code", "access_token": token}, timeout=TIMEOUT).json()
            if s.get("status_code") == "FINISHED":
                break
            if s.get("status_code") == "ERROR":
                return {"status": "error", "error": s}
            time.sleep(5)
    p = httpx.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": creation_id, "access_token": token}, timeout=TIMEOUT)
    if p.status_code != 200:
        return _err(p)
    return {"status": "ok", "media_id": p.json()["id"]}


def _caption(caption: str, hashtags: list[str]) -> str:
    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in hashtags)
    return f"{caption}\n\n{tags}".strip()


@mcp.tool()
def ig_create_post(image_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje post (zdjęcie) na Instagramie niebawem.impro. image_url musi być publicznym JPEG."""
    return _ig_publish({"image_url": image_url, "caption": _caption(caption, hashtags)})


@mcp.tool()
def ig_create_reel(video_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje Reela na Instagramie niebawem.impro. video_url musi być publicznym MP4."""
    return _ig_publish({"media_type": "REELS", "video_url": video_url, "caption": _caption(caption, hashtags)})


# -------------------------------------------------------------- Eventbrite ---

@mcp.tool()
def eventbrite_create_event(title: str, date: str, time_start: str, venue_name: str, description: str,
                            ticket_price: float = 0, ticket_quantity: int = 50, duration_minutes: int = 120) -> dict:
    """Tworzy i publikuje event na Eventbrite z pulą biletów. date: RRRR-MM-DD, time_start: GG:MM."""
    cfg = _env("EVENTBRITE_API_KEY", "EVENTBRITE_ORG_ID")
    if not cfg:
        return _mock("EVENTBRITE_API_KEY / EVENTBRITE_ORG_ID")
    h = {"Authorization": f"Bearer {cfg['EVENTBRITE_API_KEY']}"}
    org = cfg["EVENTBRITE_ORG_ID"]
    start = datetime.strptime(f"{date} {time_start}", "%Y-%m-%d %H:%M")
    end = start.timestamp() + duration_minutes * 60
    tz = "Europe/Warsaw"

    v = httpx.post(f"{EVENTBRITE}/organizations/{org}/venues/", headers=h, timeout=TIMEOUT,
                   json={"venue": {"name": venue_name, "address": {"address_1": venue_name, "city": "Warszawa", "country": "PL"}}})
    if v.status_code != 200:
        return _err(v)
    ev = httpx.post(f"{EVENTBRITE}/organizations/{org}/events/", headers=h, timeout=TIMEOUT, json={"event": {
        "name": {"html": title},
        "description": {"html": description},
        "start": {"timezone": tz, "utc": datetime.utcfromtimestamp(start.timestamp()).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "end": {"timezone": tz, "utc": datetime.utcfromtimestamp(end).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "currency": "PLN",
        "venue_id": v.json()["id"],
    }})
    if ev.status_code != 200:
        return _err(ev)
    event_id = ev.json()["id"]
    tc = {"name": "Bilet", "quantity_total": ticket_quantity}
    tc.update({"free": True} if not ticket_price else {"cost": f"PLN,{int(round(ticket_price * 100))}"})
    t = httpx.post(f"{EVENTBRITE}/events/{event_id}/ticket_classes/", headers=h, json={"ticket_class": tc}, timeout=TIMEOUT)
    if t.status_code != 200:
        return {**_err(t), "event_id": event_id}
    p = httpx.post(f"{EVENTBRITE}/events/{event_id}/publish/", headers=h, timeout=TIMEOUT)
    return {"status": "ok" if p.status_code == 200 else "created_unpublished", "event_id": event_id, "url": ev.json().get("url")}


# ------------------------------------------------------------------ GitHub ---

@mcp.tool()
def github_create_issue(repo: str, title: str, body: str, labels: list[str] = []) -> dict:
    """Tworzy issue na GitHubie. repo: 'nazwa' (w GITHUB_ORG) albo 'owner/nazwa'."""
    cfg = _env("GITHUB_TOKEN")
    if not cfg:
        return _mock("GITHUB_TOKEN")
    full = repo if "/" in repo else f"{os.getenv('GITHUB_ORG', 'Globarti')}/{repo}"
    r = httpx.post(f"{GITHUB}/repos/{full}/issues", timeout=TIMEOUT,
                   headers={"Authorization": f"Bearer {cfg['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"},
                   json={"title": title, "body": body, "labels": labels})
    if r.status_code != 201:
        return _err(r)
    j = r.json()
    return {"status": "ok", "issue_number": j["number"], "url": j["html_url"]}


@mcp.tool()
def config_status() -> dict:
    """Pokazuje, które integracje są skonfigurowane (live), a które działają w trybie mock."""
    return {
        "facebook": bool(_env("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN")),
        "instagram": bool(_env("IG_ACCOUNT_ID", "FB_PAGE_ACCESS_TOKEN")),
        "eventbrite": bool(_env("EVENTBRITE_API_KEY", "EVENTBRITE_ORG_ID")),
        "github": bool(_env("GITHUB_TOKEN")),
    }


# Use sse_app() - this is what Claude iOS connects to at /sse
app = mcp.sse_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
