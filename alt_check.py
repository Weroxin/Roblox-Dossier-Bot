from datetime import datetime, timezone
import pandas as pd

def perform_forensic_alt_check(data: dict) -> dict:
    created_at = data["created_at"]
    days_old = max((datetime.now(timezone.utc) - created_at).days, 1)
    years_old = round(days_old / 365.25, 1)

    # Categories
    ledger = {
        "Platform Tenure": [],
        "Badges & Automation": [],
        "Social Footprint": [],
        "Economic Capital": []
    }
    
    raw_points = 0  # Negative = authentic/established, Positive = throwaway/alt

    # 1. Platform Tenure
    if years_old >= 6:
        raw_points -= 16
        ledger["Platform Tenure"].append(f"🟢 **Established Veteran** (`-16 pts`) — Account is **{years_old}** years old.")
    elif years_old >= 2:
        raw_points -= 8
        ledger["Platform Tenure"].append(f"🟢 **Tenured User** (`-8 pts`) — Account is **{years_old}** years old.")
    elif days_old < 30:
        raw_points += 22
        ledger["Platform Tenure"].append(f"🔴 **Fresh Account** (`+22 pts`) — Created only **{days_old}** days ago.")

    # Official platform awards
    official = [b.lower() for b in data.get("official_badges", [])]
    if "welcome to the club" in official:
        raw_points -= 10
        ledger["Platform Tenure"].append("🟢 **Builders Club Heritage** (`-10 pts`) — Holds archived Builders Club membership.")
    if "veteran" in official:
        raw_points -= 8
        ledger["Platform Tenure"].append("🟢 **Legacy Veteran** (`-8 pts`) — Earned active tenure badge prior to 2026 retirement.")
    if "friendship" in official:
        raw_points -= 4
        ledger["Platform Tenure"].append("🟢 **Social Pioneer** (`-4 pts`) — Holds pre-2026 Friendship badge.")

    # 2. Badges & Automation
    badge_dates = data.get("badge_dates", [])
    if badge_dates:
        df = pd.DataFrame({"date": [d.date() for d in badge_dates]})
        day_counts = df.groupby("date").size()
        
        spam_days = day_counts[day_counts >= 80]
        spam_count = int(spam_days.sum())
        clean_count = len(badge_dates) - spam_count

        if spam_count > 50:
            raw_points += 6
            ledger["Badges & Automation"].append(f"🟠 **Badge Farm Activity** (`+6 pts`) — **{spam_count}** badges earned in bulk bursts.")
        if clean_count > 50:
            raw_points -= 8
            ledger["Badges & Automation"].append(f"🟢 **Organic Gameplay** (`-8 pts`) — **{clean_count}+** badges earned through regular play.")
        if len(day_counts) > 15:
            raw_points -= 8
            ledger["Badges & Automation"].append(f"🟢 **Multi-Day Consistency** (`-8 pts`) — Active across **{len(day_counts)}** distinct dates.")
    else:
        raw_points += 10
        ledger["Badges & Automation"].append("🔴 **No Unlocked Badges** (`+10 pts`) — Zero public gameplay records detected.")

    # 3. Social Footprint
    followers = data.get("followers", 0)
    friends = data.get("friend_count", 0)
    groups = data.get("group_count", 0)

    if followers > 200:
        raw_points -= 6
        ledger["Social Footprint"].append(f"🟢 **Public Audience** (`-6 pts`) — Account has **{followers:,}** followers.")
    if friends > 30:
        raw_points -= 4
        ledger["Social Footprint"].append(f"🟢 **Connected Socially** (`-4 pts`) — **{friends:,}** friends registered.")
    if groups > 5:
        raw_points -= 4
        ledger["Social Footprint"].append(f"🟢 **Community Engaged** (`-4 pts`) — Joined **{groups}** community groups.")
    elif groups == 0:
        raw_points += 8
        ledger["Social Footprint"].append("🔴 **Zero Groups** (`+8 pts`) — Account has never joined any community.")

    # 4. Economic Capital
    limiteds = data.get("limited_count", 0)
    gamepass_val = data.get("gamepass_val", 0)
    past_names = len(data.get("past_names", []))

    if limiteds > 0:
        raw_points -= 8
        ledger["Economic Capital"].append(f"🟢 **Collectible Holder** (`-8 pts`) — Owns **{limiteds}** collectible item(s).")
    if gamepass_val > 500:
        raw_points -= 6
        ledger["Economic Capital"].append(f"🟢 **Monetized Investments** (`-6 pts`) — Owns **R$ {gamepass_val:,}** in gamepasses.")
    if past_names > 0:
        raw_points -= 8
        ledger["Economic Capital"].append(f"🟢 **Paid Name Change** (`-8 pts`) — Changed username **{past_names}** time(s) (~{past_names * 1000:,} R$).")

    # Final Probability Mapping (0 to 100%)
    risk_percentage = max(2, min(98, int(((raw_points + 65) / 95) * 100)))

    if risk_percentage <= 25:
        tier_title = "VERIFIED MAIN / ESTABLISHED"
        tier_badge = "🛡️"
        color = 0x22c55e
    elif risk_percentage <= 55:
        tier_title = "MODERATE RISK / MIXED HISTORY"
        tier_badge = "⚡"
        color = 0xeab308
    elif risk_percentage <= 75:
        tier_title = "ELEVATED RISK / LIKELY ALT"
        tier_badge = "⚠️"
        color = 0xf97316
    else:
        tier_title = "HIGH THREAT / DISPOSABLE ACCOUNT"
        tier_badge = "🚨"
        color = 0xef4444

    # High-tech Unicode Progress Gauge
    blocks_total = 20
    filled = int((risk_percentage / 100) * blocks_total)
    gauge = "▰" * filled + "▱" * (blocks_total - filled)

    return {
        "risk_percentage": risk_percentage,
        "tier_title": tier_title,
        "tier_badge": tier_badge,
        "color": color,
        "gauge": gauge,
        "ledger": ledger
    }
