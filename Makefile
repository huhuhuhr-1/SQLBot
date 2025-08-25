# SQLBot Makefile
.PHONY: help build clean test install docker package dev start stop

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "SQLBot Build System"
	@echo "==================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make build     # Build all components"
	@echo "  make dev       # Start development environment"
	@echo "  make docker    # Build Docker image"
	@echo "  make clean     # Clean build artifacts"

build: ## Build all components (backend, frontend, g2-ssr)
	@echo "📦 Building all components..."
	@./quick_build.sh

backend: ## Build backend only
	@echo "📦 Building backend..."
	@cd backend && uv sync && uv build --wheel -o dist

frontend: ## Build frontend only
	@echo "🎨 Building frontend..."
	@cd frontend && npm ci && npm run build

g2-ssr: ## Install g2-ssr dependencies
	@echo "📊 Installing g2-ssr..."
	@cd g2-ssr && npm ci

docker: ## Build Docker image
	@echo "🐳 Building Docker image..."
	@./quick_build.sh -d

clean: ## Clean build artifacts
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf backend/dist frontend/dist package *.rpm build.log
	@rm -rf backend/.venv
	@rm -rf frontend/node_modules g2-ssr/node_modules
	@echo "✅ Clean completed"

test: ## Run tests
	@echo "🧪 Running tests..."
	@cd backend && uv run pytest

dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	@echo "1. Starting database..."
	@docker-compose up -d sqlbot-db
	@echo "2. Starting backend..."
	@cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
	@echo "3. Starting frontend..."
	@cd frontend && npm run dev &
	@echo "4. Starting g2-ssr..."
	@cd g2-ssr && npm start &
	@echo "✅ Development environment started"
	@echo "   Backend: http://localhost:8000"
	@echo "   Frontend: http://localhost:5173"
	@echo "   g2-ssr: http://localhost:3000"

start: ## Start production services
	@echo "🚀 Starting production services..."
	@./start.sh

deploy: build ## Build and deploy to production directory
	@echo "🚀 Deploying to production..."
	@echo "Production files ready in package/opt/sqlbot/"
	@echo "To deploy:"
	@echo "  sudo cp -r package/opt/sqlbot /opt/"
	@echo "  cd /opt/sqlbot && ./start.sh"

stop: ## Stop all services
	@echo "🛑 Stopping all services..."
	@pkill -f "uvicorn main:app" || true
	@pkill -f "npm run dev" || true
	@pkill -f "npm start" || true
	@docker-compose down || true
	@echo "✅ All services stopped"

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	@cd backend && uv sync
	@cd frontend && npm ci
	@cd g2-ssr && npm ci
	@echo "✅ Dependencies installed"

package: ## Create package (RPM)
	@echo "📦 Creating package..."
	@./quick_build.sh
	@echo "Package created in package/ directory"

logs: ## Show logs
	@echo "📋 Showing logs..."
	@docker-compose logs -f

status: ## Show service status
	@echo "📊 Service Status:"
	@echo "Database: $(shell docker-compose ps sqlbot-db | grep -q Up && echo "✅ Running" || echo "❌ Stopped")"
	@echo "Backend: $(shell pgrep -f "uvicorn main:app" > /dev/null && echo "✅ Running" || echo "❌ Stopped")"
	@echo "Frontend: $(shell pgrep -f "npm run dev" > /dev/null && echo "✅ Running" || echo "❌ Stopped")"
	@echo "g2-ssr: $(shell pgrep -f "npm start" > /dev/null && echo "✅ Running" || echo "❌ Stopped")"

lint: ## Run linting
	@echo "🔍 Running linting..."
	@cd backend && uv run black . --check
	@cd frontend && npm run lint

format: ## Format code
	@echo "🎨 Formatting code..."
	@cd backend && uv run black .
	@cd frontend && npm run format

check: ## Run all checks (lint, test)
	@echo "🔍 Running all checks..."
	@make lint
	@make test