# TNI Seed Harvester

**Automated seed collection and proposal mapping for [Tower Networking Inc](https://store.steampowered.com/app/2939600/Tower_Networking_Inc/) by Pocosia Studios**

[![Seeds](https://img.shields.io/badge/seeds-3%2C794-blue)](data/clean-collection-json/merged-seeds.json)
[![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen)](data/clean-collection-json/merged-seeds.json)
[![Combinations](https://img.shields.io/badge/combinations-455%2F455-yellow)](data/clean-collection-json/merged-seeds.json)

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
| Total Seeds | 3,794 |
| Proposal Combinations | 455 / 455 (100.00%) |
| Unique Proposals | 15 |

**Progress:** ████████████████████ **100%** 🎉🎊

*We did it! All 455 combinations discovered!*

### 🎉 Complete Coverage!

**All 455 possible combinations have been found!**

This particular leg of the hunt is complete, but there's always more data to gather!

---

## 🔮 What We've Learned

*After harvesting 3,794 seeds, patterns emerge from the chaos.*

### The Game's Hidden Hand

The seed algorithm isn't purely random.

#### Slot Favoritism

Each proposal has a "home" slot where it appears most often. Some are almost locked to one position:

| Proposal | Slot 1 | Slot 2 | Slot 3 | Verdict |
|----------|--------|--------|--------|---------|
| Poems DB | 0% | 4% | **96%** | *Almost always last* |
| Legal Retaliation | **95%** | 5% | 0% | *Almost always first* |
| Undervoltage Directive | **77%** | 22% | 2% | *Strongly prefers first* |
| Second Monitor | 1% | 23% | **76%** | *Strongly prefers last* |
| Remote Backups | 11% | 14% | **75%** | *Strongly prefers last* |
| Scanning Exploit | 3% | 33% | **64%** | *Usually last* |
| PADU | **64%** | 32% | 4% | *Usually first* |

Other proposals (Fusion Plant, Lean Administration, Overvoltage, etc.) are more flexible, appearing across all three slots without strong preference.

#### Proposals That Avoid Each Other

Some pairs rarely appear together. The five rarest pairings:

| Pair | Frequency | Notes |
|------|-----------|-------|
| Remote Backups + Scanning Exploit | 2.2% |  |
| Fusion Plant + Lobby against Tenabolt | 2.2% |  |
| Scanning Exploit + Undervoltage | 2.3% |  |
| Lobby against Tenabolt + Remote Backups | 2.3% |  |
| Overvoltage + Undervoltage | 2.3% | *Contradictory policies* |

With full coverage achieved, we can see the true rarity distribution!

#### Proposals That Stick Together

Meanwhile, these pairs appear together more often than expected:

| Pair | Frequency |
|------|-----------|
| Legal Retaliation + Undervoltage | 3.6% |
| Overvoltage + PADU | 3.4% |
| NetOps + Undervoltage | 3.4% |
| Power Management + Scanning Exploit | 3.3% |
| Lean Administration + Undervoltage | 3.3% |

Power Management Research is the social butterfly of proposals.

---

## 🦄 Unicorn Seeds

Only **1 combination** exists exactly once in our database: 

| Seed | Combination | Total Cost |
|------|-------------|------------|
| JNLRY | Scanning Exploit + Second Monitor + Undervoltage | 3900 |

---

## 📈 Proposal Draw Rates

How likely is each proposal to appear in any given seed?

| Proposal | Appears In | Draw Weight |
|----------|------------|-------------|
| Second Monitor | 19.0% of seeds | 0.95x |
| Lobby against Tenabolt | 19.2% | 0.96x |
| Cabler's Union (Base) | 19.3% | 0.97x |
| Fusion Plant | 19.5% | 0.97x |
| NetOps Research | 19.5% | 0.97x |
| Remote Backups | 19.5% | 0.98x |
| Undervoltage Directive | 19.7% | 0.99x |
| Refurbhut Investment | 20.0% | 1.00x |
| Scanning Exploit | 20.0% | 1.00x |
| PADU | 20.1% | 1.00x |
| Poems DB | 20.6% | 1.03x |
| Overvoltage Directive | 20.6% | 1.03x |
| Lean Administration | 20.7% | 1.04x |
| Legal Retaliation | 20.9% | 1.05x |
| Power Management Research | 21.4% | 1.07x |

*Draw Weight: 1.00x = expected if perfectly uniform.*

**The surprising truth:** Overall proposal frequency is nearly balanced (~3% variance). The game doesn't make proposals rarer — it controls *where* they appear and *what* they appear *with*. The weighting is in the combinations, not the individual draws.

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

### Requirements

- Windows 10/11
- [AutoHotkey v2](https://www.autohotkey.com/download/) (v2.0+, not v1.1)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (add to PATH, or configure full path in script)
- [Python 3.10+](https://www.python.org/downloads/) (for data processing)
- [Tower Networking Inc](https://store.steampowered.com/app/2939600/Tower_Networking_Inc/) (Steam)

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
   - Opens the Secretariat app and navigates to Proposals
   - Screenshots the available proposals
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
- **Game**: [Tower Networking Inc](https://store.steampowered.com/app/2939600/Tower_Networking_Inc/) by [Pocosia Studios](https://pocosia.com/)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

Use this however you like! If you find it useful, consider:
- ⭐ Starring this repo
- 🎮 Leaving a positive review for Tower Networking Inc on Steam
- 💬 Sharing cool seed finds in the Discord

---

*Keep up the awesome work [@Pocosia Studios](https://pocosia.com/) — yours is the only game like it, so "best in class" doesn't do it justice!*
