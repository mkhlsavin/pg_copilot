Param(
    [string]$JoernHome = "C:\Users\user\joern",
    [string]$Host = "localhost",
    [int]$Port = 8080,
    [int]$StartupTimeoutSeconds = 90,
    [switch]$ForceRestart
)

function Write-Info($Message) {
    Write-Host "[INFO] $Message"
}

function Write-Warn($Message) {
    Write-Warning $Message
}

function Assert-Path($Path, $Description) {
    if (-not (Test-Path $Path)) {
        throw "$Description not found: $Path"
    }
}

function Get-ListeningConnection {
    param (
        [int]$Port
    )
    try {
        return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    } catch {
        return $null
    }
}

function Wait-ForPort {
    param (
        [string]$Host,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $connection = Get-ListeningConnection -Port $Port
        if ($connection) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Assert-Path -Path $JoernHome -Description "Joern home directory"
$joernBat = Join-Path $JoernHome "joern.bat"
Assert-Path -Path $joernBat -Description "Joern launcher"
$pgClient = Join-Path $JoernHome "pg17_client.py"
Assert-Path -Path $pgClient -Description "pg17_client.py"

$existing = Get-ListeningConnection -Port $Port
if ($existing -and -not $ForceRestart) {
    Write-Info "Joern server already listening on port $Port (PID $($existing.OwningProcess))."
} else {
    if ($existing -and $ForceRestart) {
        Write-Warn "Stopping existing process on port $Port (PID $($existing.OwningProcess))."
        Stop-Process -Id $existing.OwningProcess -Force
        Start-Sleep -Seconds 2
    }

Write-Info ("Starting Joern server on {0}:{1}" -f $Host, $Port)
    $startInfo = @{
        FilePath         = $joernBat
        ArgumentList     = @('-J-Xmx16G', '--server', '--server-host', $Host, '--server-port', $Port.ToString())
        WorkingDirectory = $JoernHome
        WindowStyle      = 'Hidden'
    }
    Start-Process @startInfo | Out-Null

    if (-not (Wait-ForPort -Host $Host -Port $Port -TimeoutSeconds $StartupTimeoutSeconds)) {
        throw "Joern did not start listening on port $Port within $StartupTimeoutSeconds seconds."
    }
    Write-Info ("Joern server is listening on {0}:{1}" -f $Host, $Port)
}

$bootstrapQueries = @(
    'import _root_.io.joern.joerncli.console.Joern',
    'import _root_.io.shiftleft.semanticcpg.language._',
    'Joern.open("pg17_full.cpg")',
    'val cpg = Joern.cpg'
)

Push-Location $JoernHome
try {
    foreach ($query in $bootstrapQueries) {
        Write-Info "Running bootstrap query: $query"
        & python $pgClient --query $query
        if ($LASTEXITCODE -ne 0) {
            throw "Bootstrap query failed: $query"
        }
    }
    Write-Info "Joern workspace bootstrap complete."
} finally {
    Pop-Location
}
