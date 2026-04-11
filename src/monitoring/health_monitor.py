"""
Health Monitor - System health monitoring and diagnostics
CEO: Qwen Code | Created: 2026-04-10

Monitors:
- MT5 connection status
- System resource usage (CPU, RAM, disk)
- Trade execution latency
- Error rates
- DNA Engine status
- Data freshness
"""

import psutil
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class HealthStatus:
    """Represents system health at a point in time"""
    timestamp: datetime
    status: str  # "healthy", "warning", "critical"
    components: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


class HealthMonitor:
    """
    System health monitoring
    
    Provides:
    - Real-time health checks
    - Resource monitoring
    - Component status tracking
    - Issue detection and alerting
    """
    
    def __init__(self):
        self.check_history: List[HealthStatus] = []
        self.max_history = 1000
        
        # Component status
        self.components = {
            'mt5_connection': {'status': 'unknown', 'last_check': None, 'errors': 0},
            'dna_engine': {'status': 'unknown', 'last_check': None, 'errors': 0},
            'strategy_engine': {'status': 'unknown', 'last_check': None, 'errors': 0},
            'risk_manager': {'status': 'unknown', 'last_check': None, 'errors': 0},
            'data_feed': {'status': 'unknown', 'last_check': None, 'errors': 0},
            'database': {'status': 'unknown', 'last_check': None, 'errors': 0},
        }
        
        # Performance metrics
        self.performance_metrics = {
            'trade_execution_ms': [],
            'signal_generation_ms': [],
            'data_fetch_ms': [],
            'error_count': 0,
            'uptime_seconds': 0,
        }
        
        self.start_time = time.time()
        self.last_check_time = None
        
        logger.info("🏥 Health Monitor initialized")
    
    def check_health(self) -> HealthStatus:
        """
        Perform comprehensive health check
        
        Returns:
            HealthStatus: Current health status
        """
        status = HealthStatus(
            timestamp=datetime.now(timezone.utc),
            status="healthy",
            components={},
            issues=[],
            metrics={}
        )
        
        # Check system resources
        self._check_resources(status)
        
        # Check components
        self._check_components(status)
        
        # Check performance
        self._check_performance(status)
        
        # Determine overall status
        if any("CRITICAL" in issue for issue in status.issues):
            status.status = "critical"
        elif any("WARNING" in issue for issue in status.issues):
            status.status = "warning"
        else:
            status.status = "healthy"
        
        # Store in history
        self.check_history.append(status)
        if len(self.check_history) > self.max_history:
            self.check_history.pop(0)
        
        self.last_check_time = status.timestamp
        
        return status
    
    def _check_resources(self, status: HealthStatus):
        """Check system resource usage"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            status.metrics['cpu_percent'] = cpu_percent
            
            if cpu_percent > 90:
                status.issues.append(f"CRITICAL: CPU at {cpu_percent:.1f}%")
            elif cpu_percent > 75:
                status.issues.append(f"WARNING: CPU at {cpu_percent:.1f}%")
            
            # RAM
            ram = psutil.virtual_memory()
            status.metrics['ram_percent'] = ram.percent
            status.metrics['ram_available_gb'] = ram.available / (1024**3)
            
            if ram.percent > 90:
                status.issues.append(f"CRITICAL: RAM at {ram.percent:.1f}%")
            elif ram.percent > 75:
                status.issues.append(f"WARNING: RAM at {ram.percent:.1f}%")
            
            # Disk
            disk = psutil.disk_usage('.')
            status.metrics['disk_percent'] = disk.percent
            
            if disk.percent > 90:
                status.issues.append(f"CRITICAL: Disk at {disk.percent:.1f}%")
            elif disk.percent > 80:
                status.issues.append(f"WARNING: Disk at {disk.percent:.1f}%")
            
        except Exception as e:
            status.issues.append(f"CRITICAL: Resource check failed: {e}")
            logger.error(f"❌ Resource check error: {e}")
    
    def _check_components(self, status: HealthStatus):
        """Check all system components"""
        for component_name, component_data in self.components.items():
            try:
                # Check last update time
                if component_data['last_check']:
                    seconds_ago = (datetime.now(timezone.utc) - component_data['last_check']).total_seconds()
                    
                    # Stale component (>5 min without update)
                    if seconds_ago > 300:
                        status.issues.append(f"CRITICAL: {component_name} stale ({seconds_ago:.0f}s)")
                        component_data['status'] = 'error'
                    elif seconds_ago > 60:
                        status.issues.append(f"WARNING: {component_name} slow ({seconds_ago:.0f}s)")
                        component_data['status'] = 'warning'
                    else:
                        component_data['status'] = 'ok'
                
                # Check error count
                if component_data['errors'] > 10:
                    status.issues.append(f"CRITICAL: {component_name} has {component_data['errors']} errors")
                    component_data['status'] = 'error'
                elif component_data['errors'] > 5:
                    status.issues.append(f"WARNING: {component_name} has {component_data['errors']} errors")
                
                status.components[component_name] = {
                    'status': component_data['status'],
                    'errors': component_data['errors'],
                    'last_check': component_data['last_check'].isoformat() if component_data['last_check'] else None,
                }
                
            except Exception as e:
                status.issues.append(f"CRITICAL: {component_name} check failed: {e}")
                logger.error(f"❌ Component check error ({component_name}): {e}")
    
    def _check_performance(self, status: HealthStatus):
        """Check performance metrics"""
        try:
            # Uptime
            uptime = time.time() - self.start_time
            status.metrics['uptime_hours'] = uptime / 3600
            self.performance_metrics['uptime_seconds'] = uptime
            
            # Trade execution latency
            if self.performance_metrics['trade_execution_ms']:
                avg_exec = sum(self.performance_metrics['trade_execution_ms'][-100:]) / min(100, len(self.performance_metrics['trade_execution_ms']))
                status.metrics['avg_trade_exec_ms'] = avg_exec
                
                if avg_exec > 1000:  # >1 second
                    status.issues.append(f"CRITICAL: Slow trade execution ({avg_exec:.0f}ms)")
                elif avg_exec > 500:
                    status.issues.append(f"WARNING: Trade execution slow ({avg_exec:.0f}ms)")
            
            # Signal generation
            if self.performance_metrics['signal_generation_ms']:
                avg_signal = sum(self.performance_metrics['signal_generation_ms'][-100:]) / min(100, len(self.performance_metrics['signal_generation_ms']))
                status.metrics['avg_signal_ms'] = avg_signal
                
                if avg_signal > 5000:  # >5 seconds
                    status.issues.append(f"CRITICAL: Signal generation slow ({avg_signal:.0f}ms)")
            
            # Error rate
            total_checks = max(1, len(self.check_history))
            error_rate = self.performance_metrics['error_count'] / total_checks
            status.metrics['error_rate'] = error_rate
            
            if error_rate > 0.1:  # >10% errors
                status.issues.append(f"CRITICAL: High error rate ({error_rate*100:.1f}%)")
            elif error_rate > 0.05:
                status.issues.append(f"WARNING: Error rate elevated ({error_rate*100:.1f}%)")
            
        except Exception as e:
            status.issues.append(f"CRITICAL: Performance check failed: {e}")
    
    def update_component(self, component_name: str, status: str = 'ok'):
        """Update component status"""
        if component_name in self.components:
            self.components[component_name]['status'] = status
            self.components[component_name]['last_check'] = datetime.now(timezone.utc)
            
            if status == 'ok':
                self.components[component_name]['errors'] = 0
            else:
                self.components[component_name]['errors'] += 1
    
    def record_metric(self, metric_name: str, value: float):
        """Record a performance metric"""
        if metric_name in self.performance_metrics:
            if isinstance(self.performance_metrics[metric_name], list):
                self.performance_metrics[metric_name].append(value)
                # Keep only last 1000 values
                if len(self.performance_metrics[metric_name]) > 1000:
                    self.performance_metrics[metric_name] = self.performance_metrics[metric_name][-1000:]
            else:
                self.performance_metrics[metric_name] = value
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary"""
        if not self.check_history:
            return {'status': 'unknown', 'message': 'No health checks performed yet'}
        
        latest = self.check_history[-1]
        
        return {
            'status': latest.status,
            'timestamp': latest.timestamp.isoformat(),
            'issues_count': len(latest.issues),
            'issues': latest.issues[-5:],  # Last 5 issues
            'components_ok': sum(1 for c in latest.components.values() if c.get('status') == 'ok'),
            'components_total': len(latest.components),
            'uptime_hours': self.performance_metrics.get('uptime_seconds', 0) / 3600,
            'metrics': latest.metrics,
        }
    
    def get_health_history(self, hours: float = 1.0) -> List[Dict[str, Any]]:
        """Get health history for last N hours"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        history = [
            {
                'timestamp': h.timestamp.isoformat(),
                'status': h.status,
                'issues_count': len(h.issues),
                'metrics': h.metrics,
            }
            for h in self.check_history
            if h.timestamp > cutoff
        ]
        
        return history
