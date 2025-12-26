#!/bin/bash
# =============================================================================
# CodeGraph Installation Script for Ubuntu 22.04
# Yandex Cloud VM with OS Login
#
# Usage: sudo ./install-ubuntu.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CODEGRAPH_DIR="/opt/codegraph"
CODEGRAPH_USER="codegraph"
DOCKER_COMPOSE_VERSION="2.24.0"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# =============================================================================
# Pre-flight checks
# =============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
    fi
}

check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release; then
        log_error "This script is designed for Ubuntu. Detected: $(cat /etc/os-release | grep PRETTY_NAME)"
    fi
    log_info "Detected: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
}

# =============================================================================
# System setup
# =============================================================================

update_system() {
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    log_success "System updated"
}

install_dependencies() {
    log_info "Installing system dependencies..."
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        jq \
        openssl \
        ufw
    log_success "Dependencies installed"
}

# =============================================================================
# Docker installation
# =============================================================================

install_docker() {
    log_info "Installing Docker..."

    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Add Docker GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    log_success "Docker installed: $(docker --version)"
}

install_docker_compose() {
    log_info "Installing docker-compose standalone..."

    # Install standalone version for compatibility
    curl -SL "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    log_success "docker-compose installed: $(docker-compose --version)"
}

# =============================================================================
# User and directory setup
# =============================================================================

create_user() {
    log_info "Creating codegraph user..."

    if id "$CODEGRAPH_USER" &>/dev/null; then
        log_warning "User $CODEGRAPH_USER already exists"
    else
        useradd -r -m -s /bin/bash -d /home/$CODEGRAPH_USER $CODEGRAPH_USER
        log_success "User $CODEGRAPH_USER created"
    fi

    # Add to docker group
    usermod -aG docker $CODEGRAPH_USER
    log_success "User added to docker group"
}

setup_directories() {
    log_info "Setting up CodeGraph directories..."

    # Create main directory
    mkdir -p $CODEGRAPH_DIR

    # Create subdirectories
    mkdir -p $CODEGRAPH_DIR/data/projects
    mkdir -p $CODEGRAPH_DIR/data/duckdb
    mkdir -p $CODEGRAPH_DIR/logs
    mkdir -p $CODEGRAPH_DIR/monitoring
    mkdir -p $CODEGRAPH_DIR/grafana
    mkdir -p $CODEGRAPH_DIR/services/leads/logs

    # Check if source files exist in current directory
    if [ -f "docker-compose.yml" ]; then
        log_info "Copying files from current directory..."
        cp -r . $CODEGRAPH_DIR/
    elif [ -f "/tmp/codegraph/docker-compose.yml" ]; then
        log_info "Copying files from /tmp/codegraph..."
        cp -r /tmp/codegraph/* $CODEGRAPH_DIR/
    else
        log_warning "No source files found. Please copy files to $CODEGRAPH_DIR manually."
    fi

    # Set ownership
    chown -R $CODEGRAPH_USER:$CODEGRAPH_USER $CODEGRAPH_DIR

    log_success "Directories created at $CODEGRAPH_DIR"
}

# =============================================================================
# Secrets generation
# =============================================================================

generate_secrets() {
    log_info "Generating secure secrets..."

    # Generate random strings
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    API_JWT_SECRET=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)
    API_ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
    LEADS_API_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

    log_success "Secrets generated"
}

create_env_file() {
    log_info "Creating environment file..."

    cat > $CODEGRAPH_DIR/.env << EOF
# =============================================================================
# CodeGraph Environment Variables
# Generated: $(date)
# Location: $CODEGRAPH_DIR/.env
# =============================================================================

# ============================================================================
# PostgreSQL Database
# ============================================================================
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# ============================================================================
# API Authentication
# ============================================================================
API_JWT_SECRET=${API_JWT_SECRET}
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=${API_ADMIN_PASSWORD}

# ============================================================================
# Yandex AI Studio LLM Provider
# REQUIRED: Configure these before starting!
# Get credentials at: https://console.cloud.yandex.ru/
# ============================================================================
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-yandex-folder-id>

# ============================================================================
# Environment Settings
# ============================================================================
ENVIRONMENT=production
LOG_LEVEL=INFO

# ============================================================================
# Security Settings
# ============================================================================
SECURITY_ENABLED=true
DLP_ENABLED=true

# ============================================================================
# CORS Settings (comma-separated origins for production)
# Example: https://app.example.com,https://admin.example.com
# ============================================================================
CORS_ALLOWED_ORIGINS=

# ============================================================================
# Grafana Monitoring
# ============================================================================
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
GRAFANA_ROOT_URL=http://localhost:3000

# ============================================================================
# Leads Service (CTA form handling)
# ============================================================================
LEADS_API_KEY=${LEADS_API_KEY}
# Email notifications (optional)
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@codegraph.ru
ADMIN_EMAIL=
# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF

    chmod 600 $CODEGRAPH_DIR/.env
    chown $CODEGRAPH_USER:$CODEGRAPH_USER $CODEGRAPH_DIR/.env

    log_success "Environment file created"
}

# =============================================================================
# Firewall configuration
# =============================================================================

configure_firewall() {
    log_info "Configuring firewall..."

    # Allow SSH (critical for OS Login)
    ufw allow ssh

    # Allow application ports
    ufw allow 8000/tcp comment 'CodeGraph API'
    ufw allow 8001/tcp comment 'CodeGraph Leads API'
    ufw allow 9090/tcp comment 'Prometheus'
    ufw allow 3000/tcp comment 'Grafana'

    # Enable firewall (non-interactive)
    ufw --force enable

    log_success "Firewall configured"
    ufw status verbose
}

# =============================================================================
# Systemd service
# =============================================================================

create_systemd_service() {
    log_info "Creating systemd services..."

    # Main CodeGraph service
    cat > /etc/systemd/system/codegraph.service << EOF
[Unit]
Description=CodeGraph Code Analysis System
Documentation=https://github.com/your-org/codegraph
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$CODEGRAPH_USER
Group=docker
WorkingDirectory=$CODEGRAPH_DIR

# Start services
ExecStart=/usr/bin/docker compose up -d

# Stop services gracefully
ExecStop=/usr/bin/docker compose down

# Reload/restart
ExecReload=/usr/bin/docker compose restart

# Timeout for startup (build might take time)
TimeoutStartSec=600

# Restart policy
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Leads microservice
    cat > /etc/systemd/system/codegraph-leads.service << EOF
[Unit]
Description=CodeGraph Leads Microservice
Documentation=https://github.com/your-org/codegraph
Requires=docker.service codegraph.service
After=docker.service codegraph.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$CODEGRAPH_USER
Group=docker
WorkingDirectory=$CODEGRAPH_DIR/services/leads

# Start service
ExecStart=/usr/bin/docker compose -f docker-compose.leads.yml up -d

# Stop service gracefully
ExecStop=/usr/bin/docker compose -f docker-compose.leads.yml down

# Reload/restart
ExecReload=/usr/bin/docker compose -f docker-compose.leads.yml restart

# Timeout for startup
TimeoutStartSec=120

# Restart policy
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable codegraph.service
    systemctl enable codegraph-leads.service

    log_success "Systemd services created and enabled"
}

# =============================================================================
# Leads database setup
# =============================================================================

setup_leads_database() {
    log_info "Setting up leads database..."
    log_info "The codegraph_leads database will be created after PostgreSQL starts."
    log_info "Run this command after starting the main service:"
    log_info "  docker exec -it codegraph-postgres psql -U codegraph -c 'CREATE DATABASE codegraph_leads;'"
}

# =============================================================================
# Database migrations
# =============================================================================

run_migrations() {
    log_info "Database migrations will be run on first start..."
    log_info "To run migrations manually:"
    log_info "  cd $CODEGRAPH_DIR && docker compose exec api python -m alembic upgrade head"
}

# =============================================================================
# Summary
# =============================================================================

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${GREEN}                 CodeGraph Installation Complete!${NC}"
    echo "============================================================================="
    echo ""
    echo "Installation Directory: $CODEGRAPH_DIR"
    echo ""
    echo "============================================================================="
    echo "GENERATED CREDENTIALS (Save these securely!)"
    echo "============================================================================="
    echo ""
    echo "  PostgreSQL:"
    echo "    User:     codegraph"
    echo "    Password: $POSTGRES_PASSWORD"
    echo ""
    echo "  API Admin:"
    echo "    Username: admin"
    echo "    Password: $API_ADMIN_PASSWORD"
    echo ""
    echo "  Grafana:"
    echo "    Username: admin"
    echo "    Password: $GRAFANA_ADMIN_PASSWORD"
    echo ""
    echo "  Leads API Key: $LEADS_API_KEY"
    echo ""
    echo "============================================================================="
    echo -e "${YELLOW}IMPORTANT: Configure Yandex AI Studio before starting!${NC}"
    echo "============================================================================="
    echo ""
    echo "  1. Edit the environment file:"
    echo "     sudo nano $CODEGRAPH_DIR/.env"
    echo ""
    echo "  2. Set your Yandex Cloud credentials:"
    echo "     YANDEX_API_KEY=<your-api-key>"
    echo "     YANDEX_FOLDER_ID=<your-folder-id>"
    echo ""
    echo "  3. (Optional) Configure leads notifications:"
    echo "     SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL"
    echo "     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
    echo ""
    echo "  4. Get credentials at:"
    echo "     https://console.cloud.yandex.ru/"
    echo ""
    echo "============================================================================="
    echo "SERVICE MANAGEMENT"
    echo "============================================================================="
    echo ""
    echo "  Main Service:"
    echo "    Start:    sudo systemctl start codegraph"
    echo "    Stop:     sudo systemctl stop codegraph"
    echo "    Status:   sudo systemctl status codegraph"
    echo "    Logs:     cd $CODEGRAPH_DIR && docker compose logs -f"
    echo ""
    echo "  Leads Service:"
    echo "    Start:    sudo systemctl start codegraph-leads"
    echo "    Stop:     sudo systemctl stop codegraph-leads"
    echo "    Status:   sudo systemctl status codegraph-leads"
    echo ""
    echo "============================================================================="
    echo "LEADS SERVICE SETUP"
    echo "============================================================================="
    echo ""
    echo "  After starting the main service, create leads database:"
    echo "    docker exec -it codegraph-postgres psql -U codegraph \\"
    echo "      -c 'CREATE DATABASE codegraph_leads;'"
    echo ""
    echo "  Then start the leads service:"
    echo "    sudo systemctl start codegraph-leads"
    echo ""
    echo "============================================================================="
    echo "ACCESS URLs (after starting)"
    echo "============================================================================="
    echo ""
    echo "  API:         http://<VM_IP>:8000"
    echo "  API Docs:    http://<VM_IP>:8000/api/docs"
    echo "  Leads API:   http://<VM_IP>:8001"
    echo "  Leads Docs:  http://<VM_IP>:8001/docs"
    echo "  Prometheus:  http://<VM_IP>:9090"
    echo "  Grafana:     http://<VM_IP>:3000"
    echo ""
    echo "============================================================================="
    echo "NEXT STEPS"
    echo "============================================================================="
    echo ""
    echo "  1. Configure Yandex AI Studio credentials in .env"
    echo "  2. Start the main service: sudo systemctl start codegraph"
    echo "  3. Create leads database (see LEADS SERVICE SETUP above)"
    echo "  4. Start leads service: sudo systemctl start codegraph-leads"
    echo "  5. Check status: sudo systemctl status codegraph codegraph-leads"
    echo ""
    echo "============================================================================="
}

# =============================================================================
# Main
# =============================================================================

main() {
    log_info "Starting CodeGraph installation for Ubuntu 22.04..."
    echo ""

    check_root
    check_ubuntu
    update_system
    install_dependencies
    install_docker
    install_docker_compose
    create_user
    setup_directories
    generate_secrets
    create_env_file
    configure_firewall
    create_systemd_service
    setup_leads_database
    run_migrations
    print_summary
}

# Run main
main "$@"
