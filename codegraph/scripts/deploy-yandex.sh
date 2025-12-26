#!/bin/bash
# =============================================================================
# CodeGraph Yandex Cloud Deployment Script
# Deploys to Ubuntu 22.04 VM with OS Login
#
# Prerequisites:
#   - Yandex Cloud CLI (yc) installed and configured
#   - Service account with compute.osLogin or compute.osAdminLogin role
#   - OS Login enabled at organization level
#
# Usage:
#   export FOLDER_ID=<your-folder-id>
#   export SUBNET_ID=<your-subnet-id>
#   ./deploy-yandex.sh deploy
#   ./deploy-yandex.sh connect
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Configuration - Edit these or set via environment variables
# =============================================================================
VM_NAME="${VM_NAME:-codegraph-prod}"
FOLDER_ID="${FOLDER_ID:-}"
ZONE="${ZONE:-ru-central1-a}"
SUBNET_ID="${SUBNET_ID:-}"
PLATFORM="${PLATFORM:-standard-v3}"
CORES="${CORES:-4}"
MEMORY="${MEMORY:-16}"
DISK_SIZE="${DISK_SIZE:-100}"
DISK_TYPE="${DISK_TYPE:-network-ssd}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu-2204-lts-oslogin}"

# Project directory (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# Logging functions
# =============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# =============================================================================
# Prerequisites check
# =============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check yc CLI
    if ! command -v yc &> /dev/null; then
        log_error "Yandex Cloud CLI (yc) not found.
Install from: https://cloud.yandex.com/docs/cli/quickstart

Quick install:
  curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
  yc init"
    fi

    # Check if logged in
    if ! yc config profile list &> /dev/null; then
        log_error "yc CLI not configured. Run: yc init"
    fi

    # Check folder ID
    if [ -z "$FOLDER_ID" ]; then
        log_error "FOLDER_ID not set.
Export: FOLDER_ID=<your-folder-id>
Find it: yc resource-manager folder list"
    fi

    # Check subnet ID
    if [ -z "$SUBNET_ID" ]; then
        log_warning "SUBNET_ID not set. Will use default subnet."
        # Try to get default subnet
        SUBNET_ID=$(yc vpc subnet list --folder-id "$FOLDER_ID" --format json | jq -r '.[0].id // empty')
        if [ -z "$SUBNET_ID" ]; then
            log_error "No subnet found. Create one or export SUBNET_ID=<your-subnet-id>"
        fi
        log_info "Using subnet: $SUBNET_ID"
    fi

    log_success "Prerequisites check passed"
}

# =============================================================================
# VM operations
# =============================================================================
check_vm_exists() {
    yc compute instance get --name "$VM_NAME" --folder-id "$FOLDER_ID" &> /dev/null
}

get_vm_ip() {
    yc compute instance get --name "$VM_NAME" --folder-id "$FOLDER_ID" \
        --format json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address // empty'
}

get_vm_internal_ip() {
    yc compute instance get --name "$VM_NAME" --folder-id "$FOLDER_ID" \
        --format json | jq -r '.network_interfaces[0].primary_v4_address.address // empty'
}

create_vm() {
    log_info "Creating VM: $VM_NAME..."

    # Check if VM exists
    if check_vm_exists; then
        log_warning "VM $VM_NAME already exists"
        VM_IP=$(get_vm_ip)
        log_info "VM IP: $VM_IP"
        return
    fi

    # Create VM with Ubuntu 22.04 OS Login image
    log_info "Creating VM with:"
    log_info "  Platform: $PLATFORM"
    log_info "  Cores: $CORES"
    log_info "  Memory: ${MEMORY}GB"
    log_info "  Disk: ${DISK_SIZE}GB $DISK_TYPE"
    log_info "  Zone: $ZONE"
    log_info "  Image: $IMAGE_FAMILY"

    yc compute instance create \
        --name "$VM_NAME" \
        --folder-id "$FOLDER_ID" \
        --zone "$ZONE" \
        --platform "$PLATFORM" \
        --cores "$CORES" \
        --memory "$MEMORY" \
        --core-fraction 100 \
        --create-boot-disk "image-folder-id=standard-images,image-family=$IMAGE_FAMILY,size=$DISK_SIZE,type=$DISK_TYPE" \
        --network-interface "subnet-id=$SUBNET_ID,nat-ip-version=ipv4" \
        --metadata serial-port-enable=1 \
        --async

    log_info "Waiting for VM to be ready..."
    sleep 30

    # Wait for VM to be running
    for i in {1..60}; do
        STATUS=$(yc compute instance get --name "$VM_NAME" --folder-id "$FOLDER_ID" --format json | jq -r '.status')
        if [ "$STATUS" == "RUNNING" ]; then
            break
        fi
        log_info "VM status: $STATUS (waiting...)"
        sleep 10
    done

    VM_IP=$(get_vm_ip)
    if [ -z "$VM_IP" ]; then
        log_error "Could not get VM IP address"
    fi

    log_success "VM created successfully"
    log_info "External IP: $VM_IP"
    log_info "Internal IP: $(get_vm_internal_ip)"
}

# =============================================================================
# Deployment
# =============================================================================
deploy_files() {
    log_info "Copying files to VM..."

    VM_IP=$(get_vm_ip)
    if [ -z "$VM_IP" ]; then
        log_error "Could not get VM IP. Is the VM running?"
    fi

    log_info "Waiting for SSH to be available..."
    for i in {1..30}; do
        if yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID" -- "echo 'SSH OK'" &> /dev/null; then
            break
        fi
        log_info "Waiting for SSH... ($i/30)"
        sleep 10
    done

    # Create temp directory on VM
    log_info "Creating directory on VM..."
    yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID" -- \
        "sudo mkdir -p /tmp/codegraph && sudo chmod 777 /tmp/codegraph"

    # Copy files using rsync via SSH
    log_info "Syncing project files..."

    # Files to copy
    FILES_TO_COPY=(
        "Dockerfile"
        "docker-compose.yml"
        "docker-compose.override.yml"
        ".dockerignore"
        "config.yaml"
        "requirements.txt"
        "alembic.ini"
        "src"
        "grafana"
        "monitoring"
        "scripts/install-ubuntu.sh"
        "services/leads"
    )

    # Create archive of files
    cd "$PROJECT_DIR"
    tar -czf /tmp/codegraph-deploy.tar.gz \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='data/*' \
        --exclude='logs/*' \
        --exclude='*.duckdb' \
        --exclude='venv' \
        --exclude='.env' \
        "${FILES_TO_COPY[@]}" 2>/dev/null || true

    # Copy archive to VM
    log_info "Uploading archive..."
    yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID" -- \
        "cat > /tmp/codegraph-deploy.tar.gz" < /tmp/codegraph-deploy.tar.gz

    # Extract on VM
    log_info "Extracting files..."
    yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID" -- \
        "cd /tmp/codegraph && tar -xzf /tmp/codegraph-deploy.tar.gz"

    # Clean up local archive
    rm -f /tmp/codegraph-deploy.tar.gz

    log_success "Files copied successfully"
}

run_installation() {
    log_info "Running installation script on VM..."

    yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID" -- \
        "sudo chmod +x /tmp/codegraph/scripts/install-ubuntu.sh && \
         sudo /tmp/codegraph/scripts/install-ubuntu.sh"

    log_success "Installation completed"
}

# =============================================================================
# Connection
# =============================================================================
connect_vm() {
    log_info "Connecting to VM via OS Login..."
    yc compute ssh --name "$VM_NAME" --folder-id "$FOLDER_ID"
}

# =============================================================================
# Status
# =============================================================================
show_status() {
    log_info "VM Status:"
    echo ""

    if ! check_vm_exists; then
        log_warning "VM $VM_NAME does not exist"
        return
    fi

    # Get VM info
    VM_INFO=$(yc compute instance get --name "$VM_NAME" --folder-id "$FOLDER_ID" --format json)
    STATUS=$(echo "$VM_INFO" | jq -r '.status')
    VM_IP=$(echo "$VM_INFO" | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address // "N/A"')
    VM_INTERNAL_IP=$(echo "$VM_INFO" | jq -r '.network_interfaces[0].primary_v4_address.address // "N/A"')
    CREATED=$(echo "$VM_INFO" | jq -r '.created_at')

    echo "  Name:        $VM_NAME"
    echo "  Status:      $STATUS"
    echo "  External IP: $VM_IP"
    echo "  Internal IP: $VM_INTERNAL_IP"
    echo "  Created:     $CREATED"
    echo ""

    if [ "$STATUS" == "RUNNING" ] && [ "$VM_IP" != "N/A" ]; then
        echo "Access URLs:"
        echo "  API:        http://$VM_IP:8000"
        echo "  API Docs:   http://$VM_IP:8000/api/docs"
        echo "  Prometheus: http://$VM_IP:9090"
        echo "  Grafana:    http://$VM_IP:3000"
        echo ""
        echo "Connect: ./deploy-yandex.sh connect"
    fi
}

# =============================================================================
# Cleanup
# =============================================================================
destroy_vm() {
    log_warning "This will delete VM $VM_NAME and all its data!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Aborted"
        return
    fi

    log_info "Deleting VM..."
    yc compute instance delete --name "$VM_NAME" --folder-id "$FOLDER_ID"
    log_success "VM deleted"
}

# =============================================================================
# Help
# =============================================================================
show_help() {
    echo "CodeGraph Yandex Cloud Deployment Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  deploy    Create VM and deploy CodeGraph"
    echo "  connect   Connect to VM via OS Login SSH"
    echo "  status    Show VM status and access URLs"
    echo "  destroy   Delete VM (with confirmation)"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  FOLDER_ID    Yandex Cloud folder ID (required)"
    echo "  SUBNET_ID    Subnet ID for VM network interface"
    echo "  VM_NAME      VM name (default: codegraph-prod)"
    echo "  ZONE         Availability zone (default: ru-central1-a)"
    echo "  CORES        Number of CPU cores (default: 4)"
    echo "  MEMORY       RAM in GB (default: 16)"
    echo "  DISK_SIZE    Boot disk size in GB (default: 100)"
    echo ""
    echo "Example:"
    echo "  export FOLDER_ID=b1g1234567890"
    echo "  export SUBNET_ID=e9b1234567890"
    echo "  $0 deploy"
    echo ""
    echo "After deployment:"
    echo "  1. Connect: $0 connect"
    echo "  2. Configure: sudo nano /opt/codegraph/.env"
    echo "  3. Start: sudo systemctl start codegraph"
}

# =============================================================================
# Main
# =============================================================================
main() {
    case "${1:-help}" in
        deploy)
            check_prerequisites
            create_vm
            deploy_files
            run_installation
            echo ""
            show_status
            ;;
        connect)
            check_prerequisites
            connect_vm
            ;;
        status)
            check_prerequisites
            show_status
            ;;
        destroy)
            check_prerequisites
            destroy_vm
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1
Run '$0 help' for usage"
            ;;
    esac
}

main "$@"
