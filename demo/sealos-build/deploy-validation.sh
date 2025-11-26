#!/bin/bash
# 本地部署验证脚本 - 使用 Sealos 创建完整集群（包含 Kubernetes + SQLBot）

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

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_status "Docker is installed"
    
    if ! command -v sealos &> /dev/null; then
        print_error "Sealos is not installed"
        exit 1
    fi
    print_status "Sealos is installed"
    
    # Check if our Docker image exists
    if ! docker images | grep -q "dataease/sqlbot"; then
        print_info "Building SQLBot Docker image..."
        cd /opt/github/SQLBot
        docker build -t dataease/sqlbot:latest .
        print_status "SQLBot Docker image built"
    else
        print_status "SQLBot Docker image already exists"
    fi
}

# Check if WSL environment
check_wsl_environment() {
    if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
        print_info "WSL environment detected"
        return 0
    else
        print_warning "Not running in WSL, deployment may have compatibility issues"
        return 1
    fi
}

# Deploy using the existing WSL-compatible script
deploy_using_sealos() {
    print_info "Deploying SQLBot using Sealos (creates Kubernetes + SQLBot)..."
    
    # Temporarily rename containerd files (similar to our WSL script)
    print_info "Preparing environment (temporarily renaming containerd files)..."
    
    # Backup and rename containerd binaries
    sudo mv /usr/bin/containerd /usr/bin/containerd.bak 2>/dev/null || true
    sudo mv /usr/bin/ctr /usr/bin/ctr.bak 2>/dev/null || true
    sudo mv /usr/bin/containerd-shim-runc-v2 /usr/bin/containerd-shim-runc-v2.bak 2>/dev/null || true
    sudo systemctl restart docker
    
    print_status "Containerd files renamed, Docker restarted"
    
    # Deploy cluster with SQLBot
    print_info "Deploying Kubernetes cluster with SQLBot..."
    
    # Use sealos to run the Kubernetes cluster and deploy SQLBot
    # For Sealos, we pass all required images as arguments
    if sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 \
               swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 \
               dataease/sqlbot:latest \
               --single; then
        print_status "Kubernetes cluster with SQLBot deployed successfully!"
    else
        print_error "Failed to deploy cluster"
        # Restore containerd files in case of error
        restore_containerd
        exit 1
    fi
}

# Function to restore containerd files
restore_containerd() {
    print_info "Restoring containerd files..."
    
    # Restore original containerd files if they exist
    for file in /usr/bin/containerd /usr/bin/ctr /usr/bin/containerd-shim-runc-v2; do
        if [ -f "${file}.bak" ]; then
            sudo mv "${file}.bak" "$file"
            print_status "Restored $file"
        fi
    done
    
    # Restart Docker service
    sudo systemctl restart docker
    if [ $? -eq 0 ]; then
        print_status "Docker service restarted successfully"
    else
        print_warning "Failed to restart Docker service"
    fi
}

# Verify deployment after cluster is up
verify_deployment() {
    print_info "Waiting for cluster to be ready..."
    
    # Wait a bit for cluster to initialize
    sleep 30
    
    # Check if kubectl is now available
    if command -v kubectl &> /dev/null; then
        print_status "kubectl is available"
        
        echo -e "${GREEN}=== Cluster Nodes ===${NC}"
        kubectl get nodes || echo "Nodes not ready yet"
        
        echo -e "${GREEN}=== SQLBot Pods ===${NC}"
        kubectl get pods -n sqlbot 2>/dev/null || echo "SQLBot namespace may not be created yet"
        
        echo -e "${GREEN}=== SQLBot Services ===${NC}"
        kubectl get services -n sqlbot 2>/dev/null || echo "SQLBot services may not be created yet"
    else
        print_warning "kubectl is not available - cluster may still be initializing"
    fi
}

# Display access information
display_access_info() {
    print_info "Access information:"
    print_info "After deployment completes:"
    echo -e "${GREEN}  - SQLBot API: http://<node-ip>:30000${NC}"
    echo -e "${GREEN}  - SQLBot UI: http://<node-ip>:30001${NC}"
    print_info "Check pods with: kubectl get pods -n sqlbot"
    print_info "Check service with: kubectl get services -n sqlbot"
}

# Main function
main() {
    print_info "Starting local deployment of SQLBot application"
    print_info "==============================================="
    
    check_prerequisites
    check_wsl_environment
    deploy_using_sealos
    restore_containerd  # Restore after deployment is initiated
    verify_deployment
    display_access_info
    
    print_status "Deployment process initiated!"
    print_info "The cluster creation may take 5-10 minutes."
    print_info "You can monitor progress with kubectl commands once the cluster is ready."
}

# Execute main function
main "$@"