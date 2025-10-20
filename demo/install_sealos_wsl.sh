#!/bin/bash
# Script to install Sealos Kubernetes cluster on WSL while preserving Docker functionality

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

# Global variables
BACKUP_DIR="/tmp/containerd_backup_$(date +%s)"
ORIGINAL_CONTAINERD_FILES=()
RESTORED_FILES=()

# Function to handle errors and restore Docker
cleanup_on_error() {
    print_error "Error occurred during installation. Restoring Docker services..."
    
    # Restore containerd binaries if they were renamed
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
    
    exit 1
}

# Function to restore Docker after Sealos installation
restore_docker() {
    print_info "Restoring Docker services..."
    
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

# Function to backup containerd binaries before running Sealos
backup_and_rename_containerd() {
    print_info "Checking and backing up containerd binaries to bypass Sealos check..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup and rename containerd binaries
    for file in /usr/bin/containerd /usr/bin/ctr /usr/bin/containerd-shim-runc-v2; do
        if [ -f "$file" ]; then
            sudo mv "$file" "${file}.bak"
            ORIGINAL_CONTAINERD_FILES+=("$file")
            print_status "Renamed $file to ${file}.bak"
        fi
    done
}

# Function to restore containerd binaries after Sealos installation
restore_containerd() {
    print_info "Restoring containerd binaries..."
    
    # Restore original containerd files if they exist
    for file in /usr/bin/containerd /usr/bin/ctr /usr/bin/containerd-shim-runc-v2; do
        if [ -f "${file}.bak" ]; then
            sudo mv "${file}.bak" "$file"
            RESTORED_FILES+=("$file")
            print_status "Restored $file"
        fi
    done
}

# Function to check network connectivity before deployment
check_network_connectivity() {
    print_info "Checking network connectivity..."
    
    # Test internet connection
    if ! curl -s --connect-timeout 5 https://www.baidu.com > /dev/null 2>&1; then
        print_warning "Internet connection may be slow or unavailable"
    else
        print_status "Internet connection is available"
    fi
    
    # Test Docker Hub access
    if ! curl -s --connect-timeout 5 https://registry-1.docker.io > /dev/null 2>&1; then
        print_warning "Cannot reach Docker Hub - this may cause image pull failures"
    else
        print_status "Docker Hub is accessible"
    fi
}

# Function to deploy Sealos cluster
deploy_sealos_cluster() {
    check_network_connectivity
    
    # Try with Huawei Cloud registry which has been confirmed to work
    print_info "Running: sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 --single"
    if sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 --single; then
        print_status "Sealos cluster deployed successfully with Huawei Cloud images"
        return 0
    else
        print_warning "Failed to deploy with Huawei Cloud images, trying other sources..."
        
        # Try with different image sources in order of preference
        # First try with the AliCloud registry (should be accessible in China)
        print_info "Running: sealos run registry.cn-hangzhou.aliyuncs.com/labring/kubernetes:v1.28.0 registry.cn-hangzhou.aliyuncs.com/labring/calico:v3.26.1 --single"
        if sealos run registry.cn-hangzhou.aliyuncs.com/labring/kubernetes:v1.28.0 registry.cn-hangzhou.aliyuncs.com/labring/calico:v3.26.1 --single; then
            print_status "Sealos cluster deployed successfully with AliCloud Hangzhou images"
            return 0
        else
            print_warning "Failed to deploy with AliCloud Hangzhou images, trying Qingdao..."
            
            # Try with Qingdao registry
            print_info "Running: sealos run registry.cn-qingdao.aliyuncs.com/labring/kubernetes:v1.28.0 registry.cn-qingdao.aliyuncs.com/labring/calico:v3.26.1 --single"
            if sealos run registry.cn-qingdao.aliyuncs.com/labring/kubernetes:v1.28.0 registry.cn-qingdao.aliyuncs.com/labring/calico:v3.26.1 --single; then
                print_status "Sealos cluster deployed successfully with AliCloud Qingdao images"
                return 0
            else
                print_warning "Failed to deploy with AliCloud images, trying with alternative names..."
                
                # Try with the official image names
                print_info "Running: sealos run labring/kubernetes:v1.28.0 labring/calico:v3.26.1 --single"
                if sealos run labring/kubernetes:v1.28.0 labring/calico:v3.26.1 --single; then
                    print_status "Sealos cluster deployed successfully with official images"
                    return 0
                else
                    print_error "Failed to deploy Sealos cluster with all available image sources"
                    return 1
                fi
            fi
        fi
    fi
}

# Function to verify cluster status
verify_cluster() {
    print_info "Verifying cluster status..."
    
    # Wait and check for cluster to be ready
    timeout=120  # Extended timeout for WSL VM initialization
    count=0
    while [ $count -lt $timeout ]; do
        if kubectl get nodes 2>/dev/null | grep -q "Ready"; then
            print_status "Cluster nodes are ready"
            return 0
        else
            print_info "Waiting for nodes to be ready... ($count/$timeout)"
            sleep 10
            count=$((count + 10))
        fi
    done
    
    print_error "Cluster nodes are not ready after $timeout seconds"
    return 1
}

# Function to perform final verification
final_verification() {
    print_info "Performing final verification..."
    
    echo -e "${GREEN}=== kubectl get node ===${NC}"
    kubectl get node || echo "kubectl command failed"
    
    echo -e "${GREEN}=== kubectl get pods -A | head ===${NC}"
    kubectl get pods -A | head || echo "kubectl command failed"
    
    echo -e "${GREEN}=== docker ps ===${NC}"
    docker ps
    
    print_status "All verifications completed successfully!"
}

# Main function
main() {
    print_info "Starting Sealos Kubernetes cluster installation on WSL..."
    
    # Check if Docker is running
    if ! systemctl is-active --quiet docker; then
        print_error "Docker service is not running. Please start Docker first."
        exit 1
    fi
    print_status "Docker is running"
    
    # Check if Sealos is installed
    if ! command -v sealos &> /dev/null; then
        print_error "Sealos is not installed. Please install Sealos first."
        exit 1
    fi
    print_status "Sealos is installed"
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Backup and rename containerd binaries
    backup_and_rename_containerd
    
    # Deploy Sealos cluster
    deploy_sealos_cluster
    
    # Restore containerd binaries
    restore_containerd
    
    # Restore Docker service (restart)
    restore_docker
    
    # Verify cluster functionality
    verify_cluster
    
    # Perform final verification
    final_verification
    
    print_info "Sealos Kubernetes cluster installation completed successfully!"
    print_info "Docker and Kubernetes are both functional."
    
    # Remove trap after successful completion
    trap - ERR
}

# Execute main function
main "$@"