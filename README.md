# TNI Seed Harvester

**Automated seed collection and proposal mapping for [Tower Networking Inc](https://store.steampowered.com/app/2381090/Tower_Networking_Inc/) by Pocosia Studios**

[![Seeds](https://img.shields.io/badge/seeds-2%2C345-blue)](data/clean-collection-json/merged-seeds.json)
[![Coverage](https://img.shields.io/badge/coverage-99.56%25-brightgreen)](data/clean-collection-json/merged-seeds.json)
[![Combinations](https://img.shields.io/badge/combinations-453%2F455-yellow)](data/clean-collection-json/merged-seeds.json)

---

## 🎮 What is This?

Tower Networking Inc uses **world seeds** to determine your starting proposals (among other things). Each seed gives you exactly 3 proposals to choose from at the start of the game.

This project:
- **Harvests** seeds automatically using OCR
- **Maps** which proposals each seed provides
- **Provides** a web-based seed finder to find seeds with your desired proposals

---

## 🚀 Using the Seed Finder

**No installation required!** Just:

1. Download or clone this repo
2. Open `frontend/tni-seed-finder.html` in any web browser
3. Click proposals to find matching seeds
4. Click a seed code to copy it
5. Paste it in-game when starting a new scenario!

The seed database is embedded directly in the HTML file, so it works completely offline.

---

## 📊 Current Database Stats

| Metric | Value |
|--------|-------|
| Total Seeds | 2,345 |
| Proposal Combinations | 453 / 455 (99.56%) |
| Unique Proposals | 15 |

### The Last Two

After 2,345 seeds, these combinations remain elusive:

- **Fusion Plant + Refurbhut Investment + Scanning Exploit**
- **Scanning Exploit + Second Monitor + Undervoltage Directive**

The hunt continues...

---

## 🔮 What We've Learned

*After harvesting 2,345 seeds, patterns emerge from the chaos.*

### The Game's Hidden Hand

The seed algorithm isn't purely random.

#### Slot Favoritism

Each proposal has a "home" slot where it appears most often. Some are almost locked to one position:

| Proposal | Slot 1 | Slot 2 | Slot 3 | Verdict |
|----------|--------|--------|--------|---------|
| Legal Retaliation | **92%** | 7% | 0% | *Almost always first* |
| Poems DB | 0% | 7% | **93%** | *Almost always last* |
| Second Monitor | 1% | 21% | **79%** | *Strongly prefers last* |
| Undervoltage Directive | **73%** | 25% | 3% | *Strongly prefers first* |
| Scanning Exploit | 3% | 32% | **66%** | *Usually last* |
| Remote Backups | 18% | 15% | **67%** | *Usually last* |
| PADU | **61%** | 34% | 5% | *Usually first* |

Other proposals (Fusion Plant, Lean Administration, Overvoltage, etc.) are more flexible, appearing across all three slots without strong preference.

#### Proposals That Avoid Each Other

Some pairs rarely appear together. The five rarest pairings:

| Pair | Frequency | Notes |
|------|-----------|-------|
| Overvoltage + Undervoltage | 2.1% | *Contradictory policies* |
| NetOps Research + PADU | 2.2% | |
| Fusion Plant + Lobby against Tenabolt | 2.3% | *Faction conflict?* |
| Fusion Plant + Refurbhut Investment | 2.3% | *Both in missing combos* |
| Second Monitor + Undervoltage | 2.4% | *Both in missing combos* |

Notice how the rarest pairs involve proposals from our two missing combinations. This isn't coincidence.

#### Proposals That Stick Together

Meanwhile, these pairs appear together more often than expected:

| Pair | Frequency |
|------|-----------|
| Fusion Plant + Power Management Research | 3.6% |
| Overvoltage + Power Management Research | 3.6% |
| Power Management Research + Scanning Exploit | 3.5% |
| Overvoltage + PADU | 3.5% |
| Legal Retaliation + Poems DB | 3.5% |

Power Management Research is the social butterfly of proposals.

---

## 🦄 Unicorn Seeds

These 15 combinations exist exactly once in our database. One-of-a-kind starts:

| Seed | Combination | Total Cost |
|------|-------------|------------|
| YQA59 | Lobby against Tenabolt + Overvoltage + Undervoltage | 400 |
| K04S6 | Legal Retaliation + Poems DB + Power Management | 425 |
| D6IVP | Lobby against Tenabolt + NetOps + Overvoltage | 530 |
| WKK1U | PADU + Power Management + Undervoltage | 725 |
| YVXLY | Lobby against Tenabolt + PADU + Remote Backups | 750 |
| GWW1F | Lean Administration + Lobby against Tenabolt + Poems DB | 800 |
| KXV83 | Cabler's Union + NetOps + Power Management | 855 |
| OZMJW | Poems DB + Power Management + Refurbhut Investment | 980 |
| C7UC1 | Lean Administration + NetOps + Remote Backups | 1380 |
| 09YOS | Fusion Plant + Overvoltage + Poems DB | 1400 |
| **JCX8K** | **Fusion Plant + Refurbhut Investment + Undervoltage** | 1755 |
| GQVM2 | Cabler's Union + Poems DB + Second Monitor | 3000 |
| S4RHH | PADU + Power Management + Second Monitor | 3025 |
| 42VD2 | NetOps + Power Management + Second Monitor | 3055 |
| LS0GT | Lean Administration + Poems DB + Second Monitor | 3300 |

**JCX8K** is special — it was one of our "missing 3" combinations, discovered completely by accident during debugging. Sometimes the rarest finds come when you're not looking.

---

## 📈 Proposal Draw Rates

How likely is each proposal to appear in any given seed?

| Proposal | Appears In | Draw Weight |
|----------|------------|-------------|
| Undervoltage Directive | 18.5% of seeds | 0.92x |
| Second Monitor | 18.8% | 0.94x |
| NetOps Research | 19.1% | 0.96x |
| Refurbhut Investment | 19.4% | 0.97x |
| Remote Backups | 19.4% | 0.97x |
| Fusion Plant | 19.6% | 0.98x |
| Lobby against Tenabolt | 19.8% | 0.99x |
| Cabler's Union (Base) | 20.1% | 1.00x |
| PADU | 20.1% | 1.01x |
| Overvoltage Directive | 20.3% | 1.02x |
| Scanning Exploit | 20.5% | 1.03x |
| Lean Administration | 20.7% | 1.04x |
| Legal Retaliation | 20.8% | 1.04x |
| Poems DB | 21.1% | 1.06x |
| Power Management Research | 21.7% | 1.08x |

*Draw Weight: 1.00x = expected if perfectly uniform.*

**The surprising truth:** Overall proposal frequency is nearly balanced (~3% variance). The game doesn't make proposals rarer — it controls *where* they appear and *what* they appear *with*. The weighting is in the combinations, not the individual draws.

---

## 🎯 Why the Missing Two Are So Hard to Find

Let's break down why these specific combinations might be impossible:

### Fusion Plant + Refurbhut Investment + Scanning Exploit

- Fusion Plant + Refurbhut Investment appears in only **2.30%** of seeds
- Total cost: **2,755** credits (very expensive start)
- All three proposals are "investment" type — major upfront costs

### Scanning Exploit + Second Monitor + Undervoltage Directive

- Second Monitor + Undervoltage Directive: **2.35%** of seeds
- Scanning Exploit + Undervoltage Directive: **2.35%** of seeds  
- Total cost: **3,900** credits (the most expensive possible start?)
- Second Monitor and Scanning Exploit both strongly prefer Slot 3 — but only one can occupy it

That last point might be the key. If the algorithm assigns slots first, and both proposals "want" the same slot, the combination might be mechanically impossible.

---

## 📋 All 15 Starting Proposals

These are the proposals that can appear at game start. Other proposals (like Cabler's Union upgrades, VM Research, etc.) only unlock through gameplay.

| Proposal | Cost | Effect |
|----------|------|--------|
| Cabler's Union (Base) | 300 | Unlocks more proposals for the Cabler's Union |
| Fusion Plant | 1000 | Reduce all Data Center power cost by 20% |
| Lean Administration | 600 | Permanently reduce daily admin expenses by 30% |
| Legal Retaliation | — | Tenabolt pays 500 per outage/surge, items 10% more expensive |
| Lobby against Tenabolt | — | Tenabolt can't issue non-DC power fines, items 20% more expensive |
| NetOps Research | 330 | Unlocks 'cron', 'try', and 'notify' routines |
| Overvoltage Directive | 200 | -30% power outage, +30% power surge chance |
| PADU | 300 | Unlocks padu_v3 (stores text, image, audio, video) |
| Poems DB | 200 | Unlocks poems-db (text-only, lightweight) |
| Power Management Research | 225 | Unlocks 'power' routine on NetShell |
| Refurbhut Investment | 555 | Opens RefurbHut merchant (cheap refurbished devices) |
| Remote Backups | 450 | Unlocks 'sftp' routine (backup configs, remove malware) |
| Scanning Exploit | 1200 | Netsh and autograph scans bypass all router rules |
| Second Monitor | 2500 | Allows use of second monitor (right-alt) |
| Undervoltage Directive | 200 | +30% power outage, -30% power surge chance |

---

## 📁 Project Structure

```
tni-seed-harvester/
├── frontend/
│   └── tni-seed-finder.html      # Web UI - open this to search seeds
├── data/
│   ├── clean-collection-json/    # Processed seed data
│   │   ├── merged-seeds.json     # Master database (all seeds)
│   │   └── clean-seeds-*.json    # Individual harvest runs
│   └── dirty-collection-csv/     # Archived raw harvester output
├── output/                       # Harvester working directory
├── tni-harvester-1440p-v3.ahk    # AutoHotkey harvester (2560×1440)
├── tni-harvester-1080p-v3.ahk    # AutoHotkey harvester (1920×1080)
├── process-harvest.py            # Data processing pipeline
├── process-harvest.bat           # Double-click to process new harvest
└── show-stats.bat                # Double-click to see current stats
```

---

## 🔧 Running the Harvester

*Want to contribute to the hunt? Here's how to run your own harvests.*

### Requirements

- Windows 10/11
- [AutoHotkey v2](https://www.autohotkey.com/download/) (v2.0+, not v1.1)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (add to PATH, or configure full path in script)
- [Python 3.10+](https://www.python.org/downloads/) (for data processing)
- [Tower Networking Inc](https://store.steampowered.com/app/2381090/Tower_Networking_Inc/) (Steam)

### Available Scripts

| Script | Resolution | Display |
|--------|------------|---------|
| `tni-harvester-1440p-v3.ahk` | 2560×1440 | Fullscreen |
| `tni-harvester-1080p-v3.ahk` | 1920×1080 | Fullscreen |

### Setup

1. Choose the script matching your resolution (or see "Other Resolutions" below)

2. Edit the script and update the paths at the top:
   ```ahk
   workDir: "C:\tni-seed-harvester\output",
   gameExePath: "C:\Program Files (x86)\Steam\steamapps\common\Tower Networking Inc\Tower Networking Inc.exe",
   ```

3. If Tesseract isn't in your PATH, set the full path:
   ```ahk
   tesseractExe: "C:\Program Files\Tesseract-OCR\tesseract.exe",
   ```

4. Run the game in **fullscreen** at your target resolution

5. Start the harvester:
   - **F9** = Start harvesting loop
   - **F10** = Stop harvesting
   - **F11** = Single capture (for testing)
   - **F12** = Coordinate helper

6. After harvesting, double-click `process-harvest.bat` to:
   - Clean and validate the data
   - Merge into the master database
   - Update the frontend
   - Clear the output folder

### Other Resolutions

For resolutions other than 1440p or 1080p:

1. Copy the closest script as a starting point
2. Run the game at your resolution in fullscreen
3. Use **F12** (coordinate helper) to find correct positions for each UI element
4. Update the `coords` section in the script
5. Update the `captureRegions` section for OCR areas
6. Test with **F11** (single capture) before running the full loop

---

## 🔬 Technical Details

### How It Works

1. **Harvester** (AHK script):
   - Clicks through game menus to start a new game with a seed
   - Opens the Secretariat tablet and navigates to Proposals
   - Screenshots the proposal cards
   - Uses Tesseract OCR to extract text
   - Fuzzy-matches against known proposal patterns
   - Logs seed + proposals to CSV
   - Quits to menu and repeats

2. **Data Pipeline** (Python script):
   - Reads raw CSV from harvester
   - Removes OCR failures (UNKNOWN entries)
   - Validates seed codes (must be 5 characters)
   - Deduplicates within batch and against existing database
   - Saves clean JSON with timestamps
   - Creates backup before merging
   - Updates master database
   - Regenerates frontend with embedded data

---

## 🤝 Contributing

Found a new seed? Want to add support for a different resolution?

1. Fork this repo
2. Make your changes
3. Submit a pull request

Or just share your `seed-log.csv` in the Discord and I'll merge it!

---

## 📜 Credits

- **Project Lead & Testing**: Salvo Praxis
- **Development Assistance**: Claude (Anthropic) - AI pair programming partner
- **Game**: [Tower Networking Inc](https://store.steampowered.com/app/2381090/Tower_Networking_Inc/) by [Pocosia Studios](https://pocosia.com/)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

Use this however you like! If you find it useful, consider:
- ⭐ Starring this repo
- 🎮 Leaving a positive review for Tower Networking Inc on Steam
- 💬 Sharing cool seed finds in the Discord

---

*Keep up the awesome work [@Pocosia Studios](https://pocosia.com/) — yours is the only game like it, so "best in class" doesn't do it justice!*
