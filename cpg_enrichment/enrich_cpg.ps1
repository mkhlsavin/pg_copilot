# enrich_cpg.ps1 — Automated CPG enrichment via Joern CLI (PowerShell)
# Usage: .\enrich_cpg.ps1 [minimal|standard|full] [cpg_path]

param(
    [string]$Profile = "standard",
    [string]$CpgPath,
    [string]$Skip = ""
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration
# ============================================================================
$SCRIPTS_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:ENRICH_ROOT = $SCRIPTS_DIR

function Resolve-JoernPath {
    param([string]$Hint)

    if ([string]::IsNullOrWhiteSpace($Hint)) {
        return $null
    }

    $candidate = $Hint
    if (-not (Test-Path $candidate)) {
        return $null
    }

    if ((Test-Path $candidate -PathType Container)) {
        foreach ($suffix in @("joern.exe", "joern.bat", "joern.ps1", "joern")) {
            $possible = Join-Path $candidate $suffix
            if (Test-Path $possible -PathType Leaf) {
                return (Resolve-Path $possible).Path
            }
        }
        return $null
    }

    return (Resolve-Path $candidate).Path
}

$JOERN_CMD = Resolve-JoernPath $env:JOERN_PATH
if (-not $JOERN_CMD) {
    $joernInPath = Get-Command joern -ErrorAction SilentlyContinue
    if ($joernInPath) {
        $JOERN_CMD = $joernInPath.Path
    }
}

if (-not $JOERN_CMD) {
    $repoRoot = Split-Path $SCRIPTS_DIR -Parent
    $candidates = @(
        (Join-Path $SCRIPTS_DIR "joern"),
        (Join-Path $SCRIPTS_DIR "joern-cli\joern"),
        (Join-Path $repoRoot "joern\joern"),
        (Join-Path $repoRoot "joern-cli\joern"),
        (Join-Path $repoRoot "joern-cli\src\universal\joern"),
        (Join-Path $repoRoot "joern-cli\src\universal\joern.bat")
    )

    foreach ($candidate in $candidates) {
        $resolved = Resolve-JoernPath $candidate
        if ($resolved) {
            $JOERN_CMD = $resolved
            break
        }
    }
}

if (-not $JOERN_CMD) {
    Write-Error "Joern executable not found. Set JOERN_PATH or ensure 'joern' is available on PATH."
    exit 1
}

# Memory configuration for Joern (16GB to prevent OOM errors)
if (-not $env:JAVA_OPTS) {
    $env:JAVA_OPTS = "-Xmx16G -Xms4G"
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

# ============================================================================
# Determine CPG Location
# ============================================================================
$DefaultWorkspace = "workspace\pg17_full.cpg"
$DefaultImport = "import\postgres-REL_17_6\pg17_full.cpg.bin"

if ([string]::IsNullOrWhiteSpace($CpgPath) -eq $false) {
    Write-Info "Using user-specified CPG path: $CpgPath"
} else {
    if (Test-Path $DefaultWorkspace -PathType Container) {
        $CpgPath = $DefaultWorkspace
        Write-Info "Detected existing workspace: $CpgPath"
    } elseif (Test-Path $DefaultImport -PathType Leaf) {
        $CpgPath = $DefaultImport
        Write-Info "Workspace not found; will import from archive: $CpgPath"
    } else {
        Write-Error-Custom "Workspace not found at $DefaultWorkspace and archive missing at $DefaultImport"
        exit 1
    }
}

function Show-Banner {
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  CPG ENRICHMENT AUTOMATION" -ForegroundColor Cyan
    Write-Host "  Profile: $Profile" -ForegroundColor Cyan
    Write-Host "  CPG Path: $CpgPath" -ForegroundColor Cyan
    Write-Host "  Joern: $JOERN_CMD" -ForegroundColor Cyan
    Write-Host "  Memory: $env:JAVA_OPTS" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

# ============================================================================
# Enrichment Scripts Configuration
# ============================================================================
$SCRIPTS = @{
    # Minimal profile scripts
    "comments" = "ast_comments.sc"
    "subsystem" = "subsystem_readme.sc"

    # Standard profile scripts
    "api" = "api_usage_examples.sc"
    "security" = "security_patterns.sc"
    "metrics" = "code_metrics.sc"
    "extension" = "extension_points.sc"
    "dependency" = "dependency_graph.sc"

    # Full profile scripts
    "test" = "test_coverage.sc"
    "perf" = "performance_hotspots.sc"
    "semantic" = "semantic_classification.sc"
    "layers" = "architectural_layers.sc"

    # New node-level enrichment scripts (full profile)
    "paramroles" = "enrich_param_roles.sc"
    "identifier" = "enrich_identifier_local.sc"
    "fieldidentifier" = "enrich_field_identifier.sc"
    "typedef" = "enrich_type_decl.sc"
    "typeusage" = "enrich_type_usage.sc"
    "literal" = "enrich_literal_semantics.sc"
    "modifier" = "enrich_modifier_semantics.sc"
    "member" = "enrich_member_semantics.sc"
    "methodref" = "enrich_method_ref.sc"
    "namespace" = "enrich_namespace_semantics.sc"
    "jump" = "enrich_jump_semantics.sc"
    "childroles" = "enrich_child_roles.sc"
    "edges" = "enrich_edge_semantics.sc"
    "commentsem" = "enrich_comment_semantics.sc"
    "pdg" = "enrich_pdg_semantics.sc"
    "execution" = "enrich_execution_patterns.sc"
    "dataflow" = "enrich_data_flow.sc"
    "return" = "enrich_return_semantics.sc"
}

$DESCRIPTIONS = @{
    # Minimal profile
    "comments" = "AST Comments enrichment"
    "subsystem" = "Subsystem documentation"

    # Standard profile
    "api" = "API usage patterns"
    "security" = "Security vulnerability detection"
    "metrics" = "Code quality metrics"
    "extension" = "Extension points detection"
    "dependency" = "Module dependency analysis"

    # Full profile
    "test" = "Test coverage mapping"
    "perf" = "Performance hotspot detection"
    "semantic" = "Semantic function classification"
    "layers" = "Architectural layer classification"

    # New node-level enrichment (full profile)
    "paramroles" = "Parameter & Return semantics"
    "identifier" = "Identifier & Local semantics"
    "fieldidentifier" = "Field Identifier semantics"
    "typedef" = "Type Declaration semantics"
    "typeusage" = "Type Usage semantics"
    "literal" = "Literal semantics"
    "modifier" = "Modifier semantics"
    "member" = "Member semantics"
    "methodref" = "Method Reference semantics"
    "namespace" = "Namespace semantics"
    "jump" = "Jump semantics"
    "childroles" = "AST child role semantics"
    "edges" = "Edge semantics enrichment"
    "commentsem" = "Comment-driven semantics"
    "pdg" = "PDG flow semantics"
    "execution" = "Execution pattern semantics"
    "dataflow" = "Domain data-flow semantics"
    "return" = "Return semantics"
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
        @(
            # Minimal
            "comments", "subsystem",
            # Standard
            "api", "security", "metrics", "extension", "dependency",
            # Full - original
            "test", "perf", "semantic", "layers",
            # Full - new node-level enrichment
            "paramroles", "identifier", "fieldidentifier",
            "typedef", "typeusage", "literal", "modifier",
            "member", "methodref", "namespace", "jump",
            "childroles", "edges", "commentsem", "pdg", "execution", "dataflow", "return"
        )
    }
    default {
        Write-Error-Custom "Unknown profile: $Profile"
        Write-Host "Valid profiles: minimal, standard, full"
        exit 1
    }
}

if ($Skip) {
    $skipIds = $Skip.Split(",") | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ }
    if ($skipIds.Count -gt 0) {
        $ENABLED_SCRIPTS = $ENABLED_SCRIPTS | Where-Object { $skipIds -notcontains $_.ToLower() }
        Write-Info ("Skipping scripts: " + ($skipIds -join ", "))
    }
}

# ============================================================================
# Main Execution
# ============================================================================
Show-Banner

# Check Joern installation
Write-Info "Using Joern executable: $JOERN_CMD"

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
$ResolvedProjectName = $WorkspaceName

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
$scriptIndex = 1
$ENABLED_SCRIPTS | ForEach-Object {
    $scriptId = $_
    $scriptFile = $SCRIPTS[$scriptId]
    $description = $DESCRIPTIONS[$scriptId]
    Write-Host "  $scriptIndex. $description"
    Write-Host "     -> $scriptFile"
    $scriptIndex++
}
Write-Host "--------------------------------------------------------------------------------"

# Confirmation
$response = Read-Host "Proceed with enrichment? [y/N]"
if ($response -notmatch "^[Yy]$") {
    Write-Warning-Custom "Aborted by user"
    exit 0
}

# Resolve final CPG file + project information for enrich_all.sc
if ($IS_WORKSPACE) {
    $ResolvedCpgFile = Join-Path $CpgPath "cpg.bin"
    if (-not (Test-Path $ResolvedCpgFile -PathType Leaf)) {
        Write-Error-Custom "Workspace missing cpg.bin at: $ResolvedCpgFile"
        exit 1
    }
    $ResolvedCpgFile = (Resolve-Path $ResolvedCpgFile).Path
    $ResolvedProjectName = Split-Path -Leaf $CpgPath
} else {
    $ResolvedCpgFile = (Resolve-Path $CpgPath).Path
    if (-not $ResolvedProjectName) {
        $ResolvedProjectName = [System.IO.Path]::GetFileNameWithoutExtension($ResolvedCpgFile) -replace '\.cpg$', ''
    }
}

Write-Info "Resolved CPG file: $ResolvedCpgFile"
Write-Info "Project name: $ResolvedProjectName"

$logDir = Join-Path $SCRIPTS_DIR "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$commonScriptPath = Join-Path $SCRIPTS_DIR "enrich_common.sc"
$commonContent = if (Test-Path $commonScriptPath) { Get-Content $commonScriptPath -Raw } else { "" }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$scriptEntries = $ENABLED_SCRIPTS | ForEach-Object {
    [PSCustomObject]@{
        Id          = $_
        Path        = (Resolve-Path (Join-Path $SCRIPTS_DIR $SCRIPTS[$_])).Path
        Description = $DESCRIPTIONS[$_]
    }
}

function Invoke-EnrichmentScript {
    param(
        [int] $Index,
        [int] $Total,
        [Parameter(Mandatory=$true)] $Entry,
        [string] $ResolvedCpgFile,
        [string] $ResolvedProjectName,
        [string] $LogDirectory,
        [string] $CommonContent,
        [System.Text.UTF8Encoding] $Encoding
    )

    $scriptIdSafe = ($Entry.Id -replace '[^A-Za-z0-9_\-]', '_')
    $logFile = Join-Path $LogDirectory ("enrich_{0}_{1:yyyyMMdd_HHmmss}.log" -f $scriptIdSafe, (Get-Date))
    $errFile = "$logFile.err"
    $tempScriptPath = Join-Path $env:TEMP ("run_{0}_{1}.sc" -f $scriptIdSafe, [Guid]::NewGuid().ToString("N"))

    Write-Host "[$Index/$Total] -> $($Entry.Description) [$($Entry.Id)]"

    $builder = New-Object System.Text.StringBuilder
    $escapedCpg = $ResolvedCpgFile.Replace("\", "/")
    $escapedProject = $ResolvedProjectName.Replace("\", "\\")
    $null = $builder.AppendLine("val cpgPath = """ + $escapedCpg + """")
    $null = $builder.AppendLine("val projectName = """ + $escapedProject + """")
    $null = $builder.AppendLine("if (workspace.projectExists(projectName)) {")
    $null = $builder.AppendLine("  open(projectName)")
    $null = $builder.AppendLine("} else {")
    $null = $builder.AppendLine("  importCpg(cpgPath, projectName, true)")
    $null = $builder.AppendLine("}")
    $null = $builder.AppendLine("def persist(): Unit = {")
    $null = $builder.AppendLine("  workspace.closeProject(projectName)")
    $null = $builder.AppendLine("}")
    $null = $builder.AppendLine("")

    if ($CommonContent.Length -gt 0) {
        $null = $builder.AppendLine("// ==== enrich_common.sc")
        $null = $builder.AppendLine($CommonContent)
        $null = $builder.AppendLine("")
    }

    $scriptContent = Get-Content $Entry.Path -Raw
    $null = $builder.AppendLine("// ==== " + $Entry.Id)
    $null = $builder.AppendLine($scriptContent)
    $null = $builder.AppendLine("")
    $null = $builder.AppendLine("persist()")

    [System.IO.File]::WriteAllText($tempScriptPath, $builder.ToString(), $Encoding)

    $runParams = @{
        FilePath              = $JOERN_CMD
        ArgumentList          = @("--script", $tempScriptPath)
        WorkingDirectory      = (Split-Path -Parent $JOERN_CMD)
        RedirectStandardOutput= $logFile
        RedirectStandardError = $errFile
        Wait                  = $true
        PassThru              = $true
    }

    $proc = Start-Process @runParams
    Remove-Item $tempScriptPath -ErrorAction SilentlyContinue

    if (Test-Path $errFile) {
        Add-Content $logFile -Value "`n----- STDERR -----`n"
        Get-Content $errFile | Add-Content $logFile
        Remove-Item $errFile -ErrorAction SilentlyContinue
    }

    if ($proc.ExitCode -ne 0) {
        Write-Error-Custom "Script $($Entry.Id) failed with exit code $($proc.ExitCode). See log: $logFile"
        Write-Host "---- Log tail ----"
        Get-Content $logFile -Tail 50
        exit $proc.ExitCode
    } else {
        Write-Info "Completed $($Entry.Id). Log: $logFile"
    }
}

$totalScripts = $scriptEntries.Count
$currentIndex = 0
foreach ($entry in $scriptEntries) {
    $currentIndex++
    Invoke-EnrichmentScript -Index $currentIndex `
        -Total $totalScripts `
        -Entry $entry `
        -ResolvedCpgFile $ResolvedCpgFile `
        -ResolvedProjectName $ResolvedProjectName `
        -LogDirectory $logDir `
        -CommonContent $commonContent `
        -Encoding $utf8NoBom
}

Write-Host "--------------------------------------------------------------------------------"
Write-Success "Enrichment completed successfully!"
Write-Info "CPG is now enriched and saved (project: $ResolvedProjectName)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Verify: joern --import `"$ResolvedCpgFile`" -c 'cpg.comment.size'"
Write-Host "  2. Query: joern --import `"$ResolvedCpgFile`" -c 'cpg.method.tag.name(`"api-caller-count`").size'"
Write-Host "  3. Use enriched CPG in your RAG pipeline"
