#!/bin/bash
# 在本地 Kubernetes 集群部署 SQLBot 应用的脚本

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
    print_info "Checking prerequisites for local deployment..."
    
    if ! command_exists kubectl; then
        print_error "kubectl is not installed"
        exit 1
    fi
    print_status "kubectl is available"
    
    # Check for local Kubernetes solutions
    local_cluster_available=false
    
    if command_exists minikube; then
        print_status "Minikube is available"
        local_cluster_available=true
    fi
    
    if command_exists kind; then
        print_status "Kind is available"
        local_cluster_available=true
    fi
    
    if command_exists docker && [ -f "/var/run/docker.sock" ]; then
        print_status "Docker is available"
    else
        print_error "Docker is required for local Kubernetes deployment"
        exit 1
    fi
    
    if [ "$local_cluster_available" = false ]; then
        print_error "No local Kubernetes solution found (minikube or kind)"
        print_info "Please install either minikube or kind to create a local cluster"
        print_info "For example: 'minikube start' or 'kind create cluster'"
        exit 1
    fi
}

# Check if cluster is running
check_cluster_status() {
    print_info "Checking cluster status..."
    
    if kubectl cluster-info >/dev/null 2>&1; then
        print_status "Kubernetes cluster is running"
        return 0
    else
        print_warning "Kubernetes cluster is not running"
        return 1
    fi
}

# Start a local cluster if not running
start_local_cluster() {
    print_info "Starting local Kubernetes cluster..."
    
    # Try minikube first
    if command_exists minikube && minikube status >/dev/null 2>&1; then
        if [ "$(minikube status --format='{{.Host}}')" = "Running" ]; then
            print_status "Minikube cluster is already running"
            return 0
        fi
    fi
    
    # Start minikube if available
    if command_exists minikube; then
        print_info "Starting minikube cluster..."
        minikube start --driver=docker
        print_status "Minikube cluster started"
        return 0
    fi
    
    # Try kind if minikube is not available
    if command_exists kind; then
        if kind get clusters | grep -q "kind"; then
            print_status "Kind cluster already exists"
        else
            print_info "Creating kind cluster..."
            kind create cluster
            print_status "Kind cluster created"
        fi
        return 0
    fi
    
    print_error "Could not start local cluster"
    exit 1
}

# Deploy SQLBot application
deploy_sqlbot() {
    print_info "Deploying SQLBot application..."
    
    # Extract the application package
    TEMP_DIR="/tmp/sqlbot-deploy-$(date +%s)"
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Extract the package
    tar -xzf /opt/github/SQLBot/demo/sealos-build/sqlbot-app-v1.0.0.tar.gz
    
    # Apply the configuration to the cluster
    kubectl apply -f sqlbot-app/sqlbot-app.yaml
    
    print_status "SQLBot application deployed to cluster"
    
    # Wait for deployment to be ready
    print_info "Waiting for SQLBot deployment to be ready..."
    
    # Wait for namespace to be created
    kubectl wait --for=condition=ready namespace/sqlbot --timeout=60s || true
    
    # Wait for pods to be ready (with longer timeout for PostgreSQL initialization)
    kubectl wait --for=condition=ready pod -l app=sqlbot -n sqlbot --timeout=600s || print_warning "Timeout waiting for pods, but deployment may still be progressing"
    
    cd /opt/github/SQLBot
    rm -rf "$TEMP_DIR"
    
    print_status "SQLBot deployment completed"
}

# Verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    echo -e "${GREEN}=== Namespaces ===${NC}"
    kubectl get namespaces
    
    echo -e "${GREEN}=== Deployments in sqlbot namespace ===${NC}"
    kubectl get deployments -n sqlbot || echo "No deployments found in sqlbot namespace"
    
    echo -e "${GREEN}=== Pods in sqlbot namespace ===${NC}"
    kubectl get pods -n sqlbot || echo "No pods found in sqlbot namespace"
    
    echo -e "${GREEN}=== Services in sqlbot namespace ===${NC}"
    kubectl get services -n sqlbot || echo "No services found in sqlbot namespace"
    
    # Show pod logs if pods exist
    if kubectl get pods -n sqlbot --no-headers | grep -q .; then
        echo -e "${GREEN}=== Pod Logs ===${NC}"
        SQLBOT_POD=$(kubectl get pods -n sqlbot -l app=sqlbot -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [ -n "$SQLBOT_POD" ]; then
            kubectl logs -n sqlbot "$SQLBOT_POD" || echo "Could not retrieve logs"
        fi
    fi
}

# Display access information
display_access_info() {
    print_info "Access information:"
    
    # For Minikube
    if command_exists minikube && [ "$(minikube status --format='{{.Host}}' 2>/dev/null)" = "Running" ]; then
        MINIKUBE_IP=$(minikube ip)
        echo -e "${GREEN}SQLBot API: http://$MINIKUBE_IP:30000${NC}"
        echo -e "${GREEN}SQLBot UI: http://$MINIKUBE_IP:30001${NC}"
    else
        echo -e "${GREEN}To access NodePort services, use your node IP with the NodePort${NC}"
        echo -e "${GREEN}API: node-ip:30000${NC}"
        echo -e "${GREEN}UI: node-ip:30001${NC}"
    fi
    
    print_info "Note: The first startup may take several minutes as PostgreSQL initializes"
}

# Main function
main() {
    print_info "Deploying SQLBot application to local Kubernetes cluster"
    print_info "======================================================"
    
    check_prerequisites
    
    if ! check_cluster_status; then
        start_local_cluster
    fi
    
    deploy_sqlbot
    verify_deployment
    display_access_info
    
    print_info "Deployment completed! You can now access SQLBot."
    print_info "To check status: kubectl get pods -n sqlbot"
    print_info "To view logs: kubectl logs -n sqlbot -l app=sqlbot"
}

# Execute main function
main "$@"