#!/usr/bin/env python3
"""Advanced configuration system with profiles, rules engine, and learning."""
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CleanupRule:
    """Individual cleanup rule with conditions and actions."""
    name: str
    enabled: bool = True
    conditions: Dict[str, Any] = None
    actions: Dict[str, Any] = None
    priority: int = 0
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}
        if self.actions is None:
            self.actions = {}


@dataclass
class Profile:
    """Cleanup profile for different use cases."""
    name: str
    description: str
    paths: List[str]
    rules: List[str]  # Rule names
    schedule: Optional[str] = None
    enabled: bool = True


@dataclass
class LearningData:
    """Machine learning data for adaptive cleanup."""
    file_access_patterns: Dict[str, int] = None
    deletion_regrets: List[str] = None
    user_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.file_access_patterns is None:
            self.file_access_patterns = {}
        if self.deletion_regrets is None:
            self.deletion_regrets = []
        if self.user_preferences is None:
            self.user_preferences = {}


class SmartConfig:
    """Advanced configuration manager with profiles and rules engine."""
    
    def __init__(self, config_path: str = "smart_config.yaml"):
        self.config_path = Path(config_path)
        self.data = {
            'version': '2.0',
            'profiles': {},
            'rules': {},
            'learning': {},
            'global_settings': {},
            'last_updated': datetime.now().isoformat()
        }
        self.load()
        self._ensure_default_profiles()
        self._ensure_default_rules()
    
    def _ensure_default_profiles(self):
        """Create default profiles if none exist."""
        if not self.data['profiles']:
            self.data['profiles'] = {
                'conservative': Profile(
                    name='conservative',
                    description='Safe cleanup for important files',
                    paths=['~/Downloads', '~/Desktop'],
                    rules=['old_temp', 'zero_byte', 'browser_cache'],
                    schedule='weekly'
                ),
                'aggressive': Profile(
                    name='aggressive', 
                    description='Maximum cleanup for power users',
                    paths=['~/Downloads', '~/Desktop', '~/AppData/Local/Temp'],
                    rules=['old_temp', 'zero_byte', 'browser_cache', 'old_installers', 'large_files'],
                    schedule='daily'
                ),
                'gaming': Profile(
                    name='gaming',
                    description='Optimized for gaming systems',
                    paths=['~/Downloads', '~/AppData/Local/Temp'],
                    rules=['old_temp', 'zero_byte', 'browser_cache', 'game_cache'],
                    schedule='daily'
                )
            }
    
    def _ensure_default_rules(self):
        """Create default rules if none exist."""
        if not self.data['rules']:
            self.data['rules'] = {
                'old_temp': CleanupRule(
                    name='old_temp',
                    conditions={
                        'age_days': 7,
                        'paths': ['*Temp*', '*tmp*'],
                        'size_max': '100MB'
                    },
                    actions={
                        'operation': 'delete',
                        'priority': 'high'
                    }
                ),
                'zero_byte': CleanupRule(
                    name='zero_byte',
                    conditions={
                        'size_exact': 0,
                        'exclude_patterns': ['*.gitkeep', '*.keep']
                    },
                    actions={
                        'operation': 'delete',
                        'priority': 'high'
                    }
                ),
                'browser_cache': CleanupRule(
                    name='browser_cache',
                    conditions={
                        'paths': ['*Cache*', '*cache*'],
                        'extensions': ['.tmp', '.cache'],
                        'age_days': 3
                    },
                    actions={
                        'operation': 'delete',
                        'priority': 'medium'
                    }
                ),
                'old_installers': CleanupRule(
                    name='old_installers',
                    conditions={
                        'extensions': ['.exe', '.msi', '.zip'],
                        'age_days': 30,
                        'size_min': '10MB'
                    },
                    actions={
                        'operation': 'archive',
                        'priority': 'medium'
                    }
                ),
                'large_files': CleanupRule(
                    name='large_files',
                    conditions={
                        'size_min': '500MB',
                        'age_days': 14,
                        'exclude_patterns': ['*.iso', '*.backup']
                    },
                    actions={
                        'operation': 'review',
                        'priority': 'low'
                    }
                ),
                'game_cache': CleanupRule(
                    name='game_cache',
                    conditions={
                        'paths': ['*Steam*', '*Epic Games*', '*Origin*'],
                        'extensions': ['.cache', '.log', '.tmp'],
                        'age_days': 1
                    },
                    actions={
                        'operation': 'delete',
                        'priority': 'medium'
                    }
                )
            }
    
    def load(self):
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_data = yaml.safe_load(f) or {}
                    self.data.update(loaded_data)
                    
                # Convert dicts back to dataclasses
                for name, profile_data in self.data['profiles'].items():
                    if isinstance(profile_data, dict):
                        self.data['profiles'][name] = Profile(**profile_data)
                
                for name, rule_data in self.data['rules'].items():
                    if isinstance(rule_data, dict):
                        self.data['rules'][name] = CleanupRule(**rule_data)
                
                if 'learning' in self.data and isinstance(self.data['learning'], dict):
                    self.data['learning'] = LearningData(**self.data['learning'])
                else:
                    self.data['learning'] = LearningData()
                    
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
    
    def save(self):
        """Save configuration to file."""
        self.data['last_updated'] = datetime.now().isoformat()
        
        # Convert dataclasses to dicts for YAML serialization
        save_data = self.data.copy()
        save_data['profiles'] = {name: asdict(profile) for name, profile in self.data['profiles'].items()}
        save_data['rules'] = {name: asdict(rule) for name, rule in self.data['rules'].items()}
        save_data['learning'] = asdict(self.data['learning']) if isinstance(self.data['learning'], LearningData) else self.data['learning']
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(save_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name."""
        return self.data['profiles'].get(name)
    
    def get_rule(self, name: str) -> Optional[CleanupRule]:
        """Get a rule by name."""
        return self.data['rules'].get(name)
    
    def add_profile(self, profile: Profile):
        """Add a new profile."""
        self.data['profiles'][profile.name] = profile
        self.save()
    
    def add_rule(self, rule: CleanupRule):
        """Add a new rule."""
        self.data['rules'][rule.name] = rule
        self.save()
    
    def get_active_rules(self, profile_name: str = None) -> List[CleanupRule]:
        """Get all active rules for a profile."""
        if profile_name:
            profile = self.get_profile(profile_name)
            if not profile or not profile.enabled:
                return []
            rule_names = profile.rules
        else:
            rule_names = list(self.data['rules'].keys())
        
        rules = []
        for name in rule_names:
            rule = self.get_rule(name)
            if rule and rule.enabled:
                rules.append(rule)
        
        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules
    
    def evaluate_file(self, file_path: str, rules: List[CleanupRule] = None) -> Optional[CleanupRule]:
        """Evaluate a file against rules and return the first matching rule."""
        if rules is None:
            rules = self.get_active_rules()
        
        path = Path(file_path)
        
        for rule in rules:
            if self._matches_conditions(path, rule.conditions):
                return rule
        
        return None
    
    def _matches_conditions(self, path: Path, conditions: Dict[str, Any]) -> bool:
        """Check if a file path matches rule conditions."""
        try:
            # Age condition
            if 'age_days' in conditions:
                age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
                if age_days < conditions['age_days']:
                    return False
            
            # Size conditions
            if path.exists():
                size = path.stat().st_size
                
                if 'size_exact' in conditions and size != self._parse_size(conditions['size_exact']):
                    return False
                
                if 'size_min' in conditions and size < self._parse_size(conditions['size_min']):
                    return False
                
                if 'size_max' in conditions and size > self._parse_size(conditions['size_max']):
                    return False
            
            # Path patterns
            if 'paths' in conditions:
                path_str = str(path).lower()
                if not any(pattern.lower().replace('*', '') in path_str for pattern in conditions['paths']):
                    return False
            
            # Extension patterns
            if 'extensions' in conditions:
                if path.suffix.lower() not in [ext.lower() for ext in conditions['extensions']]:
                    return False
            
            # Exclude patterns
            if 'exclude_patterns' in conditions:
                path_str = str(path).lower()
                if any(pattern.lower().replace('*', '') in path_str for pattern in conditions['exclude_patterns']):
                    return False
            
            return True
            
        except (OSError, ValueError):
            return False
    
    def _parse_size(self, size_str) -> int:
        """Parse size string like '10MB' to bytes."""
        if isinstance(size_str, int):
            return size_str
        
        size_str = str(size_str).upper().strip()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def record_file_access(self, file_path: str):
        """Record file access for learning."""
        file_path = str(file_path)
        self.data['learning'].file_access_patterns[file_path] = \
            self.data['learning'].file_access_patterns.get(file_path, 0) + 1
        
        # Save periodically
        if len(self.data['learning'].file_access_patterns) % 100 == 0:
            self.save()
    
    def record_deletion_regret(self, file_path: str):
        """Record that user regretted deleting a file."""
        if file_path not in self.data['learning'].deletion_regrets:
            self.data['learning'].deletion_regrets.append(file_path)
            self.save()
    
    def get_smart_suggestions(self) -> List[str]:
        """Get smart suggestions based on learning data."""
        suggestions = []
        
        # Suggest protecting frequently accessed files
        for file_path, access_count in self.data['learning'].file_access_patterns.items():
            if access_count > 10:
                suggestions.append(f"Consider protecting: {file_path} (accessed {access_count} times)")
        
        # Warn about previously regretted deletions
        for file_path in self.data['learning'].deletion_regrets:
            suggestions.append(f"Previously deleted and regretted: {file_path}")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get configuration and usage statistics."""
        return {
            'profiles_count': len(self.data['profiles']),
            'rules_count': len(self.data['rules']),
            'active_profiles': sum(1 for p in self.data['profiles'].values() if p.enabled),
            'active_rules': sum(1 for r in self.data['rules'].values() if r.enabled),
            'tracked_files': len(self.data['learning'].file_access_patterns),
            'deletion_regrets': len(self.data['learning'].deletion_regrets),
            'last_updated': self.data['last_updated']
        }


def main():
    """CLI for smart configuration management."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart configuration manager')
    parser.add_argument('--init', action='store_true', help='Initialize default configuration')
    parser.add_argument('--profile', help='Show profile details')
    parser.add_argument('--rule', help='Show rule details')
    parser.add_argument('--list-profiles', action='store_true', help='List all profiles')
    parser.add_argument('--list-rules', action='store_true', help='List all rules')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--suggestions', action='store_true', help='Show smart suggestions')
    parser.add_argument('--config', default='smart_config.yaml', help='Configuration file path')
    
    args = parser.parse_args()
    
    config = SmartConfig(args.config)
    
    if args.init:
        config.save()
        print(f"✅ Configuration initialized: {args.config}")
    
    elif args.list_profiles:
        print("📋 Profiles:")
        for name, profile in config.data['profiles'].items():
            status = "✅" if profile.enabled else "❌"
            print(f"  {status} {name}: {profile.description}")
    
    elif args.list_rules:
        print("📋 Rules:")
        for name, rule in config.data['rules'].items():
            status = "✅" if rule.enabled else "❌"
            print(f"  {status} {name}: {rule.conditions}")
    
    elif args.profile:
        profile = config.get_profile(args.profile)
        if profile:
            print(f"📋 Profile: {profile.name}")
            print(f"Description: {profile.description}")
            print(f"Paths: {profile.paths}")
            print(f"Rules: {profile.rules}")
            print(f"Schedule: {profile.schedule}")
        else:
            print(f"❌ Profile not found: {args.profile}")
    
    elif args.rule:
        rule = config.get_rule(args.rule)
        if rule:
            print(f"📋 Rule: {rule.name}")
            print(f"Conditions: {rule.conditions}")
            print(f"Actions: {rule.actions}")
            print(f"Priority: {rule.priority}")
        else:
            print(f"❌ Rule not found: {args.rule}")
    
    elif args.stats:
        stats = config.get_statistics()
        print("📊 Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif args.suggestions:
        suggestions = config.get_smart_suggestions()
        print("💡 Smart Suggestions:")
        if suggestions:
            for suggestion in suggestions:
                print(f"  • {suggestion}")
        else:
            print("  No suggestions available yet.")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
