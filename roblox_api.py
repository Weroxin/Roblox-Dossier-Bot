import asyncio
from datetime import datetime, timezone
import aiohttp
from config import USER_AGENT

ROLIMONS_CACHE = {}
LAST_CACHE_TIME = 0

async def fetch_json(session: aiohttp.ClientSession, url: str, method: str = "GET", json_payload: dict = None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        if method == "POST":
            async with session.post(url, json=json_payload, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    return await resp.json()
        else:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
    return None

async def resolve_user(session: aiohttp.ClientSession, username: str):
    url = "https://users.roblox.com/v1/usernames/users"
    data = await fetch_json(session, url, method="POST", json_payload={"usernames": [username], "excludeBannedUsers": False})
    if data and data.get("data"):
        return data["data"][0]
    return None

async def batch_resolve_users(session: aiohttp.ClientSession, user_ids: list[int]) -> dict[int, dict]:
    """Resolves IDs to user handles and display names in 100-user chunks."""
    if not user_ids:
        return {}
    url = "https://users.roblox.com/v1/users"
    resolved = {}
    for i in range(0, len(user_ids), 100):
        chunk = user_ids[i:i + 100]
        data = await fetch_json(session, url, method="POST", json_payload={"userIds": chunk, "excludeBannedUsers": False})
        if data and "data" in data:
            for u in data["data"]:
                resolved[u["id"]] = {"name": u["name"], "displayName": u.get("displayName", u["name"])}
    return resolved

async def get_rolimons_table(session: aiohttp.ClientSession):
    global ROLIMONS_CACHE, LAST_CACHE_TIME
    now = datetime.now(timezone.utc).timestamp()
    if ROLIMONS_CACHE and (now - LAST_CACHE_TIME < 1800):
        return ROLIMONS_CACHE
    data = await fetch_json(session, "https://www.rolimons.com/itemapi/itemdetails")
    if data and "items" in data:
        ROLIMONS_CACHE = data["items"]
        LAST_CACHE_TIME = now
        return ROLIMONS_CACHE
    return {}

async def get_avatar_inventory(session: aiohttp.ClientSession, user_id: int):
    """Fetches user avatar clothing, accessories, and animations."""
    categories = {
        "Clothing": "Shirt,Pants,TShirt",
        "Accessories": "Hat,HairAccessory,FaceAccessory,NeckAccessory,ShoulderAccessory,FrontAccessory,BackAccessory,WaistAccessory",
        "Animations": "ClimbAnimation,DeathAnimation,FallAnimation,IdleAnimation,JumpAnimation,RunAnimation,SwimAnimation,WalkAnimation,EmoteAnimation"
    }
    
    total_assets = 0
    breakdown = {}
    sample_items = []
    
    for cat_name, asset_types in categories.items():
        url = f"https://inventory.roblox.com/v2/users/{user_id}/inventory?assetTypes={asset_types}&limit=100&sortOrder=Desc"
        data = await fetch_json(session, url)
        items = data.get("data", []) if data else []
        breakdown[cat_name] = len(items)
        total_assets += len(items)
        if items and len(sample_items) < 15:
            sample_items.extend(items[:5])

    # Standard Roblox catalog price baseline estimation: ~5 R$ per clothing, ~50 R$ per accessory
    estimated_avatar_val = (breakdown.get("Clothing", 0) * 5) + (breakdown.get("Accessories", 0) * 50) + (breakdown.get("Animations", 0) * 80)

    return {
        "total_assets": total_assets,
        "breakdown": breakdown,
        "estimated_val": estimated_avatar_val,
        "sample": sample_items
    }

async def get_gamepasses_data(session: aiohttp.ClientSession, user_id: int, max_pages: int = 5):
    """
    Paginates through gamepasses up to 500+ items using both 
    apis.roblox.com and inventory.roblox.com fallbacks.
    """
    passes = []
    seen_ids = set()

    # 1. Primary: apis.roblox.com pagination
    cursor = ""
    for _ in range(max_pages):
        owned_url = f"https://apis.roblox.com/game-passes/v1/users/{user_id}/game-passes?count=100" + (f"&exclusiveStartId={cursor}" if cursor else "")
        res = await fetch_json(session, owned_url)
        
        batch = []
        if isinstance(res, list):
            batch = res
        elif isinstance(res, dict):
            batch = res.get("gamePasses", res.get("data", []))
            
        if not batch:
            break

        for p in batch:
            pid = p.get("id") or p.get("gamePassId")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                passes.append(p)

        # Cursor for the next page
        last_item = batch[-1]
        cursor = last_item.get("id") or last_item.get("gamePassId")
        if len(batch) < 100:
            break

    # 2. Secondary: Fallback to Inventory V2 GamePass query if count is 0
    if not passes:
        cursor = ""
        for _ in range(max_pages):
            inv_url = f"https://inventory.roblox.com/v2/users/{user_id}/inventory?assetTypes=GamePass&limit=100&sortOrder=Desc" + (f"&cursor={cursor}" if cursor else "")
            res = await fetch_json(session, inv_url)
            if not res or "data" not in res:
                break
            for item in res["data"]:
                pid = item.get("assetId")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    passes.append({
                        "name": item.get("name", "Gamepass"),
                        "price": 0,
                        "id": pid
                    })
            cursor = res.get("nextPageCursor")
            if not cursor:
                break

    total_value = sum(p.get("price") or p.get("priceInRobux") or 0 for p in passes)
    return {
        "count": len(passes),
        "total_val": total_value,
        "list": passes
    }

async def get_badges_with_dates(session: aiohttp.ClientSession, user_id: int, max_pages: int = 4):
    badge_ids = []
    cursor = ""
    for _ in range(max_pages):
        url = f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100&sortOrder=Asc" + (f"&cursor={cursor}" if cursor else "")
        data = await fetch_json(session, url)
        if not data or "data" not in data:
            break
        badge_ids.extend([str(b["id"]) for b in data["data"]])
        cursor = data.get("nextPageCursor")
        if not cursor:
            break

    badge_dates = []
    for i in range(0, len(badge_ids), 100):
        chunk = badge_ids[i:i + 100]
        dates_url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={','.join(chunk)}"
        d_data = await fetch_json(session, dates_url)
        if d_data and "data" in d_data:
            for item in d_data["data"]:
                raw = item.get("awardedDate")
                if raw:
                    badge_dates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    return badge_dates
