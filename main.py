from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Any

from database import create_document, get_documents, update_document

async def root(request):
    return JSONResponse({"message": "Auction API (Starlette) running", "time": datetime.utcnow().isoformat()})

async def test(request):
    try:
        _ = await get_documents("team", {}, limit=1)
        db_ok = True
    except Exception:
        db_ok = False
    return JSONResponse({"backend": "ok", "database": "mongo", "connection_status": "ok" if db_ok else "error"})

async def create_auction(request):
    payload = await request.json()
    settings = payload.get("settings", {})
    doc = await create_document("auction", {
        "name": payload.get("name"),
        "category": payload.get("category"),
        "settings": settings,
        "created_at": datetime.utcnow().isoformat()
    })
    auction_id = doc.get("id", "")
    # create teams
    for i in range(int(settings.get("teams_count", 0))):
        await create_document("team", {
            "auction_id": auction_id,
            "name": f"Team {i+1}",
            "captain": None,
            "budget_left": int(settings.get("budget_per_team", 0)),
            "players": []
        })
    return JSONResponse({"auction_id": auction_id})

async def list_auctions(request):
    auctions = await get_documents("auction", {}, limit=100)
    return JSONResponse(auctions)

async def get_teams(request):
    auction_id = request.path_params["auction_id"]
    teams = await get_documents("team", {"auction_id": auction_id}, limit=200)
    return JSONResponse(teams)

async def overview(request):
    auction_id = request.path_params["auction_id"]
    auctions = await get_documents("auction", {"id": auction_id}, limit=1)
    if not auctions:
        return JSONResponse({"detail": "Auction not found"}, status_code=404)
    auction = auctions[0]
    settings = auction.get("settings", {})
    teams = await get_documents("team", {"auction_id": auction_id}, limit=500)
    out = []
    base_price = int(settings.get("base_price", 0))
    captain_reserved = int(settings.get("captain_reserved", 0))
    players_per_team = int(settings.get("players_per_team", 0))
    for t in teams:
        players = t.get("players", [])
        players_needed = max(players_per_team - len(players), 0)
        slots_after = max(players_needed - 1, 0)
        required_min = slots_after * base_price
        effective = max(int(t.get("budget_left", 0)) - captain_reserved, 0)
        max_bid = max(effective - required_min, 0)
        out.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "captain": t.get("captain"),
            "budget_left": t.get("budget_left"),
            "players_count": len(players),
            "players": players,
            "max_bid": max_bid
        })
    return JSONResponse({"auction": auction, "teams": out})

async def pick(request):
    import random
    auction_id = request.path_params["auction_id"]
    payload = await request.json()
    num = random.randint(int(payload.get("min_number", 1)), int(payload.get("max_number", 99999)))
    roles = ["Batter", "Bowler", "All-Rounder", "Wicket-Keeper"]
    role = roles[num % len(roles)]
    player = {"id": str(num), "name": f"Player {num}", "role": role, "base_price": 100}
    return JSONResponse({"number": num, "player": player})

async def max_bid(request):
    data = await request.json()
    budget_left = int(data.get("budget_left", 0))
    players_needed = int(data.get("players_needed", 0))
    base_price = int(data.get("base_price", 0))
    captain_reserved = int(data.get("captain_reserved", 0))
    slots_after = max(players_needed - 1, 0)
    required_min = slots_after * base_price
    effective = max(budget_left - captain_reserved, 0)
    mb = max(effective - required_min, 0)
    return JSONResponse({"max_bid": mb})

async def close_bid(request):
    auction_id = request.path_params["auction_id"]
    payload: Dict[str, Any] = await request.json()
    team_id = payload.get("team_id")
    amount = int(payload.get("amount", 0))
    teams = await get_documents("team", {"auction_id": auction_id, "name": team_id}, limit=1)
    if not teams:
        return JSONResponse({"detail": "Team not found"}, status_code=404)
    team = teams[0]
    new_budget = max(int(team.get("budget_left", 0)) - amount, 0)
    player = dict(payload.get("player", {}))
    player["bought_for"] = amount
    updated = await update_document("team", team["id"], {
        "budget_left": new_budget,
        "players": team.get("players", []) + [player]
    })
    return JSONResponse({"ok": bool(updated)})

routes = [
    Route("/", root),
    Route("/test", test),
    Route("/auctions", create_auction, methods=["POST"]),
    Route("/auctions", list_auctions),
    Route("/auctions/{auction_id}/teams", get_teams),
    Route("/auctions/{auction_id}/overview", overview),
    Route("/auctions/{auction_id}/pick", pick, methods=["POST"]),
    Route("/max-bid", max_bid, methods=["POST"]),
    Route("/auctions/{auction_id}/close-bid", close_bid, methods=["POST"]),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True),
]

app = Starlette(debug=False, routes=routes, middleware=middleware)
