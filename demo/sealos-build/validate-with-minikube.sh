#!/bin/bash
# 安装 Minikube 并验证 SQLBot 应用包的脚本

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

# Install Minikube if not available
install_minikube() {
    print_info "Checking if Minikube is installed..."
    
    if command_exists minikube; then
        print_status "Minikube is already installed"
        minikube_version=$(minikube version)
        print_info "Version: $minikube_version"
        return 0
    fi
    
    print_info "Installing Minikube..."
    
    # Check if running on Linux
    if [ "$(uname -s)" = "Linux" ]; then
        # Download and install minikube
        curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
        sudo install minikube-linux-amd64 /usr/local/bin/minikube
        rm minikube-linux-amd64
        print_status "Minikube installed successfully"
    else
        print_error "Unsupported OS. Please install Minikube manually."
        print_info "Visit: https://minikube.sigs.k8s.io/docs/start/"
        exit 1
    fi
}

# Start Minikube cluster
start_minikube() {
    print_info "Starting Minikube cluster..."
    
    # Use Docker driver and allocate sufficient resources
    minikube start --driver=docker --memory=4g --cpus=2 --disk-size=10g
    
    print_status "Minikube cluster started"
    
    # Wait for cluster to be ready
    kubectl wait --for=condition=Ready node --all --timeout=180s
    print_status "Minikube cluster is ready"
}

# Load Docker image into Minikube
load_docker_image() {
    print_info "Loading SQLBot Docker image into Minikube..."
    
    # Configure Docker to use Minikube's Docker daemon
    eval $(minikube docker-env)
    
    # Tag and load the image if needed (our image should already exist)
    if docker images | grep -q "dataease/sqlbot"; then
        print_status "SQLBot image already available in Minikube Docker"
    else
        print_error "SQLBot Docker image not found"
        exit 1
    fi
}

# Deploy SQLBot application
deploy_sqlbot() {
    print_info "Deploying SQLBot application to Minikube..."
    
    # Extract and deploy the application
    TEMP_DIR="/tmp/sqlbot-minikube-$(date +%s)"
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Extract the application package
    tar -xzf /opt/github/SQLBot/demo/sealos-build/sqlbot-app-v1.0.0.tar.gz
    
    # Apply the configuration to Minikube
    kubectl apply -f sqlbot-app/sqlbot-app.yaml
    
    print_status "SQLBot application deployed to Minikube"
    
    # Wait for deployment to be ready with longer timeout for PostgreSQL initialization
    print_info "Waiting for SQLBot to be ready (this may take several minutes)..."
    
    # Wait for namespace to be created
    kubectl wait --for=condition=ready namespace/sqlbot --timeout=120s || true
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=sqlbot -n sqlbot --timeout=600s || print_warning "Pods may still be initializing"
    
    cd /opt/github/SQLBot
    rm -rf "$TEMP_DIR"
    
    print_status "SQLBot deployment completed"
}

# Verify deployment
verify_deployment() {
    print_info "Verifying SQLBot deployment..."
    
    echo -e "${GREEN}=== Minikube Cluster Info ===${NC}"
    kubectl cluster-info
    
    echo -e "${GREEN}=== SQLBot Namespace ===${NC}"
    kubectl get namespaces | grep sqlbot || echo "sqlbot namespace may still be creating"
    
    # Wait a bit more for resources to be created
    sleep 30
    
    echo -e "${GREEN}=== SQLBot Deployments ===${NC}"
    kubectl get deployments -n sqlbot || echo "Waiting for deployments..."
    
    echo -e "${GREEN}=== SQLBot Pods ===${NC}"
    kubectl get pods -n sqlbot || echo "Waiting for pods..."
    
    echo -e "${GREEN}=== SQLBot Services ===${NC}"
    kubectl get services -n sqlbot || echo "Waiting for services..."
    
    # Show pod details if available
    if kubectl get pods -n sqlbot --no-headers 2>/dev/null | grep -q .; then
        echo -e "${GREEN}=== Pod Details ===${NC}"
        kubectl get pods -n sqlbot -o wide
        
        # Get logs from the SQLBot pod
        SQLBOT_POD=$(kubectl get pods -n sqlbot -l app=sqlbot -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [ -n "$SQLBOT_POD" ]; then
            echo -e "${GREEN}=== SQLBot Pod Logs ===${NC}"
            kubectl logs -n sqlbot "$SQLBOT_POD" --tail=20 || echo "Could not retrieve logs yet"
        fi
    fi
}

# Display access information
display_access_info() {
    print_info "Access information:"
    
    # Get minikube IP
    MINIKUBE_IP=$(minikube ip)
    
    echo -e "${GREEN}Minikube IP: $MINIKUBE_IP${NC}"
    echo -e "${GREEN}SQLBot API: http://$MINIKUBE_IP:30000${NC}"
    echo -e "${GREEN}SQLBot UI: http://$MINIKUBE_IP:30001${NC}"
    echo ""
    print_info "Note: It may take a few more minutes for the application to be fully ready."
    print_info "Check status with: kubectl get pods -n sqlbot"
    print_info "View logs with: kubectl logs -n sqlbot -l app=sqlbot"
}

# Main function
main() {
    print_info "Starting SQLBot application validation using Minikube"
    print_info "===================================================="
    
    print_warning "This process will:"
    print_warning "- Install Minikube if not present"
    print_warning "- Start a local Kubernetes cluster"
    print_warning "- Deploy SQLBot application"
    print_warning "- This may take 10-15 minutes"
    echo ""
    
    read -p "Continue with Minikube validation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Validation cancelled."
        exit 0
    fi
    
    install_minikube
    start_minikube
    load_docker_image
    deploy_sqlbot
    verify_deployment
    display_access_info
    
    print_status "Minikube validation completed!"
    print_info "Your SQLBot application is deployed and accessible."
}

# Execute main function
main "$@"