#!/usr/bin/env python3
"""Smart scheduling system with adaptive timing and automation."""
import json
import logging
import os
import platform
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import schedule

logger = logging.getLogger(__name__)


class SmartScheduler:
    """Intelligent scheduler that learns optimal cleanup times."""

    def __init__(self, config_path: str = "scheduler_config.json"):
        self.config_path = Path(config_path)
        self.config = {
            'enabled': False,
            'profiles': {},
            'adaptive_timing': True,
            'system_usage_threshold': 80,  # Don't run if CPU > 80%
            'disk_space_threshold': 90,    # Run if disk > 90% full
            'idle_time_required': 300,     # 5 minutes idle
            'learning_data': {
                'successful_runs': [],
                'failed_runs': [],
                'system_load_history': [],
                'user_activity_patterns': {}
            },
            'notifications': {
                'enabled': True,
                'before_run': True,
                'after_run': True,
                'on_error': True
            }
        }
        self.load_config()
        self.running = False
        self.scheduler_thread = None

    def load_config(self):
        """Load scheduler configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except Exception as e:
                logger.error(f"Failed to load scheduler config: {e}")

    def save_config(self):
        """Save scheduler configuration."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler config: {e}")

    def add_profile_schedule(self, profile_name: str, schedule_expression: str,
                           conditions: Dict = None):
        """Add a profile to the schedule.

        Args:
            profile_name: Name of the cleanup profile
            schedule_expression: Cron-like expression (e.g., 'daily at 02:00', 'weekly on monday')
            conditions: Additional conditions for running
        """
        if conditions is None:
            conditions = {}

        self.config['profiles'][profile_name] = {
            'schedule': schedule_expression,
            'conditions': conditions,
            'enabled': True,
            'last_run': None,
            'next_run': None,
            'run_count': 0,
            'success_count': 0
        }
        self.save_config()

    def remove_profile_schedule(self, profile_name: str):
        """Remove a profile from the schedule."""
        if profile_name in self.config['profiles']:
            del self.config['profiles'][profile_name]
            self.save_config()

    def _parse_schedule(self, schedule_expression: str) -> schedule.Job:
        """Parse schedule expression and return schedule job."""
        # Simple parsing - can be extended for more complex expressions
        if 'daily' in schedule_expression.lower():
            if 'at' in schedule_expression.lower():
                time_part = schedule_expression.lower().split('at')[1].strip()
                return schedule.every().day.at(time_part)
            else:
                return schedule.every().day.at("02:00")
        elif 'weekly' in schedule_expression.lower():
            if 'on' in schedule_expression.lower():
                day_part = schedule_expression.lower().split('on')[1].strip()
                day_map = {
                    'monday': schedule.every().monday,
                    'tuesday': schedule.every().tuesday,
                    'wednesday': schedule.every().wednesday,
                    'thursday': schedule.every().thursday,
                    'friday': schedule.every().friday,
                    'saturday': schedule.every().saturday,
                    'sunday': schedule.every().sunday
                }
                day = day_part.split()[0]
                job = day_map.get(day, schedule.every().monday)
                if 'at' in day_part:
                    time_part = day_part.split('at')[1].strip()
                    return job.at(time_part)
                return job.at("02:00")
        elif 'hourly' in schedule_expression.lower():
            return schedule.every().hour
        else:
            # Default to daily at 2 AM
            return schedule.every().day.at("02:00")

    def _check_system_conditions(self) -> bool:
        """Check if system conditions are suitable for cleanup."""
        try:
            # Check system load (simplified)
            if platform.system() == "Windows":
                # Use Windows-specific methods to check CPU usage
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.config['system_usage_threshold']:
                    logger.info(f"System busy (CPU: {cpu_percent}%), skipping cleanup")
                    return False
            else:
                # Unix-like systems
                load_avg = os.getloadavg()[0]
                if load_avg > self.config['system_usage_threshold'] / 20:  # Rough conversion
                    logger.info(f"System busy (load: {load_avg}), skipping cleanup")
                    return False

            # Check disk space
            disk_usage = psutil.disk_usage(Path.home().anchor)
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            if disk_percent < self.config['disk_space_threshold']:
                logger.info(f"Disk space sufficient ({disk_percent:.1f}%), skipping cleanup")
                return False

            # Check idle time (simplified)
            # In a real implementation, you'd use platform-specific idle detection
            return True

        except Exception as e:
            logger.error(f"Error checking system conditions: {e}")
            return True  # Default to running if we can't check

    def _check_user_activity(self) -> bool:
        """Check if user is active based on learned patterns."""
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()

        # Get user activity patterns
        patterns = self.config['learning_data']['user_activity_patterns']

        # If no patterns learned, assume it's okay to run
        if not patterns:
            return True

        # Check if this is typically an active time
        key = f"{current_day}_{current_hour}"
        if key in patterns and patterns[key] > 0.7:  # 70% activity threshold
            logger.info("User typically active at this time, delaying cleanup")
            return False

        return True

    def _run_cleanup_profile(self, profile_name: str):
        """Run cleanup for a specific profile."""
        start_time = datetime.now()

        try:
            # Check conditions
            if profile_name not in self.config['profiles']:
                self._record_run(profile_name, False, "Profile not found")
                return

            if not self._check_system_conditions():
                self._record_run(profile_name, False, "System conditions not met")
                return

            if not self._check_user_activity():
                self._record_run(profile_name, False, "User activity detected")
                return

            # Send notification before run
            if self.config['notifications']['before_run']:
                self._send_notification(f"Starting cleanup: {profile_name}")

            # Run the actual cleanup
            cmd = [
                'python', 'main.py',
                '--config', 'smart_config.yaml',
                '--profile', profile_name,
                '--apply'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout

            success = result.returncode == 0
            message = result.stdout if success else result.stderr

            # Record the run
            self._record_run(profile_name, success, message)

            # Send notification after run
            if self.config['notifications']['after_run']:
                status = "completed" if success else "failed"
                self._send_notification(f"Cleanup {status}: {profile_name}")

            # Update next run time
            if success:
                self._update_next_run(profile_name)

        except subprocess.TimeoutExpired:
            self._record_run(profile_name, False, "Timeout after 1 hour")
            if self.config['notifications']['on_error']:
                self._send_notification(f"Cleanup timeout: {profile_name}")

        except Exception as e:
            self._record_run(profile_name, False, str(e))
            if self.config['notifications']['on_error']:
                self._send_notification(f"Cleanup error: {profile_name} - {e}")

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Cleanup run for {profile_name} completed in {duration:.1f}s")

    def _record_run(self, profile_name: str, success: bool, message: str):
        """Record a cleanup run for learning."""
        run_record = {
            'timestamp': datetime.now().isoformat(),
            'profile': profile_name,
            'success': success,
            'message': message,
            'system_load': self._get_system_load()
        }

        if success:
            self.config['learning_data']['successful_runs'].append(run_record)
            self.config['profiles'][profile_name]['success_count'] += 1
        else:
            self.config['learning_data']['failed_runs'].append(run_record)

        self.config['profiles'][profile_name]['run_count'] += 1
        self.config['profiles'][profile_name]['last_run'] = datetime.now().isoformat()

        # Keep only last 1000 records to prevent bloat
        if len(self.config['learning_data']['successful_runs']) > 1000:
            self.config['learning_data']['successful_runs'] = self.config['learning_data']['successful_runs'][-1000:]
        if len(self.config['learning_data']['failed_runs']) > 1000:
            self.config['learning_data']['failed_runs'] = self.config['learning_data']['failed_runs'][-1000:]

        self.save_config()

    def _get_system_load(self) -> Dict:
        """Get current system load metrics."""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage(Path.home().anchor).percent
            }
        except ImportError:
            return {}

    def _update_next_run(self, profile_name: str):
        """Update next run time based on adaptive learning."""
        if not self.config['adaptive_timing']:
            return

        # Analyze recent runs to find optimal time
        recent_runs = self.config['learning_data']['successful_runs'][-20:]  # Last 20 runs

        if len(recent_runs) < 5:
            return  # Not enough data

        # Find successful run times
        successful_hours = []
        for run in recent_runs:
            if run['profile'] == profile_name:
                hour = datetime.fromisoformat(run['timestamp']).hour
                successful_hours.append(hour)

        if len(successful_hours) < 3:
            return

        # Find the most common successful hour
        from collections import Counter
        hour_counts = Counter(successful_hours)
        best_hour = hour_counts.most_common(1)[0][0]

        # Update schedule to run at the optimal time
        self.config['profiles'][profile_name]['optimal_time'] = f"{best_hour:02d}:00"
        self.save_config()

    def _send_notification(self, message: str):
        """Send system notification."""
        try:
            if platform.system() == "Windows":
                # Use Windows toast notifications
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast("Smart Cleaner", message, duration=5)
            else:
                # Use notify-send on Linux/Mac
                subprocess.run(['notify-send', 'Smart Cleaner', message], check=False)
        except ImportError:
            logger.info(f"Notification: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler started")

        # Schedule all profiles
        for profile_name, profile_config in self.config['profiles'].items():
            if profile_config['enabled']:
                job = self._parse_schedule(profile_config['schedule'])
                job.do(self._run_cleanup_profile, profile_name).tag(profile_name)

        # Run the scheduler
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

        logger.info("Scheduler stopped")

    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.config['enabled'] = True
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.save_config()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler not running")
            return

        self.running = False
        self.config['enabled'] = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        schedule.clear()
        self.save_config()
        logger.info("Scheduler stopped")

    def get_status(self) -> Dict:
        """Get scheduler status and statistics."""
        return {
            'enabled': self.config['enabled'],
            'running': self.running,
            'profiles': self.config['profiles'],
            'successful_runs': len(self.config['learning_data']['successful_runs']),
            'failed_runs': len(self.config['learning_data']['failed_runs']),
            'next_runs': {name: config.get('next_run') for name, config in self.config['profiles'].items()}
        }

    def learn_user_activity(self, active: bool):
        """Record user activity for adaptive scheduling."""
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        key = f"{current_day}_{current_hour}"

        patterns = self.config['learning_data']['user_activity_patterns']
        if key not in patterns:
            patterns[key] = 0.5  # Start neutral

        # Update with exponential moving average
        alpha = 0.1  # Learning rate
        patterns[key] = (1 - alpha) * patterns[key] + alpha * (1.0 if active else 0.0)

        self.save_config()


def main():
    """CLI for scheduler management."""
    import argparse

    parser = argparse.ArgumentParser(description='Smart scheduler')
    parser.add_argument('--start', action='store_true', help='Start scheduler')
    parser.add_argument('--stop', action='store_true', help='Stop scheduler')
    parser.add_argument('--status', action='store_true', help='Show scheduler status')
    parser.add_argument('--add-profile', help='Add profile to schedule')
    parser.add_argument('--schedule', help='Schedule expression (e.g., "daily at 02:00")')
    parser.add_argument('--remove-profile', help='Remove profile from schedule')
    parser.add_argument('--config', default='scheduler_config.json', help='Config file path')

    args = parser.parse_args()

    scheduler = SmartScheduler(args.config)

    if args.start:
        scheduler.start()
        print("✅ Scheduler started")

    elif args.stop:
        scheduler.stop()
        print("✅ Scheduler stopped")

    elif args.status:
        status = scheduler.get_status()
        print("📊 Scheduler Status:")
        print(f"  Enabled: {status['enabled']}")
        print(f"  Running: {status['running']}")
        print(f"  Successful runs: {status['successful_runs']}")
        print(f"  Failed runs: {status['failed_runs']}")
        print("  Profiles:")
        for name, config in status['profiles'].items():
            print(f"    {name}: {config['schedule']} (enabled: {config['enabled']})")

    elif args.add_profile and args.schedule:
        scheduler.add_profile_schedule(args.add_profile, args.schedule)
        print(f"✅ Added {args.add_profile} to schedule: {args.schedule}")

    elif args.remove_profile:
        scheduler.remove_profile_schedule(args.remove_profile)
        print(f"✅ Removed {args.remove_profile} from schedule")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
