; =============================================================================
; TNI Seed Harvester v3.0 (1080p)
; =============================================================================
; Automates seed collection and proposal OCR for Tower Networking Inc
; 
; GitHub: https://github.com/salvo-praxis/tni-seed-harvester
; Game:   Tower Networking Inc by Pocosia Studios
;
; RESOLUTION: 1920x1080 (fullscreen)
;   - Coordinates scaled from 1440p version (×0.75)
;   - For 1440p, use tni-harvester-1440p-v3.ahk instead
;   - For other resolutions, update the coords section below
;   - Use F12 to find correct coordinates for your setup
;
; FEATURES:
;   - Automated seed harvesting with OCR extraction
;   - Crash detection and auto-recovery
;   - Automatic game restart on failure
;   - First-run setup (Tutorials -> Scenarios tab click)
;   - Systematic seed mode (00000, 00001, ...) or random
;   - Configurable timing for different systems
;
; REQUIREMENTS:
;   - AutoHotkey v2.0+
;   - Tesseract OCR installed and in PATH
;   - Tower Networking Inc (Steam)
;   - Python 3.10+ (for data processing)
;
; SETUP:
;   1. Update workDir below to match your installation path
;   2. Update gameExePath if your Steam library is elsewhere
;   3. Run game in fullscreen at 1920x1080
;   4. Use F12 to verify/update coordinates if needed
;
; HOTKEYS:
;   F9  = Start harvesting loop
;   F10 = Stop harvesting loop  
;   F11 = Single capture (for testing)
;   F12 = Coordinate helper (shows mouse position)
;
; AFTER HARVESTING:
;   Run process-harvest.bat (or: python process-harvest.py)
;   to clean, merge, and update the frontend.
; =============================================================================

#Requires AutoHotkey v2.0
#SingleInstance Force

; =============================================================================
; CONFIGURATION
; =============================================================================
; Update these paths to match your setup!

global CONFIG := {
    ; --------------------------------------------------------------------------
    ; PATHS - UPDATE THESE FOR YOUR SYSTEM
    ; --------------------------------------------------------------------------
    
    ; Working directory - where the harvester saves output files
    ; This should point to the 'output' folder in your tni-seed-harvester directory
    workDir: "C:\tni-seed-harvester\output",
    
    ; Game executable path - update if your Steam library is elsewhere
    gameExePath: "C:\Program Files (x86)\Steam\steamapps\common\Tower Networking Inc\Tower Networking Inc.exe",
    gameWindowTitle: "Tower Networking Inc",
    
    ; DEBUG MODE - set to true to save screenshots with unique names for troubleshooting
    debugMode: false,
    
    ; SYSTEMATIC MODE - set to true to iterate seeds sequentially instead of random
    ; When false: uses game's random seed generation
    ; When true: types seeds systematically (00000, 00001, 00002, ...)
    systematicMode: false,
    
    ; Starting seed for systematic mode (base-36 string, 5 chars)
    ; Set this to resume from where you left off
    systematicStartSeed: "00000",
    
    ; Output files
    seedLog: "seed-log.csv",
    unknownLog: "unknown-proposals.csv",
    rawOcrLog: "raw-ocr-debug.log",
    crashLog: "crash-recovery.log",
    progressFile: "harvest-progress.txt",  ; Stores last seed for resume
    
    ; Timing (milliseconds) - CONSERVATIVE to prevent crashes (update: tuned for speed)
    clickDelay: 450,           ; Was 500 - slightly more buffer
    shortDelay: 200,           ; Was 250
    gameLoadDelayFirst: 27000, ; First load after crash recovery (cold cache) - 27 sec
    gameLoadDelay: 13000,      ; Subsequent loads (warm cache) - 13 sec
    tabletOpenDelay: 600,      ; Was 1200
    appSwitchDelay: 400,       ; Was 1000
    scrollDelay: 200,          ; Was 800
    menuExitDelay: 600,        ; Was 4200
    loopDelay: 1500,           ; Was 2200
    secretariatWait: 400,      ; Was 900
    
    ; Crash recovery timing
    gameStartupDelay: 8500,    ; Wait for game exe to reach main menu (9 sec)
    processCheckDelay: 300,    ; Delay between process checks
    maxRecoveryAttempts: 3,    ; Max consecutive recovery attempts before stopping
    
    ; Screen coordinates for 1920x1080 fullscreen
    ; Scaled from 1440p (×0.75) - verify with F12 if clicks seem off
    coords: {
        ; Main menu - "Start a new game" button center
        startNewGame: { x: 776, y: 308 },
        
        ; New game setup screen - TABS
        scenariosTab: { x: 298, y: 339 },     ; Scenarios tab - click to switch from Tutorials
        
        ; New game setup screen - after clicking Scenarios
        seedField: { x: 464, y: 588 },        ; World seed text field center
        playSolo: { x: 245, y: 813 },         ; Play Solo button center
        
        ; In-game tablet
        secretariatIcon: { x: 374, y: 575 },  ; The Secretariat app icon
        proposalsTab: { x: 205, y: 124 },     ; Proposals tab in Secretariat
        
        ; Escape menu
        quitToMainMenu: { x: 289, y: 486 },   ; "Quit to main menu" button
        
        ; Scroll - click bottom of scrollbar to scroll down
        scrollbarBottom: { x: 490, y: 890 }
    },
    
    ; OCR capture regions (scaled for 1080p)
    captureRegions: {
        full: { x1: 38, y1: 173, x2: 484, y2: 900 },
        top: { x1: 38, y1: 173, x2: 484, y2: 536 },
        bottom: { x1: 38, y1: 375, x2: 484, y2: 900 }
    },
    
    ; Tesseract settings
    ; If Tesseract isn't in PATH, set the full path here:
    ; tesseractExe: "C:\Program Files\Tesseract-OCR\tesseract.exe",
    tesseractExe: "tesseract",  ; Uses PATH by default
    tesseract: {
        dpi: 150,
        lang: "eng",
        psm: 6
    }
}

; Global state variables
global isRunning := false
global currentSeed := ""
global iterationCount := 0
global recoveryAttempts := 0
global needsFirstRunSetup := false
global systematicSeedIndex := 0
global isFirstLoadAfterRecovery := false  ; Track if next load needs longer delay

; ============================================================================
; HELPER FUNCTIONS
; ============================================================================

ShowStatus(message) {
    ; Show tooltip at fixed position (top center of screen) to avoid interfering with OCR
    ; Position: x=960 (center of 1920), y=50 (near top)
    ToolTip(message, 960, 50)
}

; ===========================================
; KNOWN PROPOSALS - Comprehensive list
; ===========================================
global KNOWN_PROPOSALS := Map(
    ; TECH UNLOCKS
    "REMOTE BACKUPS", "Remote Backups",
    "REMOTE BACKUP", "Remote Backups",
    "SFTP", "Remote Backups",
    "3-2-1", "Remote Backups",
    "BACK IT UP", "Remote Backups",
    
    "NETOPS RESEARCH", "NetOps Research",
    "NETOPS", "NetOps Research",
    "NET OPS", "NetOps Research",
    "IMPROVISE, ADAPT", "NetOps Research",
    
    "SCANNING EXPLOIT", "Scanning Exploit",
    "SCANNING RESEARCH", "Scanning Exploit",
    "SCANS TOO SHALL PASS", "Scanning Exploit",
    
    "POWER MANAGEMENT RESEARCH", "Power Management Research",
    "POWER MANAGEMENT", "Power Management Research",
    "POWER RESEARCH", "Power Management Research",
    "POWER ROUTINES", "Power Management Research",
    "KEEP BILLS LOW", "Power Management Research",
    
    ; POWER POLICIES
    "OVERVOLTAGE DIRECTIVE", "Overvoltage Directive",
    "OVERVOLTAGE", "Overvoltage Directive",
    "POWER OVERWHELMING", "Overvoltage Directive",
    "-30% OUTAGE", "Overvoltage Directive",
    "+30% SURGE", "Overvoltage Directive",
    
    "UNDERVOLTAGE DIRECTIVE", "Undervoltage Directive",
    "UNDERVOLTAGE", "Undervoltage Directive",
    "BETTER DARK THAN MAGIC SMOKE", "Undervoltage Directive",
    "+30% OUTAGE", "Undervoltage Directive",
    "-30% SURGE", "Undervoltage Directive",
    
    ; ECONOMY
    "LEAN ADMINISTRATION", "Lean Administration",
    "LEAN ADMIN", "Lean Administration",
    "REDUCE BASE EXPENSES", "Lean Administration",
    "PAIN NOW FOR GAIN LATER", "Lean Administration",
    
    "REFURBHUT INVESTMENT", "Refurbhut Investment",
    "REFURBHUT", "Refurbhut Investment",
    "REFURB", "Refurbhut Investment",
    "AS LONG AS IT WORKS", "Refurbhut Investment",
    
    "LEGAL RETALIATION", "Legal Retaliation",
    "RETALIATION", "Legal Retaliation",
    "ANOTHER POWER OUTAGE", "Legal Retaliation",
    "SEE YOU IN COURT", "Legal Retaliation",
    "TENABOLT CORPORATION NOW PAYS 500", "Legal Retaliation",
    "PAYS 500 PER OUTAGE", "Legal Retaliation",
    "500 PER OUTAGE/SURGE", "Legal Retaliation",
    
    "LOBBY AGAINST TENABOLT", "Lobby against Tenabolt",
    "POWER TO THE PEOPLE", "Lobby against Tenabolt",
    "NO LONGER ISSUE FINES", "Lobby against Tenabolt",
    "NON DATA CENTER POWER USE", "Lobby against Tenabolt",
    "LOBBY FOR NEW LAW", "Lobby against Tenabolt",
    
    ; SOFTWARE / PROGRAMS
    "PADU DEVELOPMENT FUNDING", "PADU",
    "PADU DEVELOPMENT", "PADU",
    "PADU", "PADU",
    "EVERYONE'S FAVORITE DATABASE", "PADU",
    
    "POEMS DB", "Poems DB",
    "POEMS-DB", "Poems DB",
    "POEMS DATABASE", "Poems DB",
    "TEXT CHADS", "Poems DB",
    
    ; QUALITY OF LIFE
    "SECOND MONITOR", "Second Monitor",
    "SECOND SCREEN", "Second Monitor",
    "SCREEN TOO SMALL", "Second Monitor",
    
    ; FACTIONS - Cabler's Union (Base only - upgrades unlock later)
    "SUPPORT THE CABLER'S UNION", "Cabler's Union (Base)",
    "CABLER'S UNION", "Cabler's Union (Base)",
    "CABLERS UNION", "Cabler's Union (Base)",
    "R&D - REWIRE AND DISTRIBUTE", "Cabler's Union (Base)",
    "REWIRE AND DISTRIBUTE", "Cabler's Union (Base)",
    
    ; FACTIONS - Tenabolt
    "FUSION PLANT FUNDING", "Fusion Plant",
    "FUSION PLANT", "Fusion Plant",
    "LET'S MAKE A SUN", "Fusion Plant",
    "MAKE A SUN", "Fusion Plant",
    "SUPPORT TENABOLT", "Fusion Plant",
    "TENABOLT CORPORATION'S EFFORT", "Fusion Plant",
    "DATA CENTER POWER COST", "Fusion Plant"
)

; ============================================================================
; HOTKEYS
; ============================================================================

F9::StartLoop()
F10::StopLoop()
F11::TestCapture()
F12::ShowCoords()

; ============================================================================
; CRASH DETECTION & RECOVERY
; ============================================================================

IsGameRunning() {
    ; Check if game process is running (more reliable than window title)
    return IsGameProcessRunning()
}

IsGameProcessRunning() {
    ; Check if the process is running using WMI
    try {
        for proc in ComObjGet("winmgmts:").ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'Tower Networking Inc.exe'") {
            return true
        }
    }
    
    ; Fallback: try checking for window by exe
    if WinExist("ahk_exe Tower Networking Inc.exe") {
        return true
    }
    
    return false
}

KillGameProcess() {
    ; Force kill the game process if it's hanging
    try {
        Run('taskkill /F /IM "Tower Networking Inc.exe"',, "Hide")
        Sleep(1000)
    }
    LogCrash("Killed game process")
}

LaunchGame() {
    ; Launch the game executable directly (not via Steam)
    LogCrash("Launching game...")
    
    ; Get the directory from the exe path for working directory
    SplitPath(CONFIG.gameExePath,, &gameDir)
    
    try {
        Run(CONFIG.gameExePath, gameDir)  ; Run with working directory set
    } catch as err {
        LogCrash("Failed to launch game: " err.Message)
        return false
    }
    
    ; Wait for game to fully load
    ShowStatus("Waiting for game to start...")
    Sleep(CONFIG.gameStartupDelay)
    
    ; Verify game process is running (more reliable than window title)
    if !IsGameProcessRunning() {
        LogCrash("Game process not found after launch")
        return false
    }
    
    ; Give it a moment then try to activate window
    Sleep(2000)
    
    ; Try to activate by process class or partial title match
    try {
        WinActivate("ahk_exe Tower Networking Inc.exe")
    } catch {
        ; If that fails, just continue - process is running
        LogCrash("Could not activate window, but process is running")
    }
    
    Sleep(1000)
    
    LogCrash("Game launched successfully")
    return true
}

RecoverFromCrash() {
    global recoveryAttempts, needsFirstRunSetup, isRunning
    
    recoveryAttempts++
    LogCrash("=== CRASH RECOVERY ATTEMPT " recoveryAttempts " ===")
    
    if recoveryAttempts > CONFIG.maxRecoveryAttempts {
        LogCrash("Max recovery attempts exceeded. Stopping.")
        isRunning := false
        ShowStatus("Recovery failed after " CONFIG.maxRecoveryAttempts " attempts. Stopped.")
        Sleep(5000)
        ToolTip()
        return false
    }
    
    ; Kill any existing game process
    if IsGameProcessRunning() {
        KillGameProcess()
        Sleep(2000)
    }
    
    ; Launch fresh instance
    if !LaunchGame() {
        return false
    }
    
    ; Mark that we need first-run setup (Scenarios tab click)
    needsFirstRunSetup := true
    isFirstLoadAfterRecovery := true  ; First load after recovery needs longer delay
    
    LogCrash("Recovery successful, resuming harvest")
    return true
}

PerformFirstRunSetup() {
    global needsFirstRunSetup
    
    if !needsFirstRunSetup {
        return true
    }
    
    LogCrash("Performing first-run setup (clicking Scenarios tab)")
    ShowStatus("First-run setup: Clicking Scenarios tab...")
    
    CoordMode("Mouse", "Screen")
    
    ; Click "Start a new game" from main menu
    Click(CONFIG.coords.startNewGame.x, CONFIG.coords.startNewGame.y)
    Sleep(CONFIG.clickDelay)
    
    ; Click "Scenarios" tab (since Tutorials is selected by default)
    Click(CONFIG.coords.scenariosTab.x, CONFIG.coords.scenariosTab.y)
    Sleep(CONFIG.clickDelay)
    
    ; Now we're at the seed screen - click "Endless Babel" to make sure it's selected
    ; (It should be the first item, but click the list area to be safe)
    ; Actually, from the screenshot it seems to auto-select, so we can skip this
    
    needsFirstRunSetup := false
    ToolTip()
    
    return true
}

ValidateOcrResult(proposals) {
    ; Check if OCR result is valid (got 3 known proposals)
    if proposals.Length < 3 {
        return false
    }
    
    ; Check for UNKNOWN entries
    for p in proposals {
        if p = "UNKNOWN" {
            return false
        }
    }
    
    return true
}

LogCrash(message) {
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    FileAppend("[" timestamp "] " message "`n", CONFIG.workDir "\" CONFIG.crashLog)
}

; ============================================================================
; SYSTEMATIC SEED GENERATION
; ============================================================================

InitializeSystematicSeed() {
    global systematicSeedIndex
    
    ; Convert starting seed string to index
    systematicSeedIndex := SeedToIndex(CONFIG.systematicStartSeed)
    
    ; Try to load progress from file
    progressFile := CONFIG.workDir "\" CONFIG.progressFile
    if FileExist(progressFile) {
        try {
            lastSeed := Trim(FileRead(progressFile))
            if StrLen(lastSeed) = 5 {
                systematicSeedIndex := SeedToIndex(lastSeed) + 1
                LogCrash("Resuming from seed: " lastSeed " (index " systematicSeedIndex ")")
            }
        }
    }
}

SeedToIndex(seed) {
    ; Convert 5-char base-36 seed to integer index
    chars := "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    seed := StrUpper(seed)
    index := 0
    
    Loop 5 {
        char := SubStr(seed, A_Index, 1)
        pos := InStr(chars, char) - 1
        if pos < 0
            pos := 0
        index := index * 36 + pos
    }
    
    return index
}

IndexToSeed(index) {
    ; Convert integer index to 5-char base-36 seed
    chars := "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    seed := ""
    
    Loop 5 {
        seed := SubStr(chars, Mod(index, 36) + 1, 1) . seed
        index := index // 36
    }
    
    return seed
}

GetNextSystematicSeed() {
    global systematicSeedIndex
    
    seed := IndexToSeed(systematicSeedIndex)
    systematicSeedIndex++
    
    ; Save progress
    try {
        progressFile := CONFIG.workDir "\" CONFIG.progressFile
        if FileExist(progressFile)
            FileDelete(progressFile)
        FileAppend(seed, progressFile)
    }
    
    return seed
}

TypeSeed(seed) {
    ; Clear existing seed and type new one
    CoordMode("Mouse", "Screen")
    
    ; Click seed field
    Click(CONFIG.coords.seedField.x, CONFIG.coords.seedField.y)
    Sleep(CONFIG.shortDelay)
    
    ; Select all existing text
    Send("^a")
    Sleep(100)
    
    ; Type the new seed
    Send(seed)
    Sleep(CONFIG.shortDelay)
}

; ============================================================================
; MAIN LOOP
; ============================================================================

StartLoop() {
    global isRunning, iterationCount, recoveryAttempts, needsFirstRunSetup, isFirstLoadAfterRecovery
    
    if isRunning {
        ShowStatus("Already running!")
        Sleep(1000)
        ToolTip()
        return
    }
    
    isRunning := true
    iterationCount := 0
    recoveryAttempts := 0
    
    ; Ensure output directory exists
    if !DirExist(CONFIG.workDir) {
        DirCreate(CONFIG.workDir)
    }
    
    ; Initialize CSV if needed
    csvPath := CONFIG.workDir "\" CONFIG.seedLog
    if !FileExist(csvPath) {
        FileAppend("seed,proposal1,proposal2,proposal3,raw_ocr,timestamp`n", csvPath)
    }
    
    ; Initialize systematic seed if enabled
    if CONFIG.systematicMode {
        InitializeSystematicSeed()
        LogCrash("Systematic mode enabled, starting at index " systematicSeedIndex)
    }
    
    ; Check if game is already running
    if !IsGameRunning() {
        LogCrash("Game not running at start, launching...")
        if !LaunchGame() {
            isRunning := false
            MsgBox("Failed to launch game. Check the path in CONFIG.gameExePath")
            return
        }
        needsFirstRunSetup := true
        isFirstLoadAfterRecovery := true  ; First load needs longer delay
    }
    
    ShowStatus("Starting harvest loop... (F10 to stop)")
    Sleep(1000)
    
    ; Main loop
    while isRunning {
        ; === PRE-ITERATION CHECKS ===
        
        ; Check if game is still running
        if !IsGameRunning() {
            ShowStatus("Game window lost! Attempting recovery...")
            if !RecoverFromCrash() {
                break
            }
            continue
        }
        
        ; Activate game window
        WinActivate("ahk_exe Tower Networking Inc.exe")
        Sleep(500)
        
        ; Perform first-run setup if needed (after crash recovery)
        if needsFirstRunSetup {
            if !PerformFirstRunSetup() {
                ShowStatus("First-run setup failed!")
                if !RecoverFromCrash() {
                    break
                }
                continue
            }
            ; After first-run setup, we're at the seed screen
            ; Continue with seed handling below
        } else {
            ; Normal iteration - click Start New Game
            CoordMode("Mouse", "Screen")
            Click(CONFIG.coords.startNewGame.x, CONFIG.coords.startNewGame.y)
            Sleep(CONFIG.clickDelay)
        }
        
        ; === SEED HANDLING ===
        if CONFIG.systematicMode {
            ; Type the next systematic seed
            nextSeed := GetNextSystematicSeed()
            TypeSeed(nextSeed)
            ShowStatus("Iteration " (iterationCount + 1) " - Seed: " nextSeed " (systematic)")
        } else {
            ; Random mode - just copy whatever seed is shown
            ShowStatus("Iteration " (iterationCount + 1) " - Capturing random seed...")
        }
        
        ; Click seed field to select it
        Click(CONFIG.coords.seedField.x, CONFIG.coords.seedField.y)
        Sleep(CONFIG.shortDelay)
        
        ; Select all and copy the seed
        Send("^a")
        Sleep(100)
        Send("^c")
        Sleep(200)
        
        ; Get seed from clipboard
        global currentSeed := Trim(A_Clipboard)
        
        if StrLen(currentSeed) != 5 {
            LogCrash("Invalid seed captured: '" currentSeed "' - may be at wrong screen")
            if !RecoverFromCrash() {
                break
            }
            continue
        }
        
        ShowStatus("Iteration " (iterationCount + 1) " - Seed: " currentSeed)
        
        ; === START GAME ===
        Click(CONFIG.coords.playSolo.x, CONFIG.coords.playSolo.y)
        
        ; Use longer delay for first load after recovery (cold cache), shorter for subsequent
        if isFirstLoadAfterRecovery {
            ShowStatus("Iteration " (iterationCount + 1) " - Loading (first run, please wait)...")
            Sleep(CONFIG.gameLoadDelayFirst)
            isFirstLoadAfterRecovery := false  ; Reset flag after first load
        } else {
            ShowStatus("Iteration " (iterationCount + 1) " - Loading...")
            Sleep(CONFIG.gameLoadDelay)
        }
        
        ; Verify game loaded (window should still exist)
        if !IsGameRunning() {
            LogCrash("Game crashed during loading for seed: " currentSeed)
            if !RecoverFromCrash() {
                break
            }
            continue
        }
        
        ; === OPEN TABLET AND CAPTURE ===
        ; IMPORTANT: Re-activate game window before sending keys/clicking
        WinActivate("ahk_exe Tower Networking Inc.exe")
        Sleep(500)
        
        ; Press Alt to open tablet (same as v2)
        Send("{Alt}")
        Sleep(CONFIG.tabletOpenDelay)
        
        ; Click Secretariat icon
        Click(CONFIG.coords.secretariatIcon.x, CONFIG.coords.secretariatIcon.y)
        Sleep(CONFIG.secretariatWait)
        
        ; Proposals tab is default view, no click needed
        Sleep(CONFIG.appSwitchDelay)
        
        ; === CAPTURE SCREENSHOTS ===
        screenshotName1 := CONFIG.debugMode ? (currentSeed "_proposals.png") : "proposals.png"
        screenshotName2 := CONFIG.debugMode ? (currentSeed "_proposals_scrolled.png") : "proposals_scrolled.png"
        
        captureFile1 := CONFIG.workDir "\" screenshotName1
        captureFile2 := CONFIG.workDir "\" screenshotName2
        
        ; Capture top
        CaptureRegion(CONFIG.captureRegions.full, captureFile1)
        Sleep(300)
        
        ; Scroll down
        Click(CONFIG.coords.scrollbarBottom.x, CONFIG.coords.scrollbarBottom.y)
        Sleep(CONFIG.scrollDelay)
        
        ; Capture bottom
        CaptureRegion(CONFIG.captureRegions.full, captureFile2)
        Sleep(300)
        
        ; === RUN OCR ===
        text1 := RunOcr(captureFile1)
        text2 := RunOcr(captureFile2)
        combinedText := Trim(text1) "`n" Trim(text2)
        
        ; === PARSE PROPOSALS ===
        proposals := ParseProposals(combinedText)
        
        ; Validate OCR result
        if !ValidateOcrResult(proposals) {
            LogCrash("Invalid OCR result for seed " currentSeed " - got " proposals.Length " valid proposals")
            ; Don't immediately recover - might just be a one-off OCR issue
            ; Log it and continue, but if this keeps happening, we'll detect via window check
        }
        
        ; === LOG RESULT ===
        LogResult(currentSeed, proposals, combinedText)
        
        ; Reset recovery attempts on successful iteration
        recoveryAttempts := 0
        
        ; === EXIT TO MAIN MENU ===
        Send("{Escape}")
        Sleep(CONFIG.clickDelay)
        Click(CONFIG.coords.quitToMainMenu.x, CONFIG.coords.quitToMainMenu.y)
        Sleep(CONFIG.menuExitDelay)
        
        ; Verify we made it back to main menu
        if !IsGameRunning() {
            LogCrash("Game crashed while returning to menu for seed: " currentSeed)
            if !RecoverFromCrash() {
                break
            }
            continue
        }
        
        iterationCount++
        ShowStatus("Completed " iterationCount " iterations. Last seed: " currentSeed)
        Sleep(CONFIG.loopDelay)
    }
    
    ShowStatus("Harvest stopped. Total iterations: " iterationCount)
    Sleep(3000)
    ToolTip()
}

StopLoop() {
    global isRunning
    isRunning := false
    ShowStatus("Stopping after current iteration...")
}

; ============================================================================
; CAPTURE AND OCR FUNCTIONS
; ============================================================================

CaptureRegion(region, outputFile) {
    x := region.x1
    y := region.y1
    w := region.x2 - region.x1
    h := region.y2 - region.y1
    
    psScript := "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap(" w ", " h "); $g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen(" x ", " y ", 0, 0, $b.Size); $b.Save('" outputFile "'); $g.Dispose(); $b.Dispose()"
    
    try {
        RunWait('powershell -NoProfile -Command "' psScript '"',, "Hide")
    } catch as err {
        LogCrash("Screenshot failed: " err.Message)
    }
}

RunOcr(imageFile) {
    outputBase := SubStr(imageFile, 1, -4)  ; Remove .png
    outputFile := outputBase ".txt"
    
    if FileExist(outputFile)
        FileDelete(outputFile)
    
    ; Use configured tesseract path (allows full path if not in PATH)
    tesseractCmd := Format('"{}" "{}" "{}" -l {} --dpi {} --psm {}',
                  CONFIG.tesseractExe,
                  imageFile, outputBase, 
                  CONFIG.tesseract.lang,
                  CONFIG.tesseract.dpi,
                  CONFIG.tesseract.psm)
    
    try {
        RunWait(tesseractCmd,, "Hide")
    } catch as err {
        LogCrash("Tesseract failed: " err.Message)
        LogCrash("Command was: " tesseractCmd)
        return ""
    }
    
    if FileExist(outputFile) {
        return FileRead(outputFile)
    }
    return ""
}

ParseProposals(text) {
    found := []
    foundIds := Map()
    
    textUpper := StrUpper(text)
    
    ; Sort keys by length (longest first) to match more specific patterns first
    keys := []
    for key, val in KNOWN_PROPOSALS {
        keys.Push({key: key, val: val, len: StrLen(key)})
    }
    
    ; Simple bubble sort by length descending
    loop keys.Length - 1 {
        i := A_Index
        loop keys.Length - i {
            j := A_Index + i
            if keys[A_Index + i - 1].len < keys[j].len {
                temp := keys[A_Index + i - 1]
                keys[A_Index + i - 1] := keys[j]
                keys[j] := temp
            }
        }
    }
    
    ; Find matches
    for item in keys {
        if InStr(textUpper, item.key) {
            canonical := item.val
            
            if foundIds.Has(canonical)
                continue
            
            found.Push(canonical)
            foundIds[canonical] := true
            
            if found.Length >= 3
                break
        }
    }
    
    ; Log if we found fewer than 3
    if found.Length < 3 {
        LogUnknown(text, found)
    }
    
    return found
}

LogResult(seed, proposals, rawText) {
    while proposals.Length < 3 {
        proposals.Push("UNKNOWN")
    }
    
    rawEscaped := StrReplace(rawText, '"', '""')
    rawEscaped := StrReplace(rawEscaped, "`n", " | ")
    rawEscaped := StrReplace(rawEscaped, "`r", "")
    
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    
    line := Format('{},{},{},{},"{}",{}`n',
                   seed,
                   proposals[1],
                   proposals[2],
                   proposals[3],
                   rawEscaped,
                   timestamp)
    
    FileAppend(line, CONFIG.workDir "\" CONFIG.seedLog)
}

LogUnknown(rawText, foundProposals) {
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    
    foundStr := ""
    for p in foundProposals {
        foundStr .= p ", "
    }
    
    line := Format('[{}] Found {} proposals: {}. Raw text:`n{}`n---`n',
                   timestamp, foundProposals.Length, RTrim(foundStr, ", "), rawText)
    
    FileAppend(line, CONFIG.workDir "\" CONFIG.unknownLog)
}

; ============================================================================
; TEST FUNCTIONS
; ============================================================================

TestCapture() {
    ShowStatus("Test capture starting...")
    
    if !DirExist(CONFIG.workDir) {
        DirCreate(CONFIG.workDir)
    }
    
    captureFile1 := CONFIG.workDir "\test_capture_top.png"
    captureFile2 := CONFIG.workDir "\test_capture_bottom.png"
    
    ; Capture top
    CaptureRegion(CONFIG.captureRegions.full, captureFile1)
    Sleep(300)
    
    ; Scroll
    CoordMode("Mouse", "Screen")
    Click(CONFIG.coords.scrollbarBottom.x, CONFIG.coords.scrollbarBottom.y)
    Sleep(600)
    
    ; Capture bottom
    CaptureRegion(CONFIG.captureRegions.full, captureFile2)
    Sleep(300)
    
    ; OCR
    text1 := RunOcr(captureFile1)
    text2 := RunOcr(captureFile2)
    combinedText := Trim(text1) "`n" Trim(text2)
    
    proposals := ParseProposals(combinedText)
    
    result := "=== TEST RESULTS ===`n`n"
    result .= "Found " proposals.Length " proposals:`n"
    for p in proposals {
        result .= "  ✓ " p "`n"
    }
    result .= "`n--- Raw OCR (first 500 chars) ---`n"
    result .= SubStr(combinedText, 1, 500)
    
    ToolTip()
    MsgBox(result, "Test Capture", "0x40000")
}

ShowCoords() {
    CoordMode("Mouse", "Screen")
    
    loop {
        MouseGetPos(&x, &y)
        ToolTip("Screen: " x ", " y "`nPress Escape to stop")
        Sleep(100)
        
        if GetKeyState("Escape", "P") {
            break
        }
    }
    
    ToolTip()
}
