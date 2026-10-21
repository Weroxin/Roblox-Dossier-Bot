from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio

from config import TOKEN, DEVEX_RATE
import roblox_api
from ui_views import DossierInteractiveView

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="dossier", description="Deep forensic audit on any Roblox account.")
@app_commands.describe(username="Roblox username to investigate")
async def dossier(interaction: discord.Interaction, username: str):
    await interaction.response.send_message("⚙️ `(0/4) Resolving user identity...`")

    async with aiohttp.ClientSession() as session:
        # Step 1: User Identity
        user_stub = await roblox_api.resolve_user(session, username)
        if not user_stub:
            return await interaction.edit_original_response(content=f"❌ User **{username}** was not found on Roblox.")

        user_id = user_stub["id"]
        current_name = user_stub["name"]
        display_name = user_stub.get("displayName", current_name)

        # Step 2: Concurrently Fetch Base Profiles
        await interaction.edit_original_response(content="⚙️ `(1/4) Aggregating profile records, affiliations & connections...`")
        
        async with asyncio.TaskGroup() as tg:
            t_info = tg.create_task(roblox_api.fetch_json(session, f"https://users.roblox.com/v1/users/{user_id}"))
            t_names = tg.create_task(roblox_api.fetch_json(session, f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"))
            t_friends = tg.create_task(roblox_api.fetch_json(session, f"https://friends.roblox.com/v1/users/{user_id}/friends"))
            t_followers = tg.create_task(roblox_api.fetch_json(session, f"https://friends.roblox.com/v1/users/{user_id}/followers/count"))
            t_following = tg.create_task(roblox_api.fetch_json(session, f"https://friends.roblox.com/v1/users/{user_id}/followings/count"))
            t_groups = tg.create_task(roblox_api.fetch_json(session, f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"))
            t_primary = tg.create_task(roblox_api.fetch_json(session, f"https://groups.roblox.com/v1/users/{user_id}/groups/primary/role"))
            t_badges_official = tg.create_task(roblox_api.fetch_json(session, f"https://accountinformation.roblox.com/v1/users/{user_id}/roblox-badges"))
            t_collectibles = tg.create_task(roblox_api.fetch_json(session, f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=100"))
            t_favorites = tg.create_task(roblox_api.fetch_json(session, f"https://games.roblox.com/v2/users/{user_id}/favorite/games?limit=50&sortOrder=Desc"))

        user_info = t_info.result() or {}
        created_str = user_info.get("created", "")
        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.now(timezone.utc)
        days_old = max((datetime.now(timezone.utc) - created_at).days, 1)
        years_old = round(days_old / 365.25, 1)

        # Step 3: Badges Forensics with Award Dates
        await interaction.edit_original_response(content="⚙️ `(2/4) Parsing badge timeline & detecting bulk automation...`")
        badge_dates = await roblox_api.get_badges_with_dates(session, user_id, max_pages=4)

        # Step 4: Asset & Economy Auditing (Avatar Items + Limiteds + Passes)
        await interaction.edit_original_response(content="⚙️ `(3/4) Auditing catalog inventory, gamepasses & market data...`")
        roli = await roblox_api.get_rolimons_table(session)
        avatar_inv = await roblox_api.get_avatar_inventory(session, user_id)
        gamepass_data = await roblox_api.get_gamepasses_data(session, user_id)

        # Collectibles / Limiteds
        collectibles_raw = t_collectibles.result()
        collectibles = collectibles_raw.get("data", []) if collectibles_raw else []
        total_rap = sum(item.get("recentAveragePrice", 0) for item in collectibles)
        total_val = sum((roli.get(str(item.get("assetId")), [0, 0, 0, 0])[3] or item.get("recentAveragePrice", 0)) for item in collectibles)
        usd_value = total_val * DEVEX_RATE

        # Batch resolve friend IDs to handles
        friends_raw = t_friends.result().get("data", []) if t_friends.result() else []
        friend_ids = [f["id"] for f in friends_raw]
        resolved_friends = await roblox_api.batch_resolve_users(session, friend_ids)

        group_list = t_groups.result().get("data", []) if t_groups.result() else []
        base_rank_count = sum(1 for g in group_list if g.get("role", {}).get("rank", 1) <= 1)
        base_rank_pct = round((base_rank_count / len(group_list)) * 100) if group_list else 0

        past_names = [n["name"] for n in t_names.result().get("data", [])] if t_names.result() else []
        official_badges = [b["name"] for b in t_badges_official.result()] if t_badges_official.result() else []
        favorite_games = t_favorites.result().get("data", []) if t_favorites.result() else []

        dossier_data = {
            "name": current_name,
            "display_name": display_name,
            "id": user_id,
            "created_at": created_at,
            "years_old": years_old,
            "bio": user_info.get("description", "").strip(),
            "verified": user_info.get("hasVerifiedBadge", False),
            "is_banned": user_info.get("isBanned", False),
            "past_names": past_names,
            "friends_raw": friends_raw,
            "resolved_friends": resolved_friends,
            "friend_count": len(friends_raw),
            "followers": t_followers.result().get("count", 0) if t_followers.result() else 0,
            "following": t_following.result().get("count", 0) if t_following.result() else 0,
            "group_count": len(group_list),
            "base_rank_count": base_rank_count,
            "base_rank_pct": base_rank_pct,
            "primary_group": t_primary.result(),
            "group_list": group_list,
            "avatar_inv": avatar_inv,
            "limited_count": len(collectibles),
            "total_rap": total_rap,
            "total_val": total_val,
            "usd_value": usd_value,
            "gamepass_data": gamepass_data["list"],
            "gamepass_count": gamepass_data["count"],
            "gamepass_val": gamepass_data["total_val"],
            "badge_dates": badge_dates,
            "unique_badge_days": len(set(d.date() for d in badge_dates)),
            "official_badges": official_badges,
            "favorites_list": favorite_games
        }

        # Step 5: Render Master Embed with 3-Way Valuations
        embed = discord.Embed(
            title=f"Dossier: {display_name} (@{current_name})",
            url=f"https://www.roblox.com/users/{user_id}/profile",
            color=0x1e293b
        )
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=150&height=150&format=png")

        embed.description = (
            f"Forensic Assessment · Processed just now\n\n"
            f"📁 **Profile Overview**\n"
            f"Joined **{created_at.strftime('%B %d, %Y')}** ({int(years_old)} years ago)\n"
            f"User ID `{user_id}` · Past Names: `{past_names[0] if past_names else 'None'}`\n\n"
            f"🌐 **Connections**\n"
            f"**{len(friends_raw):,}** friends · **{dossier_data['followers']:,}** followers · **{dossier_data['following']:,}** following\n\n"
            f"🏛️ **Affiliations**\n"
            f"**{len(group_list)}** groups · Base rank in **{base_rank_count} ({base_rank_pct}%)**\n\n"
            f"💎 **Three-Tier Economy**\n"
            f"• **Avatar Inventory:** {avatar_inv['total_assets']} items (~R$ {avatar_inv['estimated_val']:,})\n"
            f"• **Limiteds (Collectibles):** {len(collectibles)} items (R$ {total_val:,.0f} · ~${usd_value:,.2f} USD)\n"
            f"• **Gamepasses:** {gamepass_data['count']} passes (R$ {gamepass_data['total_val']:,})\n\n"
            f"⭐ **Engagement**\n"
            f"**{len(favorite_games):,}** favorite games registered\n\n"
            f"🏷️ **Badges & Activity**\n"
            f"**{len(badge_dates):,}+** indexed across **{dossier_data['unique_badge_days']}** distinct active days"
        )
        embed.set_footer(text="Click any category below to open its dedicated view.")

        view = DossierInteractiveView(dossier_data)
        await interaction.edit_original_response(content=None, embed=embed, view=view)

if __name__ == "__main__":
    bot.run(TOKEN)
