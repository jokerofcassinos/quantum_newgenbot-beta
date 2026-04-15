"""
Web Dashboard - FastAPI + WebSocket real-time dashboard
CEO: Qwen Code | Created: 2026-04-10

Features:
- Real-time equity curve
- Live positions
- Performance metrics
- Health status
- Trade history
- DNA parameters view
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List
import asyncio
import json
from datetime import datetime, timezone
from loguru import logger

from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.performance_tracker import PerformanceTracker


class DashboardApp:
    """
    Real-time Web Dashboard
    
    Provides:
    - Live equity curve
    - Open positions
    - Performance metrics
    - Health monitoring
    - Trade history
    - DNA parameters
    """
    
    def __init__(self, health_monitor: HealthMonitor, performance_tracker: PerformanceTracker):
        self.app = FastAPI(title="Forex Quantum Bot Dashboard")
        self.health_monitor = health_monitor
        self.performance_tracker = performance_tracker
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Real-time data
        self.current_data = {
            'equity': 100000.0,
            'pnl': 0.0,
            'positions': [],
            'trades_today': 0,
            'health': 'healthy',
        }
        
        self._setup_routes()
        
        logger.info(" Dashboard App initialized")
    
    def _setup_routes(self):
        """Setup all routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Main dashboard page"""
            return self._get_dashboard_html()
        
        @self.app.get("/api/status")
        async def get_status():
            """Get current system status"""
            return {
                'equity': self.current_data['equity'],
                'pnl': self.current_data['pnl'],
                'health': self.current_data['health'],
                'trades_today': self.current_data['trades_today'],
            }
        
        @self.app.get("/api/performance")
        async def get_performance():
            """Get performance statistics"""
            stats = self.performance_tracker.get_current_stats()
            return stats
        
        @self.app.get("/api/health")
        async def get_health():
            """Get system health"""
            return self.health_monitor.get_health_summary()
        
        @self.app.get("/api/equity-curve")
        async def get_equity_curve():
            """Get equity curve data"""
            return self.performance_tracker.get_equity_curve()
        
        @self.app.get("/api/dna")
        async def get_dna():
            """Get current DNA parameters"""
            return {"message": "DNA endpoint - integrate with ConfigManager"}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates"""
            await self._websocket_handler(websocket)
    
    async def _websocket_handler(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                # Send current data every second
                await websocket.send_json(self._get_realtime_data())
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    def _get_realtime_data(self) -> Dict[str, Any]:
        """Get real-time data for WebSocket"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'equity': self.current_data['equity'],
            'pnl': self.current_data['pnl'],
            'health': self.current_data['health'],
            'positions': len(self.current_data['positions']),
            'trades_today': self.current_data['trades_today'],
        }
    
    def update_data(self, data: Dict[str, Any]):
        """Update dashboard data"""
        self.current_data.update(data)
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Forex Quantum Bot - Dashboard</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, sans-serif; 
            background: #0a0e27; 
            color: #f8fafc;
        }
        .header { 
            background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 50%, #0ea5e9 100%);
            padding: 2rem; 
            text-align: center;
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 1.5rem; 
            margin-bottom: 2rem;
        }
        .card { 
            background: rgba(255,255,255,0.05); 
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px; 
            padding: 1.5rem;
        }
        .metric-value { 
            font-size: 2.5rem; 
            font-weight: 700; 
            margin-bottom: 0.5rem;
        }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .neutral { color: #00d4ff; }
        .metric-label { 
            font-size: 0.875rem; 
            color: #94a3b8;
            text-transform: uppercase;
        }
        #chart { height: 400px; margin: 2rem 0; }
        .status-ok { color: #10b981; }
        .status-warning { color: #f59e0b; }
        .status-error { color: #ef4444; }
    </style>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
    <div class="header">
        <h1> FOREX QUANTUM BOT</h1>
        <p>Real-Time Dashboard</p>
    </div>
    
    <div class="container">
        <div class="grid">
            <div class="card">
                <div class="metric-value neutral" id="equity">$100,000</div>
                <div class="metric-label">Current Equity</div>
            </div>
            
            <div class="card">
                <div class="metric-value" id="pnl">$0</div>
                <div class="metric-label">Net P&L</div>
            </div>
            
            <div class="card">
                <div class="metric-value neutral" id="trades">0</div>
                <div class="metric-label">Trades Today</div>
            </div>
            
            <div class="card">
                <div class="metric-value status-ok" id="health">HEALTHY</div>
                <div class="metric-label">System Status</div>
            </div>
        </div>
        
        <div class="card">
            <h2 style="margin-bottom: 1rem;">Equity Curve</h2>
            <div id="chart"></div>
        </div>
    </div>
    
    <script>
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update metrics
            document.getElementById('equity').textContent = 
                '$' + data.equity.toLocaleString('en-US', {minimumFractionDigits: 2});
            
            const pnlEl = document.getElementById('pnl');
            pnlEl.textContent = '$' + data.pnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            pnlEl.className = 'metric-value ' + (data.pnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('trades').textContent = data.trades_today;
            
            const healthEl = document.getElementById('health');
            healthEl.textContent = data.health.toUpperCase();
            healthEl.className = 'metric-value status-' + (data.health === 'healthy' ? 'ok' : data.health === 'warning' ? 'warning' : 'error');
        };
        
        // Load initial chart
        fetch('/api/equity-curve')
            .then(r => r.json())
            .then(data => {
                if (data.length > 0) {
                    Plotly.newPlot('chart', [{
                        x: data.map(d => d.timestamp),
                        y: data.map(d => d.equity),
                        type: 'scatter',
                        mode: 'lines',
                        fill: 'tozeroy',
                        line: {color: '#00d4ff'},
                        fillcolor: 'rgba(0, 212, 255, 0.1)'
                    }], {
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: {color: '#f8fafc'},
                        margin: {t: 20, r: 20, b: 40, l: 60}
                    });
                }
            });
    </script>
</body>
</html>
"""




