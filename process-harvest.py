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
FRONTEND_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TNI Seed Finder</title> 
    <style>
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace;
            background: linear-gradient(135deg, #0a0e14 0%, #1a1f2e 50%, #0d1117 100%);
            color: #c9d1d9;
            margin: 0;
            padding: 24px;
            min-height: 100vh;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        .header {{
            border-bottom: 1px solid #30363d;
            padding-bottom: 16px;
            margin-bottom: 24px;
            text-align: center;
        }}
        
        h1 {{
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
            margin: 0 0 8px 0;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        
        h1 span {{ color: #58a6ff; }}
        
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
        
        .site-footer a:hover {{ color: #58a6ff; }}
        
        .site-footer .sep {{
            margin: 0 8px;
            color: #30363d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TNI <span>SEED FINDER</span></h1>
            <p class="subtitle">Find seeds by selecting desired proposals</p>
            <p class="stats">Database: <span id="seedCount">0</span> verified seeds</p>
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
        </div>
    </div>
    
    <div class="tooltip" id="tooltip">Copied!</div>

    <script>
{proposals_js}{seed_db_js}
        let selectedProposals = [];

        function init() {{
            document.getElementById('seedCount').textContent = SEED_DB.seeds.length;
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
            renderProposals();
            renderSelectionSummary();
            updateResults();
        }}

        function updateResults() {{
            const resultsDiv = document.getElementById('seedResults');
            const countDiv = document.getElementById('resultsCount');
            
            if (selectedProposals.length === 0) {{
                resultsDiv.innerHTML = '<div class="no-results">👆 Click on proposals above to find matching seeds</div>';
                countDiv.textContent = 'Select proposals above to find seeds';
                return;
            }}
            
            const matches = SEED_DB.seeds.filter(entry => 
                selectedProposals.every(p => entry.p.includes(p))
            );
            
            if (matches.length === 0) {{
                resultsDiv.innerHTML = `<div class="no-results">😔 No seeds found with all selected proposals<br><small>Try selecting fewer proposals or different combinations</small></div>`;
                countDiv.textContent = '0 seeds found';
                return;
            }}
            
            countDiv.textContent = `${{matches.length}} seed${{matches.length > 1 ? 's' : ''}} found`;
            
            resultsDiv.innerHTML = matches.slice(0, 50).map(entry => {{
                return `
                    <div class="seed-card">
                        <div class="seed-code" onclick="copySeed('${{entry.s}}', this)" title="Click to copy">${{entry.s}}</div>
                        <div class="seed-proposals">
                            ${{entry.p.map(p => {{
                                const info = PROPOSALS[p];
                                const isMatched = selectedProposals.includes(p);
                                return `<div class="seed-proposal ${{isMatched ? 'matched' : ''}}">
                                    <div class="seed-proposal-name">${{p}}</div>
                                    <div class="seed-proposal-effect">${{info ? info.effect : 'Unknown'}}</div>
                                </div>`;
                            }}).join('')}}
                        </div>
                    </div>
                `;
            }}).join('') + (matches.length > 50 ? `<div class="no-results">...and ${{matches.length - 50}} more</div>` : '');
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

        document.getElementById('proposalSearch').addEventListener('input', renderProposals);
        init();
    </script>
    
    <div class="site-footer">
        <a href="https://github.com/salvo-praxis/tni-toolkit" target="_blank">TNI Toolkit</a>
        <span class="sep">|</span>
        <a href="https://store.steampowered.com/app/2939600/Tower_Networking_Inc/" target="_blank">Tower Networking Inc. on Steam</a>
    </div>
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


def calculate_combinations(seed_map):
    """
    Calculate unique proposal combinations from a seed map.
    
    Each seed has 3 proposals. This function finds all unique combinations
    regardless of order (sorted for consistency).
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        set: Set of tuples, each containing 3 sorted proposal names
    """
    found = set()
    for props in seed_map.values():
        # Sort to normalize order - (A,B,C) == (C,B,A)
        combo = tuple(sorted(props))
        found.add(combo)
    return found


def get_missing_combinations(found_combinations):
    """
    Determine which proposal combinations haven't been found yet.
    
    Compares found combinations against all possible 3-proposal combinations
    from the 15 known proposals.
    
    Args:
        found_combinations: Set of found combination tuples
        
    Returns:
        list: Sorted list of missing combination tuples
    """
    all_combos = set(tuple(sorted(c)) for c in combinations(ALL_PROPOSALS, 3))
    return sorted(all_combos - found_combinations)


# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================

def read_csv(csv_path):
    """
    Read and parse the raw seed-log.csv file from the AHK harvester.
    
    Expected CSV format:
        seed,proposal1,proposal2,proposal3,raw_ocr,timestamp
        
    Args:
        csv_path: Path object pointing to the CSV file
        
    Returns:
        list: List of dicts with seed data (seed, proposals, raw_ocr, timestamp)
    """
    seeds = []
    
    if not csv_path.exists():
        return seeds
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract and clean fields
            seed = row.get('seed', '').strip()
            p1 = row.get('proposal1', '').strip()
            p2 = row.get('proposal2', '').strip()
            p3 = row.get('proposal3', '').strip()
            
            seeds.append({
                'seed': seed,
                'proposals': [p1, p2, p3],
                'raw_ocr': row.get('raw_ocr', ''),
                'timestamp': row.get('timestamp', '')
            })
    
    return seeds


def clean_seeds(seeds):
    """
    Clean and validate seed data from the harvester.
    
    Cleaning steps:
        1. Remove entries with invalid seed codes (must be exactly 5 characters)
        2. Remove entries containing UNKNOWN proposals (OCR failures)
        3. Remove duplicate seed codes within the same harvest batch
    
    Note: Duplicate seed CODES are removed, but different seeds with the same
    PROPOSAL combination are kept (different seeds can have same proposals).
    
    Args:
        seeds: List of raw seed dicts from read_csv()
        
    Returns:
        tuple: (clean_seeds_list, removal_stats_dict)
    """
    clean = []
    seen_seeds = set()  # Track seed codes to detect within-batch duplicates
    
    # Removal counters
    unknown_count = 0
    invalid_count = 0
    dupe_count = 0
    
    for entry in seeds:
        seed = entry['seed']
        props = entry['proposals']
        
        # Validation: Seed codes must be exactly 5 characters
        if not seed or len(seed) != 5:
            invalid_count += 1
            continue
        
        # Validation: Skip entries where OCR failed (contains UNKNOWN)
        if 'UNKNOWN' in props:
            unknown_count += 1
            continue
        
        # Deduplication: Skip if we've already seen this seed code in this batch
        if seed in seen_seeds:
            dupe_count += 1
            continue
        
        # Valid entry - add to clean list
        seen_seeds.add(seed)
        clean.append({
            'seed': seed,
            'proposals': props
        })
    
    return clean, {
        'unknown': unknown_count,
        'invalid': invalid_count,
        'duplicates': dupe_count
    }


def load_merged_database():
    """
    Load the existing merged seed database.
    
    If no database exists yet, returns an empty structure ready for population.
    
    Returns:
        dict: Database structure with meta, proposals, and seeds
    """
    if MERGED_JSON.exists():
        with open(MERGED_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Return empty structure for first run
    return {
        'meta': {
            'total_seeds': 0,
            'unique_proposals': 15,
            'unique_combinations': 0,
            'coverage_percent': 0.0,
            'version': '1.0'
        },
        'proposals': PROPOSAL_DEFINITIONS,
        'seeds': []
    }


def merge_seeds(existing_data, new_seeds):
    """
    Merge new seeds into the existing database.
    
    Merging is done by seed code (the unique key). If a seed code already
    exists in the database, it is NOT overwritten - we keep the original.
    
    Different seeds can have the same proposal combinations - this is expected
    and valuable data since seeds control more than just starting proposals.
    
    Args:
        existing_data: Dict from load_merged_database()
        new_seeds: List of clean seed dicts to merge
        
    Returns:
        tuple: (merged_seed_map, new_count, duplicate_count)
            - merged_seed_map: Dict mapping all seed codes to proposals
            - new_count: Number of genuinely new seeds added
            - duplicate_count: Number of seeds already in database (skipped)
    """
    # Build map from existing database
    seed_map = {}
    for entry in existing_data.get('seeds', []):
        # Handle both full format (seed) and compact format (s)
        seed = entry.get('seed', entry.get('s'))
        props = entry.get('proposals', entry.get('p'))
        seed_map[seed] = props
    
    before_count = len(seed_map)
    dupes_skipped = 0
    
    # Attempt to add new seeds
    for entry in new_seeds:
        seed = entry['seed']
        props = entry['proposals']
        
        if seed in seed_map:
            # Seed already exists in database - skip it
            dupes_skipped += 1
        else:
            # New seed - add to database
            seed_map[seed] = props
    
    after_count = len(seed_map)
    new_additions = after_count - before_count
    
    return seed_map, new_additions, dupes_skipped


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def save_clean_json(seeds, timestamp):
    """
    Save cleaned seeds to a timestamped JSON file.
    
    This creates an individual harvest record that can be used for tracking
    or re-processing if needed.
    
    Args:
        seeds: List of clean seed dicts
        timestamp: Timestamp string for filename
        
    Returns:
        Path: Path to the saved file
    """
    filename = f"clean-seeds-{timestamp}.json"
    filepath = CLEAN_JSON_DIR / filename
    
    output = {
        'meta': {
            'total_seeds': len(seeds),
            'unique_proposals': 15,
            'version': '1.0',
            'created': datetime.now().isoformat()
        },
        'proposals': PROPOSAL_DEFINITIONS,
        'seeds': seeds
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return filepath


def save_merged_database(seed_map):
    """
    Save the complete merged seed database.
    
    This is the master database containing all collected seeds.
    Also calculates and stores combination coverage statistics.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        set: Set of found combinations (for reporting)
    """
    # Calculate coverage statistics
    found_combos = calculate_combinations(seed_map)
    coverage = 100 * len(found_combos) / TOTAL_COMBINATIONS
    
    output = {
        'meta': {
            'total_seeds': len(seed_map),
            'unique_proposals': 15,
            'unique_combinations': len(found_combos),
            'coverage_percent': round(coverage, 4),
            'version': datetime.now().strftime("%Y%m%d"),  # Version by date
            'updated': datetime.now().isoformat()
        },
        'proposals': PROPOSAL_DEFINITIONS,
        'seeds': [{'seed': s, 'proposals': p} for s, p in sorted(seed_map.items())]
    }
    
    with open(MERGED_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return found_combos


def archive_csv(timestamp):
    """
    Archive the raw CSV to the dirty collection folder.
    
    Preserves the original harvester output with a timestamp for reference.
    
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
            seed_db_js=seed_db_line
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
            seed_db_js=seed_db_line
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
        seed_db_js=seed_db_line
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
