#!/usr/bin/env python3
"""
================================================================================
TNI Seed Harvester - Data Processing Pipeline
================================================================================

This script processes harvested seed data through the complete pipeline:

    1. Reads raw CSV from output/seed-log.csv (produced by the AHK harvester)
    2. Cleans and validates the data (removes UNKNOWNs, validates seed codes)
    3. Saves timestamped clean JSON to data/clean-collection-json/
    4. Archives raw CSV to data/dirty-collection-csv/
    5. Backs up existing merged database before modification
    6. Merges new data into merged-seeds.json
    7. Updates the frontend HTML with embedded seed data
    8. Clears output/ directory for the next harvesting run

Usage:
    python process-harvest.py                    # Process new harvest and update everything
    python process-harvest.py --dry-run          # Preview changes without modifying files
    python process-harvest.py --stats            # Display current database statistics
    python process-harvest.py --regenerate-frontend  # Regenerate frontend with new styling

Or double-click process-harvest.bat

Directory Structure:
    tni-seed-harvester/
    ├── output/                         # AHK harvester writes here (cleared after processing)
    │   └── seed-log.csv                # Raw harvest output
    ├── data/
    │   ├── clean-collection-json/      # Processed JSON files
    │   │   ├── clean-seeds-*.json      # Individual harvest runs
    │   │   ├── merged-seeds.json       # Master database
    │   │   └── merged-seeds-backup-*.json  # Backups before merge
    │   └── dirty-collection-csv/       # Archived raw CSVs
    │       └── seed-log-*.csv          # Timestamped raw data
    └── frontend/
        └── tni-seed-finder.html        # Web UI with embedded data

Repository: https://github.com/salvo-praxis/tni-seed-harvester
Game: Tower Networking Inc by Pocosia Studios
================================================================================
"""

import csv
import json
import shutil
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path
from collections import OrderedDict


# =============================================================================
# CONFIGURATION
# =============================================================================

# Base directory - automatically detected from script location
BASE_DIR = Path(__file__).parent.resolve()

# Directory paths (relative to BASE_DIR)
OUTPUT_DIR = BASE_DIR / "output"                    # Where AHK writes raw data
DATA_DIR = BASE_DIR / "data"                        # Parent data directory
CLEAN_JSON_DIR = DATA_DIR / "clean-collection-json" # Processed JSON storage
DIRTY_CSV_DIR = DATA_DIR / "dirty-collection-csv"   # Raw CSV archives
FRONTEND_DIR = BASE_DIR / "frontend"                # Web UI files

# Important file paths
SEED_LOG_CSV = OUTPUT_DIR / "seed-log.csv"          # Raw harvest output from AHK
MERGED_JSON = CLEAN_JSON_DIR / "merged-seeds.json"  # Master seed database
FRONTEND_HTML = FRONTEND_DIR / "tni-seed-finder.html"  # Web interface

# All known proposals in Tower Networking Inc
# Used for calculating combination coverage (15 proposals = 455 possible 3-combos)
ALL_PROPOSALS = [
    "Cabler's Union (Base)",
    "Fusion Plant",
    "Lean Administration",
    "Legal Retaliation",
    "Lobby against Tenabolt",
    "NetOps Research",
    "Overvoltage Directive",
    "PADU",
    "Poems DB",
    "Power Management Research",
    "Refurbhut Investment",
    "Remote Backups",
    "Scanning Exploit",
    "Second Monitor",
    "Undervoltage Directive"
]

# Total possible 3-proposal combinations: C(15,3) = 455
TOTAL_COMBINATIONS = 455

# Proposal definitions with game details
# These are embedded in the JSON output for reference
PROPOSAL_DEFINITIONS = {
    "Cabler's Union (Base)": {
        "description": "Support the Cabler's Union R&D institute",
        "cost": 300,
        "effect": "Unlocks more proposals for the Cabler's Union"
    },
    "Fusion Plant": {
        "description": "Fusion Plant Funding (Phase 1) - Let's make a Sun",
        "cost": 1000,
        "effect": "Reduce all Data Center power cost by 20%"
    },
    "Lean Administration": {
        "description": "Pain now for gain later",
        "cost": 600,
        "effect": "Permanently reduce daily admin expenses by 30%"
    },
    "Legal Retaliation": {
        "description": "Another power outage? See you in court!",
        "cost": None,  # Policy change, no direct cost
        "effect": "Tenabolt pays 500 per outage/surge, items 10% more expensive, eliminates Tenabolt collaboration"
    },
    "Lobby against Tenabolt": {
        "description": "Power to the people",
        "cost": None,  # Policy change, no direct cost
        "effect": "Tenabolt can't issue non-DC power fines, items 20% more expensive, eliminates Tenabolt collaboration"
    },
    "NetOps Research": {
        "description": "Improvise, adapt, overcome",
        "cost": 330,
        "effect": "Unlocks 'cron', 'try', and 'notify' routines on NetShell"
    },
    "Overvoltage Directive": {
        "description": "POWER OVERWHELMING!",
        "cost": 200,
        "effect": "-30% power outage chance, +30% power surge chance"
    },
    "PADU": {
        "description": "PADU Development Funding - Everyone's favorite database",
        "cost": 300,
        "effect": "Unlocks padu_v3 program (stores text, image, audio, video)"
    },
    "Poems DB": {
        "description": "A DB just for the text chads",
        "cost": 200,
        "effect": "Unlocks poems-db program (text-only storage, lightweight)"
    },
    "Power Management Research": {
        "description": "Keep bills low and reliability high",
        "cost": 225,
        "effect": "Unlocks 'power' routine on NetShell"
    },
    "Refurbhut Investment": {
        "description": "As long as it works...",
        "cost": 555,
        "effect": "Opens RefurbHut merchant (cheap refurbished devices, no warranty)"
    },
    "Remote Backups": {
        "description": "3-2-1, let's back it up!",
        "cost": 450,
        "effect": "Unlocks 'sftp' routine (backup configs, remove malware)"
    },
    "Scanning Exploit": {
        "description": "Scans too shall pass",
        "cost": 1200,
        "effect": "Netsh and autograph scans bypass all router rules (toggle on/off)"
    },
    "Second Monitor": {
        "description": "Screen too small?",
        "cost": 2500,
        "effect": "Allows use of second monitor (right-alt)"
    },
    "Undervoltage Directive": {
        "description": "Better dark than magic smoke",
        "cost": 200,
        "effect": "+30% power outage chance, -30% power surge chance"
    }
}

# JavaScript template for frontend PROPOSALS constant
# This is injected into the HTML when updating the frontend
FRONTEND_PROPOSALS_JS = '''        const PROPOSALS = {
            "Cabler's Union (Base)": { tagline: "Support the Cabler's Union R&D institute", effect: "Unlocks more proposals for the Cabler's Union", cost: 300 },
            "Fusion Plant": { tagline: "Let's make a Sun", effect: "Reduce all Data Center power cost by 20%", cost: 1000 },
            "Lean Administration": { tagline: "Pain now for gain later", effect: "Permanently reduce daily admin expenses by 30%", cost: 600 },
            "Legal Retaliation": { tagline: "Another power outage? See you in court!", effect: "Tenabolt pays 500 per outage/surge, items 10% more expensive", cost: null },
            "Lobby against Tenabolt": { tagline: "Power to the people", effect: "Tenabolt can't issue non-DC power fines, items 20% more expensive", cost: null },
            "NetOps Research": { tagline: "Improvise, adapt, overcome", effect: "Unlocks 'cron', 'try', and 'notify' routines", cost: 330 },
            "Overvoltage Directive": { tagline: "POWER OVERWHELMING!", effect: "-30% power outage, +30% power surge chance", cost: 200 },
            "PADU": { tagline: "Everyone's favorite database", effect: "Unlocks padu_v3 (stores text, image, audio, video)", cost: 300 },
            "Poems DB": { tagline: "A DB just for the text chads", effect: "Unlocks poems-db (text-only, lightweight)", cost: 200 },
            "Power Management Research": { tagline: "Keep bills low and reliability high", effect: "Unlocks 'power' routine on NetShell", cost: 225 },
            "Refurbhut Investment": { tagline: "As long as it works...", effect: "Opens RefurbHut merchant (cheap refurbished devices)", cost: 555 },
            "Remote Backups": { tagline: "3-2-1, let's back it up!", effect: "Unlocks 'sftp' routine (backup configs, remove malware)", cost: 450 },
            "Scanning Exploit": { tagline: "Scans too shall pass", effect: "Netsh and autograph scans bypass all router rules", cost: 1200 },
            "Second Monitor": { tagline: "Screen too small?", effect: "Allows use of second monitor (right-alt)", cost: 2500 },
            "Undervoltage Directive": { tagline: "Better dark than magic smoke", effect: "+30% power outage, -30% power surge chance", cost: 200 }
        };
        
'''

# Complete HTML template for generating the frontend from scratch
# Uses modern NOC-style dark theme with green/blue accents
# Version 1.3.0 - Added Spoiler Prevention mode
FRONTEND_HTML_TEMPLATE = '''<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  TNI Starting Proposal Seed Finder                                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Version: 1.3.0                                                              ║
║  Updated: {generation_date}                                                  ║
║  Part of: TNI Toolkit (https://github.com/salvo-praxis/tni-toolkit)          ║
║  Source:  TNI Seed Harvester (https://github.com/salvo-praxis/tni-seed-harvester)
╠══════════════════════════════════════════════════════════════════════════════╣
║  Description:                                                                ║
║    Search a database of verified seeds by selecting up to 3 starting         ║
║    proposals. Find the perfect seed for your preferred playstyle.            ║
║                                                                              ║
║  Features:                                                                   ║
║    - 455 possible starting proposal combinations                             ║
║    - 100% coverage of all combinations achieved                              ║
║    - Filter by proposal name, search by seed                                 ║
║    - Shows total starting cost for each seed                                 ║
║    - Configurable results per page with pagination                           ║
║    - Spoiler Prevention mode to hide unselected proposals                    ║
║                                                                              ║
║  Data Pipeline:                                                              ║
║    AutoHotkey v2 automation → Tesseract OCR → Python processing → HTML       ║
║                                                                              ║
║  Contributors:                                                               ║
║    - Salvo Praxis (automation pipeline, data collection)                     ║
║    - Claude (Anthropic)                                                      ║
║                                                                              ║
║  Changelog:                                                                  ║
║    1.3.0 - Added Spoiler Prevention mode to hide unselected proposals        ║
║    1.2.0 - Added config menu, pagination, results per page stepper           ║
║    1.1.0 - Renamed "Starting Proposal Seed Finder", header/footer, back link ║
║    1.0.0 - Initial release with 3,794 seeds, 455 combinations                ║
╚══════════════════════════════════════════════════════════════════════════════╝
-->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seed Finder - TNI Toolkit</title>
    
    <!-- SEO Meta Tags -->
    <meta name="description" content="Find Tower Networking Inc. world seeds by starting proposals. 455 combinations across 3,794 verified seeds.">
    <meta name="author" content="Salvo Praxis">
    <meta name="robots" content="index, follow">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Seed Finder - TNI Toolkit">
    <meta property="og:description" content="Find Tower Networking Inc. world seeds by starting proposals. 455 combinations across 3,794 verified seeds.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://tni-toolkit.salvo.host/tools/seed-finder.html">
    <meta property="og:site_name" content="TNI Toolkit">
    <meta property="og:image" content="https://tni-toolkit.salvo.host/images/og-preview.png">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Seed Finder - TNI Toolkit">
    <meta name="twitter:description" content="Find TNI world seeds by starting proposals. 455 combinations, 3,794 seeds.">
    
    <!-- Canonical URL -->
    <link rel="canonical" href="https://tni-toolkit.salvo.host/tools/seed-finder.html">
    
    <style>
        * {{ box-sizing: border-box; }}
        
        /* Custom Scrollbars */
        * {{
            scrollbar-width: thin;
            scrollbar-color: #30363d #0d1117;
        }}
        
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #0d1117; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 4px; border: 1px solid #0d1117; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #58a6ff; }}
        ::-webkit-scrollbar-corner {{ background: #0d1117; }}
        
        body {{
            font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace;
            background: linear-gradient(135deg, #0a0e14 0%, #1a1f2e 50%, #0d1117 100%);
            color: #c9d1d9;
            margin: 0;
            padding: 24px;
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        /* Back to Toolkit button */
        .back-link {{
            display: none;
            margin-top: 16px;
            color: #58a6ff;
            text-decoration: none;
            font-size: 11px;
            padding: 6px 12px;
            border: 1px solid #30363d;
            border-radius: 4px;
            transition: all 0.15s;
        }}
        .back-link:hover {{
            border-color: #58a6ff;
            background: rgba(88, 166, 255, 0.1);
        }}
        .back-link.visible {{
            display: inline-block;
        }}
        
        .header {{
            text-align: center;
            padding: 40px 0 30px;
            border-bottom: 1px solid #30363d;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
            margin: 0 0 8px 0;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        
        .header h1 span {{ color: #58a6ff; }}
        
        .subtitle {{ color: #8b949e; margin: 0; font-size: 12px; }}
        .stats {{ color: #7d8590; font-size: 11px; margin-top: 8px; }}
        
        .panel {{
            background: rgba(22,27,34,0.8);
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }}
        
        .panel h2 {{
            margin-top: 0;
            color: #58a6ff;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #30363d;
            padding-bottom: 12px;
        }}
        
        .proposals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 10px;
        }}
        
        .proposal-card {{
            background: rgba(22,27,34,0.8);
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        
        .proposal-card:hover {{
            border-color: #58a6ff;
            background: rgba(88,166,255,0.08);
        }}
        
        .proposal-card.selected {{
            border-color: #00ff88;
            background: rgba(0,255,136,0.1);
        }}
        
        .proposal-card.disabled {{ opacity: 0.4; cursor: not-allowed; }}
        .proposal-name {{ font-weight: 500; color: #c9d1d9; margin-bottom: 4px; font-size: 12px; }}
        .proposal-tagline {{ font-style: italic; color: #8b949e; font-size: 10px; margin-bottom: 6px; }}
        .proposal-effect {{ font-size: 10px; color: #58a6ff; }}
        .proposal-cost {{ font-size: 10px; color: #f0883e; margin-top: 4px; }}
        
        .selection-summary {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        
        .selected-tag {{
            background: rgba(0,255,136,0.15);
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 500;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .selected-tag .remove {{ cursor: pointer; opacity: 0.7; }}
        .selected-tag .remove:hover {{ opacity: 1; }}
        
        .clear-btn {{
            background: rgba(248,81,73,0.15);
            border: 1px solid #f85149;
            color: #f85149;
            padding: 6px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            font-family: inherit;
        }}
        .clear-btn:hover {{ background: rgba(248,81,73,0.25); }}
        
        .results-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .results-count {{ color: #00ff88; font-weight: 600; font-size: 12px; }}
        
        .seed-results {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 15px;
        }}
        
        .seed-card {{
            background: rgba(22,27,34,0.8);
            border-radius: 6px;
            padding: 15px;
            border: 1px solid #30363d;
        }}
        
        .seed-code {{
            font-family: inherit;
            font-size: 1.4em;
            font-weight: 600;
            color: #00ff88;
            text-align: center;
            padding: 10px;
            background: rgba(0,255,136,0.08);
            border: 1px solid #238636;
            border-radius: 4px;
            margin-bottom: 12px;
            letter-spacing: 4px;
            cursor: pointer;
            transition: background 0.15s;
        }}
        
        .seed-code:hover {{ background: rgba(0,255,136,0.15); }}
        .seed-code.copied {{ background: rgba(35,134,54,0.3); border-color: #238636; }}
        
        .seed-proposals {{ display: flex; flex-direction: column; gap: 8px; }}
        
        .seed-proposal {{
            background: rgba(22,27,34,0.6);
            padding: 8px 10px;
            border-radius: 4px;
            border-left: 3px solid #58a6ff;
        }}
        
        .seed-proposal.matched {{
            border-left-color: #00ff88;
            background: rgba(0,255,136,0.08);
        }}
        
        .seed-proposal-name {{ font-weight: 500; color: #c9d1d9; font-size: 11px; }}
        .seed-proposal-effect {{ font-size: 10px; color: #8b949e; margin-top: 2px; }}
        .no-results {{ text-align: center; color: #8b949e; padding: 40px; font-size: 12px; }}
        
        .search-box {{ margin-bottom: 15px; }}
        .search-box input {{
            width: 100%;
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid #30363d;
            background: rgba(22,27,34,0.8);
            color: #c9d1d9;
            font-size: 12px;
            font-family: inherit;
        }}
        .search-box input:focus {{ outline: none; border-color: #58a6ff; }}
        .search-box input::placeholder {{ color: #8b949e; }}

        .tooltip {{
            position: fixed;
            background: #238636;
            color: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 500;
            font-size: 11px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.15s;
            z-index: 1000;
        }}
        .tooltip.show {{ opacity: 1; }}
        
        /* Config Bar */
        .config-bar {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 16px;
            position: relative;
        }}
        
        .config-btn {{
            background: rgba(22, 27, 34, 0.8);
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 8px 12px;
            color: #8b949e;
            cursor: pointer;
            font-family: inherit;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s;
        }}
        
        .config-btn:hover {{
            border-color: #58a6ff;
            color: #c9d1d9;
        }}
        
        .config-btn.active {{
            border-color: #58a6ff;
            background: rgba(88, 166, 255, 0.1);
            color: #58a6ff;
        }}
        
        .config-btn svg {{
            width: 14px;
            height: 14px;
        }}
        
        .config-panel {{
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 8px;
            background: rgba(22, 27, 34, 0.95);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            min-width: 320px;
            z-index: 100;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            display: none;
        }}
        
        .config-panel.show {{ display: block; }}
        
        .config-panel h3 {{
            color: #58a6ff;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #30363d;
        }}
        
        .config-option {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            min-height: 36px;
        }}
        
        .config-option + .config-option {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #21262d;
        }}
        
        .config-option-label {{
            color: #c9d1d9;
            font-size: 12px;
        }}
        
        .config-option-desc {{
            color: #8b949e;
            font-size: 10px;
            margin-top: 2px;
        }}
        
        .stepper {{
            display: flex;
            align-items: center;
            gap: 0;
            background: #21262d;
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid #30363d;
        }}
        
        .stepper button {{
            width: 28px;
            height: 26px;
            border: none;
            background: linear-gradient(180deg, #2d333b 0%, #22272e 100%);
            color: #58a6ff;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .stepper button:hover:not(:disabled) {{
            background: linear-gradient(180deg, #3d444d 0%, #2d333b 100%);
            color: #00ff88;
        }}
        
        .stepper button:active:not(:disabled) {{
            background: linear-gradient(180deg, #22272e 0%, #2d333b 100%);
        }}
        
        .stepper button:disabled {{
            color: #484f58;
            cursor: not-allowed;
            background: #21262d;
        }}
        
        .stepper button:first-child {{
            border-right: 1px solid #30363d;
        }}
        
        .stepper button:last-child {{
            border-left: 1px solid #30363d;
        }}
        
        .stepper-value {{
            min-width: 40px;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #00ff88;
            padding: 0 6px;
            background: rgba(0, 255, 136, 0.05);
            border: none;
            outline: none;
            height: 26px;
        }}
        
        .stepper-value::-webkit-outer-spin-button,
        .stepper-value::-webkit-inner-spin-button {{
            -webkit-appearance: none;
            appearance: none;
            margin: 0;
        }}
        
        .stepper-value[type=number] {{
            -moz-appearance: textfield;
            appearance: textfield;
        }}
        
        /* Toggle Switch */
        .toggle-switch {{
            position: relative;
            width: 44px;
            height: 24px;
            flex-shrink: 0;
        }}
        
        .toggle-switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        
        .toggle-slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 12px;
            transition: all 0.2s;
        }}
        
        .toggle-slider:before {{
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 2px;
            bottom: 2px;
            background: #8b949e;
            border-radius: 50%;
            transition: all 0.2s;
        }}
        
        .toggle-switch input:checked + .toggle-slider {{
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
        }}
        
        .toggle-switch input:checked + .toggle-slider:before {{
            transform: translateX(20px);
            background: #00ff88;
        }}
        
        .toggle-switch:hover .toggle-slider {{
            border-color: #58a6ff;
        }}
        
        /* Redacted Proposal Styles */
        .seed-proposal.redacted {{
            background: repeating-linear-gradient(
                90deg,
                #1a1f2e 0px,
                #1a1f2e 2px,
                #21262d 2px,
                #21262d 4px
            );
            border-left-color: #484f58;
            position: relative;
            overflow: hidden;
            min-height: 52px;
        }}
        
        .seed-proposal.redacted .seed-proposal-name,
        .seed-proposal.redacted .seed-proposal-effect {{
            visibility: hidden;
        }}
        
        .redacted-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(
                90deg,
                rgba(22, 27, 34, 0.95) 0%,
                rgba(33, 38, 45, 0.98) 50%,
                rgba(22, 27, 34, 0.95) 100%
            );
            border-left: 3px solid #484f58;
            margin-left: -3px;
        }}
        
        .redacted-bar {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: linear-gradient(180deg, #2d333b 0%, #21262d 100%);
            border: 1px solid #484f58;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #6e7681;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }}
        
        .redacted-bar svg {{
            width: 12px;
            height: 12px;
            opacity: 0.6;
        }}
        
        /* Spoiler indicator badge */
        .spoiler-badge {{
            display: none;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: rgba(110, 118, 129, 0.15);
            border: 1px solid #484f58;
            border-radius: 4px;
            font-size: 9px;
            color: #6e7681;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-right: 8px;
        }}
        
        .spoiler-badge.active {{
            display: inline-flex;
        }}
        
        .spoiler-badge svg {{
            width: 11px;
            height: 11px;
        }}
        
        /* Pagination */
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .page-btn {{
            background: rgba(22, 27, 34, 0.8);
            border: 1px solid #30363d;
            color: #8b949e;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            font-family: inherit;
            transition: all 0.15s;
        }}
        
        .page-btn:hover:not(:disabled) {{
            border-color: #58a6ff;
            color: #58a6ff;
        }}
        
        .page-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .page-btn.active {{
            background: rgba(0, 255, 136, 0.15);
            border-color: #00ff88;
            color: #00ff88;
        }}
        
        .page-info {{
            color: #8b949e;
            font-size: 11px;
            padding: 0 8px;
        }}
        
        /* Footer */
        .site-footer {{
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #30363d;
            text-align: center;
            font-size: 11px;
            color: #7d8590;
        }}
        
        .site-footer a {{
            color: #8b949e;
            text-decoration: none;
            transition: color 0.15s;
        }}
        
        .site-footer a:hover {{
            color: #58a6ff;
        }}
        
        .site-footer .sep {{
            margin: 0 8px;
            color: #30363d;
        }}
        
        .site-footer .footer-note {{
            margin: 12px 0;
            color: #7d8590;
        }}
        
        .site-footer .footer-badges {{
            margin-top: 12px;
        }}
        
        .site-footer .version-badge {{
            display: inline-block;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #30363d;
            color: #8b949e;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 10px;
            margin-right: 8px;
        }}
        
        .site-footer .license-badge {{
            display: inline-block;
            background: rgba(88, 166, 255, 0.1);
            border: 1px solid #30363d;
            color: #8b949e;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 10px;
            text-decoration: none;
            transition: all 0.15s;
        }}
        
        .site-footer .license-badge:hover {{
            border-color: #58a6ff;
            color: #58a6ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span>TNI</span> STARTING PROPOSAL SEED FINDER</h1>
            <p class="subtitle">Select Proposals • 455 Combinations • <span id="seedCount">0</span> Seeds</p>
            <a href="../index.html" class="back-link" id="back-to-toolkit">← Back to Toolkit</a>
        </div>
        
        <!-- Config Bar -->
        <div class="config-bar">
            <span class="spoiler-badge" id="spoilerBadge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
                Spoiler Prevention Active
            </span>
            <button class="config-btn" id="configToggle" onclick="toggleConfig()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                Settings
            </button>
            <div class="config-panel" id="configPanel">
                <h3>⚙ Display Settings</h3>
                <div class="config-option">
                    <div>
                        <div class="config-option-label">Results per page</div>
                        <div class="config-option-desc">Seeds shown per page (1-200)</div>
                    </div>
                    <div class="stepper">
                        <button id="stepDown" title="Decrease by 20">−</button>
                        <input type="number" class="stepper-value" id="resultsPerPage" value="20" min="1" max="200" step="1">
                        <button id="stepUp" title="Increase by 20">+</button>
                    </div>
                </div>
                <div class="config-option">
                    <div>
                        <div class="config-option-label">Spoiler Prevention</div>
                        <div class="config-option-desc">Hide unselected proposals for surprise</div>
                    </div>
                    <label class="toggle-switch">
                        <input type="checkbox" id="spoilerToggle">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>📋 Select Proposals (up to 3)</h2>
            <div class="search-box">
                <input type="text" id="proposalSearch" placeholder="Filter proposals...">
            </div>
            <div class="selection-summary" id="selectionSummary"></div>
            <div class="proposals-grid" id="proposalsGrid"></div>
        </div>
        
        <div class="panel">
            <h2>🎯 Matching Seeds</h2>
            <div class="results-header">
                <span class="results-count" id="resultsCount">Select proposals above to find seeds</span>
            </div>
            <div id="seedResults" class="seed-results">
                <div class="no-results">👆 Click on proposals above to find matching seeds</div>
            </div>
            <div class="pagination" id="pagination"></div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip">Copied!</div>

    <script>
{proposals_js}{seed_db_js}
        let selectedProposals = [];
        let currentPage = 1;
        let resultsPerPage = parseInt(localStorage.getItem('seedFinderResultsPerPage')) || 20;
        let spoilerPrevention = localStorage.getItem('seedFinderSpoilerPrevention') === 'true';
        let currentMatches = [];

        function init() {{
            document.getElementById('seedCount').textContent = SEED_DB.seeds.length;
            document.getElementById('resultsPerPage').value = resultsPerPage;
            document.getElementById('spoilerToggle').checked = spoilerPrevention;
            updateSpoilerBadge();
            updateStepperButtons();
            renderProposals();
            updateResults();
        }}

        function renderProposals() {{
            const grid = document.getElementById('proposalsGrid');
            const searchTerm = document.getElementById('proposalSearch').value.toLowerCase();
            grid.innerHTML = '';
            
            for (const [name, info] of Object.entries(PROPOSALS)) {{
                if (searchTerm && !name.toLowerCase().includes(searchTerm) && !info.effect.toLowerCase().includes(searchTerm)) continue;
                
                const card = document.createElement('div');
                card.className = 'proposal-card';
                if (selectedProposals.includes(name)) card.classList.add('selected');
                else if (selectedProposals.length >= 3) card.classList.add('disabled');
                
                card.innerHTML = `
                    <div class="proposal-name">${{name}}</div>
                    <div class="proposal-tagline">"${{info.tagline}}"</div>
                    <div class="proposal-effect">${{info.effect}}</div>
                    ${{info.cost ? `<div class="proposal-cost">💰 Cost: ${{info.cost}}</div>` : `<div class="proposal-cost">📜 Policy change</div>`}}
                `;
                card.onclick = () => toggleProposal(name);
                grid.appendChild(card);
            }}
        }}

        function toggleProposal(name) {{
            const idx = selectedProposals.indexOf(name);
            if (idx >= 0) selectedProposals.splice(idx, 1);
            else if (selectedProposals.length < 3) selectedProposals.push(name);
            currentPage = 1;
            renderProposals();
            renderSelectionSummary();
            updateResults();
        }}

        function renderSelectionSummary() {{
            const summary = document.getElementById('selectionSummary');
            if (selectedProposals.length === 0) {{
                summary.innerHTML = '<span style="color: #8b949e">No proposals selected</span>';
                return;
            }}
            let html = selectedProposals.map(name => `
                <span class="selected-tag">${{name}}<span class="remove" onclick="event.stopPropagation(); toggleProposal('${{name.replace(/'/g, "\\\\'")}}')">\u2715</span></span>
            `).join('');
            html += `<button class="clear-btn" onclick="clearSelection()">Clear All</button>`;
            summary.innerHTML = html;
        }}

        function clearSelection() {{
            selectedProposals = [];
            currentPage = 1;
            renderProposals();
            renderSelectionSummary();
            updateResults();
        }}

        function renderProposalCard(proposalName, isMatched, isRedacted) {{
            const info = PROPOSALS[proposalName];
            
            if (isRedacted) {{
                return `<div class="seed-proposal redacted">
                    <div class="seed-proposal-name">${{proposalName}}</div>
                    <div class="seed-proposal-effect">${{info ? info.effect : 'Unknown'}}</div>
                    <div class="redacted-overlay">
                        <div class="redacted-bar">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                                <line x1="1" y1="1" x2="23" y2="23"></line>
                            </svg>
                            Proposal Redacted
                        </div>
                    </div>
                </div>`;
            }}
            
            return `<div class="seed-proposal ${{isMatched ? 'matched' : ''}}">
                <div class="seed-proposal-name">${{proposalName}}</div>
                <div class="seed-proposal-effect">${{info ? info.effect : 'Unknown'}}</div>
            </div>`;
        }}

        function updateResults() {{
            const resultsDiv = document.getElementById('seedResults');
            const countDiv = document.getElementById('resultsCount');
            const paginationDiv = document.getElementById('pagination');
            
            if (selectedProposals.length === 0) {{
                resultsDiv.innerHTML = '<div class="no-results">👆 Click on proposals above to find matching seeds</div>';
                countDiv.textContent = 'Select proposals above to find seeds';
                paginationDiv.innerHTML = '';
                return;
            }}
            
            currentMatches = SEED_DB.seeds.filter(entry => 
                selectedProposals.every(p => entry.p.includes(p))
            );
            
            if (currentMatches.length === 0) {{
                resultsDiv.innerHTML = `<div class="no-results">😔 No seeds found with all selected proposals<br><small>Try selecting fewer proposals or different combinations</small></div>`;
                countDiv.textContent = '0 seeds found';
                paginationDiv.innerHTML = '';
                return;
            }}
            
            const totalPages = Math.ceil(currentMatches.length / resultsPerPage);
            if (currentPage > totalPages) currentPage = totalPages;
            
            const startIdx = (currentPage - 1) * resultsPerPage;
            const endIdx = Math.min(startIdx + resultsPerPage, currentMatches.length);
            const pageMatches = currentMatches.slice(startIdx, endIdx);
            
            countDiv.textContent = `${{currentMatches.length}} seed${{currentMatches.length > 1 ? 's' : ''}} found (showing ${{startIdx + 1}}-${{endIdx}})`;
            
            resultsDiv.innerHTML = pageMatches.map(entry => {{
                return `
                    <div class="seed-card">
                        <div class="seed-code" onclick="copySeed('${{entry.s}}', this)" title="Click to copy">${{entry.s}}</div>
                        <div class="seed-proposals">
                            ${{entry.p.map(p => {{
                                const isMatched = selectedProposals.includes(p);
                                const isRedacted = spoilerPrevention && !isMatched;
                                return renderProposalCard(p, isMatched, isRedacted);
                            }}).join('')}}
                        </div>
                    </div>
                `;
            }}).join('');
            
            renderPagination(totalPages);
        }}

        function renderPagination(totalPages) {{
            const paginationDiv = document.getElementById('pagination');
            if (totalPages <= 1) {{
                paginationDiv.innerHTML = '';
                return;
            }}
            
            let html = '';
            html += `<button class="page-btn" onclick="goToPage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}}>← Prev</button>`;
            
            const maxVisible = 5;
            let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
            let endPage = Math.min(totalPages, startPage + maxVisible - 1);
            if (endPage - startPage < maxVisible - 1) {{
                startPage = Math.max(1, endPage - maxVisible + 1);
            }}
            
            if (startPage > 1) {{
                html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
                if (startPage > 2) html += `<span class="page-info">...</span>`;
            }}
            
            for (let i = startPage; i <= endPage; i++) {{
                html += `<button class="page-btn ${{i === currentPage ? 'active' : ''}}" onclick="goToPage(${{i}})">${{i}}</button>`;
            }}
            
            if (endPage < totalPages) {{
                if (endPage < totalPages - 1) html += `<span class="page-info">...</span>`;
                html += `<button class="page-btn" onclick="goToPage(${{totalPages}})">${{totalPages}}</button>`;
            }}
            
            html += `<button class="page-btn" onclick="goToPage(${{currentPage + 1}})" ${{currentPage === totalPages ? 'disabled' : ''}}>Next →</button>`;
            
            paginationDiv.innerHTML = html;
        }}

        function goToPage(page) {{
            const totalPages = Math.ceil(currentMatches.length / resultsPerPage);
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            updateResults();
            document.querySelector('.panel:nth-child(2)').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}

        function copySeed(seed, element) {{
            navigator.clipboard.writeText(seed).then(() => {{
                element.classList.add('copied');
                const tooltip = document.getElementById('tooltip');
                const rect = element.getBoundingClientRect();
                tooltip.style.left = rect.left + rect.width/2 - 40 + 'px';
                tooltip.style.top = rect.top - 40 + 'px';
                tooltip.classList.add('show');
                setTimeout(() => {{
                    element.classList.remove('copied');
                    tooltip.classList.remove('show');
                }}, 1500);
            }});
        }}
        
        function updateStepperButtons() {{
            const value = parseInt(document.getElementById('resultsPerPage').value);
            document.getElementById('stepDown').disabled = value <= 1;
            document.getElementById('stepUp').disabled = value >= 200;
        }}
        
        function setResultsPerPage(value) {{
            value = Math.max(1, Math.min(200, Math.floor(value)));
            resultsPerPage = value;
            document.getElementById('resultsPerPage').value = value;
            localStorage.setItem('seedFinderResultsPerPage', value);
            updateStepperButtons();
            currentPage = 1;
            updateResults();
        }}
        
        function updateSpoilerBadge() {{
            const badge = document.getElementById('spoilerBadge');
            if (spoilerPrevention) {{
                badge.classList.add('active');
            }} else {{
                badge.classList.remove('active');
            }}
        }}
        
        function setSpoilerPrevention(enabled) {{
            spoilerPrevention = enabled;
            localStorage.setItem('seedFinderSpoilerPrevention', enabled);
            updateSpoilerBadge();
            updateResults();
        }}

        // Event Listeners
        document.getElementById('proposalSearch').addEventListener('input', renderProposals);
        
        document.getElementById('stepDown').addEventListener('click', () => {{
            setResultsPerPage(parseInt(document.getElementById('resultsPerPage').value) - 20);
        }});
        
        document.getElementById('stepUp').addEventListener('click', () => {{
            setResultsPerPage(parseInt(document.getElementById('resultsPerPage').value) + 20);
        }});
        
        document.getElementById('resultsPerPage').addEventListener('change', function() {{
            setResultsPerPage(parseInt(this.value) || 20);
        }});
        
        document.getElementById('spoilerToggle').addEventListener('change', function() {{
            setSpoilerPrevention(this.checked);
        }});
        
        // Close config panel when clicking outside
        document.addEventListener('click', function(e) {{
            const configBar = document.querySelector('.config-bar');
            if (!configBar.contains(e.target)) {{
                document.getElementById('configPanel').classList.remove('show');
                document.getElementById('configToggle').classList.remove('active');
            }}
        }});
        
        function toggleConfig() {{
            const panel = document.getElementById('configPanel');
            const btn = document.getElementById('configToggle');
            panel.classList.toggle('show');
            btn.classList.toggle('active');
        }}
        
        init();
        
        // Show back link if toolkit index is accessible
        (function() {{
            const backLink = document.getElementById('back-to-toolkit');
            const hostname = window.location.hostname;
            const isSalvoHost = hostname.includes('salvo.host');
            const isGitHubPages = hostname.includes('github.io');
            const fromToolkit = new URLSearchParams(window.location.search).get('from') === 'toolkit';
            const hasIndexReferrer = document.referrer.includes('index.html') || 
                                     document.referrer.includes('tni-toolkit');
            const isHttp = window.location.protocol.startsWith('http');
            
            if (isSalvoHost || fromToolkit || hasIndexReferrer) {{
                backLink.classList.add('visible');
                backLink.href = '../index.html';
            }} else if (isGitHubPages) {{
                backLink.classList.add('visible');
                backLink.href = 'https://salvo-praxis.github.io/tni-toolkit/';
            }} else if (isHttp) {{
                fetch('../index.html', {{ method: 'HEAD' }})
                    .then(response => {{
                        if (response.ok) {{
                            backLink.classList.add('visible');
                            backLink.href = '../index.html';
                        }}
                    }})
                    .catch(() => {{}});
            }}
        }})();
    </script>
    
    <footer class="site-footer">
        <div class="footer-links">
            <a href="../index.html">TNI Toolkit</a>
            <span class="sep">|</span>
            <a href="https://github.com/salvo-praxis/tni-toolkit" target="_blank">GitHub</a>
            <span class="sep">|</span>
            <a href="../contributions.html">Contributions Log</a>
            <span class="sep">|</span>
            <a href="https://store.steampowered.com/app/2939600/Tower_Networking_Inc/" target="_blank">TNI on Steam</a>
        </div>
        <p class="footer-note">Made with ❤️ for the TNI community</p>
        <div class="footer-badges">
            <span class="version-badge">v1.3.0</span>
            <a href="https://github.com/salvo-praxis/tni-toolkit/blob/main/LICENSE" target="_blank" class="license-badge">MIT License — Free to use, modify, and share</a>
        </div>
    </footer>
</body>
</html>
'''


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_timestamp():
    """
    Generate a timestamp string for file naming.
    
    Uses 24-hour format for unambiguous sorting and clarity.
    Format: MM-DD-YY-HH-MM-SS (e.g., 12-01-25-14-30-45)
    
    Returns:
        str: Formatted timestamp string
    """
    return datetime.now().strftime("%m-%d-%y-%H-%M-%S")


def read_csv(filepath):
    """
    Read seed data from a CSV file.
    
    Expected CSV format:
        seed,proposal1,proposal2,proposal3
        ABC12,Remote Backups,PADU,Lean Administration
        ...
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        list: List of dicts with 'seed' and 'proposals' keys
    """
    seeds = []
    
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # Skip header row
        
        for row in reader:
            if len(row) >= 4:
                seeds.append({
                    'seed': row[0].strip(),
                    'proposals': [row[1].strip(), row[2].strip(), row[3].strip()]
                })
    
    return seeds


def clean_seeds(raw_seeds):
    """
    Clean and validate seed data.
    
    Removes:
        - Entries with "UNKNOWN" proposals (OCR failures)
        - Entries with invalid seed codes (wrong length/format)
        - Duplicate entries (same seed code)
    
    Args:
        raw_seeds: List of raw seed entries from CSV
        
    Returns:
        tuple: (clean_seeds list, removal_stats dict)
    """
    clean = []
    seen_seeds = set()
    
    removed = {
        'unknown': 0,
        'invalid': 0,
        'duplicates': 0
    }
    
    for entry in raw_seeds:
        seed = entry['seed']
        proposals = entry['proposals']
        
        # Check for UNKNOWN proposals (OCR failures)
        if 'UNKNOWN' in proposals:
            removed['unknown'] += 1
            continue
        
        # Validate seed format (should be 5 alphanumeric characters)
        if len(seed) != 5 or not seed.isalnum():
            removed['invalid'] += 1
            continue
        
        # Check for duplicates
        if seed in seen_seeds:
            removed['duplicates'] += 1
            continue
        
        seen_seeds.add(seed)
        clean.append(entry)
    
    return clean, removed


def load_merged_database():
    """
    Load the existing merged seed database.
    
    Creates a new empty database structure if the file doesn't exist.
    
    Returns:
        dict: Database with 'meta', 'proposals', and 'seeds' keys
    """
    if not MERGED_JSON.exists():
        return {
            'meta': {
                'created': datetime.now().isoformat(),
                'updated': datetime.now().isoformat(),
                'total_seeds': 0,
                'combinations_found': 0,
                'coverage_percent': 0.0
            },
            'proposals': PROPOSAL_DEFINITIONS,
            'seeds': []
        }
    
    with open(MERGED_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_seeds(existing_data, new_seeds):
    """
    Merge new seeds into the existing database.
    
    Avoids duplicates by checking seed codes. Returns a seed_map
    for convenient coverage calculation.
    
    Args:
        existing_data: Current database dict
        new_seeds: List of new seed entries to merge
        
    Returns:
        tuple: (seed_map dict, new_count int, duplicate_count int)
    """
    # Build map from existing data
    seed_map = {e['seed']: e['proposals'] for e in existing_data.get('seeds', [])}
    
    new_count = 0
    duplicate_count = 0
    
    for entry in new_seeds:
        seed = entry['seed']
        if seed not in seed_map:
            seed_map[seed] = entry['proposals']
            new_count += 1
        else:
            duplicate_count += 1
    
    return seed_map, new_count, duplicate_count


def calculate_combinations(seed_map):
    """
    Calculate the unique 3-proposal combinations found in the database.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        set: Set of frozen sets, each representing a unique combination
    """
    found_combos = set()
    
    for proposals in seed_map.values():
        # Sort to ensure consistent ordering, then freeze
        combo = frozenset(proposals)
        found_combos.add(combo)
    
    return found_combos


def get_missing_combinations(found_combos):
    """
    Identify which 3-proposal combinations are still missing.
    
    Args:
        found_combos: Set of found combinations (as frozen sets)
        
    Returns:
        list: List of missing combinations as sorted tuples
    """
    # Generate all possible 3-combinations
    all_possible = set(frozenset(c) for c in combinations(ALL_PROPOSALS, 3))
    
    # Find missing ones
    missing = all_possible - found_combos
    
    # Convert to sorted tuples for display
    return sorted([tuple(sorted(m)) for m in missing])


def save_clean_json(clean_seeds, timestamp):
    """
    Save cleaned seed data to a timestamped JSON file.
    
    This preserves each harvest run for potential analysis or recovery.
    
    Args:
        clean_seeds: List of cleaned seed entries
        timestamp: Timestamp string for filename
        
    Returns:
        Path: Path to the saved file
    """
    filename = f"clean-seeds-{timestamp}.json"
    filepath = CLEAN_JSON_DIR / filename
    
    data = {
        'harvested': timestamp,
        'count': len(clean_seeds),
        'seeds': clean_seeds
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def save_merged_database(seed_map):
    """
    Save the updated merged database.
    
    Includes metadata about coverage and combination statistics.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
    """
    # Calculate statistics
    found_combos = calculate_combinations(seed_map)
    coverage = 100 * len(found_combos) / TOTAL_COMBINATIONS
    
    # Build structured data
    seeds_list = [{'seed': s, 'proposals': p} for s, p in sorted(seed_map.items())]
    
    data = {
        'meta': {
            'updated': datetime.now().isoformat(),
            'total_seeds': len(seeds_list),
            'combinations_found': len(found_combos),
            'total_combinations': TOTAL_COMBINATIONS,
            'coverage_percent': round(coverage, 4)
        },
        'proposals': PROPOSAL_DEFINITIONS,
        'seeds': seeds_list
    }
    
    with open(MERGED_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def archive_csv(timestamp):
    """
    Archive the raw CSV to the dirty collection directory.
    
    Preserves raw data for potential reprocessing or analysis.
    
    Args:
        timestamp: Timestamp string for filename
        
    Returns:
        Path or None: Path to archived file, or None if no CSV existed
    """
    if not SEED_LOG_CSV.exists():
        return None
    
    filename = f"seed-log-{timestamp}.csv"
    dest = DIRTY_CSV_DIR / filename
    shutil.copy2(SEED_LOG_CSV, dest)  # copy2 preserves metadata
    
    return dest


def backup_merged_database(timestamp):
    """
    Create a backup of the merged database before modification.
    
    This provides a safety net in case something goes wrong during
    the merge or if data needs to be recovered.
    
    Args:
        timestamp: Timestamp string for filename
        
    Returns:
        Path or None: Path to backup file, or None if no database existed
    """
    if not MERGED_JSON.exists():
        return None
    
    filename = f"merged-seeds-backup-{timestamp}.json"
    dest = CLEAN_JSON_DIR / filename
    shutil.copy2(MERGED_JSON, dest)
    
    return dest


def update_frontend(seed_map):
    """
    Update the frontend HTML with current seed data.
    
    If the frontend file doesn't exist, it will be generated from the template.
    If it exists, the data section will be updated in place.
    
    The compact format uses 's' for seed and 'p' for proposals to minimize
    file size since the data is embedded in HTML.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        bool: True if update succeeded, False otherwise
    """
    # Build compact SEED_DB for minimal file size
    compact_seeds = [{'s': s, 'p': p} for s, p in sorted(seed_map.items())]
    seed_db = {
        'version': datetime.now().strftime("%Y%m%d"),
        'count': len(compact_seeds),
        'seeds': compact_seeds
    }
    seed_db_json = json.dumps(seed_db, separators=(',', ':'))  # Compact JSON
    seed_db_line = f"        const SEED_DB = {seed_db_json};\n"
    
    # If frontend doesn't exist, generate from template
    if not FRONTEND_HTML.exists():
        print(f"  Generating new frontend from template...")
        html = FRONTEND_HTML_TEMPLATE.format(
            proposals_js=FRONTEND_PROPOSALS_JS,
            seed_db_js=seed_db_line,
            generation_date=datetime.now().strftime("%Y-%m-%d")
        )
        with open(FRONTEND_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    
    # Read existing frontend HTML
    with open(FRONTEND_HTML, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Find the data section markers in the HTML
    # Structure: ... const PROPOSALS = {...}; const SEED_DB = {...}; let selectedProposals ...
    lines = html.split('\n')
    proposals_start = None
    seed_db_start = None
    seed_db_end = None
    
    for i, line in enumerate(lines):
        if 'const PROPOSALS = {' in line:
            proposals_start = i
        elif 'const SEED_DB = ' in line:
            seed_db_start = i
        elif seed_db_start is not None and line.strip().startswith('let selectedProposals'):
            seed_db_end = i
            break
    
    if proposals_start is None or seed_db_start is None:
        print("  Warning: Could not find data markers in frontend HTML")
        print("  Regenerating frontend from template...")
        html = FRONTEND_HTML_TEMPLATE.format(
            proposals_js=FRONTEND_PROPOSALS_JS,
            seed_db_js=seed_db_line,
            generation_date=datetime.now().strftime("%Y-%m-%d")
        )
        with open(FRONTEND_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    
    # Build the data section line (no trailing newline - joining adds it)
    seed_db_line_no_newline = f"        const SEED_DB = {seed_db_json};"
    
    # Rebuild HTML with new data
    new_lines = (
        lines[:proposals_start] +
        [FRONTEND_PROPOSALS_JS + seed_db_line_no_newline] +
        lines[seed_db_end:]
    )
    
    new_html = '\n'.join(new_lines)
    
    with open(FRONTEND_HTML, 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    return True


def regenerate_frontend(seed_map):
    """
    Force regenerate the frontend HTML from template.
    
    This replaces the entire frontend file with a fresh copy from the template,
    useful when the styling has been updated.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        bool: True if regeneration succeeded
    """
    # Build compact SEED_DB for minimal file size
    compact_seeds = [{'s': s, 'p': p} for s, p in sorted(seed_map.items())]
    seed_db = {
        'version': datetime.now().strftime("%Y%m%d"),
        'count': len(compact_seeds),
        'seeds': compact_seeds
    }
    seed_db_json = json.dumps(seed_db, separators=(',', ':'))
    seed_db_line = f"        const SEED_DB = {seed_db_json};\n"
    
    html = FRONTEND_HTML_TEMPLATE.format(
        proposals_js=FRONTEND_PROPOSALS_JS,
        seed_db_js=seed_db_line,
        generation_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    with open(FRONTEND_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return True


def clear_output_directory():
    """
    Clear the output directory for the next harvesting run.
    
    Removes all files from the output directory. The AHK harvester
    will create new files on the next run.
    """
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.iterdir():
            if file.is_file():
                file.unlink()


# =============================================================================
# STATISTICS DISPLAY
# =============================================================================

def show_stats():
    """
    Display current database statistics.
    
    Shows total seeds, combination coverage, and lists any missing combinations.
    Useful for tracking progress toward 100% coverage.
    """
    print("\n" + "=" * 60)
    print("TNI SEED HARVESTER - DATABASE STATISTICS")
    print("=" * 60)
    
    # Load current database
    data = load_merged_database()
    seed_map = {e['seed']: e['proposals'] for e in data.get('seeds', [])}
    
    # Calculate coverage
    found_combos = calculate_combinations(seed_map)
    missing = get_missing_combinations(found_combos)
    coverage = 100 * len(found_combos) / TOTAL_COMBINATIONS
    
    # Display stats
    print(f"\nTotal seeds:        {len(seed_map):,}")
    print(f"Combinations found: {len(found_combos)} / {TOTAL_COMBINATIONS}")
    print(f"Coverage:           {coverage:.4f}%")
    print(f"Missing:            {len(missing)}")
    
    # Show missing combinations if any remain
    if missing:
        print(f"\nMissing combinations:")
        for combo in missing:
            print(f"  - {combo[0]}, {combo[1]}, {combo[2]}")
    else:
        print(f"\n*** 100% COVERAGE ACHIEVED! All combinations found! ***")
    
    print()


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_pipeline(dry_run=False):
    """
    Execute the complete data processing pipeline.
    
    Steps:
        1. Check for new harvest data
        2. Clean and validate the data
        3. Load existing database
        4. Merge new data (with duplicate detection)
        5. Save clean JSON for this run
        6. Backup existing merged database
        7. Save updated merged database
        8. Update frontend
        9. Archive raw CSV and clear output directory
    
    Args:
        dry_run: If True, show what would happen without modifying files
    """
    print("\n" + "=" * 60)
    print("TNI SEED HARVESTER - DATA PROCESSING PIPELINE")
    print("=" * 60)
    
    timestamp = get_timestamp()
    print(f"\nTimestamp: {timestamp}")
    print(f"Dry run:   {dry_run}")
    
    # -------------------------------------------------------------------------
    # Step 1: Check for new data
    # -------------------------------------------------------------------------
    print(f"\n[1/8] Checking for new data...")
    
    if not SEED_LOG_CSV.exists():
        print(f"  No seed-log.csv found in {OUTPUT_DIR}")
        print("  Nothing to process. Run the harvester first!")
        return
    
    raw_seeds = read_csv(SEED_LOG_CSV)
    print(f"  Found {len(raw_seeds)} entries in seed-log.csv")
    
    if len(raw_seeds) == 0:
        print("  CSV is empty. Nothing to process.")
        return
    
    # -------------------------------------------------------------------------
    # Step 2: Clean the data
    # -------------------------------------------------------------------------
    print(f"\n[2/8] Cleaning data...")
    
    clean, removed = clean_seeds(raw_seeds)
    print(f"  Clean seeds:     {len(clean)}")
    print(f"  Removed UNKNOWN: {removed['unknown']}")
    print(f"  Removed invalid: {removed['invalid']}")
    print(f"  Removed dupes:   {removed['duplicates']}")
    
    if len(clean) == 0:
        print("  No valid seeds after cleaning. Aborting.")
        return
    
    # -------------------------------------------------------------------------
    # Step 3: Load existing database
    # -------------------------------------------------------------------------
    print(f"\n[3/8] Loading existing database...")
    
    existing = load_merged_database()
    print(f"  Existing seeds: {existing['meta']['total_seeds']}")
    
    # -------------------------------------------------------------------------
    # Step 4: Merge data
    # -------------------------------------------------------------------------
    print(f"\n[4/8] Merging data...")
    
    seed_map, new_count, merge_dupes = merge_seeds(existing, clean)
    print(f"  New unique seeds:    {new_count}")
    print(f"  Already in database: {merge_dupes}")
    print(f"  Total after merge:   {len(seed_map)}")
    
    # Calculate and display coverage statistics
    found_combos = calculate_combinations(seed_map)
    coverage = 100 * len(found_combos) / TOTAL_COMBINATIONS
    missing = get_missing_combinations(found_combos)
    
    print(f"\n  Combinations: {len(found_combos)} / {TOTAL_COMBINATIONS} ({coverage:.4f}%)")
    
    if missing:
        print(f"  Still missing {len(missing)} combinations:")
        for combo in missing[:5]:
            print(f"    - {combo[0]}, {combo[1]}, {combo[2]}")
        if len(missing) > 5:
            print(f"    ... and {len(missing) - 5} more")
    else:
        print(f"  *** 100% COVERAGE ACHIEVED! ***")
    
    # -------------------------------------------------------------------------
    # Dry run stops here
    # -------------------------------------------------------------------------
    if dry_run:
        print("\n[DRY RUN] No files will be modified.")
        return
    
    # -------------------------------------------------------------------------
    # Step 5: Save clean JSON for this run
    # -------------------------------------------------------------------------
    print(f"\n[5/8] Saving clean JSON...")
    
    clean_path = save_clean_json(clean, timestamp)
    print(f"  Saved: {clean_path.name}")
    
    # -------------------------------------------------------------------------
    # Step 6: Backup existing merged database
    # -------------------------------------------------------------------------
    print(f"\n[6/8] Backing up merged database...")
    
    backup_path = backup_merged_database(timestamp)
    if backup_path:
        print(f"  Backup: {backup_path.name}")
    else:
        print(f"  No existing database to backup (first run)")
    
    # -------------------------------------------------------------------------
    # Step 7: Save updated merged database
    # -------------------------------------------------------------------------
    print(f"\n[7/8] Saving merged database...")
    
    save_merged_database(seed_map)
    print(f"  Updated: {MERGED_JSON.name}")
    
    # -------------------------------------------------------------------------
    # Step 8: Update frontend
    # -------------------------------------------------------------------------
    print(f"\n[8/8] Updating frontend...")
    
    if update_frontend(seed_map):
        print(f"  Updated: {FRONTEND_HTML.name}")
    
    # -------------------------------------------------------------------------
    # Cleanup: Archive and clear
    # -------------------------------------------------------------------------
    print(f"\n[CLEANUP] Archiving and cleaning...")
    
    archived = archive_csv(timestamp)
    if archived:
        print(f"  Archived CSV: {archived.name}")
    
    clear_output_directory()
    print(f"  Cleared output directory")
    
    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  New seeds added:   {new_count}")
    print(f"  Total seeds:       {len(seed_map)}")
    print(f"  Coverage:          {coverage:.4f}%")
    print(f"  Missing combos:    {len(missing)}")
    print()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Ensure all required directories exist
    CLEAN_JSON_DIR.mkdir(parents=True, exist_ok=True)
    DIRTY_CSV_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Parse command-line arguments
    if '--stats' in sys.argv:
        show_stats()
    elif '--dry-run' in sys.argv:
        run_pipeline(dry_run=True)
    elif '--regenerate-frontend' in sys.argv:
        # Force regenerate frontend from template with current database
        print("\n" + "=" * 60)
        print("REGENERATING FRONTEND FROM TEMPLATE")
        print("=" * 60)
        data = load_merged_database()
        seed_map = {e['seed']: e['proposals'] for e in data.get('seeds', [])}
        if regenerate_frontend(seed_map):
            print(f"  Regenerated: {FRONTEND_HTML.name}")
            print(f"  Seeds embedded: {len(seed_map)}")
        print()
    elif '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
    else:
        run_pipeline(dry_run=False)
