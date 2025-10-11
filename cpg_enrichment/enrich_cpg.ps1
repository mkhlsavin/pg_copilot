# enrich_cpg.ps1 — Automated CPG enrichment via Joern CLI (PowerShell)
# Usage: .\enrich_cpg.ps1 [minimal|standard|full] [cpg_path]

param(
    [string]$Profile = "standard",
    [string]$CpgPath = "workspace/postgres-REL_17_6"
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration
# ============================================================================
$SCRIPTS_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$JOERN_PATH = if ($env:JOERN_PATH) { $env:JOERN_PATH } else { ".\joern" }

# Memory configuration for Joern (24GB to prevent OOM errors)
if (-not $env:JAVA_OPTS) {
    $env:JAVA_OPTS = "-Xmx24G -Xms4G"
}

# ============================================================================
# Helper Functions
# ============================================================================
function Write-Info {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[X] $Message" -ForegroundColor Red
}

function Show-Banner {
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  CPG ENRICHMENT AUTOMATION" -ForegroundColor Cyan
    Write-Host "  Profile: $Profile" -ForegroundColor Cyan
    Write-Host "  CPG Path: $CpgPath" -ForegroundColor Cyan
    Write-Host "  Memory: $env:JAVA_OPTS" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

# ============================================================================
# Enrichment Scripts Configuration
# ============================================================================
$SCRIPTS = @{
    "comments" = "ast_comments.sc"
    "subsystem" = "subsystem_readme.sc"
    "api" = "api_usage_examples.sc"
    "security" = "security_patterns.sc"
    "metrics" = "code_metrics.sc"
    "extension" = "extension_points.sc"
    "dependency" = "dependency_graph.sc"
    "test" = "test_coverage.sc"
    "perf" = "performance_hotspots.sc"
    "semantic" = "semantic_classification.sc"
    "layers" = "architectural_layers.sc"
}

$DESCRIPTIONS = @{
    "comments" = "AST Comments enrichment"
    "subsystem" = "Subsystem documentation"
    "api" = "API usage patterns"
    "security" = "Security vulnerability detection"
    "metrics" = "Code quality metrics"
    "extension" = "Extension points detection"
    "dependency" = "Module dependency analysis"
    "test" = "Test coverage mapping"
    "perf" = "Performance hotspot detection"
    "semantic" = "Semantic function classification"
    "layers" = "Architectural layer classification"
}

# Profile definitions
$ENABLED_SCRIPTS = switch ($Profile) {
    "minimal" {
        @("comments", "subsystem")
    }
    "standard" {
        @("comments", "subsystem", "api", "security", "metrics", "extension", "dependency")
    }
    "full" {
        @("comments", "subsystem", "api", "security", "metrics", "extension", "dependency", "test", "perf", "semantic", "layers")
    }
    default {
        Write-Error-Custom "Unknown profile: $Profile"
        Write-Host "Valid profiles: minimal, standard, full"
        exit 1
    }
}

# ============================================================================
# Main Execution
# ============================================================================
Show-Banner

# Check Joern installation
if (-not (Test-Path $JOERN_PATH) -and -not (Test-Path "joern-cli")) {
    Write-Error-Custom "Joern not found. Please set JOERN_PATH environment variable"
    exit 1
}

# Check CPG exists and determine if it's a directory (workspace) or file (bin)
$IS_WORKSPACE = Test-Path $CpgPath -PathType Container
$IS_BIN_FILE = Test-Path $CpgPath -PathType Leaf

if (-not $IS_WORKSPACE -and -not $IS_BIN_FILE) {
    Write-Error-Custom "CPG not found at: $CpgPath"
    Write-Info "Please provide either:"
    Write-Info "  - A workspace directory (created by Joern)"
    Write-Info "  - A .bin.zip file to import"
    exit 1
}

if ($IS_WORKSPACE) {
    Write-Info "Found Joern workspace at: $CpgPath"
} else {
    Write-Info "Found CPG file at: $CpgPath (will import to workspace)"
    # Generate workspace name from file
    $WorkspaceName = [System.IO.Path]::GetFileNameWithoutExtension($CpgPath) -replace '\.bin$', ''
    Write-Info "Workspace name: $WorkspaceName"
}

# Check scripts exist
Write-Info "Checking enrichment scripts..."
$MISSING_SCRIPTS = 0
foreach ($script_id in $ENABLED_SCRIPTS) {
    $script_file = $SCRIPTS[$script_id]
    $script_path = Join-Path $SCRIPTS_DIR $script_file
    if (-not (Test-Path $script_path)) {
        Write-Error-Custom "Script not found: $script_file"
        $MISSING_SCRIPTS++
    }
}

if ($MISSING_SCRIPTS -gt 0) {
    Write-Error-Custom "$MISSING_SCRIPTS script(s) missing. Aborting."
    exit 1
}

Write-Success "All scripts found"
Write-Host "--------------------------------------------------------------------------------"

# Display plan
Write-Info "Enrichment plan ($($ENABLED_SCRIPTS.Count) scripts):"
for ($i = 0; $i -lt $ENABLED_SCRIPTS.Count; $i++) {
    $script_id = $ENABLED_SCRIPTS[$i]
    $script_file = $SCRIPTS[$script_id]
    $description = $DESCRIPTIONS[$script_id]
    Write-Host "  $($i+1). $description"
    Write-Host "     -> $script_file"
}
Write-Host "--------------------------------------------------------------------------------"

# Confirmation
$response = Read-Host "Proceed with enrichment? [y/N]"
if ($response -notmatch "^[Yy]$") {
    Write-Warning-Custom "Aborted by user"
    exit 0
}

# Create batch script for Joern
$BATCH_SCRIPT = Join-Path $env:TEMP "joern_enrich_$PID.sc"
Write-Info "Creating batch script: $BATCH_SCRIPT"

# Write initial part (UTF8 without BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

if ($IS_WORKSPACE) {
    # Open existing workspace
    $workspaceName = Split-Path -Leaf $CpgPath
$content = @"
// Auto-generated enrichment batch script
println("=" * 80)
println("Opening workspace...")
println("=" * 80)

val workspaceName = "$workspaceName"
println(s"[*] Opening: `$workspaceName")

open(workspaceName)

println("[+] Workspace opened")
println("")
println("=" * 80)
println("Starting CPG enrichment...")
println("=" * 80)

val startTime = System.currentTimeMillis()

"@
    [System.IO.File]::WriteAllText($BATCH_SCRIPT, $content, $utf8NoBom)
} else {
    # Import from .bin file first
$content = @"
// Auto-generated enrichment batch script
println("=" * 80)
println("Importing CPG from file...")
println("=" * 80)

val cpgPath = "$($CpgPath -replace '\\', '/')"
val workspaceName = "$WorkspaceName"

println(s"[*] Importing: `$cpgPath")
println(s"[*] Workspace: `$workspaceName")

importCpg(cpgPath, workspaceName)

println("[+] CPG imported successfully")
println("")
println("=" * 80)
println("Starting CPG enrichment...")
println("=" * 80)

val startTime = System.currentTimeMillis()

"@
    [System.IO.File]::WriteAllText($BATCH_SCRIPT, $content, $utf8NoBom)
}

# Add each script by embedding its content in isolated blocks
for ($i = 0; $i -lt $ENABLED_SCRIPTS.Count; $i++) {
    $script_id = $ENABLED_SCRIPTS[$i]
    $script_file = $SCRIPTS[$script_id]
    $script_path = Join-Path $SCRIPTS_DIR $script_file

    # Build the isolated block with proper escaping
    $block_header = @"

println("")
println("-" * 80)
println("[$($i+1)/$($ENABLED_SCRIPTS.Count)] Loading: $script_file")
println("-" * 80)
val scriptStart_$i = System.currentTimeMillis()

try {
  // Isolated block for $script_file
  {

"@
    [System.IO.File]::AppendAllText($BATCH_SCRIPT, $block_header, $utf8NoBom)

    # Read and append the script content
    $scriptContent = Get-Content $script_path -Raw
    [System.IO.File]::AppendAllText($BATCH_SCRIPT, $scriptContent, $utf8NoBom)

    $block_footer = @"

  }
  val scriptEnd_$i = System.currentTimeMillis()
  println("[+] Completed in " + ((scriptEnd_$i - scriptStart_$i) / 1000.0) + "s")
} catch {
  case e: Exception =>
    println("[X] Error in $script_file`: " + e.getMessage)
    e.printStackTrace()
}

"@
    [System.IO.File]::AppendAllText($BATCH_SCRIPT, $block_footer, $utf8NoBom)
}

# Add summary and save
$summary = @"

println("")
println("=" * 80)
println("Enrichment Summary")
println("=" * 80)
println("[*] CPG Statistics:")
try {
    println(f"    Comments: `${cpg.comment.size}%,d")
    println(f"    Tags: `${cpg.tag.size}%,d")
    println(f"    Files: `${cpg.file.size}%,d")
    println(f"    Methods: `${cpg.method.size}%,d")
} catch {
    case e: Exception => println("[!] Could not get statistics: " + e.getMessage)
}

val endTime = System.currentTimeMillis()
val totalTime = (endTime - startTime) / 1000.0
println(f"\n[+] Total time: `${totalTime}%.1fs")

println("\n[*] Saving CPG...")
println("[!] Note: CPG is auto-saved on workspace close")
println("[+] Enrichment data has been added to the CPG")

println("=" * 80)
println("[+] Enrichment complete!")
println("=" * 80)
"@
[System.IO.File]::AppendAllText($BATCH_SCRIPT, $summary, $utf8NoBom)

Write-Success "Batch script created"
Write-Host "--------------------------------------------------------------------------------"

# Execute enrichment
Write-Info "Starting Joern with CPG: $CpgPath"
Write-Warning-Custom "This may take 10-90 minutes depending on profile..."

# Run Joern
try {
    if ($IS_WORKSPACE) {
        # Open existing workspace (no --import needed for directories)
        if (Test-Path "$JOERN_PATH.bat") {
            & "$JOERN_PATH.bat" --script $BATCH_SCRIPT
        } elseif (Test-Path $JOERN_PATH) {
            & $JOERN_PATH --script $BATCH_SCRIPT
        } else {
            & ".\joern-cli\joern" --script $BATCH_SCRIPT
        }
    } else {
        # Import from file (no --import needed, script handles importCpg)
        if (Test-Path "$JOERN_PATH.bat") {
            & "$JOERN_PATH.bat" --script $BATCH_SCRIPT
        } elseif (Test-Path $JOERN_PATH) {
            & $JOERN_PATH --script $BATCH_SCRIPT
        } else {
            & ".\joern-cli\joern" --script $BATCH_SCRIPT
        }
    }
    $EXIT_CODE = $LASTEXITCODE
} catch {
    Write-Error-Custom "Failed to execute Joern: $_"
    Remove-Item $BATCH_SCRIPT -ErrorAction SilentlyContinue
    exit 1
}

# Cleanup
Remove-Item $BATCH_SCRIPT -ErrorAction SilentlyContinue

if ($EXIT_CODE -eq 0) {
    Write-Host "--------------------------------------------------------------------------------"
    Write-Success "Enrichment completed successfully!"
    Write-Info "CPG is now enriched and saved"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Verify: joern --import $CpgPath -c 'cpg.comment.size'"
    Write-Host "  2. Query: joern --import $CpgPath -c 'cpg.method.tag.name(`"api-caller-count`").size'"
    Write-Host "  3. Use enriched CPG in your RAG pipeline"
} else {
    Write-Error-Custom "Enrichment failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
}
