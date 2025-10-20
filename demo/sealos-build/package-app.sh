#!/bin/bash
# 创建 SQLBot 应用镜像包的脚本

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker image exists
check_docker_image() {
    if ! docker images | grep -q "dataease/sqlbot"; then
        print_info "Building SQLBot Docker image..."
        cd /opt/github/SQLBot
        docker build -t dataease/sqlbot:latest .
        print_status "SQLBot Docker image built successfully"
    else
        print_status "SQLBot Docker image already exists"
    fi
}

# Create application package
create_app_package() {
    print_info "Creating SQLBot application package..."
    
    # Create a temporary directory for the package
    TEMP_DIR="/tmp/sqlbot-app-package-$(date +%s)"
    mkdir -p "$TEMP_DIR/sqlbot-app"
    
    # Copy the necessary files for the application
    cp /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml "$TEMP_DIR/sqlbot-app/"
    cp /opt/github/SQLBot/demo/sealos-build/Applicationfile "$TEMP_DIR/sqlbot-app/"
    
    # Create a package info file
    cat > "$TEMP_DIR/sqlbot-app/package-info.yaml" << 'EOF'
apiVersion: apps.sealos.io/v1beta1
kind: ApplicationPackage
metadata:
  name: sqlbot-application
  version: 1.0.0
spec:
  name: sqlbot
  description: "SQLBot application with built-in PostgreSQL"
  version: "latest"
  images:
    - dataease/sqlbot:latest
  manifests:
    - sqlbot-app.yaml
EOF
    
    # Create README for the package
    cat > "$TEMP_DIR/sqlbot-app/README.md" << 'EOF'
# SQLBot Application Package

This package contains the SQLBot application with built-in PostgreSQL database.

## Contents
- sqlbot-app.yaml: Kubernetes deployment configuration
- Applicationfile: Sealos application definition

## Usage
To deploy this application to an existing Kubernetes cluster:

```bash
kubectl apply -f sqlbot-app.yaml
```

## Requirements
- Kubernetes cluster (1.25+)
- At least 4GB RAM available
- At least 2 CPU cores available
- Persistent volume support for data storage
EOF
    
    # Create the package archive
    PACKAGE_NAME="sqlbot-app-v1.0.0.tar.gz"
    cd "$TEMP_DIR"
    tar -czf "$PACKAGE_NAME" sqlbot-app
    mv "$PACKAGE_NAME" "/opt/github/SQLBot/demo/sealos-build/"
    
    # Clean up temporary directory
    cd /opt/github/SQLBot
    rm -rf "$TEMP_DIR"
    
    print_status "SQLBot application package created: $PACKAGE_NAME"
}

# Main function
main() {
    print_info "Creating SQLBot application package..."
    
    check_docker_image
    create_app_package
    
    print_info "Application package created successfully in /opt/github/SQLBot/demo/sealos-build/"
    print_info "Package contains only the application, not Kubernetes base components"
}

# Execute main function
main "$@"