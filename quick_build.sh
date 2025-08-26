#!/usr/bin/env bash
set -euo pipefail

# Quick Build Script for SQLBot
# A simplified version of the main build script for quick builds

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
VERSION="1.0.1"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Print header
print_header() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    SQLBot Quick Build                        ║"
    echo "║                        v$VERSION                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if we're in the right directory
check_directory() {
    if [[ ! -d "backend" || ! -d "frontend" ]]; then
        error "Please run this script from the SQLBot root directory"
        exit 1
    fi
}

# Function to check command availability
check_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        warn "$1 not found"
        return 1
    fi
    return 0
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! check_cmd "python3"; then
        missing_tools+=("python3")
    fi
    
    if ! check_cmd "node"; then
        missing_tools+=("node")
    fi
    
    if ! check_cmd "npm"; then
        missing_tools+=("npm")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    log "All prerequisites satisfied"
}

# Function to build backend
build_backend() {
    log "Building backend..."
    
    if check_cmd "uv"; then
        cd backend
        info "Installing dependencies with uv..."
        uv sync
        info "Building wheel..."
        uv build --wheel -o dist
        cd "$ROOT_DIR"
        log "Backend built successfully"
    else
        warn "uv not available, trying with pip..."
        cd backend
        if [[ -f "requirements.txt" ]]; then
            pip install -r requirements.txt
        fi
        python setup.py bdist_wheel
        cd "$ROOT_DIR"
        log "Backend built successfully (with pip)"
    fi
}

# Function to build frontend
build_frontend() {
    log "Building frontend..."
    
    if check_cmd "npm"; then
        cd frontend
        info "Installing dependencies..."
        npm ci --silent || npm install --silent
        info "Building assets..."
        npm run build
        cd "$ROOT_DIR"
        log "Frontend built successfully"
    else
        error "npm not available, cannot build frontend"
        exit 1
    fi
}

# Function to install g2-ssr
install_g2_ssr() {
    log "Installing g2-ssr..."
    
    if check_cmd "npm"; then
        cd g2-ssr
        info "Installing dependencies..."
        npm ci --silent || npm install --silent
        cd "$ROOT_DIR"
        log "g2-ssr installed successfully"
    else
        warn "npm not available, skipping g2-ssr"
    fi
}

# Function to collect build artifacts
collect_artifacts() {
    log "Collecting build artifacts..."
    
    # Create production directory structure
    local PROD_DIR="package/opt/sqlbot"
    mkdir -p "$PROD_DIR"
    
    # Copy backend
    if [[ -d "backend" ]]; then
        info "Copying backend..."
        cp -r backend "$PROD_DIR/app"
        # Remove unnecessary files
        rm -rf "$PROD_DIR/app/.venv" "$PROD_DIR/app/__pycache__" "$PROD_DIR/app/.pytest_cache" 2>/dev/null || true
        log "Backend copied to $PROD_DIR/app"
    fi
    
    # Copy frontend dist
    if [[ -d "frontend/dist" ]]; then
        info "Copying frontend..."
        mkdir -p "$PROD_DIR/app/static"
        cp -r frontend/dist/* "$PROD_DIR/app/static/"
        log "Frontend copied to $PROD_DIR/app/static"
    fi
    
    # Copy g2-ssr
    if [[ -d "g2-ssr" ]]; then
        info "Copying g2-ssr..."
        cp -r g2-ssr "$PROD_DIR/"
        # Remove unnecessary files
        rm -rf "$PROD_DIR/g2-ssr/node_modules" "$PROD_DIR/g2-ssr/package-lock.json" 2>/dev/null || true
        log "g2-ssr copied to $PROD_DIR/g2-ssr"
    fi
    
    # Copy scripts and configs
    info "Copying scripts and configs..."
    cp start.sh "$PROD_DIR/"
    cp docker-compose.yaml "$PROD_DIR/"
    cp -r installer "$PROD_DIR/" 2>/dev/null || true
    
    # Make scripts executable
    chmod +x "$PROD_DIR/start.sh"
    
    log "Build artifacts collected in $PROD_DIR"
}

# Function to build Docker image
build_docker() {
    log "Building Docker image..."
    
    if check_cmd "docker"; then
        info "Building image..."
        export DOCKER_BUILDKIT=1
        docker build -t sqlbot:latest .
        log "Docker image built successfully"
    else
        warn "docker not available, skipping Docker build"
    fi
}

# Function to show build summary
show_summary() {
    echo ""
    echo -e "${GREEN}🎉 Build completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Build artifacts:${NC}"
    if [[ -d "backend/dist" ]]; then
        echo "  • Backend: backend/dist/ (wheel packages)"
    fi
    if [[ -d "frontend/dist" ]]; then
        echo "  • Frontend: frontend/dist/ (static assets)"
    fi
    if [[ -d "g2-ssr/node_modules" ]]; then
        echo "  • g2-ssr: g2-ssr/ (chart rendering service)"
    fi
    if [[ -d "package/opt/sqlbot" ]]; then
        echo "  • Production: package/opt/sqlbot/ (deployment ready)"
    fi
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  • Run: ./start.sh"
    echo "  • Or use Docker: docker run -p 8000:8000 sqlbot:latest"
    echo "  • Or use docker-compose: docker-compose up -d"
    echo "  • Or deploy from package/opt/sqlbot/"
    echo ""
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --docker   Build Docker image automatically"
    echo "  -c, --clean    Clean build artifacts before building"
    echo "  -v, --verbose  Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0              # Interactive build"
    echo "  $0 -d           # Build with Docker"
    echo "  $0 -c -d        # Clean build with Docker"
}

# Function to clean build artifacts
clean_build() {
    log "Cleaning build artifacts..."
    rm -rf backend/dist frontend/dist package *.rpm build.log
    rm -rf backend/.venv
    rm -rf frontend/node_modules g2-ssr/node_modules
    log "Clean completed"
}

# Parse command line arguments
BUILD_DOCKER=false
CLEAN_BUILD=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--docker)
            BUILD_DOCKER=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    # Check directory
    check_directory
    
    # Check prerequisites
    check_prerequisites
    
    # Clean if requested
    if [[ "$CLEAN_BUILD" == true ]]; then
        clean_build
    fi
    
    # Build components
    build_backend
    echo ""
    build_frontend
    echo ""
    install_g2_ssr
    echo ""
    
    # Collect artifacts for production deployment
    collect_artifacts
    echo ""
    
    # Build Docker if requested or interactive
    if [[ "$BUILD_DOCKER" == true ]]; then
        build_docker
    else
        read -p "Do you want to build a Docker image? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            build_docker
        fi
    fi
    
    # Show summary
    show_summary
}

# Run main function
main "$@"
