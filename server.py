"""
niebawem.fun — MCP Server Szkielet v0.1 — wszystkie tools zwracają MOCK data.
Cel: weryfikacja połączenia Claude ↔ serwer.
"""
from mcp.server.fastmcp import FastMCP
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("niebawem-tools")


@mcp.tool()
def fb_create_event(title: str, date: str, time: str, location: str, description: str, ticket_price: float = 0) -> dict:
    """Tworzy event na stronie Facebook niebawem.fun."""
    return {"status": "mock_success", "event_id": "FB_MOCK_123456", "url": "https://facebook.com/events/mock_123456", "title": title, "date": date, "time": time, "location": location, "ticket_price_pln": ticket_price, "note": "⚠ MOCK — event nie został faktycznie utworzony na FB"}

@mcp.tool()
def fb_create_post(text: str, image_url: str = "", schedule_datetime: str = "") -> dict:
    """Publikuje post na stronie Facebook niebawem.fun."""
    return {"status": "mock_success", "post_id": "FB_POST_MOCK_789", "text_preview": text[:80], "has_image": bool(image_url), "scheduled": bool(schedule_datetime), "note": "⚠ MOCK — post nie został faktycznie opublikowany"}

@mcp.tool()
def ig_create_post(image_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje post na Instagramie niebawem.fun."""
    return {"status": "mock_success", "media_id": "IG_MOCK_456789", "caption_preview": caption[:100], "hashtag_count": len(hashtags), "note": "⚠ MOCK — post nie został faktycznie opublikowany na IG"}

@mcp.tool()
def ig_create_reel(video_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje Reela na Instagramie."""
    return {"status": "mock_success", "reel_id": "IG_REEL_MOCK_321", "video_url": video_url, "note": "⚠ MOCK — Reel nie został faktycznie opublikowany"}

@mcp.tool()
def eventbrite_create_event(title: str, date: str, time_start: str, venue_name: str, description: str, ticket_price: float = 0, ticket_quantity: int = 50) -> dict:
    """Tworzy i publikuje event na Eventbrite z biletami."""
    return {"status": "mock_success", "event_id": "EB_MOCK_654321", "url": "https://eventbrite.com/e/mock-654321", "title": title, "tickets_created": ticket_quantity, "price_pln": ticket_price, "note": "⚠ MOCK — event nie powstał na Eventbrite"}

@mcp.tool()
def github_create_issue(repo: str, title: str, body: str, labels: list[str] = []) -> dict:
    """Tworzy issue na GitHubie."""
    org = os.getenv("GITHUB_ORG", "niebawem-fun")
    full_repo = repo if "/" in repo else f"{org}/{repo}"
    return {"status": "mock_success", "issue_number": 42, "url": f"https://github.com/{full_repo}/issues/42", "title": title, "labels": labels, "note": "⚠ MOCK — issue nie powstał na GitHub"}


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse

    async def health(request):
        return JSONResponse({
            "status": "ok",
            "server": "niebawem-mcp",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "mode": "SKELETON — mock data only",
            "tools": ["fb_create_event", "fb_create_post", "ig_create_post", "ig_create_reel", "eventbrite_create_event", "github_create_issue"],
        })

    # mcp.sse_app() returns Starlette app for SSE transport
    mcp_sse_app = mcp.sse_app()

    app = Starlette(routes=[
        Route("/health", health),
        Mount("/", app=mcp_sse_app),
    ])

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info"
    )
