#!/bin/bash
# =============================================================================
# AI-Powered VAPT Tool - Linux Installation & Setup Script
# Version: 3.0.0
# =============================================================================

set -euo pipefail  # Exit on error, undefined variable, and pipe failure

# =============================================================================
# COLOR CODES FOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# =============================================================================
# CONFIGURATION VARIABLES
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/opt/vapt-tool}"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_FILE="${INSTALL_DIR}/install.log"
CONFIG_FILE="${INSTALL_DIR}/config/config.yaml"
BACKUP_DIR="${INSTALL_DIR}/backups"

# Version information
VAPT_VERSION="3.0.0"
PYTHON_VERSION="3.9"
MIN_RAM_MB=4096
MIN_DISK_GB=10

# Default database credentials
DB_NAME="vapt_tool"
DB_USER="vapt_user"
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 48)
JWT_SECRET=$(openssl rand -base64 48)

# Service ports
WEB_PORT=8000
API_PORT=5000
POSTGRES_PORT=5432
REDIS_PORT=6379
MONGODB_PORT=27017

# Detect Redis service name (deb: redis-server, rpm: redis)
REDIS_SVC="redis-server"
if systemctl list-unit-files 2>/dev/null | grep -q "^redis "; then
    REDIS_SVC="redis"
fi

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     █████╗ ██╗    ██╗   ██╗ █████╗ ██████╗ ████████╗         ║
║    ██╔══██╗██║    ██║   ██║██╔══██╗██╔══██╗╚══██╔══╝         ║
║    ███████║██║    ██║   ██║███████║██████╔╝   ██║            ║
║    ██╔══██║██║    ╚██╗ ██╔╝██╔══██║██╔═══╝    ██║            ║
║    ██║  ██║██║     ╚████╔╝ ██║  ██║██║        ██║            ║
║    ╚═╝  ╚═╝╚═╝      ╚═══╝  ╚═╝  ╚═╝╚═╝        ╚═╝            ║
║                                                               ║
║    AI-Powered Vulnerability Assessment & Penetration Testing  ║
║    Version 3.0.0                                                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "${BOLD}${CYAN}[*] Automated Installation Script${NC}"
    echo -e "${CYAN}[*] Support: Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+${NC}"
    echo ""
}

log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[+] ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}[!] ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[-] ${message}${NC}"
            ;;
        "STEP")
            echo -e "${BLUE}[*] ${message}${NC}"
            ;;
    esac
    
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_message "WARN" "Running as root. This is not recommended for production."
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

check_system_requirements() {
    log_message "STEP" "Checking system requirements..."
    
    # Check OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        log_message "ERROR" "Unsupported operating system"
        exit 1
    fi
    
    log_message "INFO" "Operating System: $OS $OS_VERSION"
    
    # Check RAM
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $total_ram -lt $MIN_RAM_MB ]]; then
        log_message "WARN" "Low memory: ${total_ram}MB (Recommended: ${MIN_RAM_MB}MB)"
    else
        log_message "INFO" "RAM: ${total_ram}MB"
    fi
    
    # Check disk space
    available_disk=$(df /opt | awk 'NR==2 {print $4}')
    available_disk_gb=$((available_disk / 1024 / 1024))
    if [[ $available_disk_gb -lt $MIN_DISK_GB ]]; then
        log_message "ERROR" "Insufficient disk space: ${available_disk_gb}GB (Required: ${MIN_DISK_GB}GB)"
        exit 1
    fi
    log_message "INFO" "Available disk: ${available_disk_gb}GB"
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 &>/dev/null; then
        log_message "INFO" "Internet connectivity: OK"
    else
        log_message "ERROR" "No internet connectivity"
        exit 1
    fi
}

detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
        PKG_INSTALL="apt-get install -y"
        PKG_UPDATE="apt-get update"
    elif command -v yum &>/dev/null; then
        PKG_MANAGER="yum"
        PKG_INSTALL="yum install -y"
        PKG_UPDATE="yum check-update"
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        PKG_INSTALL="dnf install -y"
        PKG_UPDATE="dnf check-update"
    else
        log_message "ERROR" "No supported package manager found"
        exit 1
    fi
    
    log_message "INFO" "Package manager: $PKG_MANAGER"
}

# =============================================================================
# INSTALLATION FUNCTIONS
# =============================================================================

install_system_dependencies() {
    log_message "STEP" "Installing system dependencies..."
    
    $PKG_UPDATE
    
    # Common dependencies
    local packages=(
        python3 python3-pip python3-venv python3-dev
        build-essential libssl-dev libffi-dev
        libxml2-dev libxslt1-dev zlib1g-dev
        libjpeg-dev libpng-dev libpq-dev
        git curl wget unzip tar
        nmap masscan
        chromium-browser chromium-chromedriver
        postgresql postgresql-contrib
        redis-server
        nodejs npm
        supervisor
        nginx
        certbot python3-certbot-nginx
    )
    
    for package in "${packages[@]}"; do
        if ! command -v "$package" &>/dev/null; then
            log_message "INFO" "Installing $package..."
            $PKG_INSTALL "$package" || {
                log_message "WARN" "Failed to install $package, continuing..."
            }
        fi
    done
    
    # Install MongoDB (optional)
    if [[ "$INSTALL_MONGODB" == "yes" ]]; then
        log_message "INFO" "Installing MongoDB..."
        curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-6.0.gpg
        echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
        $PKG_UPDATE
        $PKG_INSTALL mongodb-org
    fi
}

setup_python_environment() {
    log_message "STEP" "Setting up Python virtual environment..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Create Python virtual environment
    python3 -m venv "$VENV_DIR"
    
    # Activate and upgrade pip
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Install Python dependencies
    log_message "INFO" "Installing Python packages..."
    
    cat > /tmp/requirements.txt << 'EOF'
# Core Framework
numpy==1.24.3
pandas==2.0.3
scipy==1.10.1
python-dateutil==2.8.2

# Machine Learning & AI
tensorflow==2.13.0
scikit-learn==1.3.0
joblib==1.3.1
nltk==3.8.1

# Network Scanning
python-nmap==0.7.1
scapy==2.5.0
paramiko==3.2.0

# Web Testing
requests==2.31.0
selenium==4.10.0
beautifulsoup4==4.12.2
lxml==4.9.3
aiohttp==3.8.5

# Web Framework
fastapi==0.100.0
uvicorn==0.23.1
pydantic==2.0.3
jinja2==3.1.2

# Database
sqlalchemy==2.0.18
psycopg2-binary==2.9.6
redis==4.6.0
pymongo==4.4.1
alembic==1.11.1

# Security & Cryptography
cryptography==41.0.2
pyjwt==2.8.0
passlib==1.7.4
bcrypt==4.0.1

# Cloud Providers
boto3==1.28.3
azure-storage-blob==12.17.0
google-cloud-storage==2.10.0

# Reporting & Visualization
weasyprint==59.0
plotly==5.15.0
matplotlib==3.7.1

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
click==8.1.4
rich==13.4.2
tqdm==4.65.0
celery==5.3.1

# Testing
pytest==7.4.0
pytest-cov==4.1.0
factory-boy==3.2.1
EOF
    
    pip install -r /tmp/requirements.txt || {
        log_message "WARN" "Some packages failed to install. Check log for details."
    }
    
    # Install spaCy model for NLP
    python3 -m spacy download en_core_web_sm 2>/dev/null || true
    
    deactivate
}

setup_database() {
    log_message "STEP" "Configuring databases..."
    
    # PostgreSQL setup
    log_message "INFO" "Setting up PostgreSQL..."
    
    sudo -u postgres psql << EOF
-- Create user
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
-- Create database
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
-- Allow the user to create databases for tests
ALTER USER ${DB_USER} CREATEDB;
EOF
    
    # Configure PostgreSQL for better performance
    sudo tee -a /etc/postgresql/*/main/postgresql.conf > /dev/null << EOF
# VAPT Tool optimizations
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 5242kB
min_wal_size = 1GB
max_wal_size = 4GB
EOF
    
    sudo systemctl restart postgresql
    
    # Redis setup
    log_message "INFO" "Setting up Redis..."
    
    # Detect Redis service name (deb: redis-server, rpm: redis)
    REDIS_SVC="redis-server"
    if ! systemctl list-unit-files | grep -q "^redis-server"; then
        REDIS_SVC="redis"
    fi
    
    sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup 2>/dev/null || true
    
    sudo tee /etc/redis/redis.conf > /dev/null << EOF
# VAPT Tool Redis Configuration
bind 127.0.0.1
port ${REDIS_PORT}
requirepass ${REDIS_PASSWORD}
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF
    
    sudo systemctl restart "${REDIS_SVC}"
}

deploy_source_files() {
    log_message "STEP" "Deploying source files to ${INSTALL_DIR}..."

    SCRIPT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Copy the top-level Python files
    for f in vapt_tool.py requirements.txt pyproject.toml; do
        if [[ -f "${SCRIPT_SRC}/${f}" ]]; then
            cp "${SCRIPT_SRC}/${f}" "${INSTALL_DIR}/${f}"
            log_message "INFO" "Deployed ${f}"
        fi
    done

    # Copy the full src/ tree from the repo into INSTALL_DIR/src/
    if [[ -d "${SCRIPT_SRC}/src" ]]; then
        cp -r "${SCRIPT_SRC}/src/." "${INSTALL_DIR}/src/"
        log_message "INFO" "Deployed src/ package tree"
    fi

    # Copy legacy scanner modules that the installer expects
    local scanner_dirs=(network web api cloud)
    for d in "${scanner_dirs[@]}"; do
        if [[ -d "${SCRIPT_SRC}/src/scanners/${d}" ]]; then
            mkdir -p "${INSTALL_DIR}/src/scanners/${d}"
            cp "${SCRIPT_SRC}/src/scanners/${d}/scanner.py" \
               "${INSTALL_DIR}/src/scanners/${d}/scanner.py"
            log_message "INFO" "Deployed scanner: ${d}"
        fi
    done

    # Copy AI, API, core, utils modules
    for sub in core api ai utils; do
        if [[ -d "${SCRIPT_SRC}/src/${sub}" ]]; then
            mkdir -p "${INSTALL_DIR}/src/${sub}"
            cp "${SCRIPT_SRC}/src/${sub}/"*.py "${INSTALL_DIR}/src/${sub}/" 2>/dev/null || true
            log_message "INFO" "Deployed module tree: ${sub}"
        fi
    done

    # Top-level src modules
    for f in exceptions.py version.py main.py; do
        if [[ -f "${SCRIPT_SRC}/src/${f}" ]]; then
            cp "${SCRIPT_SRC}/src/${f}" "${INSTALL_DIR}/src/${f}"
        fi
    done

    # Install the package into the venv so `import vapt_tool` works
    source "${VENV_DIR}/bin/activate"
    pip install -e "${INSTALL_DIR}" 2>/dev/null || \
        pip install "${INSTALL_DIR}/vapt_tool.py" 2>/dev/null || \
        log_message "WARN" "Could not pip-install vapt_tool.py into venv"
    deactivate
}

setup_directories() {
    log_message "STEP" "Creating directory structure..."
    
    local directories=(
        "${INSTALL_DIR}/src"
        "${INSTALL_DIR}/src/core"
        "${INSTALL_DIR}/src/scanners"
        "${INSTALL_DIR}/src/scanners/network"
        "${INSTALL_DIR}/src/scanners/web"
        "${INSTALL_DIR}/src/scanners/api"
        "${INSTALL_DIR}/src/scanners/cloud"
        "${INSTALL_DIR}/src/ai"
        "${INSTALL_DIR}/src/ai/models"
        "${INSTALL_DIR}/src/ai/training"
        "${INSTALL_DIR}/src/ai/inference"
        "${INSTALL_DIR}/src/api"
        "${INSTALL_DIR}/src/api/routes"
        "${INSTALL_DIR}/src/api/middleware"
        "${INSTALL_DIR}/src/web"
        "${INSTALL_DIR}/src/web/static"
        "${INSTALL_DIR}/src/web/templates"
        "${INSTALL_DIR}/config"
        "${INSTALL_DIR}/data"
        "${INSTALL_DIR}/data/raw"
        "${INSTALL_DIR}/data/processed"
        "${INSTALL_DIR}/models"
        "${INSTALL_DIR}/models/pretrained"
        "${INSTALL_DIR}/models/custom"
        "${INSTALL_DIR}/models/checkpoints"
        "${INSTALL_DIR}/reports"
        "${INSTALL_DIR}/logs"
        "${INSTALL_DIR}/tests"
        "${INSTALL_DIR}/tests/unit"
        "${INSTALL_DIR}/tests/integration"
        "${INSTALL_DIR}/scripts"
        "${INSTALL_DIR}/docs"
        "${BACKUP_DIR}"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_message "INFO" "Created: $dir"
    done
    
    # Set permissions
    chmod -R 755 "${INSTALL_DIR}"
    chmod -R 700 "${INSTALL_DIR}/config"
    chmod -R 700 "${BACKUP_DIR}"
}

generate_configuration() {
    log_message "STEP" "Generating configuration files..."
    
    # Main configuration file
    cat > "${CONFIG_FILE}" << EOF
# =============================================================================
# AI-VAPT Tool Configuration
# Generated: $(date)
# =============================================================================

app:
  name: "AI-VAPT Tool"
  version: "${VAPT_VERSION}"
  environment: "production"
  debug: false
  secret_key: "${SECRET_KEY}"
  jwt_secret: "${JWT_SECRET}"
  token_expiry: 3600

server:
  host: "0.0.0.0"
  web_port: ${WEB_PORT}
  api_port: ${API_PORT}
  workers: 4
  timeout: 300
  max_request_size: "100MB"

database:
  postgresql:
    host: "localhost"
    port: ${POSTGRES_PORT}
    name: "${DB_NAME}"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    pool_size: 20
    max_overflow: 10
  
  redis:
    host: "localhost"
    port: ${REDIS_PORT}
    password: "${REDIS_PASSWORD}"
    db: 0
  
  mongodb:
    host: "localhost"
    port: ${MONGODB_PORT}
    name: "vapt_scans"
    enabled: false

ai:
  model_path: "${INSTALL_DIR}/models"
  training:
    batch_size: 32
    epochs: 100
    learning_rate: 0.001
    validation_split: 0.2
  
  inference:
    confidence_threshold: 0.85
    max_batch_size: 64
    use_gpu: false

scanning:
  threads: 10
  timeout: 30
  max_depth: 5
  rate_limit: 100
  user_agent: "AI-VAPT-Scanner/${VAPT_VERSION}"
  
  nmap:
    flags: "-sS -sV -O -A -T4"
    default_ports: "1-65535"
  
  web:
    max_pages: 1000
    crawl_depth: 3
    form_timeout: 10

reporting:
  formats: ["html", "pdf", "json", "xml"]
  template_dir: "${INSTALL_DIR}/src/web/templates"
  output_dir: "${INSTALL_DIR}/reports"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "${INSTALL_DIR}/logs/vapt.log"
  max_size: "100MB"
  backup_count: 10

security:
  encryption_key: "${SECRET_KEY}"
  allowed_hosts: ["localhost", "127.0.0.1"]
  cors_origins: ["http://localhost:${WEB_PORT}"]
  rate_limiting: true
  max_requests_per_minute: 60

notifications:
  email:
    enabled: false
    smtp_server: ""
    smtp_port: 587
    username: ""
    password: ""
  
  slack:
    enabled: false
    webhook_url: ""
  
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""

integrations:
  shodan:
    api_key: ""
  virustotal:
    api_key: ""
  alienvault:
    api_key: ""
EOF
    
    # Environment file
    cat > "${INSTALL_DIR}/.env" << EOF
# AI-VAPT Tool Environment Variables
APP_ENV=production
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${POSTGRES_PORT}/${DB_NAME}
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:${REDIS_PORT}/0
AI_MODEL_PATH=${INSTALL_DIR}/models
LOG_LEVEL=INFO
EOF
    
    chmod 600 "${CONFIG_FILE}"
    chmod 600 "${INSTALL_DIR}/.env"
    
    log_message "INFO" "Configuration files generated"
}

create_systemd_services() {
    log_message "STEP" "Creating systemd services..."
    
    # Main application service
    cat > /etc/systemd/system/vapt-tool.service << EOF
[Unit]
Description=AI-Powered VAPT Tool
After=network.target postgresql.service ${REDIS_SVC}.service
Requires=postgresql.service ${REDIS_SVC}.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=${INSTALL_DIR}
EnvironmentFile=-${INSTALL_DIR}/.env
ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/vapt_tool.py
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR}/logs/vapt-web.log
StandardError=append:${INSTALL_DIR}/logs/vapt-web-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # API service
    cat > /etc/systemd/system/vapt-api.service << EOF
[Unit]
Description=AI-VAPT API Service
After=network.target postgresql.service ${REDIS_SVC}.service
Requires=postgresql.service ${REDIS_SVC}.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=${INSTALL_DIR}
EnvironmentFile=-${INSTALL_DIR}/.env
ExecStart=${VENV_DIR}/bin/uvicorn vapt_tool:create_app --factory --host 0.0.0.0 --port ${API_PORT} --workers 1
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR}/logs/vapt-api.log
StandardError=append:${INSTALL_DIR}/logs/vapt-api-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Celery worker service
    cat > /etc/systemd/system/vapt-worker.service << EOF
[Unit]
Description=AI-VAPT Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=${INSTALL_DIR}
EnvironmentFile=-${INSTALL_DIR}/.env
ExecStart=${VENV_DIR}/bin/celery -A vapt_tool.celery_app worker -l info -c 4
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR}/logs/vapt-worker.log
StandardError=append:${INSTALL_DIR}/logs/vapt-worker-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Celery beat service
    cat > /etc/systemd/system/vapt-beat.service << EOF
[Unit]
Description=AI-VAPT Celery Beat Scheduler
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=${INSTALL_DIR}
EnvironmentFile=-${INSTALL_DIR}/.env
ExecStart=${VENV_DIR}/bin/python -m celery -A vapt_tool beat -l info
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR}/logs/vapt-beat.log
StandardError=append:${INSTALL_DIR}/logs/vapt-beat-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable vapt-tool.service
    systemctl enable vapt-api.service
    systemctl enable vapt-worker.service
    systemctl enable vapt-beat.service
    
    log_message "INFO" "Systemd services created and enabled"
}

create_nginx_config() {
    log_message "STEP" "Configuring Nginx reverse proxy..."
    
    cat > /etc/nginx/sites-available/vapt-tool << EOF
server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    # Web interface
    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT}/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
    
    # WebSocket support for real-time updates
    location /ws/ {
        proxy_pass http://127.0.0.1:${API_PORT}/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
    
    # Static files
    location /static/ {
        alias ${INSTALL_DIR}/src/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Reports directory
    location /reports/ {
        alias ${INSTALL_DIR}/reports/;
        autoindex off;
        auth_basic "Restricted Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/vapt-tool /etc/nginx/sites-enabled/
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    nginx -t && systemctl reload nginx
    
    log_message "INFO" "Nginx configured successfully"
}

create_backup_script() {
    log_message "STEP" "Creating backup script..."
    
    cat > "${INSTALL_DIR}/scripts/backup.sh" << BACKUPEOF
#!/bin/bash
# VAPT Tool Backup Script

INSTALL_DIR="${INSTALL_DIR}"
BACKUP_DIR="${INSTALL_DIR}/backups"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\${BACKUP_DIR}/vapt_backup_\${TIMESTAMP}.tar.gz"
RETENTION_DAYS=30

echo "Starting backup at \$(date)..."

# Backup database
pg_dump -U vapt_user vapt_tool > "${BACKUP_DIR}/database_${TIMESTAMP}.sql"

# Backup configuration
cp "${INSTALL_DIR}/config/config.yaml" "${BACKUP_DIR}/config_${TIMESTAMP}.yaml"
cp "${INSTALL_DIR}/.env" "${BACKUP_DIR}/env_${TIMESTAMP}.txt"

# Backup models
tar -czf "${BACKUP_DIR}/models_${TIMESTAMP}.tar.gz" "${INSTALL_DIR}/models/"

# Create complete backup
tar -czf "${BACKUP_FILE}" \
    "${BACKUP_DIR}/database_${TIMESTAMP}.sql" \
    "${BACKUP_DIR}/config_${TIMESTAMP}.yaml" \
    "${BACKUP_DIR}/env_${TIMESTAMP}.txt" \
    "${BACKUP_DIR}/models_${TIMESTAMP}.tar.gz"

# Clean up temporary files
rm -f "${BACKUP_DIR}/database_${TIMESTAMP}.sql"
rm -f "${BACKUP_DIR}/config_${TIMESTAMP}.yaml"
rm -f "${BACKUP_DIR}/env_${TIMESTAMP}.txt"
rm -f "${BACKUP_DIR}/models_${TIMESTAMP}.tar.gz"

# Remove old backups
find "${BACKUP_DIR}" -name "vapt_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: ${BACKUP_FILE}"
echo "Backup size: $(du -h ${BACKUP_FILE} | cut -f1)"
BACKUPEOF
    
    chmod +x "${INSTALL_DIR}/scripts/backup.sh"
    
    # Create cron job for daily backup
    (crontab -l 2>/dev/null; echo "0 2 * * * ${INSTALL_DIR}/scripts/backup.sh") | crontab -
    
    log_message "INFO" "Backup script created and scheduled"
}

create_uninstall_script() {
    log_message "STEP" "Creating uninstall script..."
    
    cat > "${INSTALL_DIR}/scripts/uninstall.sh" << UNINSTALLEOF
#!/bin/bash
# VAPT Tool Uninstall Script

INSTALL_DIR="${INSTALL_DIR}"

echo -e "\033[0;31mWARNING: This will completely remove the VAPT Tool and all its data!\033[0m"
echo -e "\033[0;31mThis action cannot be undone.\033[0m"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo "Stopping services..."
systemctl stop vapt-tool vapt-api vapt-worker vapt-beat
systemctl disable vapt-tool vapt-api vapt-worker vapt-beat

echo "Removing service files..."
rm -f /etc/systemd/system/vapt-tool.service
rm -f /etc/systemd/system/vapt-api.service
rm -f /etc/systemd/system/vapt-worker.service
rm -f /etc/systemd/system/vapt-beat.service
systemctl daemon-reload

echo "Removing Nginx configuration..."
rm -f /etc/nginx/sites-enabled/vapt-tool
rm -f /etc/nginx/sites-available/vapt-tool
systemctl reload nginx

echo "Removing cron jobs..."
crontab -l | grep -v "backup.sh" | crontab -

echo "Removing installation directory..."
rm -rf "${INSTALL_DIR}"

echo "Removing database..."
DB_NAME="vapt_tool"
DB_USER="vapt_user"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME};"
sudo -u postgres psql -c "DROP USER IF EXISTS ${DB_USER};"

echo -e "\033[0;32mVAPT Tool has been completely uninstalled.\033[0m"
UNINSTALLEOF
    
    chmod +x "${INSTALL_DIR}/scripts/uninstall.sh"
    
    log_message "INFO" "Uninstall script created"
}

create_cli_wrapper() {
    log_message "STEP" "Creating CLI wrapper..."
    
    cat > /usr/local/bin/vapt << EOF
#!/bin/bash
# VAPT Tool CLI Wrapper

INSTALL_DIR="${INSTALL_DIR}"
VENV_DIR="${VENV_DIR}"

# Activate virtual environment and run command
source "\${VENV_DIR}/bin/activate"
export PYTHONPATH="\${INSTALL_DIR}"
exec python "\${INSTALL_DIR}/vapt_tool.py" "\$@"
EOF
    
    chmod +x /usr/local/bin/vapt
    
    log_message "INFO" "CLI wrapper created at /usr/local/bin/vapt"
}

train_initial_models() {
    log_message "STEP" "Training initial AI models..."
    
    # Generate sample training data
    cat > /tmp/generate_training_data.py << 'PYEOF'
import pandas as pd
import numpy as np
import random

vulnerability_types = ['sql_injection', 'xss', 'command_injection', 'path_traversal', 'normal']
payloads = {
    'sql_injection': ["' OR 1=1 --", "' UNION SELECT NULL--", "admin'--"],
    'xss': ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>'],
    'command_injection': ['; ls -la', '| cat /etc/passwd'],
    'path_traversal': ['../../../etc/passwd', '..\\..\\..\\windows\\win.ini'],
    'normal': ['test', 'hello world', '12345']
}

data = []
for _ in range(1000):
    vuln_type = random.choice(vulnerability_types)
    payload = random.choice(payloads[vuln_type])
    data.append({
        'payload': payload,
        'response_code': random.choice([200, 403, 500]),
        'response_time': random.uniform(0.1, 5.0),
        'response_length': random.randint(100, 5000),
        'open_ports': random.randint(1, 100),
        'ssl_issues': random.randint(0, 5),
        'vulnerability_type': vuln_type
    })

df = pd.DataFrame(data)
df.to_csv('${INSTALL_DIR}/data/raw/training_data.csv', index=False)
print(f"Generated {len(df)} training samples")
PYEOF
    
    # Train models
    cd "${INSTALL_DIR}"
    python "${INSTALL_DIR}/vapt_tool.py" train data/raw/training_data.csv --output-dir models/
    
    log_message "INFO" "Initial AI models trained"
}

setup_firewall() {
    log_message "STEP" "Configuring firewall..."
    
    if command -v ufw &>/dev/null; then
        ufw allow ${WEB_PORT}/tcp
        ufw allow ${API_PORT}/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow ssh
        
        echo "y" | ufw enable
        log_message "INFO" "Firewall configured with UFW"
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=${WEB_PORT}/tcp
        firewall-cmd --permanent --add-port=${API_PORT}/tcp
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --reload
        log_message "INFO" "Firewall configured with firewalld"
    fi
}

display_completion_info() {
    local ip_address=$(hostname -I | awk '{print $1}')
    
    cat << EOF

${GREEN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     Installation Completed Successfully! 🎉                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝${NC}

${BOLD}Quick Start Guide:${NC}

1. ${CYAN}Access Web Interface:${NC}
   http://${ip_address}:${WEB_PORT}
   or
   http://localhost:${WEB_PORT}

2. ${CYAN}API Endpoint:${NC}
   http://${ip_address}:${API_PORT}/docs

3. ${CYAN}Command Line Usage:${NC}
   vapt --help
   vapt scan https://example.com --ai-assist
   vapt train data/training_data.csv

4. ${CYAN}Service Management:${NC}
   systemctl start vapt-tool       # Start web interface
   systemctl stop vapt-tool        # Stop web interface
   systemctl status vapt-tool      # Check status
   journalctl -u vapt-tool -f      # View logs

5. ${CYAN}Backup & Restore:${NC}
   ${INSTALL_DIR}/scripts/backup.sh

6. ${CYAN}Uninstall:${NC}
   ${INSTALL_DIR}/scripts/uninstall.sh

${YELLOW}Important Locations:${NC}
   Installation: ${INSTALL_DIR}
   Configuration: ${CONFIG_FILE}
   Logs: ${INSTALL_DIR}/logs/
   Reports: ${INSTALL_DIR}/reports/
   Models: ${INSTALL_DIR}/models/

${YELLOW}Default Credentials:${NC}
   Database User: ${DB_USER}
   Database Name: ${DB_NAME}
   (Passwords stored in: ${INSTALL_DIR}/.env)

${RED}Security Recommendations:${NC}
   1. Change default passwords
   2. Configure SSL/TLS with: certbot --nginx
   3. Set up authentication in config.yaml
   4. Review firewall rules
   5. Enable 2FA for web interface

${GREEN}Support:${NC}
   Documentation: ${INSTALL_DIR}/docs/
   GitHub Issues: https://github.com/yourusername/vapt-tool/issues
   Community: https://discord.gg/vapt-tool

EOF
}

# =============================================================================
# MAIN INSTALLATION FUNCTION
# =============================================================================

main() {
    # Initialize log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    print_banner
    
    # Pre-installation checks
    check_root
    check_system_requirements
    detect_package_manager
    
    # Confirm installation
    echo -e "${YELLOW}This will install VAPT Tool v${VAPT_VERSION} on your system.${NC}"
    echo -e "${YELLOW}Installation directory: ${INSTALL_DIR}${NC}"
    echo -e "${YELLOW}Required disk space: ~2GB${NC}"
    echo ""
    read -p "Do you want to continue? (y/n): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_message "INFO" "Installation cancelled by user"
        exit 0
    fi
    
    # Optional: Install MongoDB
    read -p "Install MongoDB for additional storage? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        INSTALL_MONGODB="yes"
    else
        INSTALL_MONGODB="no"
    fi
    
    # Record start time
    local start_time=$(date +%s)
    
    # Installation steps
    log_message "INFO" "Starting installation at $(date)"
    
    install_system_dependencies
    setup_python_environment
    setup_directories
    deploy_source_files
    generate_configuration
    setup_database
    create_systemd_services
    create_nginx_config
    create_backup_script
    create_uninstall_script
    create_cli_wrapper
    
    # Train AI models (optional but recommended)
    echo ""
    read -p "Train initial AI models? (recommended, takes ~10 min) (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        train_initial_models
    fi
    
    setup_firewall
    
    # Start services
    log_message "INFO" "Starting services..."
    systemctl start vapt-tool
    systemctl start vapt-api
    systemctl start vapt-worker
    systemctl start vapt-beat
    
    # Calculate installation time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    log_message "INFO" "Installation completed in ${minutes}m ${seconds}s"
    
    # Display completion information
    display_completion_info
    
    # Save installation info
    cat > "${INSTALL_DIR}/.installation_info" << EOF
Installation Date: $(date)
Version: ${VAPT_VERSION}
Duration: ${minutes}m ${seconds}s
OS: ${OS} ${OS_VERSION}
Python: $(python3 --version)
EOF
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

cleanup_on_error() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_message "ERROR" "Installation failed with exit code ${exit_code}"
        log_message "ERROR" "Check log file: ${LOG_FILE}"
        echo -e "${RED}Installation failed! Check ${LOG_FILE} for details.${NC}"
        
        # Ask if user wants to rollback
        read -p "Do you want to rollback the installation? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_message "INFO" "Starting rollback..."
            if [ -f "${INSTALL_DIR}/scripts/uninstall.sh" ]; then
                bash "${INSTALL_DIR}/scripts/uninstall.sh"
            fi
        fi
    fi
    exit $exit_code
}

# Set up error trap
trap cleanup_on_error ERR

# =============================================================================
# EXECUTION
# =============================================================================

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check for command line arguments
    case "${1:-}" in
        --uninstall)
            if [ -f "${INSTALL_DIR}/scripts/uninstall.sh" ]; then
                bash "${INSTALL_DIR}/scripts/uninstall.sh"
            else
                echo "Uninstall script not found. Manual removal may be required."
            fi
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --uninstall    Remove VAPT Tool completely"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Run without options to install VAPT Tool"
            ;;
        *)
            main "$@"
            ;;
    esac
fi

# =============================================================================
# POST-INSTALLATION QUICK REFERENCE
# =============================================================================
# Normal installation:     ./install.sh
# Uninstall:               ./install.sh --uninstall
# Show help:               ./install.sh --help
# Run with sudo:           sudo ./install.sh
#
# Access points:
#   http://YOUR_IP:8000   # Web interface
#   http://YOUR_IP:5000/docs  # API documentation
#
# CLI commands:
#   vapt --version
#   vapt scan https://example.com
#   vapt --help
#   vapt scan http://testphp.vulnweb.com -t web --ai-assist
#
# Service management:
#   systemctl status vapt-tool
#   systemctl status vapt-api vapt-worker vapt-beat
#   journalctl -u vapt-tool -f
#   systemctl start/stop/restart vapt-tool
# =============================================================================
