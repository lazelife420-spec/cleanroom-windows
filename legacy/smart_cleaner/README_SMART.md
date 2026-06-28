# 🧹 Smart Cleaner - Professional Grade Cleanup System

Archived under `legacy/smart_cleaner/`. Root-level compatibility shims remain
for `smart_config.py`, `smart_scheduler.py`, and `archive_manager.py`.

A comprehensive, intelligent file cleanup system with machine learning, web dashboard, and advanced automation capabilities.

## ✨ Key Features

### 🤖 Smart Intelligence
- **Machine Learning**: Learns your file access patterns and adapts automatically
- **Profile-Based Cleanup**: Pre-configured profiles (Conservative, Aggressive, Gaming)
- **Rules Engine**: Complex IF/THEN conditions for intelligent file filtering
- **Usage Tracking**: Protects frequently accessed files automatically

### 📱 Modern Interface
- **Web Dashboard**: Real-time monitoring at `http://localhost:8080`
- **Interactive Controls**: Browse archives, selective deletion, live statistics
- **Visual Analytics**: Charts showing cleanup trends and space savings
- **Mobile Friendly**: Works on any device with a web browser

### ⚡ Advanced Automation
- **Adaptive Scheduling**: Learns optimal cleanup times based on your patterns
- **System Awareness**: Only runs when computer is idle and disk space is needed
- **Smart Notifications**: Desktop alerts before/after cleanup operations
- **Self-Learning**: Improves scheduling based on success/failure history

### 🛡️ Enterprise Safety
- **Comprehensive Logging**: Full audit trail of all cleanup operations
- **Undo Functionality**: Restore files from archive with one click
- **Multi-Layer Protection**: Prevents accidental deletion of important files
- **Performance Optimized**: Handles millions of files efficiently

## 🚀 Quick Start

### 1. Installation
```bash
# Clone or download the smart_clean_tool directory
cd smart_clean_tool

# Install required dependencies
pip install flask flask-socketio schedule psutil pyyaml send2trash
```

### 2. Initialize Smart Configuration
```bash
python smart_config.py --init
```

### 3. Start the Web Dashboard
```bash
python dashboard.py --start --port 8080
```
Visit `http://localhost:8080` to see the beautiful interface!

### 4. Set Up Automatic Scheduling
```bash
# Add conservative profile to daily schedule at 2 AM
python smart_scheduler.py --add-profile conservative --schedule "daily at 02:00"

# Start the scheduler service
python smart_scheduler.py --start
```

## 📋 Usage Examples

### Basic Cleanup Operations
```bash
# Quick scan (dry run)
python main.py

# Conservative cleanup (safe)
python main.py --profile conservative --apply

# Aggressive cleanup (more thorough)
python main.py --profile aggressive --apply

# Direct deletion (no archive)
python main.py --delete --no-prompt
```

### Archive Management
```bash
# Show archive summary
python main.py --archive summary

# Browse archived files
python main.py --archive browse

# Interactive archive cleanup
python main.py --archive manage
```

### Smart Configuration
```bash
# List available profiles
python smart_config.py --list-profiles

# Show profile details
python smart_config.py --profile conservative

# List all rules
python smart_config.py --list-rules

# View statistics
python smart_config.py --stats

# Get smart suggestions
python smart_config.py --suggestions
```

### Scheduler Management
```bash
# Check scheduler status
python smart_scheduler.py --status

# Add custom schedule
python smart_scheduler.py --add-profile gaming --schedule "daily at 03:00"

# Stop scheduler
python smart_scheduler.py --stop
```

## 🎯 Available Profiles

### Conservative Profile
- **Description**: Safe cleanup for important files
- **Paths**: Downloads, Desktop
- **Rules**: old_temp, zero_byte, browser_cache
- **Schedule**: Weekly
- **Safety**: High - only removes obvious junk

### Aggressive Profile
- **Description**: Maximum cleanup for power users
- **Paths**: Downloads, Desktop, Temp folders
- **Rules**: old_temp, zero_byte, browser_cache, old_installers, large_files
- **Schedule**: Daily
- **Safety**: Medium - removes more files but still safe

### Gaming Profile
- **Description**: Optimized for gaming systems
- **Paths**: Downloads, Temp folders
- **Rules**: old_temp, zero_byte, browser_cache, game_cache
- **Schedule**: Daily
- **Safety**: Medium - focuses on game-related cleanup

## 📜 Rule System

The system uses a sophisticated rules engine with these conditions:

### File Conditions
- `age_days`: File age in days
- `size_min`/`size_max`: File size range (e.g., "10MB", "500MB")
- `paths`: Path patterns (e.g., ["*Temp*", "*cache*"])
- `extensions`: File extensions (e.g., [".tmp", ".log"])
- `exclude_patterns`: Patterns to exclude

### Actions
- `delete`: Permanent deletion (with Recycle Bin fallback)
- `archive`: Move to archive for safekeeping
- `review`: Flag for manual review

### Example Rules
```yaml
old_temp:
  conditions:
    age_days: 7
    paths: ["*Temp*", "*tmp*"]
    size_max: "100MB"
  actions:
    operation: delete
    priority: high

old_installers:
  conditions:
    extensions: [".exe", ".msi", ".zip"]
    age_days: 30
    size_min: "10MB"
  actions:
    operation: archive
    priority: medium
```

## 📊 Web Dashboard Features

### Real-time Monitoring
- **System Status**: CPU, memory, disk usage
- **Cleanup History**: Visual charts of cleanup trends
- **Archive Management**: Browse and delete archived files
- **Activity Logs**: Real-time feed of system activity

### Interactive Controls
- **One-Click Cleanup**: Start cleanup with any profile
- **File Selection**: Select individual files for deletion
- **Progress Tracking**: Watch cleanup progress in real-time
- **Statistics**: Detailed cleanup analytics

## 🧠 Machine Learning Features

### Adaptive Learning
- **File Access Patterns**: Tracks which files you use frequently
- **Deletion Regrets**: Learns from files you restore
- **Optimal Timing**: Finds best times for cleanup based on your usage
- **Smart Protection**: Automatically protects important files

### Usage Tracking
```bash
# Record file access (automatic during normal use)
python smart_config.py --record-access "C:\path\to\important\file.txt"

# Record deletion regret
python smart_config.py --record-regret "C:\path\to\deleted\file.txt"

# View learning suggestions
python smart_config.py --suggestions
```

## 🔧 Advanced Configuration

### Custom Profiles
```python
from smart_config import Profile, CleanupRule, SmartConfig

config = SmartConfig()

# Create custom profile
custom_profile = Profile(
    name='development',
    description='For developers',
    paths=['~/Downloads', '~/Projects', '~/.cache'],
    rules=['old_temp', 'build_artifacts', 'node_modules'],
    schedule='daily'
)

config.add_profile(custom_profile)
```

### Custom Rules
```python
# Create custom rule
custom_rule = CleanupRule(
    name='build_artifacts',
    conditions={
        'paths': ['*build*', '*dist*', '*target*'],
        'extensions': ['.o', '.obj', '.pyc'],
        'age_days': 3
    },
    actions={
        'operation': 'delete',
        'priority': 'medium'
    }
)

config.add_rule(custom_rule)
```

## 📱 Mobile Access

The web dashboard is fully responsive and works on:
- **Desktop browsers**: Chrome, Firefox, Safari, Edge
- **Mobile browsers**: iOS Safari, Android Chrome
- **Tablets**: iPad, Android tablets

## 🔒 Safety Features

### Multi-Layer Protection
1. **Rule-Based Filtering**: Only files matching rules are considered
2. **Smart Learning**: Protects frequently accessed files
3. **Archive First**: Files are archived before deletion
4. **Recycle Bin**: Uses system trash when possible
5. **Confirmation Prompts**: Requires confirmation for large operations

### Recovery Options
```bash
# Restore from archive
python restore.py --log cleanup_log.json --apply

# Interactive archive management
python main.py --archive manage

# Browse before deleting
python main.py --archive browse
```

## 📈 Performance

### Optimized For
- **Large File Sets**: Handles millions of files efficiently
- **Network Drives**: Works with mapped network drives
- **SSD/HDD**: Optimized for both storage types
- **Multi-Core**: Parallel processing when available

### Benchmarks
- **Scan Speed**: ~10,000 files/second
- **Memory Usage**: <50MB for typical operations
- **CPU Impact**: <5% during normal operation
- **Disk I/O**: Optimized for minimal impact

## 🛠️ Troubleshooting

### Common Issues
```bash
# Check configuration
python smart_config.py --stats

# Test scheduler
python smart_scheduler.py --status

# Verify dashboard
python dashboard.py --start --port 8081

# Check logs
tail -f cleanup_log.json
```

### Debug Mode
```bash
# Enable verbose logging
python main.py --profile conservative --apply --verbose

# Test rules without applying
python smart_config.py --test-rule old_temp --path "C:\temp\test.txt"
```

## 📚 API Reference

### Main Commands
- `main.py`: Core cleanup engine
- `smart_config.py`: Configuration and profiles
- `smart_scheduler.py`: Automation and scheduling
- `dashboard.py`: Web interface
- `archive_manager.py`: Archive management
- `restore.py`: File recovery

### Configuration Files
- `smart_config.yaml`: Main configuration
- `scheduler_config.json`: Scheduling settings
- `cleanup_log.json`: Operation history
- `cleanup_plan.json`: Dry-run plans

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Check code style
flake8 *.py
black *.py
```

### Adding New Features
1. Create feature branch
2. Add tests for new functionality
3. Update documentation
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check GitHub issues
4. Create detailed bug reports

---

**Smart Cleaner** - Transform your file cleanup from a chore into an intelligent, automated system that learns and adapts to your needs. 🚀
