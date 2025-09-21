# Diagram Generator API Makefile
.PHONY: help install run stop clean test setup-db logs status

# Default target
help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Start the API server"
	@echo "  make stop        - Stop the API server"
	@echo "  make restart     - Restart the API server"
	@echo "  make setup-db    - Setup MySQL database"
	@echo "  make test        - Test the API endpoints"
	@echo "  make logs        - Show server logs"
	@echo "  make status      - Show server status"
	@echo "  make clean       - Clean up processes and temp files"

# Variables
SERVER_HOST = 127.0.0.1
SERVER_PORT = 8080
PID_FILE = server.pid

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Start the server
run:
	@echo "Starting Diagram Generator API server..."
	@if [ -f $(PID_FILE) ]; then \
		echo "Server is already running (PID: $$(cat $(PID_FILE)))"; \
		exit 1; \
	fi
	@export DB_USER=root DB_PASSWORD="your_password_here" DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=diagram_chat && \
	nohup python -m uvicorn app.main:app --host $(SERVER_HOST) --port $(SERVER_PORT) --reload > server.log 2>&1 & \
	echo $$! > $(PID_FILE)
	@sleep 2
	@if ps -p $$(cat $(PID_FILE)) > /dev/null 2>&1; then \
		echo "✅ Server started successfully on http://$(SERVER_HOST):$(SERVER_PORT)"; \
		echo "📋 API Documentation: http://$(SERVER_HOST):$(SERVER_PORT)/docs"; \
		echo "📊 PID: $$(cat $(PID_FILE))"; \
	else \
		echo "❌ Failed to start server. Check server.log for details."; \
		rm -f $(PID_FILE); \
		exit 1; \
	fi

# Stop the server
stop:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "Stopping server (PID: $$PID)..."; \
			kill $$PID; \
			sleep 2; \
			if ps -p $$PID > /dev/null 2>&1; then \
				echo "Force killing server..."; \
				kill -9 $$PID; \
			fi; \
			echo "✅ Server stopped"; \
		else \
			echo "Server process not found"; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "Server is not running (no PID file found)"; \
		pkill -f "uvicorn app.main:app" || true; \
	fi

# Restart the server
restart: stop run

# Setup database
setup-db:
	@echo "Setting up MySQL database..."
	@export DB_USER=root DB_PASSWORD="your_password_here" DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=diagram_chat && \
	python scripts/setup_database.py

# Test the API
test:
	@echo "Testing API endpoints..."
	@echo "Testing health check..."
	@curl -s http://$(SERVER_HOST):$(SERVER_PORT)/docs > /dev/null && echo "✅ Server is responding" || echo "❌ Server is not responding"
	@echo ""
	@echo "Testing basic diagram generation..."
	@curl -s -X POST http://$(SERVER_HOST):$(SERVER_PORT)/query \
		-H 'content-type: application/json' \
		-d '{"prompt": "Simple test system", "diagram_types": ["sequential"]}' | \
		python -m json.tool > /dev/null 2>&1 && echo "✅ Query endpoint working" || echo "❌ Query endpoint failed"
	@echo ""
	@echo "Testing chat endpoint (may fail if DB not available)..."
	@curl -s -X POST http://$(SERVER_HOST):$(SERVER_PORT)/chat/start \
		-H 'content-type: application/json' \
		-d '{"initial_prompt": "Test system", "diagram_types": ["sequential"]}' | \
		python -m json.tool > /dev/null 2>&1 && echo "✅ Chat endpoint working" || echo "⚠️  Chat endpoint not available (database required)"

# Show server logs
logs:
	@if [ -f server.log ]; then \
		echo "📋 Server logs (last 20 lines):"; \
		tail -20 server.log; \
	else \
		echo "No server logs found"; \
	fi

# Show server status
status:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "✅ Server is running"; \
			echo "📊 PID: $$PID"; \
			echo "🌐 URL: http://$(SERVER_HOST):$(SERVER_PORT)"; \
			echo "📋 Docs: http://$(SERVER_HOST):$(SERVER_PORT)/docs"; \
			echo "💾 Memory usage: $$(ps -o rss= -p $$PID | awk '{printf "%.1f MB", $$1/1024}')"; \
		else \
			echo "❌ Server process not found (stale PID file)"; \
			rm -f $(PID_FILE); \
		fi; \
	else \
		echo "⚪ Server is not running"; \
	fi
	@echo ""
	@echo "🔌 Port status:"
	@lsof -i :$(SERVER_PORT) 2>/dev/null || echo "Port $(SERVER_PORT) is free"

# Clean up
clean:
	@echo "Cleaning up..."
	@pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@rm -f $(PID_FILE)
	@rm -f server.log
	@rm -f test_env_vars.txt
	@echo "✅ Cleanup complete"

# Development commands
dev-run:
	@echo "Starting in development mode..."
	@export DB_USER=root DB_PASSWORD="your_password_here" DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=diagram_chat && \
	python -m uvicorn app.main:app --host $(SERVER_HOST) --port $(SERVER_PORT) --reload

# Quick test with sample data
quick-test:
	@echo "Running quick test..."
	@curl -s -X POST http://$(SERVER_HOST):$(SERVER_PORT)/query \
		-H 'content-type: application/json' \
		-d '{"prompt": "SEBI compliance monitoring system", "diagram_types": ["sequential", "component"]}' | \
		python -c "import sys, json; data=json.load(sys.stdin); print('✅ Generated', len(data), 'diagrams'); [print(f'- {k}: {len(v)} characters') for k,v in data.items()]" 2>/dev/null || echo "❌ Test failed"

# Install and setup everything
bootstrap: install setup-db
	@echo "🚀 Bootstrap complete! Run 'make run' to start the server."
