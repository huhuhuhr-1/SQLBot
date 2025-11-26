#!/bin/bash
# 验证 SQLBot 应用包的脚本

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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if command_exists docker; then
        print_status "Docker is available"
        docker_version=$(docker --version)
        print_info "Docker version: $docker_version"
    else
        print_error "Docker is not installed"
        exit 1
    fi
    
    if command_exists kubectl; then
        print_status "kubectl is available"
        kubectl_version=$(kubectl version --client --short 2>/dev/null || echo "unknown")
        print_info "kubectl version: $kubectl_version"
    else
        print_warning "kubectl is not installed (this is OK if you don't plan to use Kubernetes)"
    fi
    
    if command_exists sealos; then
        print_status "Sealos is available"
        sealos_version=$(sealos version 2>/dev/null | grep "gitVersion" || echo "unknown")
        print_info "Sealos version: $sealos_version"
    else
        print_warning "Sealos is not installed (this is OK)"
    fi
}

# Check Docker image
check_docker_image() {
    print_info "Checking Docker image..."
    
    if docker images | grep -q "dataease/sqlbot"; then
        IMAGE_INFO=$(docker images | grep "dataease/sqlbot" | head -1)
        print_status "Docker image exists: $IMAGE_INFO"
    else
        print_error "Docker image 'dataease/sqlbot:latest' does not exist"
        print_info "Please run: docker build -t dataease/sqlbot:latest . in /opt/github/SQLBot"
        return 1
    fi
}

# Check application package
check_app_package() {
    print_info "Checking application package..."
    
    PACKAGE_PATH="/opt/github/SQLBot/demo/sealos-build/sqlbot-app-v1.0.0.tar.gz"
    
    if [ -f "$PACKAGE_PATH" ]; then
        PACKAGE_SIZE=$(du -h "$PACKAGE_PATH" | cut -f1)
        print_status "Application package exists: $PACKAGE_PATH (size: $PACKAGE_SIZE)"
        
        # List package contents
        print_info "Package contents:"
        tar -tzf "$PACKAGE_PATH" | sed 's/^/  - /'
        
        # Check if required files are in the package
        if tar -tzf "$PACKAGE_PATH" | grep -q "sqlbot-app/sqlbot-app.yaml"; then
            print_status "✓ sqlbot-app.yaml found in package"
        else
            print_error "✗ sqlbot-app.yaml NOT found in package"
            return 1
        fi
        
        if tar -tzf "$PACKAGE_PATH" | grep -q "sqlbot-app/Applicationfile"; then
            print_status "✓ Applicationfile found in package"
        else
            print_error "✗ Applicationfile NOT found in package"
            return 1
        fi
    else
        print_error "Application package does not exist: $PACKAGE_PATH"
        return 1
    fi
}

# Validate YAML syntax
validate_yaml_syntax() {
    print_info "Validating YAML syntax..."
    
    YAML_FILE="/opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml"
    
    if command_exists python3; then
        # Check if pyyaml is available
        if python3 -c "import yaml" >/dev/null 2>&1; then
            if python3 -c "import yaml; yaml.safe_load(open('$YAML_FILE'))" 2>/dev/null; then
                print_status "YAML syntax is valid"
            else
                print_error "YAML syntax error in $YAML_FILE"
                return 1
            fi
        else
            print_warning "Python yaml module not available, skipping YAML validation"
        fi
    else
        print_warning "Python3 not available, skipping YAML validation"
    fi
}

# Check if image is referenced correctly in YAML
check_image_reference() {
    print_info "Checking image reference in deployment file..."
    
    if grep -q "dataease/sqlbot:latest" /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml; then
        print_status "✓ Docker image correctly referenced in deployment file"
    else
        print_error "✗ Docker image NOT found in deployment file"
        return 1
    fi
}

# Check PostgreSQL configuration
check_postgres_config() {
    print_info "Checking PostgreSQL configuration..."
    
    if grep -q "POSTGRES_SERVER: \"localhost\"" /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml; then
        print_status "✓ PostgreSQL configuration is correct (internal DB)"
    else
        print_warning "PostgreSQL configuration may need review"
    fi
}

# Print deployment instructions
print_deployment_info() {
    print_info "Deployment instructions:"
    echo -e "${GREEN}  1. To deploy to existing Kubernetes cluster:${NC}"
    echo "     kubectl apply -f /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml"
    echo ""
    echo -e "${GREEN}  2. To deploy using the packaged version:${NC}"
    echo "     tar -xzf /opt/github/SQLBot/demo/sealos-build/sqlbot-app-v1.0.0.tar.gz"
    echo "     kubectl apply -f sqlbot-app/sqlbot-app.yaml"
    echo ""
    echo -e "${GREEN}  3. To verify deployment:${NC}"
    echo "     kubectl get namespaces"
    echo "     kubectl get pods -n sqlbot"
    echo "     kubectl get services -n sqlbot"
}

# Main function
main() {
    print_info "Verifying SQLBot application package..."
    print_info "========================================"
    
    check_prerequisites
    echo ""
    
    check_docker_image
    echo ""
    
    check_app_package
    echo ""
    
    validate_yaml_syntax
    echo ""
    
    check_image_reference
    echo ""
    
    check_postgres_config
    echo ""
    
    print_deployment_info
    echo ""
    
    print_status "Verification completed successfully!"
    print_status "Your SQLBot application package is ready for deployment."
}

# Execute main function
main "$@"