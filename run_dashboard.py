"""
Run Web Dashboard - Start the real-time dashboard server
CEO: Qwen Code | Created: 2026-04-10

Usage:
    python run_dashboard.py
    
This starts the FastAPI dashboard server on http://localhost:8000
"""

import sys
from pathlib import Path
import uvicorn

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.performance_tracker import PerformanceTracker
from src.dashboard.web_dashboard import DashboardApp

def main():
    """Start dashboard server"""
    print("\n" + "="*80)
    print("🖥️ FOREX QUANTUM BOT - WEB DASHBOARD")
    print("="*80)
    
    # Initialize monitoring
    health_monitor = HealthMonitor()
    performance_tracker = PerformanceTracker(initial_capital=100000.0)
    
    # Create dashboard
    dashboard = DashboardApp(
        health_monitor=health_monitor,
        performance_tracker=performance_tracker,
    )
    
    print("\n📊 Dashboard ready!")
    print("   URL: http://localhost:8000")
    print("   WebSocket: ws://localhost:8000/ws")
    print("\n💡 Open in browser for real-time monitoring")
    print("="*80 + "\n")
    
    # Start server
    uvicorn.run(
        dashboard.app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

if __name__ == "__main__":
    main()
