#!/bin/bash

# SQLBot Production Startup Script
# This script starts all SQLBot services in production environment

# Set paths - check if running from package directory or source
if [[ -d "/opt/sqlbot" ]]; then
    # Production environment
    BASE_DIR="/opt/sqlbot"
    SSR_PATH="$BASE_DIR/g2-ssr"
    APP_PATH="$BASE_DIR/app"
elif [[ -d "package/opt/sqlbot" ]]; then
    # Local package build
    BASE_DIR="package/opt/sqlbot"
    SSR_PATH="$BASE_DIR/g2-ssr"
    APP_PATH="$BASE_DIR/app"
else
    # Development environment
    BASE_DIR="."
    SSR_PATH="g2-ssr"
    APP_PATH="backend"
fi

echo "Starting SQLBot services..."
echo "Base directory: $BASE_DIR"
echo "SSR path: $SSR_PATH"
echo "App path: $APP_PATH"

# Function to check if a service is already running
is_service_running() {
    local port=$1
    lsof -i :$port >/dev/null 2>&1
}

# Function to start g2-ssr service
start_g2_ssr() {
    if [[ ! -d "$SSR_PATH" ]]; then
        echo "Warning: g2-ssr directory not found at $SSR_PATH"
        return 1
    fi
    
    if is_service_running 3000; then
        echo "g2-ssr service already running on port 3000"
        return 0
    fi
    
    echo "Starting g2-ssr service..."
    cd "$SSR_PATH"
    
    # Install dependencies if node_modules doesn't exist
    if [[ ! -d "node_modules" ]]; then
        echo "Installing g2-ssr dependencies..."
        npm install --silent
    fi
    
    # Start the service
    nohup node app.js > g2-ssr.log 2>&1 &
    echo "g2-ssr service started (PID: $!)"
    cd - >/dev/null
}

# Function to start MCP service
start_mcp() {
    if is_service_running 8001; then
        echo "MCP service already running on port 8001"
        return 0
    fi
    
    echo "Starting MCP service..."
    cd "$APP_PATH"
    
    # Check if virtual environment exists
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # Start MCP service
    nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 > mcp.log 2>&1 &
    echo "MCP service started (PID: $!)"
    cd - >/dev/null
}

# Function to start main application
start_main_app() {
    if is_service_running 8000; then
        echo "Main application already running on port 8000"
        return 0
    fi
    
    echo "Starting main application..."
    cd "$APP_PATH"
    
    # Check if virtual environment exists
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # Start main application
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
}

# Main execution
main() {
    echo "=== SQLBot Production Startup ==="
    echo "Starting services..."
    echo ""
    
    # Start g2-ssr service
    start_g2_ssr
    sleep 2
    
    # Start MCP service
    start_mcp
    sleep 2
    
    # Start main application (this will block)
    echo ""
    echo "Starting main application (this will block)..."
    start_main_app
}

# Run main function
main "$@"
