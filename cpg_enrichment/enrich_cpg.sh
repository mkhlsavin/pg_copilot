#!/bin/bash
# enrich_cpg.sh — Automated CPG enrichment via Joern CLI
# Usage: ./enrich_cpg.sh [minimal|standard|full] [cpg_path]

set -e

# ============================================================================
# Configuration
# ============================================================================
PROFILE="${1:-standard}"
USER_CPG_PATH="${2:-}"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Expose the enrichment root so Scala scripts can locate sibling files
export ENRICH_ROOT="$SCRIPTS_DIR"

# Memory configuration for Joern (16GB to prevent OOM errors)
export JAVA_OPTS="${JAVA_OPTS:--Xmx16G -Xms4G}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Joern Binary Resolution
# ============================================================================
JOERN_CMD=""

resolve_candidate() {
    local candidate="$1"
    local resolved=""

    if [ -z "$candidate" ]; then
        return 1
    fi

    if [ -d "$candidate" ]; then
        for suffix in joern joern.sh joern.exe; do
            if [ -x "$candidate/$suffix" ]; then
                resolved="$candidate/$suffix"
                break
            elif [ -f "$candidate/$suffix" ]; then
                resolved="$candidate/$suffix"
                break
            fi
        done
    elif [ -f "$candidate" ]; then
        resolved="$candidate"
    fi

    if [ -n "$resolved" ]; then
        JOERN_CMD="$resolved"
        return 0
    fi

    return 1
}

# 1. Respect explicit JOERN_PATH hints
if [ -n "${JOERN_PATH:-}" ]; then
    resolve_candidate "$JOERN_PATH"
fi

# 2. Fall back to PATH lookup
if [ -z "$JOERN_CMD" ] && command -v joern >/dev/null 2>&1; then
    JOERN_CMD="$(command -v joern)"
fi

# 3. Try common installation locations relative to the repo
if [ -z "$JOERN_CMD" ]; then
    JOERN_CANDIDATES=(
        "$SCRIPTS_DIR/joern"
        "$SCRIPTS_DIR/joern-cli/joern"
        "$SCRIPTS_DIR/../joern/joern"
        "$SCRIPTS_DIR/../joern-cli/joern"
        "$SCRIPTS_DIR/../joern-cli/src/universal/joern"
    )

    for candidate in "${JOERN_CANDIDATES[@]}"; do
        if resolve_candidate "$candidate"; then
            break
        fi
    done
fi

if [ -z "$JOERN_CMD" ]; then
    echo "--------------------------------------------------------------------------------"
    echo "[X] Joern executable not found."
    echo "[!] Set JOERN_PATH to the Joern binary or add it to PATH before running this script."
    exit 1
fi

# ============================================================================
# Helper Functions
# ============================================================================
log_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[X]${NC} $1"
}

# ============================================================================
# Determine CPG Location
# ============================================================================
DEFAULT_WORKSPACE_PATH="$SCRIPTS_DIR/workspace/pg17_full.cpg"
DEFAULT_IMPORT_PATH="$SCRIPTS_DIR/import/postgres-REL_17_6/pg17_full.cpg.bin"

if [ -n "$USER_CPG_PATH" ]; then
    CPG_PATH="$USER_CPG_PATH"
    log_info "Using user-specified CPG path: $CPG_PATH"
else
    if [ -d "$DEFAULT_WORKSPACE_PATH" ]; then
        CPG_PATH="$DEFAULT_WORKSPACE_PATH"
        log_info "Detected existing workspace: $CPG_PATH"
    elif [ -f "$DEFAULT_IMPORT_PATH" ]; then
        CPG_PATH="$DEFAULT_IMPORT_PATH"
        log_info "Workspace not found; will import from archive: $CPG_PATH"
    else
        log_error "Workspace not found at $DEFAULT_WORKSPACE_PATH and archive missing at $DEFAULT_IMPORT_PATH"
        exit 1
    fi
fi

print_banner() {
    echo "================================================================================"
    echo "  CPG ENRICHMENT AUTOMATION"
    echo "  Profile: $PROFILE"
    echo "  CPG Path: $CPG_PATH"
    echo "  Joern: $JOERN_CMD"
    echo "  Memory: $JAVA_OPTS"
    echo "================================================================================"
}

# ============================================================================
# Enrichment Scripts Configuration
# ============================================================================
declare -A SCRIPTS=(
    ["comments"]="ast_comments.sc"
    ["subsystem"]="subsystem_readme.sc"
    ["api"]="api_usage_examples.sc"
    ["security"]="security_patterns.sc"
    ["metrics"]="code_metrics.sc"
    ["extension"]="extension_points.sc"
    ["dependency"]="dependency_graph.sc"
    ["test"]="test_coverage.sc"
    ["perf"]="performance_hotspots.sc"
    ["semantic"]="semantic_classification.sc"
    ["layers"]="architectural_layers.sc"
)

declare -A DESCRIPTIONS=(
    ["comments"]="AST Comments enrichment"
    ["subsystem"]="Subsystem documentation"
    ["api"]="API usage patterns"
    ["security"]="Security vulnerability detection"
    ["metrics"]="Code quality metrics"
    ["extension"]="Extension points detection"
    ["dependency"]="Module dependency analysis"
    ["test"]="Test coverage mapping"
    ["perf"]="Performance hotspot detection"
    ["semantic"]="Semantic function classification"
    ["layers"]="Architectural layer classification"
)

# Profile definitions
case "$PROFILE" in
    minimal)
        ENABLED_SCRIPTS=("comments" "subsystem")
        ;;
    standard)
        ENABLED_SCRIPTS=("comments" "subsystem" "api" "security" "metrics" "extension" "dependency")
        ;;
    full)
        ENABLED_SCRIPTS=("comments" "subsystem" "api" "security" "metrics" "extension" "dependency" "test" "perf" "semantic" "layers")
        ;;
    *)
        log_error "Unknown profile: $PROFILE"
        echo "Valid profiles: minimal, standard, full"
        exit 1
        ;;
esac

# ============================================================================
# Main Execution
# ============================================================================
print_banner

# Check Joern installation
log_info "Using Joern executable: $JOERN_CMD"

# Check CPG exists and determine if it's a directory (workspace) or file (bin)
IS_WORKSPACE=false
IS_BIN_FILE=false

if [ -d "$CPG_PATH" ]; then
    IS_WORKSPACE=true
    log_info "Found Joern workspace at: $CPG_PATH"
elif [ -f "$CPG_PATH" ]; then
    IS_BIN_FILE=true
    log_info "Found CPG file at: $CPG_PATH (will import to workspace)"
    # Generate workspace name from file
    WORKSPACE_NAME=$(basename "$CPG_PATH" | sed 's/\.bin\.zip$//' | sed 's/\.bin$//')
    log_info "Workspace name: $WORKSPACE_NAME"
else
    log_error "CPG not found at: $CPG_PATH"
    log_info "Please provide either:"
    log_info "  - A workspace directory (created by Joern)"
    log_info "  - A .bin.zip file to import"
    exit 1
fi

# Check scripts exist
log_info "Checking enrichment scripts..."
MISSING_SCRIPTS=0
for script_id in "${ENABLED_SCRIPTS[@]}"; do
    script_file="${SCRIPTS[$script_id]}"
    if [ ! -f "$SCRIPTS_DIR/$script_file" ]; then
        log_error "Script not found: $script_file"
        MISSING_SCRIPTS=$((MISSING_SCRIPTS + 1))
    fi
done

if [ $MISSING_SCRIPTS -gt 0 ]; then
    log_error "$MISSING_SCRIPTS script(s) missing. Aborting."
    exit 1
fi

log_success "All scripts found"
echo "--------------------------------------------------------------------------------"

# Display plan
log_info "Enrichment plan (${#ENABLED_SCRIPTS[@]} scripts):"
for i in "${!ENABLED_SCRIPTS[@]}"; do
    script_id="${ENABLED_SCRIPTS[$i]}"
    script_file="${SCRIPTS[$script_id]}"
    description="${DESCRIPTIONS[$script_id]}"
    echo "  $((i+1)). $description"
    echo "     -> $script_file"
done
echo "--------------------------------------------------------------------------------"

# Confirmation
read -p "Proceed with enrichment? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Aborted by user"
    exit 0
fi

# Create batch script for Joern
BATCH_SCRIPT="/tmp/joern_enrich_$$_.sc"
log_info "Creating batch script: $BATCH_SCRIPT"

if [ "$IS_WORKSPACE" = true ]; then
    cat > "$BATCH_SCRIPT" << 'EOF'
// Auto-generated enrichment batch script
println("=" * 80)
println("Starting CPG enrichment...")
println("=" * 80)

val startTime = System.currentTimeMillis()

EOF
else
    # Import from .bin file first
    cat > "$BATCH_SCRIPT" << EOF
// Auto-generated enrichment batch script
println("=" * 80)
println("Importing CPG from file...")
println("=" * 80)

val cpgPath = "$CPG_PATH"
val workspaceName = "$WORKSPACE_NAME"

println(s"[*] Importing: \$cpgPath")
println(s"[*] Workspace: \$workspaceName")

importCpg(cpgPath, workspaceName)

println("[+] CPG imported successfully")
println("")
println("=" * 80)
println("Starting CPG enrichment...")
println("=" * 80)

val startTime = System.currentTimeMillis()

EOF
fi

# Add each script by embedding its content in isolated blocks
for i in "${!ENABLED_SCRIPTS[@]}"; do
    script_id="${ENABLED_SCRIPTS[$i]}"
    script_file="${SCRIPTS[$script_id]}"
    script_path="$SCRIPTS_DIR/$script_file"

    cat >> "$BATCH_SCRIPT" << EOF

println("")
println("-" * 80)
println("[$((i+1))/${#ENABLED_SCRIPTS[@]}] Loading: $script_file")
println("-" * 80)
val scriptStart_$i = System.currentTimeMillis()

try {
  // Isolated block for $script_file
  {

EOF

    # Append the script content directly
    cat "$script_path" >> "$BATCH_SCRIPT"

    cat >> "$BATCH_SCRIPT" << EOF

  }
  val scriptEnd_$i = System.currentTimeMillis()
  println("[+] Completed in " + ((scriptEnd_$i - scriptStart_$i) / 1000.0) + "s")
} catch {
  case e: Exception =>
    println("[X] Error in $script_file: " + e.getMessage)
    e.printStackTrace()
}

EOF
done

# Add summary and save
cat >> "$BATCH_SCRIPT" << 'EOF'

println("")
println("=" * 80)
println("Enrichment Summary")
println("=" * 80)
println("[*] CPG Statistics:")
try {
    println(f"    Comments: ${cpg.comment.size}%,d")
    println(f"    Tags: ${cpg.tag.size}%,d")
    println(f"    Files: ${cpg.file.size}%,d")
    println(f"    Methods: ${cpg.method.size}%,d")
} catch {
    case e: Exception => println("[!] Could not get statistics: " + e.getMessage)
}

val endTime = System.currentTimeMillis()
val totalTime = (endTime - startTime) / 1000.0
println(f"\n[+] Total time: ${totalTime}%.1fs")

println("\n[*] Saving CPG...")
println("[!] Note: CPG is auto-saved on workspace close")
println("[+] Enrichment data has been added to the CPG")

println("=" * 80)
println("[+] Enrichment complete!")
println("=" * 80)
EOF

log_success "Batch script created"
echo "--------------------------------------------------------------------------------"

# Execute enrichment
log_info "Starting Joern with CPG: $CPG_PATH"
log_warn "This may take 10-90 minutes depending on profile..."

# Run Joern
if [ "$IS_WORKSPACE" = true ]; then
    "$JOERN_CMD" --script "$BATCH_SCRIPT" --import "$CPG_PATH"
else
    "$JOERN_CMD" --script "$BATCH_SCRIPT"
fi

EXIT_CODE=$?

# Cleanup
rm -f "$BATCH_SCRIPT"

if [ $EXIT_CODE -eq 0 ]; then
    echo "--------------------------------------------------------------------------------"
    log_success "Enrichment completed successfully!"
    log_info "CPG is now enriched and saved"
    echo ""
    echo "Next steps:"
    echo "  1. Verify: joern --cpg $CPG_PATH -c 'cpg.comment.size'"
    echo "  2. Query: joern --cpg $CPG_PATH -c 'cpg.method.tag.name(\"api-caller-count\").size'"
    echo "  3. Use enriched CPG in your RAG pipeline"
else
    log_error "Enrichment failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi
