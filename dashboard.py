#!/usr/bin/env python3
"""Web dashboard for monitoring and managing smart cleanup operations."""
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

try:
    from flask import Flask, jsonify, request
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

logger = logging.getLogger(__name__)


class Dashboard:
    """Web dashboard for real-time monitoring and control."""

    def __init__(self, port: int = 8080, host: str = 'localhost'):
        self.port = port
        self.host = host
        self.app = None
        self.socketio = None
        self.running = False

        if not FLASK_AVAILABLE:
            logger.error("Flask not available - install with: pip install flask flask-socketio")
            return

        self._setup_app()

    def _setup_app(self):
        """Setup Flask application and routes."""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.environ.get(
            'DASHBOARD_SECRET_KEY', secrets.token_hex(32))
        self.socketio = SocketIO(self.app, cors_allowed_origins=self.host)

        @self.app.route('/')
        def index():
            return self._get_dashboard_html()

        @self.app.route('/api/status')
        def get_status():
            return jsonify(self._get_system_status())

        @self.app.route('/api/history')
        def get_history():
            days = min(request.args.get('days', 7, type=int), 365)
            return jsonify(self._get_cleanup_history(days))

        @self.app.route('/api/archive')
        def get_archive_info():
            return jsonify(self._get_archive_info())

        @self.app.route('/api/stats')
        def get_stats():
            return jsonify(self._get_statistics())

        @self.app.route('/api/run', methods=['POST'])
        def run_cleanup():
            data = request.get_json()
            profile = data.get('profile', 'conservative')
            dry_run = data.get('dry_run', True)

            allowed_profiles = ('conservative', 'moderate', 'aggressive')
            if profile not in allowed_profiles:
                return jsonify({
                    'success': False,
                    'error': f'Invalid profile. Must be one of: {allowed_profiles}'
                }), 400

            try:
                # Execute cleanup
                import subprocess
                cmd = ['python', 'main.py', '--profile', profile]
                if not dry_run:
                    cmd.append('--apply')

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                return jsonify({
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })

        @self.app.route('/api/archive/delete', methods=['POST'])
        def delete_archive_files():
            data = request.get_json()
            files = data.get('files', [])

            try:
                import archive_runtime
                log_file = 'cleanup_log.json'
                archive_dir = Path('cleanup_archive').resolve()

                # Validate each path is within the archive directory
                validated = []
                for file_path in files:
                    resolved = Path(file_path).resolve()
                    if not str(resolved).startswith(str(archive_dir)):
                        return jsonify({
                            'success': False,
                            'error': f'Path outside archive directory: {file_path}'
                        }), 403
                    validated.append(str(resolved))

                records = []
                for file_path in validated:
                    records.append({
                        'dest': file_path,
                        'src': '',
                        'reason': 'manual_delete',
                        'size': 0,
                        'when': datetime.now().isoformat()
                    })

                result = archive_runtime.apply_prune(records, log_file, dry_run=False)

                return jsonify({
                    'success': True,
                    'deleted_count': len(result['pruned']),
                    'bytes_freed': result['bytes_pruned']
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })

        # WebSocket events
        @self.socketio.on('connect')
        def handle_connect():
            emit('status_update', self._get_system_status())

        @self.socketio.on('request_status')
        def handle_status_request():
            emit('status_update', self._get_system_status())

    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>Smart Cleaner Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card { background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { color: #2c3e50; margin-bottom: 1rem; }
        .metric { display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0; }
        .metric-value { font-size: 1.5rem; font-weight: bold; color: #3498db; }
        .btn { background: #3498db; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; cursor: pointer; margin: 0.25rem; }
        .btn:hover { background: #2980b9; }
        .btn.danger { background: #e74c3c; }
        .btn.danger:hover { background: #c0392b; }
        .status { padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem; }
        .status.running { background: #d4edda; color: #155724; }
        .status.idle { background: #f8d7da; color: #721c24; }
        .log { background: #f8f9fa; padding: 1rem; border-radius: 4px; font-family: monospace; font-size: 0.875rem; max-height: 200px; overflow-y: auto; }
        .progress { width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .progress-bar { height: 100%; background: #3498db; transition: width 0.3s ease; }
        .file-list { max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; }
        .file-item { padding: 0.5rem; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .file-item:last-child { border-bottom: none; }
        .checkbox { margin-right: 0.5rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧹 Smart Cleaner Dashboard</h1>
        <p>Real-time monitoring and control</p>
    </div>

    <div class="container">
        <div class="grid">
            <!-- System Status -->
            <div class="card">
                <h3>📊 System Status</h3>
                <div class="metric">
                    <span>Status:</span>
                    <span id="system-status" class="status idle">Idle</span>
                </div>
                <div class="metric">
                    <span>Disk Usage:</span>
                    <span id="disk-usage" class="metric-value">--</span>
                </div>
                <div class="metric">
                    <span>Files Cleaned:</span>
                    <span id="files-cleaned" class="metric-value">--</span>
                </div>
                <div class="metric">
                    <span>Space Freed:</span>
                    <span id="space-freed" class="metric-value">--</span>
                </div>
                <div class="progress">
                    <div id="disk-progress" class="progress-bar" style="width: 0%"></div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="card">
                <h3>⚡ Quick Actions</h3>
                <button class="btn" onclick="runCleanup('conservative', true)">🔍 Quick Scan</button>
                <button class="btn" onclick="runCleanup('conservative', false)">🧹 Conservative Clean</button>
                <button class="btn" onclick="runCleanup('aggressive', false)">⚡ Aggressive Clean</button>
                <button class="btn" onclick="refreshData()">🔄 Refresh</button>
                <div id="action-status" class="log" style="margin-top: 1rem;"></div>
            </div>

            <!-- Archive Management -->
            <div class="card">
                <h3>📦 Archive Management</h3>
                <div class="metric">
                    <span>Archive Size:</span>
                    <span id="archive-size" class="metric-value">--</span>
                </div>
                <div class="metric">
                    <span>Files in Archive:</span>
                    <span id="archive-count" class="metric-value">--</span>
                </div>
                <button class="btn" onclick="loadArchiveFiles()">📋 Browse Files</button>
                <button class="btn danger" onclick="deleteSelectedFiles()">🗑️ Delete Selected</button>
                <div id="archive-files" class="file-list" style="margin-top: 1rem;"></div>
            </div>

            <!-- Cleanup History -->
            <div class="card">
                <h3>📈 Cleanup History</h3>
                <canvas id="history-chart" width="400" height="200"></canvas>
                <div id="history-stats" style="margin-top: 1rem;"></div>
            </div>

            <!-- Recent Activity -->
            <div class="card">
                <h3>🕐 Recent Activity</h3>
                <div id="activity-log" class="log"></div>
            </div>

            <!-- System Health -->
            <div class="card">
                <h3>🏥 System Health</h3>
                <div class="metric">
                    <span>CPU Usage:</span>
                    <span id="cpu-usage" class="metric-value">--</span>
                </div>
                <div class="metric">
                    <span>Memory Usage:</span>
                    <span id="memory-usage" class="metric-value">--</span>
                </div>
                <div class="metric">
                    <span>Uptime:</span>
                    <span id="uptime" class="metric-value">--</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let selectedFiles = [];

        // Socket events
        socket.on('connect', () => {
            console.log('Connected to dashboard');
            refreshData();
        });

        socket.on('status_update', (data) => {
            updateStatus(data);
        });

        // Update functions
        function updateStatus(data) {
            document.getElementById('system-status').textContent = data.status || 'Idle';
            document.getElementById('system-status').className = `status ${data.status === 'running' ? 'running' : 'idle'}`;
            document.getElementById('disk-usage').textContent = data.disk_usage || '--';
            document.getElementById('files-cleaned').textContent = data.files_cleaned || '--';
            document.getElementById('space-freed').textContent = data.space_freed || '--';

            if (data.disk_percent) {
                document.getElementById('disk-progress').style.width = data.disk_percent + '%';
            }

            if (data.system_health) {
                document.getElementById('cpu-usage').textContent = data.system_health.cpu + '%';
                document.getElementById('memory-usage').textContent = data.system_health.memory + '%';
            }
        }

        function refreshData() {
            fetch('/api/status').then(r => r.json()).then(updateStatus);
            loadArchiveInfo();
            loadHistory();
            loadActivity();
        }

        function runCleanup(profile, dryRun) {
            const statusDiv = document.getElementById('action-status');
            statusDiv.textContent = dryRun ? '🔍 Scanning...' : '🧹 Cleaning...';

            fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({profile: profile, dry_run: dryRun})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    statusDiv.textContent = '✅ ' + data.output;
                } else {
                    statusDiv.textContent = '❌ ' + data.error;
                }
                refreshData();
            })
            .catch(err => {
                statusDiv.textContent = '❌ Error: ' + err.message;
            });
        }

        function loadArchiveInfo() {
            fetch('/api/archive').then(r => r.json()).then(data => {
                document.getElementById('archive-size').textContent = formatBytes(data.total_size || 0);
                document.getElementById('archive-count').textContent = data.file_count || 0;
            });
        }

        function loadArchiveFiles() {
            fetch('/api/archive').then(r => r.json()).then(data => {
                const filesDiv = document.getElementById('archive-files');
                filesDiv.innerHTML = '';

                if (data.files && data.files.length > 0) {
                    data.files.slice(0, 20).forEach(file => {
                        const fileDiv = document.createElement('div');
                        fileDiv.className = 'file-item';
                        fileDiv.innerHTML = `
                            <div>
                                <input type="checkbox" class="checkbox" onchange="toggleFile('${file.path}', this.checked)">
                                <span>${file.name}</span>
                            </div>
                            <div>
                                <span>${formatBytes(file.size)}</span>
                                <span style="margin-left: 1rem; color: #666;">${file.age}d ago</span>
                            </div>
                        `;
                        filesDiv.appendChild(fileDiv);
                    });
                } else {
                    filesDiv.innerHTML = '<div style="padding: 1rem; text-align: center; color: #666;">No files in archive</div>';
                }
            });
        }

        function toggleFile(filePath, checked) {
            if (checked) {
                selectedFiles.push(filePath);
            } else {
                selectedFiles = selectedFiles.filter(f => f !== filePath);
            }
        }

        function deleteSelectedFiles() {
            if (selectedFiles.length === 0) {
                alert('No files selected');
                return;
            }

            if (!confirm(`Delete ${selectedFiles.length} selected files? This cannot be undone.`)) {
                return;
            }

            fetch('/api/archive/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({files: selectedFiles})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert(`✅ Deleted ${data.deleted_count} files, freed ${formatBytes(data.bytes_freed)}`);
                    selectedFiles = [];
                    loadArchiveFiles();
                    loadArchiveInfo();
                } else {
                    alert('❌ Error: ' + data.error);
                }
            });
        }

        function loadHistory() {
            fetch('/api/history?days=7').then(r => r.json()).then(data => {
                updateHistoryChart(data);
                updateHistoryStats(data);
            });
        }

        function updateHistoryChart(data) {
            const ctx = document.getElementById('history-chart').getContext('2d');

            const labels = data.map(d => new Date(d.date).toLocaleDateString());
            const filesData = data.map(d => d.files_cleaned);
            const spaceData = data.map(d => d.space_freed / (1024*1024)); // Convert to MB

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Files Cleaned',
                        data: filesData,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y'
                    }, {
                        label: 'Space Freed (MB)',
                        data: spaceData,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left'
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }

        function updateHistoryStats(data) {
            const totalFiles = data.reduce((sum, d) => sum + d.files_cleaned, 0);
            const totalSpace = data.reduce((sum, d) => sum + d.space_freed, 0);

            document.getElementById('history-stats').innerHTML = `
                <div class="metric">
                    <span>7-day Total:</span>
                    <span>${totalFiles} files, ${formatBytes(totalSpace)}</span>
                </div>
            `;
        }

        function loadActivity() {
            // Simulate activity log
            const activities = [
                'System started',
                'Scheduled scan completed',
                'Archive cleanup performed',
                'User logged in'
            ];

            const logDiv = document.getElementById('activity-log');
            logDiv.innerHTML = activities.map(activity =>
                `<div>${new Date().toLocaleTimeString()} - ${activity}</div>`
            ).join('');
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);

        // Initial load
        refreshData();
    </script>
</body>
</html>
        '''

    def _get_system_status(self) -> Dict:
        """Get current system status."""
        try:
            import psutil

            # Get disk usage
            disk_usage = psutil.disk_usage(Path.home().anchor)
            disk_percent = (disk_usage.used / disk_usage.total) * 100

            # Get cleanup statistics
            stats = self._get_statistics()

            return {
                'status': 'running' if self.running else 'idle',
                'disk_usage': f"{disk_percent:.1f}%",
                'disk_percent': disk_percent,
                'files_cleaned': stats.get('total_files_cleaned', 0),
                'space_freed': self._format_bytes(stats.get('total_space_freed', 0)),
                'system_health': {
                    'cpu': psutil.cpu_percent(),
                    'memory': psutil.virtual_memory().percent
                },
                'timestamp': datetime.now().isoformat()
            }
        except ImportError:
            return {
                'status': 'running' if self.running else 'idle',
                'disk_usage': 'N/A',
                'files_cleaned': 0,
                'space_freed': '0 B',
                'timestamp': datetime.now().isoformat()
            }

    def _get_cleanup_history(self, days: int = 7) -> List[Dict]:
        """Get cleanup history for the last N days."""
        history = []
        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            with open('cleanup_log.json', 'r') as f:
                log_data = json.load(f)

            # Group by date
            daily_stats = {}
            for entry in log_data:
                if isinstance(entry, dict) and 'when' in entry:
                    try:
                        date = datetime.fromisoformat(entry['when'].replace('Z', '+00:00')).date()
                        if date >= cutoff_date.date():
                            if date not in daily_stats:
                                daily_stats[date] = {'files_cleaned': 0, 'space_freed': 0}
                            daily_stats[date]['files_cleaned'] += 1
                            daily_stats[date]['space_freed'] += entry.get('size', 0)
                    except (ValueError, KeyError):
                        continue

            # Convert to list
            for date, stats in sorted(daily_stats.items()):
                history.append({
                    'date': date.isoformat(),
                    'files_cleaned': stats['files_cleaned'],
                    'space_freed': stats['space_freed']
                })

        except Exception:
            pass

        return history

    def _get_archive_info(self) -> Dict:
        """Get archive information."""
        try:
            import archive_runtime

            archive_dir = 'cleanup_archive'
            summary = archive_runtime.get_archive_summary(archive_dir)

            # Get file details
            files = archive_runtime.browse_archive(archive_dir, limit=50)

            return {
                'total_size': summary.get('archive_size_mb', 0) * 1024 * 1024,  # Convert to bytes
                'file_count': summary.get('file_count', 0),
                'files': [{
                    'path': f['dest'],
                    'name': Path(f['dest']).name,
                    'size': f['size'],
                    'age': f['age_days']
                } for f in files[:20]]
            }
        except Exception as e:
            logger.error(f"Error getting archive info: {e}")
            return {'total_size': 0, 'file_count': 0, 'files': []}

    def _get_statistics(self) -> Dict:
        """Get overall statistics."""
        stats = {
            'total_files_cleaned': 0,
            'total_space_freed': 0,
            'last_cleanup': None,
            'cleanup_count': 0
        }

        try:
            with open('cleanup_log.json', 'r') as f:
                log_data = json.load(f)

            for entry in log_data:
                if isinstance(entry, dict) and entry.get('action') != 'prune':
                    stats['total_files_cleaned'] += 1
                    stats['total_space_freed'] += entry.get('size', 0)
                    stats['cleanup_count'] += 1

                    if not stats['last_cleanup'] or entry.get('when', '') > stats['last_cleanup']:
                        stats['last_cleanup'] = entry.get('when')

        except Exception:
            pass

        return stats

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"

    def start(self):
        """Start the dashboard server."""
        if not FLASK_AVAILABLE:
            logger.error("Cannot start dashboard - Flask not available")
            return False

        if self.running:
            logger.warning("Dashboard already running")
            return True

        try:
            self.running = True
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
            return True
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            self.running = False
            return False

    def stop(self):
        """Stop the dashboard server."""
        self.running = False
        # Flask-SocketIO doesn't have a clean stop method, but this will stop the loop
        logger.info("Dashboard stopped")


def main():
    """CLI for dashboard management."""
    import argparse

    parser = argparse.ArgumentParser(description='Smart cleaner dashboard')
    parser.add_argument('--start', action='store_true', help='Start dashboard')
    parser.add_argument('--port', type=int, default=8080, help='Port to run on')
    parser.add_argument('--host', default='localhost', help='Host to bind to')

    args = parser.parse_args()

    if args.start:
        dashboard = Dashboard(args.port, args.host)
        print(f"🚀 Starting dashboard on http://{args.host}:{args.port}")
        dashboard.start()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
