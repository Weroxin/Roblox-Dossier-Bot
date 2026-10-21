import io
import discord
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timezone
from alt_check import perform_forensic_alt_check

def build_activity_chart(badge_dates: list[datetime], created_at: datetime, username: str) -> io.BytesIO:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=150)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    df = pd.DataFrame({"date": [d.date() for d in badge_dates]})
    daily_counts = df.groupby("date").size().reset_index(name="count")
    daily_counts["date"] = pd.to_datetime(daily_counts["date"])
    daily_counts = daily_counts.sort_values("date")

    ax.bar(daily_counts["date"], daily_counts["count"], width=3.5, color="#38bdf8", alpha=0.9, label="Badges Earned")
    creation_date = pd.to_datetime(created_at.date())
    ax.axvline(creation_date, color="#f43f5e", linestyle="--", linewidth=1.4, label="Account Creation")

    ax.set_title(f"Activity Timeline: {username}", fontsize=11, fontweight="bold", color="#f8fafc", pad=12)
    ax.set_ylabel("Daily Badges", fontsize=8, color="#94a3b8")
    ax.tick_params(axis="both", which="both", colors="#64748b", labelsize=8)
    ax.grid(True, linestyle=":", alpha=0.2, color="#334155")
    
    today = pd.to_datetime(datetime.now(timezone.utc).date())
    ax.set_xlim(left=creation_date - pd.Timedelta(days=30), right=today + pd.Timedelta(days=30))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()

    legend = ax.legend(loc="upper left", fontsize=8, frameon=True)
    legend.get_frame().set_facecolor("#1e293b")
    legend.get_frame().set_edgecolor("#334155")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf

class GenericListPaginator(discord.ui.View):
    def __init__(self, title: str, items: list[str], page_size: int = 10):
        super().__init__(timeout=180)
        self.title = title
        self.items = items
        self.page_size = page_size
        self.page = 0
        self.total_pages = max(1, (len(items) + page_size - 1) // page_size)
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= self.total_pages - 1
        self.page_btn.label = f"Page {self.page + 1}/{self.total_pages}"

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"{self.title} — Page {self.page + 1}/{self.total_pages}", color=0x1e293b)
        start = self.page * self.page_size
        slice_items = self.items[start:start + self.page_size]
        embed.description = "\n".join(slice_items) if slice_items else "*No entries available.*"
        embed.set_footer(text=f"Total: {len(self.items):,} items registered.")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
        self.page -= 1
        self.update_buttons()
        await inter.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        await inter.response.edit_message(embed=self.get_embed(), view=self)

class DossierInteractiveView(discord.ui.View):
    def __init__(self, data: dict):
        super().__init__(timeout=300)
        self.d = data

    @discord.ui.button(label="Profile Info", style=discord.ButtonStyle.secondary, emoji="📁", row=0)
    async def view_profile(self, inter: discord.Interaction, btn: discord.ui.Button):
        d = self.d
        embed = discord.Embed(title=f"📁 Profile Dossier: {d['display_name']}", color=0x1e293b)
        embed.add_field(name="Username", value=f"`{d['name']}`", inline=True)
        embed.add_field(name="Display Name", value=f"`{d['display_name']}`", inline=True)
        embed.add_field(name="User ID", value=f"`{d['id']}`", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(d['created_at'].timestamp())}:F>\n(<t:{int(d['created_at'].timestamp())}:R>)", inline=False)
        embed.add_field(name="Verified Badge", value="`yes` ☑️" if d['verified'] else "`no`", inline=True)
        embed.add_field(name="Banned", value=f"`{str(d['is_banned']).lower()}`", inline=True)
        past_str = ", ".join([f"`{n}`" for n in d['past_names']]) if d['past_names'] else "`none`"
        embed.add_field(name=f"Previous Usernames ({len(d['past_names'])}):", value=past_str, inline=False)
        embed.add_field(name="Description", value=f"```{d['bio'] if d['bio'] else 'No biography provided.'}```", inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Connections", style=discord.ButtonStyle.secondary, emoji="👥", row=0)
    async def view_connections(self, inter: discord.Interaction, btn: discord.ui.Button):
        d = self.d
        resolved = d["resolved_friends"]
        friends_list = d["friends_raw"]

        formatted_lines = []
        for idx, f in enumerate(friends_list, start=1):
            uid = f["id"]
            user_data = resolved.get(uid, {"name": f"User_{uid}", "displayName": f"User_{uid}"})
            formatted_lines.append(f"`{idx:02d}.` **[{user_data['displayName']} (@{user_data['name']})](https://www.roblox.com/users/{uid}/profile)**")

        paginator = GenericListPaginator(f"👥 Friends Directory ({len(friends_list)})", formatted_lines, page_size=10)
        await inter.response.send_message(embed=paginator.get_embed(), view=paginator, ephemeral=True)

    @discord.ui.button(label="Groups", style=discord.ButtonStyle.secondary, emoji="🏛️", row=0)
    async def view_groups(self, inter: discord.Interaction, btn: discord.ui.Button):
        d = self.d
        embed = discord.Embed(title=f"Groups Details ({d['group_count']})", color=0x1e293b)
        if d['primary_group']:
            g = d['primary_group']
            embed.add_field(name="👑 Primary Group", value=f"**{g.get('group',{}).get('name')}**\n{g.get('role',{}).get('name')} ({g.get('role',{}).get('rank')})", inline=False)

        high_ranks = [f"• **{g['group']['name']}** — `{g['role']['name']}` ({g['role']['rank']})" for g in d['group_list'] if g.get("role", {}).get("rank", 1) > 1]
        base_ranks = [f"• **{g['group']['name']}** — `{g['role']['name']}` (1)" for g in d['group_list'] if g.get("role", {}).get("rank", 1) <= 1]

        embed.add_field(name=f"⭐ High Rank Groups ({len(high_ranks)})", value="\n".join(high_ranks[:6]) if high_ranks else "*None*", inline=False)
        embed.add_field(name=f"👥 Base Rank Groups ({len(base_ranks)})", value="\n".join(base_ranks[:6]) if base_ranks else "*None*", inline=False)

        class GroupExpandView(discord.ui.View):
            def __init__(self, hr, br):
                super().__init__(timeout=120)
                self.hr = hr
                self.br = br

            @discord.ui.button(label="Expand High Rank", style=discord.ButtonStyle.primary)
            async def open_hr(self, i: discord.Interaction, b: discord.ui.Button):
                pag = GenericListPaginator("⭐ High Rank Groups", self.hr, page_size=12)
                await i.response.send_message(embed=pag.get_embed(), view=pag, ephemeral=True)

            @discord.ui.button(label="Expand Base Rank", style=discord.ButtonStyle.secondary)
            async def open_br(self, i: discord.Interaction, b: discord.ui.Button):
                pag = GenericListPaginator("👥 Base Rank Groups", self.br, page_size=12)
                await i.response.send_message(embed=pag.get_embed(), view=pag, ephemeral=True)

        await inter.response.send_message(embed=embed, view=GroupExpandView(high_ranks, base_ranks), ephemeral=True)

    @discord.ui.button(label="Inventory & Economy", style=discord.ButtonStyle.secondary, emoji="💎", row=1)
    async def view_economy(self, inter: discord.Interaction, btn: discord.ui.Button):
        d = self.d
        embed = discord.Embed(title=f"Economic Footprint: {d['display_name']}", color=0x1e293b)
        
        # 1. Avatar Inventory
        avatar = d["avatar_inv"]
        embed.add_field(
            name="👕 Avatar Inventory",
            value=f"**Items:** {avatar['total_assets']} catalog items\n**Est. Value:** R$ {avatar['estimated_val']:,}\n`{avatar['breakdown'].get('Clothing', 0)} clothing · {avatar['breakdown'].get('Accessories', 0)} accessories`",
            inline=False
        )

        # 2. Limiteds / Collectibles
        embed.add_field(
            name="🏆 Collectibles (Limiteds)",
            value=f"**Owned:** {d['limited_count']} items\n**RAP:** R$ {d['total_rap']:,.0f}\n**Value:** R$ {d['total_val']:,.0f}\n**DevEx:** ~${d['usd_value']:,.2f} USD",
            inline=False
        )

        # 3. Gamepasses
        embed.add_field(
            name="🛒 Gamepasses",
            value=f"**Total Passes:** {d['gamepass_count']}\n**Gross Value:** R$ {d['gamepass_val']:,}",
            inline=False
        )

        # Bug fix: Only attach view if gamepass items exist
        if d["gamepass_data"]:
            class PassExpandView(discord.ui.View):
                def __init__(self, passes):
                    super().__init__(timeout=120)
                    self.passes = passes

                @discord.ui.button(label="Expand Gamepasses Directory", style=discord.ButtonStyle.primary)
                async def open_passes(self, i: discord.Interaction, b: discord.ui.Button):
                    lines = [f"• **{p.get('name','Gamepass')}** — R$ {(p.get('price') or p.get('priceInRobux') or 0):,}" for p in self.passes]
                    pag = GenericListPaginator("🛒 Owned Gamepasses", lines, page_size=12)
                    await i.response.send_message(embed=pag.get_embed(), view=pag, ephemeral=True)

            await inter.response.send_message(embed=embed, view=PassExpandView(d["gamepass_data"]), ephemeral=True)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Favorites", style=discord.ButtonStyle.secondary, emoji="⭐", row=1)
    async def view_favorites(self, inter: discord.Interaction, btn: discord.ui.Button):
        d = self.d
        games = d['favorites_list']
        lines = [f"• **[{g.get('name') or 'Experience'}](https://www.roblox.com/games/{g.get('rootPlace',{}).get('id') or g.get('id')})** `(ID: {g.get('rootPlace',{}).get('id') or g.get('id')})`" for g in games]
        pag = GenericListPaginator(f"⭐ Favorite Games ({len(games)})", lines, page_size=15)
        await inter.response.send_message(embed=pag.get_embed(), view=pag, ephemeral=True)

    @discord.ui.button(label="Forensic Assessment", style=discord.ButtonStyle.success, emoji="🛡️", row=2)
    async def view_altcheck(self, inter: discord.Interaction, btn: discord.ui.Button):
        alt = perform_forensic_alt_check(self.d)
        embed = discord.Embed(
            title=f"{alt['tier_badge']} Forensic Risk Audit: {self.d['name']}",
            description=f"### Security Standing: `{alt['tier_title']}`\n"
                        f"**Threat Index:** `{alt['risk_percentage']}%` Alt Likelihood\n"
                        f"`[{alt['gauge']}]`\n"
                        f"*(0% = Verified Main | 100% = Disposable Alt)*",
            color=alt["color"]
        )

        for category, bullet_points in alt["ledger"].items():
            if bullet_points:
                embed.add_field(name=category, value="\n".join(bullet_points), inline=False)

        await inter.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Activity Graph", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def view_badges(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer(ephemeral=True)
        d = self.d
        if not d['badge_dates']:
            return await inter.followup.send("⚠️ No dated badges found to build graph.", ephemeral=True)

        chart_buf = build_activity_chart(d['badge_dates'], d['created_at'], d['name'])
        chart_file = discord.File(chart_buf, filename="activity_timeline.png")

        embed = discord.Embed(title=f"Activity Progression: {d['display_name']}", color=0x38bdf8)
        embed.add_field(name="Total Badges Scanned", value=f"**{len(d['badge_dates']):,}**", inline=True)
        embed.add_field(name="Active Days Recorded", value=f"**{d['unique_badge_days']}** days", inline=True)
        embed.set_image(url="attachment://activity_timeline.png")
        await inter.followup.send(embed=embed, file=chart_file, ephemeral=True)
