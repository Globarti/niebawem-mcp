"""niebawem.fun — MCP Server v0.1 — mock data only."""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import os
from dotenv import load_dotenv

load_dotenv()

# Disable DNS rebinding protection - server is behind HTTPS Caddy proxy
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("niebawem-tools", transport_security=security)

@mcp.tool()
def fb_create_event(title: str, date: str, time: str, location: str, description: str, ticket_price: float = 0) -> dict:
    """Tworzy event na stronie Facebook niebawem.fun."""
    return {"status": "mock_success", "event_id": "FB_MOCK_123456", "title": title, "note": "MOCK"}

@mcp.tool()
def fb_create_post(text: str, image_url: str = "", schedule_datetime: str = "") -> dict:
    """Publikuje post na stronie Facebook niebawem.fun."""
    return {"status": "mock_success", "post_id": "FB_POST_MOCK_789", "note": "MOCK"}

@mcp.tool()
def ig_create_post(image_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje post na Instagramie niebawem.fun."""
    return {"status": "mock_success", "media_id": "IG_MOCK_456789", "note": "MOCK"}

@mcp.tool()
def ig_create_reel(video_url: str, caption: str, hashtags: list[str] = []) -> dict:
    """Publikuje Reela na Instagramie."""
    return {"status": "mock_success", "reel_id": "IG_REEL_MOCK_321", "note": "MOCK"}

@mcp.tool()
def eventbrite_create_event(title: str, date: str, time_start: str, venue_name: str, description: str, ticket_price: float = 0, ticket_quantity: int = 50) -> dict:
    """Tworzy i publikuje event na Eventbrite z biletami."""
    return {"status": "mock_success", "event_id": "EB_MOCK_654321", "note": "MOCK"}

@mcp.tool()
def github_create_issue(repo: str, title: str, body: str, labels: list[str] = []) -> dict:
    """Tworzy issue na GitHubie."""
    return {"status": "mock_success", "issue_number": 42, "note": "MOCK"}

# Use sse_app() - this is what Claude iOS connects to at /sse
app = mcp.sse_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
