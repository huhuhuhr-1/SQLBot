#!/bin/bash
# SQLBot Sealos 集群部署脚本

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
    
    if ! command -v sealos &> /dev/null; then
        print_error "sealos is not installed"
        exit 1
    fi
    print_status "sealos is installed"
    
    if ! command -v docker &> /dev/null; then
        print_error "docker is not installed"
        exit 1
    fi
    print_status "docker is installed"
    
    # Check if we have the required images
    if ! docker images | grep -q "dataease/sqlbot"; then
        print_info "Building SQLBot Docker image..."
        cd /opt/github/SQLBot
        docker build -t dataease/sqlbot:latest .
        print_status "SQLBot Docker image built successfully"
    fi
}

# Function to deploy SQLBot cluster with WSL compatibility (Full cluster mode)
deploy_sqlbot_full_cluster() {
    print_info "Deploying SQLBot full cluster (Kubernetes + Application) with WSL compatibility..."
    
    # Check if we need to temporarily rename containerd files for WSL
    if systemctl is-active --quiet docker; then
        print_info "Preparing WSL environment (temporarily renaming containerd files)..."
        
        # Backup and rename containerd binaries
        sudo mv /usr/bin/containerd /usr/bin/containerd.bak 2>/dev/null || true
        sudo mv /usr/bin/ctr /usr/bin/ctr.bak 2>/dev/null || true
        sudo mv /usr/bin/containerd-shim-runc-v2 /usr/bin/containerd-shim-runc-v2.bak 2>/dev/null || true
        sudo systemctl restart docker
        
        print_status "Containerd files renamed, Docker restarted"
    fi
    
    # Deploy the cluster using sealos
    print_info "Running sealos to deploy SQLBot cluster with Kubernetes..."
    
    # Use the Clusterfile to deploy with both Kubernetes and SQLBot
    cd /opt/github/SQLBot/sealos-build
    sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 \
               swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 \
               --with-images dataease/sqlbot:latest
    
    if [ $? -eq 0 ]; then
        print_status "SQLBot full cluster deployed successfully!"
    else
        print_error "Failed to deploy SQLBot full cluster"
        
        # Restore containerd files in case of error
        restore_containerd
        exit 1
    fi
}

# Function to deploy only SQLBot application (Application-only mode)
deploy_sqlbot_application_only() {
    print_info "Deploying only SQLBot application to existing Kubernetes cluster..."
    
    # Apply the application manifests directly to existing cluster
    kubectl apply -f /opt/github/SQLBot/sealos-build/sqlbot-app.yaml
    
    print_status "SQLBot application deployed to existing cluster!"
    
    # Wait for application to be ready
    print_info "Waiting for SQLBot application to be ready..."
    kubectl wait --for=condition=ready pod -l app=sqlbot -n sqlbot --timeout=600s
    
    print_status "SQLBot application is ready!"
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

# Function to deploy SQLBot application to existing cluster
deploy_to_existing_cluster() {
    print_info "Deploying SQLBot application to existing cluster..."
    
    # Apply the Kubernetes manifests
    kubectl apply -f /opt/github/SQLBot/sealos-build/sqlbot-k8s.yaml
    
    print_status "SQLBot application deployed to existing cluster"
    
    # Wait for deployments to be ready
    print_info "Waiting for SQLBot deployments to be ready..."
    kubectl wait --for=condition=ready pod -l app=sqlbot -n sqlbot --timeout=600s  # Increased timeout for PostgreSQL initialization
    
    print_status "SQLBot application is ready"
}

# Function to verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    echo -e "${GREEN}=== Namespaces ===${NC}"
    kubectl get namespaces
    
    echo -e "${GREEN}=== Deployments in sqlbot namespace ===${NC}"
    kubectl get deployments -n sqlbot
    
    echo -e "${GREEN}=== Pods in sqlbot namespace ===${NC}"
    kubectl get pods -n sqlbot
    
    echo -e "${GREEN}=== Services in sqlbot namespace ===${NC}"
    kubectl get services -n sqlbot
    
    echo -e "${GREEN}=== PVCs in sqlbot namespace ===${NC}"
    kubectl get pvc -n sqlbot
}

# Function to display access information
display_access_info() {
    print_info "Access information:"
    echo -e "${GREEN}SQLBot API: http://<node-ip>:30000${NC}"
    echo -e "${GREEN}SQLBot UI: http://<node-ip>:30001${NC}"
    echo -e "${GREEN}You can access the application via Ingress at: http://sqlbot.local${NC}"
    echo -e "${GREEN}Make sure to add sqlbot.local to your /etc/hosts file pointing to your node IP${NC}"
}

# Main function
main() {
    print_info "Starting SQLBot Sealos Deployment"
    
    # Parse command line arguments
    case "${1:-app}" in
        "new"|"full")
            print_info "Deploying full SQLBot cluster (Kubernetes + Application)..."
            check_prerequisites
            deploy_sqlbot_full_cluster
            # Restore containerd after deployment
            restore_containerd
            verify_deployment
            display_access_info
            ;;
        "app"|"application")
            print_info "Deploying only SQLBot application to existing cluster..."
            check_prerequisites
            deploy_sqlbot_application_only
            verify_deployment
            display_access_info
            ;;
        "existing")
            print_info "Deploying SQLBot application to existing cluster..."
            check_prerequisites
            deploy_to_existing_cluster
            verify_deployment
            display_access_info
            ;;
        "verify")
            verify_deployment
            display_access_info
            ;;
        *)
            print_error "Usage: $0 [full|app|existing|verify]"
            print_info "  full|new: Deploy full cluster with Kubernetes + SQLBot"
            print_info "  app|application: Deploy only SQLBot application to existing cluster (default)"
            print_info "  existing: Deploy SQLBot to existing cluster (legacy)"
            print_info "  verify: Verify existing deployment"
            exit 1
            ;;
    esac
    
    print_info "SQLBot deployment completed!"
}

# Execute main function
main "$@"