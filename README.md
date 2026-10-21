# 🛡️ Roblox Dossier Intelligence Bot

A high-performance Discord audit bot designed for deep forensic investigations of Roblox profiles, economy tracking, and alt detection. Built as an open-source, modular alternative to background-check tools like SpiderEye.

---

## ✨ Features

- **Profile Forensics:** Extracts creation milestones, past username history, ID verification status, ban flags, and exact account age.
- **Connections Directory:** Paginated friends browser (`◀` `▶`) with dynamic username resolution and clickable profile links.
- **Group Hierarchy Audit:** Categorizes affiliations into **👑 Primary Group**, **⭐ High Rank (2–255)**, and **👥 Base Rank (Rank 1)** with dedicated expandable views.
- **Three-Tier Economy Valuation:**
  - **👕 Avatar Inventory:** Item counts and price estimations across Clothing, Accessories, and Animations.
  - **🏆 Collectibles (Limiteds):** Cross-referenced in real-time against Rolimon's market data (RAP, Value, and DevEx USD conversion).
  - **🛒 Gamepasses:** Multi-page index of user-owned gamepasses and gross Robux value.
- **Sentinel Alt-Check:** Categorized security audit calculating an Alt Likelihood score across Tenure, Automation, Social Footprint, and Capital.
- **Privacy-Friendly:** Detailed drill-down menus open as ephemeral Discord messages to prevent server chat spam.

---

## ⚠️ Known Issues

- **Badges System Currently Disabled / Incomplete:** 
  - The badge timeline graph and award-date analysis are currently not working as expected due to upstream rate limits and changes to Roblox's user badge endpoints. A fix is being worked on for a future update.

---

## 📁 Project Structure

```text
Roblox-Dossier-Bot/
├── config.py          # Configuration loader & constants
├── roblox_api.py      # Roblox & Rolimons network scrapers
├── alt_check.py       # Algorithmic risk & alt-likelihood engine
├── ui_views.py        # Discord interactive buttons & paginators
├── bot.py             # Bot initialization & slash commands
├── requirements.txt   # Python package dependencies
├── run.bat            # One-click Windows runner
├── LICENSE            # License terms
└── README.md          # Project documentation
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10 or higher installed with **"Add Python to PATH"** checked.
- A registered bot application from the Discord Developer Portal.

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Weroxin/Roblox-Dossier-Bot.git
cd Roblox-Dossier-Bot
```

### Step 2: Configure Your Bot Token
Create a file named `.env` in the root folder:
```text
DISCORD_BOT_TOKEN=your_bot_token_here
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Bot
- **Windows:** Double-click `run.bat` or run:
  ```bash
  python bot.py
  ```
- **Linux/macOS:**
  ```bash
  python3 bot.py
  ```

---

## ⚙️ Discord Developer Portal Permissions

When generating your bot invite URL in the **OAuth2 -> URL Generator** tab:

1. **Scopes:**
   - `bot`
   - `applications.commands`

2. **Bot Permissions:**
   - `Send Messages`
   - `Embed Links`
   - `Attach Files`
   - `Read Message History`

---

## 📋 Commands

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/dossier` | `username: <RobloxUsername>` | Initiates full profile audit with interactive drill-down views |

---

## 🛠️ Troubleshooting

- **The command does not appear when typing `/`:**
  - Global slash commands can take a moment to register. Press `Ctrl + R` (or `Cmd + R` on Mac) to reload your Discord client.
- **`AttributeError: 'NoneType' object has no attribute 'is_finished'`:**
  - Ensure you are using the latest `ui_views.py` from the repository with the interaction view guard included.

---

## 🔒 Security Notice

Never share or upload your `.env` file containing your bot token to any public website or repository. Anyone with access to your token can take full control of your Discord bot.
