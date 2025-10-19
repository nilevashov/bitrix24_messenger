#!/bin/bash

# Start all services for Bitrix24 Messenger Connector

set -e

echo "🚀 Starting Bitrix24 Messenger Connector - All Services"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

# Function to start service in background
start_service() {
    local service_name=$1
    local script_path=$2
    
    print_status "Starting $service_name..."
    
    if [ -f "$script_path" ]; then
        # Start service in background
        nohup bash "$script_path" > "logs/${service_name}.log" 2>&1 &
        local pid=$!
        echo $pid > "logs/${service_name}.pid"
        
        # Wait a moment and check if process is still running
        sleep 2
        if kill -0 $pid 2>/dev/null; then
            print_success "$service_name started (PID: $pid)"
        else
            print_error "$service_name failed to start. Check logs/${service_name}.log"
            return 1
        fi
    else
        print_error "Script not found: $script_path"
        return 1
    fi
}

# Function to stop service
stop_service() {
    local service_name=$1
    
    if [ -f "logs/${service_name}.pid" ]; then
        local pid=$(cat "logs/${service_name}.pid")
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping $service_name (PID: $pid)..."
            kill $pid
            rm "logs/${service_name}.pid"
            print_success "$service_name stopped"
        else
            print_warning "$service_name was not running"
            rm "logs/${service_name}.pid"
        fi
    else
        print_warning "$service_name was not running"
    fi
}

# Create logs directory
mkdir -p logs

# Check command line arguments
case "${1:-start}" in
    "start")
        print_status "Starting all services..."
        
        # Start FastAPI application
        start_service "app" "scripts/run-app.sh"
        
        # Wait a moment for app to start
        sleep 3
        
        # Start FastStream router
        start_service "router" "scripts/run-router.sh"
        
        print_success "All services started!"
        echo ""
        print_status "Access points:"
        echo "  🌐 API: http://localhost:8000"
        echo "  📚 Docs: http://localhost:8000/docs"
        echo "  🎛️  Admin: http://localhost:8000/api/v1/admin/"
        echo "  ❤️  Health: http://localhost:8000/health"
        echo "  🐰 RabbitMQ: http://localhost:15672 (guest/guest)"
        echo ""
        print_status "Logs are available in the logs/ directory"
        print_status "To stop all services, run: $0 stop"
        ;;
        
    "stop")
        print_status "Stopping all services..."
        stop_service "router"
        stop_service "app"
        print_success "All services stopped!"
        ;;
        
    "restart")
        print_status "Restarting all services..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    "status")
        print_status "Service status:"
        
        if [ -f "logs/app.pid" ]; then
            local app_pid=$(cat "logs/app.pid")
            if kill -0 $app_pid 2>/dev/null; then
                print_success "App: Running (PID: $app_pid)"
            else
                print_error "App: Not running"
            fi
        else
            print_error "App: Not running"
        fi
        
        if [ -f "logs/router.pid" ]; then
            local router_pid=$(cat "logs/router.pid")
            if kill -0 $router_pid 2>/dev/null; then
                print_success "Router: Running (PID: $router_pid)"
            else
                print_error "Router: Not running"
            fi
        else
            print_error "Router: Not running"
        fi
        ;;
        
    "logs")
        local service=${2:-"app"}
        if [ -f "logs/${service}.log" ]; then
            print_status "Showing logs for $service:"
            tail -f "logs/${service}.log"
        else
            print_error "No logs found for $service"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status"
        echo "  logs    - Show logs (app|router)"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 stop"
        echo "  $0 logs app"
        echo "  $0 logs router"
        exit 1
        ;;
esac
