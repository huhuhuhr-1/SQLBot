#!/bin/bash
# Sealos Demo Application Deployment Script

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
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    print_status "kubectl is installed"
    
    if ! command -v docker &> /dev/null; then
        print_error "docker is not installed"
        exit 1
    fi
    print_status "docker is installed"
    
    # Check if demo-app image exists
    if ! docker images | grep -q "demo-app"; then
        print_info "Building demo-app image..."
        cd /opt/github/SQLBot/demo-app
        docker build -t demo-app:1.0 .
        print_status "demo-app image built"
    fi
}

# Function to deploy demo application
deploy_demo_app() {
    print_info "Deploying demo application..."
    
    # Deploy the application using the manifest
    kubectl apply -f /opt/github/SQLBot/sealos-demo/manifests/demo-app.yaml
    
    print_status "Demo application deployed"
    
    # Wait for the deployment to be ready
    print_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=ready pod -l app=demo-app --timeout=180s
    
    print_status "Demo application is ready"
}

# Function to verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    echo -e "${GREEN}=== Deployments ===${NC}"
    kubectl get deployments
    
    echo -e "${GREEN}=== Pods ===${NC}"
    kubectl get pods
    
    echo -e "${GREEN}=== Services ===${NC}"
    kubectl get services
    
    # Get pod logs
    POD_NAME=$(kubectl get pods -l app=demo-app -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$POD_NAME" ]; then
        print_info "Getting logs from $POD_NAME"
        kubectl logs $POD_NAME
    fi
}

# Main function
main() {
    print_info "Starting Sealos Demo Application Deployment"
    
    check_prerequisites
    deploy_demo_app
    verify_deployment
    
    print_info "Demo application deployment completed successfully!"
    print_info "To access the application, you can use port forwarding:"
    print_info "kubectl port-forward service/demo-app-service 8080:80"
}

# Execute main function
main "$@"