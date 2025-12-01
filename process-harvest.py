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
    python process-harvest.py           # Process new harvest and update everything
    python process-harvest.py --dry-run # Preview changes without modifying files
    python process-harvest.py --stats   # Display current database statistics

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
# This allows the script to work regardless of where it's run from
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
    
    The frontend is a standalone HTML file with embedded JavaScript data.
    This function locates the data section and replaces it with current data.
    
    The compact format uses 's' for seed and 'p' for proposals to minimize
    file size since the data is embedded in HTML.
    
    Args:
        seed_map: Dict mapping seed codes to proposal lists
        
    Returns:
        bool: True if update succeeded, False otherwise
    """
    if not FRONTEND_HTML.exists():
        print(f"  Warning: Frontend not found at {FRONTEND_HTML}")
        return False
    
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
        return False
    
    # Build compact SEED_DB for minimal file size
    compact_seeds = [{'s': s, 'p': p} for s, p in sorted(seed_map.items())]
    seed_db = {
        'version': datetime.now().strftime("%Y%m%d"),
        'count': len(compact_seeds),
        'seeds': compact_seeds
    }
    seed_db_json = json.dumps(seed_db, separators=(',', ':'))  # Compact JSON
    seed_db_line = f"        const SEED_DB = {seed_db_json};"
    
    # Rebuild HTML with new data
    new_lines = (
        lines[:proposals_start] +
        [FRONTEND_PROPOSALS_JS + seed_db_line] +
        lines[seed_db_end:]
    )
    
    new_html = '\n'.join(new_lines)
    
    with open(FRONTEND_HTML, 'w', encoding='utf-8') as f:
        f.write(new_html)
    
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
    elif '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
    else:
        run_pipeline(dry_run=False)
