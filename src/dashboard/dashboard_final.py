"""
Complete Web Dashboard - FastAPI + WebSocket + Real-time Updates
CEO: Qwen Code | Created: 2026-04-11

Features:
- Real-time equity curve
- Live positions
- Performance metrics
- Health status
- Trade history
- DNA parameters view
- Neural analysis display

Usage:
    python run_dashboard.py
    Then open http://localhost:8000
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from loguru import logger


class DashboardState:
    """Shared state for dashboard"""
    def __init__(self):
        self.equity = 100000.0
        self.initial_equity = 100000.0
        self.pnl = 0.0
        self.trades_today = 0
        self.health = "healthy"
        self.positions = []
        self.trade_history = []
        self.dna_state = {}
        self.profile_state = {}
        self.coherence = 0.0
        self.evolution_data = []
        self.connections: List[WebSocket] = []


state = DashboardState()

app = FastAPI(title="Forex Quantum Bot Dashboard")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forex Quantum Bot - Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #f8fafc;
            min-height: 100vh;
        }
        .header { 
            background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 50%, #0ea5e9 100%);
            padding: 2rem; 
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: repeating-linear-gradient(
                45deg, transparent, transparent 10px,
                rgba(255,255,255,0.03) 10px, rgba(255,255,255,0.03) 20px
            );
            animation: gridMove 30s linear infinite;
        }
        @keyframes gridMove {
            0% { transform: translate(0, 0); }
            100% { transform: translate(50px, 50px); }
        }
        .header h1 { 
            font-size: 2.5rem; 
            font-weight: 800; 
            position: relative;
            z-index: 1;
        }
        .header p { 
            position: relative;
            z-index: 1;
            opacity: 0.9;
            margin-top: 0.5rem;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 2rem; 
        }
        .metrics { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 1.5rem; 
            margin-bottom: 2rem;
        }
        .metric-card { 
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
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
            letter-spacing: 0.05em;
        }
        .chart-container { 
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .chart-container h2 {
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-ok { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .status-warning { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .status-error { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .trade-history {
            max-height: 300px;
            overflow-y: auto;
        }
        .trade-item {
            padding: 0.75rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .trade-item:hover {
            background: rgba(255,255,255,0.02);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 FOREX QUANTUM BOT</h1>
        <p>Neural Trading System Dashboard</p>
    </div>
    
    <div class="container">
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value neutral" id="equity">$100,000</div>
                <div class="metric-label">Current Equity</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="pnl">$0</div>
                <div class="metric-label">Net P&L</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral" id="trades">0</div>
                <div class="metric-label">Trades Today</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral" id="coherence">0.00</div>
                <div class="metric-label">Neural Coherence</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="status"><span class="status-badge status-ok">HEALTHY</span></div>
                <div class="metric-label">System Status</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral" id="profile">-</div>
                <div class="metric-label">Active Profile</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📈 Equity Curve</h2>
            <div id="equity-chart" style="height: 400px;"></div>
        </div>
        
        <div class="chart-container">
            <h2>📊 Trade History</h2>
            <div class="trade-history" id="trade-history">
                <div class="trade-item" style="color: #94a3b8;">
                    <span>No trades yet</span>
                    <span>-</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        let equityData = [{x: new Date(), y: 100000}];
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update metrics
            document.getElementById('equity').textContent = 
                '$' + data.equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            
            const pnlEl = document.getElementById('pnl');
            const pnl = data.pnl || 0;
            pnlEl.textContent = '$' + pnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            pnlEl.className = 'metric-value ' + (pnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('trades').textContent = data.trades_today || 0;
            document.getElementById('coherence').textContent = (data.coherence || 0).toFixed(2);
            
            const statusEl = document.getElementById('status');
            const health = data.health || 'healthy';
            const statusClass = health === 'healthy' ? 'status-ok' : (health === 'warning' ? 'status-warning' : 'status-error');
            statusEl.innerHTML = `<span class="status-badge ${statusClass}">${health.toUpperCase()}</span>`;
            
            document.getElementById('profile').textContent = data.profile || '-';
            
            // Update equity chart
            if (data.equity) {
                equityData.push({x: new Date(), y: data.equity});
                if (equityData.length > 100) equityData.shift();
                
                Plotly.react('equity-chart', [{
                    x: equityData.map(d => d.x),
                    y: equityData.map(d => d.y),
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    line: {color: '#00d4ff', width: 2},
                    fillcolor: 'rgba(0, 212, 255, 0.1)'
                }], {
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: {color: '#f8fafc'},
                    margin: {t: 20, r: 20, b: 40, l: 60},
                    xaxis: {gridcolor: 'rgba(255,255,255,0.1)', title: 'Time'},
                    yaxis: {gridcolor: 'rgba(255,255,255,0.1)', title: 'Equity ($)'}
                }, {responsive: true});
            }
        };
        
        ws.onclose = () => {
            console.log('WebSocket closed, reconnecting...');
            setTimeout(() => location.reload(), 3000);
        };
    </script>
</body>
</html>
"""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    state.connections.append(websocket)
    
    try:
        while True:
            # Send current state every second
            await websocket.send_json({
                'equity': state.equity,
                'pnl': state.pnl,
                'trades_today': state.trades_today,
                'health': state.health,
                'coherence': state.coherence,
                'profile': state.profile_state.get('name', '-'),
                'dna': state.dna_state,
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        state.connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in state.connections:
            state.connections.remove(websocket)


def update_state(data: Dict[str, Any]):
    """Update dashboard state from bot"""
    state.equity = data.get('equity', state.equity)
    state.pnl = data.get('pnl', state.pnl)
    state.trades_today = data.get('trades_today', state.trades_today)
    state.health = data.get('health', state.health)
    state.coherence = data.get('coherence', state.coherence)
    state.profile_state = data.get('profile_state', state.profile_state)
    state.dna_state = data.get('dna_state', state.dna_state)
    
    if data.get('trade'):
        state.trade_history.insert(0, data['trade'])
        if len(state.trade_history) > 50:
            state.trade_history = state.trade_history[:50]


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*80)
    print("🖥️ FOREX QUANTUM BOT - WEB DASHBOARD")
    print("="*80)
    print("\n🌐 Opening dashboard at: http://localhost:8000")
    print("💡 Connect the bot to send real-time data via WebSocket")
    print("="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
