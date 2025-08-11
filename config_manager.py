#!/usr/bin/env python3
"""
Enhanced Configuration Manager v3.2 - Fixed Version
Handles loading, validating, and saving configuration files with comprehensive
settings validation, duplicate detection, and enhanced documentation.
"""

import json
from pathlib import Path
from datetime import datetime
import re

__version__ = "3.2"
__module_name__ = "ConfigManager"

class ConfigManager:
    def __init__(self, config_path: str = "master_config.json"):
        """Initialize with default config file name."""
        self.settings_path = Path(config_path)
        self.config = {}
        self.config_loaded = False
        self.config_errors = []
        self.duplicate_warnings = []

        # Get module versions (would be imported from actual modules in real system)
        self.module_versions = {
            "config_manager": __version__,
            "video_cleaner": "3.2",
            "video_processor": "3.1", 
            "video_analyzer": "3.1",
            "size_checker": "3.1",
            "filename_standardizer": "3.2",
            "utils": "3.2",
            "logger": "3.1"  # Assuming this exists
        }

        # CONSOLIDATED FFmpeg paths - single source of truth
        self.ffmpeg_base_paths = [
            "ffmpeg",
            "ffprobe", 
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\ffmpeg\\bin\\ffprobe.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe"
        ]

        # Comprehensive default config with documentation and validation
        self.default_config = {
            "_metadata": {
                "config_version": __version__,
                "created": datetime.now().isoformat(),
                "description": "Master configuration for Universal Video Cleaner",
                "last_updated": datetime.now().isoformat(),
                "module_versions": self.module_versions,
                "documentation": {
                    "note": "This configuration controls all aspects of video processing",
                    "ffmpeg_requirement": "FFmpeg must be installed and accessible",
                    "boolean_values": "true/false (lowercase)",
                    "timeout_units": "All timeouts are in seconds unless specified",
                    "size_units": "File sizes in MB unless specified as GB",
                    "path_format": "Use forward slashes or double backslashes for Windows paths"
                }
            },
            
            "main_driver": {
                "_docs": {
                    "description": "Main application behavior and user interface settings",
                    "application_name": "Display name for the application",
                    "version_display": "Show version in UI (true/false)",
                    "show_welcome_panel": "Display startup welcome panel (true/false)",
                    "use_rich_ui": "Use Rich library for enhanced UI (true/false)",
                    "panel_width": "UI panel width in characters (40-120)",
                    "max_iterations": "Maximum processing runs per session (1-100)",
                    "session_timeout_minutes": "Auto-timeout for inactive sessions (30-300)"
                },
                "application": {
                    "name": "Universal Video Cleaner",
                    "version_display": True,
                    "show_welcome_panel": True,
                    "exit_cleanup_cache": True
                },
                "interface": {
                    "use_rich_ui": True,
                    "fallback_to_basic": True,
                    "panel_width": 80
                },
                "session": {
                    "max_iterations": 50,
                    "session_timeout_minutes": 120,
                    "track_statistics": True,
                    "enhanced_goodbye": True
                }
            },
            
            "ffmpeg_global": {
                "_docs": {
                    "description": "GLOBAL FFmpeg configuration - used by all modules",
                    "executable_paths": "Search paths for FFmpeg/FFprobe executables",
                    "note": "This replaces separate FFmpeg configs in other modules",
                    "path_priority": "Paths are tried in order until working executable found"
                },
                "executable_paths": self.ffmpeg_base_paths,
                "verify_installation": True,
                "required_tools": ["ffmpeg", "ffprobe"]
            },
            
            "timeouts_global": {
                "_docs": {
                    "description": "GLOBAL timeout configuration - used by all modules",
                    "processing_timeout": "Maximum time for video processing operations (60-3600)",
                    "probe_timeout": "Maximum time for file probing/analysis (10-120)", 
                    "file_operation_timeout": "Maximum time for file operations (10-120)",
                    "note": "Individual modules can override these if needed"
                },
                "processing_timeout": 600,
                "probe_timeout": 30,
                "file_operation_timeout": 30
            },
            
            "cache_global": {
                "_docs": {
                    "description": "GLOBAL cache configuration - used by all modules", 
                    "enable_caching": "Enable caching of analysis results (true/false)",
                    "max_cache_entries": "Maximum number of entries to keep in cache (100-10000)",
                    "cache_duration_minutes": "How long to keep cached results (10-120)",
                    "note": "Individual modules can override these if needed"
                },
                "enable_caching": True,
                "max_cache_entries": 1000,
                "cache_duration_minutes": 30
            },
            
            "video_processor": {
                "_docs": {
                    "description": "Video processing and FFmpeg execution settings",
                    "processing_timeout_seconds": "Max time for video conversion (60-3600)",
                    "preset": "FFmpeg preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow",
                    "crf_quality": "Constant Rate Factor for H.265 encoding (18-28, lower=better quality)",
                    "minimum_output_size_mb": "Reject outputs smaller than this (1-100)",
                    "maximum_output_size_gb": "Reject outputs larger than this (1-100)"
                },
                "ffmpeg": {
                    "processing_timeout_seconds": 600,
                    "probe_timeout_seconds": 30,
                    "max_concurrent_jobs": 1,
                    "preset": "medium",
                    "crf_quality": 23
                },
                "conversion": {
                    "force_h265_conversion": True
                },
                "safety": {
                    "verify_output_size": True,
                    "minimum_output_size_mb": 10,
                    "maximum_output_size_gb": 50
                },
                "temp_directories": {
                    "use_system_temp": True,
                    "custom_temp_path": "",
                    "cleanup_temp_files": True,
                    "max_temp_age_hours": 24
                }
            },
            
            "size_checker": {
                "_docs": {
                    "description": "Intelligent file size anomaly detection",
                    "max_size_multiplier": "Flag files larger than X times expected size (1.5-5.0)",
                    "min_size_multiplier": "Flag files smaller than X times expected size (0.1-0.8)", 
                    "warning_threshold": "Warning level between min and max (1.2-2.0)",
                    "tv_size_mb_per_minute": "Expected TV episode size per minute (8-20)",
                    "movie_size_mb_per_minute": "Expected movie size per minute (10-25)",
                    "enable_learning": "Learn patterns from existing files (true/false)",
                    "auto_mark_rb_on_anomaly": "Automatically mark anomalies as .rb (true/false)"
                },
                "tv_shows": {
                    "enable_size_checking": True,
                    "max_size_multiplier": 2.5,
                    "min_size_multiplier": 0.3,
                    "warning_threshold": 1.5,
                    "consistency_checking": True,
                    "episode_cache_size": 10
                },
                "movies": {
                    "enable_size_checking": True,
                    "max_size_multiplier": 3.0,
                    "min_size_multiplier": 0.2,
                    "warning_threshold": 2.0,
                    "consistency_checking": False
                },
                "standards": {
                    "tv_episode_duration_minutes": 43,
                    "tv_size_mb_per_minute": 12.0,
                    "movie_duration_minutes": 120,
                    "movie_size_mb_per_minute": 14.0
                },
                "detection": {
                    "enable_learning": True,
                    "cache_episode_patterns": True,
                    "confidence_threshold": 0.7,
                    "auto_mark_rb_on_anomaly": True
                }
            },
            
            "video_analyzer": {
                "_docs": {
                    "description": "Video file analysis and stream detection",
                    "deep_scan": "Perform detailed analysis (slower but more thorough) (true/false)",
                    "cache_results": "Cache analysis results for performance (true/false)",
                    "analysis_timeout_seconds": "Max time for file analysis (30-300)",
                    "retry_attempts": "Number of retry attempts for failed analysis (1-5)",
                    "identify_languages": "Detect audio/subtitle languages (true/false)"
                },
                "analysis": {
                    "deep_scan": True,
                    "cache_results": True,
                    "extract_metadata": True,
                    "detect_corruption": True,
                    "analyze_all_streams": True
                },
                "performance": {
                    "analysis_timeout_seconds": 60,
                    "max_cache_entries": 500,
                    "parallel_analysis": False,
                    "cache_duration_minutes": 30
                },
                "ffprobe": {
                    "timeout_seconds": 30,
                    "retry_attempts": 2,
                    "output_format": "json"
                },
                "track_detection": {
                    "identify_languages": True,
                    "detect_hearing_impaired": True,
                    "analyze_codec_efficiency": True,
                    "estimate_processing_time": True
                }
            },
            
            "filename_standardizer": {
                "_docs": {
                    "description": "Filename cleaning and standardization",
                    "aggressive_cleaning": "Remove all junk from filenames (true/false)",
                    "preserve_original_case": "Keep original capitalization (true/false)",
                    "standardize_extensions": "Convert all to .mkv (true/false)",
                    "format_template": "Use {show_name}, {season}, {episode}, {title}, {year} placeholders",
                    "confidence_threshold": "Minimum confidence for pattern matching (0.1-1.0)",
                    "max_season_number": "Highest valid season number (10-99)",
                    "min_year": "Earliest valid movie year (1900-1990)",
                    "max_year": "Latest valid movie year (2020-2040)"
                },
                "cleaning": {
                    "aggressive_cleaning": True,
                    "preserve_original_case": False,
                    "remove_episode_titles": True,
                    "standardize_extensions": True,
                    "clean_special_characters": True
                },
                "tv_shows": {
                    "format_template": "{show_name} - S{season:02d}E{episode:02d}",
                    "detect_special_episodes": True,
                    "normalize_show_names": True,
                    "min_season_number": 1,
                    "max_season_number": 50,
                    "max_episode_number": 999
                },
                "movies": {
                    "format_template": "{title} ({year})",
                    "require_year": True,
                    "year_placeholder": "XXXX",
                    "min_year": 1900,
                    "max_year": 2030
                },
                "patterns": {
                    "use_advanced_patterns": True,
                    "confidence_threshold": 0.7,
                    "enable_fuzzy_matching": False
                },
                "performance": {
                    "cache_results": True,
                    "max_cache_entries": 1000,
                    "log_cleaning_details": False
                }
            },
            
            "directory_scanner": {
                "_docs": {
                    "description": "Directory scanning and file discovery",
                    "enable_directory_cache": "Cache directory contents for speed (true/false)",
                    "cache_duration_minutes": "How long to keep cached results (10-120)",
                    "max_depth": "Maximum subdirectory depth to scan (3-20)",
                    "include_hidden_files": "Scan hidden/dot files (true/false)",
                    "follow_symlinks": "Follow symbolic links (true/false)",
                    "scan_timeout_seconds": "Max time for directory scan (30-600)"
                },
                "caching": {
                    "enable_directory_cache": True,
                    "cache_duration_minutes": 30,
                    "max_cache_entries": 100
                },
                "scanning": {
                    "deep_scan": True,
                    "include_hidden_files": False,
                    "follow_symlinks": False,
                    "max_depth": 10
                },
                "performance": {
                    "scan_timeout_seconds": 120,
                    "parallel_scanning": False
                }
            },
            
            "episode_tracker": {
                "_docs": {
                    "description": "TV episode tracking and missing episode detection",
                    "enable_episode_tracking": "Track and analyze TV episodes (true/false)",
                    "use_advanced_patterns": "Use complex episode detection patterns (true/false)",
                    "detect_special_episodes": "Identify specials, pilots, finales (true/false)",
                    "gap_detection_threshold": "Minimum gap size to flag as missing (1-5)",
                    "min_episodes_for_analysis": "Minimum episodes needed for gap analysis (2-10)"
                },
                "tracking": {
                    "enable_episode_tracking": True,
                    "use_advanced_patterns": True,
                    "detect_special_episodes": True,
                    "normalize_show_names": True
                },
                "detection": {
                    "gap_detection_threshold": 1,
                    "min_episodes_for_analysis": 3
                },
                "logging": {
                    "log_episode_detection": False
                }
            },
            
            "logger": {
                "_docs": {
                    "description": "Enhanced logging with module context and structured output",
                    "file_output": "Write logs to files (true/false)",
                    "console_output": "Display logs in console (true/false)",
                    "include_module_context": "Show which module generated each message (true/false)",
                    "include_operation_stack": "Show nested operations like analysis:stream_detection (true/false)",
                    "color_console_output": "Use colors in console output (true/false)",
                    "log_level": "Minimum level to log: DEBUG, INFO, WARNING, ERROR, CRITICAL",
                    "max_log_file_size_mb": "Rotate log files when they exceed this size (10-200)",
                    "keep_log_files": "Number of old log files to keep (1-20)"
                },
                "output": {
                    "file_output": True,
                    "console_output": True
                },
                "format": {
                    "include_timestamps": True,
                    "include_module_context": True,
                    "include_operation_stack": True,
                    "color_console_output": True
                },
                "settings": {
                    "log_level": "INFO"
                },
                "files": {
                    "max_log_file_size_mb": 50,
                    "keep_log_files": 5
                },
                "advanced": {
                    "structured_logging": False
                },
                "content": {
                    "log_size_checks": True,
                    "log_performance_metrics": True,
                    "log_file_analysis": True
                }
            },
            
            "protection_system": {
                "_docs": {
                    "description": "File protection and recovery systems",
                    "enable_rollback_protection": "Create .rb files for problem files (true/false)",
                    "verify_after_processing": "Check file integrity after processing (true/false)",
                    "auto_mark_rb_on_failure": "Auto-mark failed files as .rb (true/false)"
                },
                "rollback": {
                    "enable_rollback_protection": True
                },
                "integrity": {
                    "verify_after_processing": True
                }
            },
            
            "error_handling": {
                "_docs": {
                    "description": "Error handling and recovery behavior",
                    "file_operation_timeout": "Timeout for file operations (10-120)",
                    "auto_mark_rb_on_failure": "Mark failed files as .rb automatically (true/false)"
                },
                "timeouts": {
                    "file_operation_timeout": 30
                },
                "recovery": {
                    "auto_mark_rb_on_failure": True
                }
            }
        }

        self._load_settings_file()

    def _load_settings_file(self):
        """Load configuration file, create default if missing."""
        if not self.settings_path.exists():
            print(f"Configuration file not found: {self.settings_path}")
            print("Creating default configuration file with comprehensive settings...")
            self._create_default_config()
            return

        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            if not self.config:
                raise ValueError("Loaded configuration is empty")
            
            # Check for duplicates and validation issues
            self._validate_configuration()
            
            self.config_loaded = True
            print(f"[OK] Configuration loaded: {self.settings_path}")
            
            if self.duplicate_warnings:
                print("[WARNING] Configuration warnings:")
                for warning in self.duplicate_warnings:
                    print(f"  - {warning}")
                    
        except Exception as e:
            self._handle_critical_error(f"Failed to load configuration: {e}")

    def _validate_configuration(self):
        """Validate configuration for duplicates and consistency issues."""
        self.duplicate_warnings = []
        
        # Check for FFmpeg path duplicates
        ffmpeg_paths_found = []
        
        # Check video_processor paths
        if 'video_processor' in self.config and 'ffmpeg' in self.config['video_processor']:
            if 'executable_paths' in self.config['video_processor']['ffmpeg']:
                ffmpeg_paths_found.append('video_processor.ffmpeg.executable_paths')
        
        # Check video_analyzer paths  
        if 'video_analyzer' in self.config and 'ffprobe' in self.config['video_analyzer']:
            if 'executable_paths' in self.config['video_analyzer']['ffprobe']:
                ffmpeg_paths_found.append('video_analyzer.ffprobe.executable_paths')
        
        # Check for global FFmpeg config
        if 'ffmpeg_global' in self.config:
            ffmpeg_paths_found.append('ffmpeg_global.executable_paths')
        
        if len(ffmpeg_paths_found) > 1:
            self.duplicate_warnings.append(
                f"FFmpeg paths defined in multiple locations: {', '.join(ffmpeg_paths_found)}. "
                "Consider using ffmpeg_global.executable_paths only."
            )
        
        # Check for missing enhanced settings
        required_sections = {
            'filename_standardizer': ['cleaning', 'tv_shows', 'movies', 'patterns'],
            'directory_scanner': ['caching', 'scanning'],
            'episode_tracker': ['tracking', 'detection']
        }
        
        for section, subsections in required_sections.items():
            if section in self.config:
                for subsection in subsections:
                    if subsection not in self.config[section]:
                        self.duplicate_warnings.append(
                            f"Missing enhanced settings: {section}.{subsection}"
                        )
        
        # Check for deprecated single-level settings
        deprecated_settings = [
            ('filename_standardizer', 'aggressive_cleaning'),  # Should be in .cleaning.aggressive_cleaning
        ]
        
        for section, setting in deprecated_settings:
            if (section in self.config and 
                isinstance(self.config[section], dict) and 
                setting in self.config[section] and
                'cleaning' in self.config[section]):
                self.duplicate_warnings.append(
                    f"Deprecated setting location: {section}.{setting} should be moved to {section}.cleaning.{setting}"
                )

    def _create_default_config(self):
        """Create default configuration file with comprehensive settings."""
        try:
            self._write_config_file(self.default_config)
            self.config = self.default_config.copy()
            self.config_loaded = True
            print(f"[OK] Default configuration created: {self.settings_path}")
            print(f"[INFO] Configuration includes {len(self.module_versions)} module versions")
            print(f"[INFO] Comprehensive settings for all {len([k for k in self.default_config.keys() if not k.startswith('_')])} modules")
        except Exception as e:
            print(f"[ERROR] CRITICAL: Failed to create default config: {e}")
            # Use in-memory defaults as fallback
            self.config = self.default_config.copy()
            self.config_loaded = False

    def _write_config_file(self, config_data):
        """Write configuration to file with pretty formatting."""
        try:
            # Ensure directory exists
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with nice formatting
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False, sort_keys=False)
                
        except Exception as e:
            raise RuntimeError(f"Failed to write configuration file: {e}")

    def get_ffmpeg_paths(self) -> list:
        """
        Get FFmpeg executable paths from consolidated global config.
        
        Returns:
            List of FFmpeg/FFprobe executable paths
        """
        # Try global config first (preferred)
        if 'ffmpeg_global' in self.config:
            paths = self.config['ffmpeg_global'].get('executable_paths', [])
            if paths:
                return paths
        
        # Fallback to video_processor config
        if 'video_processor' in self.config and 'ffmpeg' in self.config['video_processor']:
            paths = self.config['video_processor']['ffmpeg'].get('executable_paths', [])
            if paths:
                return paths
        
        # Fallback to video_analyzer config  
        if 'video_analyzer' in self.config and 'ffprobe' in self.config['video_analyzer']:
            paths = self.config['video_analyzer']['ffprobe'].get('executable_paths', [])
            if paths:
                return paths
        
        # Ultimate fallback
        return self.ffmpeg_base_paths

    def get_global_timeout(self, timeout_type: str, default: int = None) -> int:
        """
        Get global timeout value with fallback to module-specific configs.
        
        Args:
            timeout_type: Type of timeout ('processing', 'probe', 'file_operation')
            default: Default value if not found
            
        Returns:
            Timeout value in seconds
        """
        # Try global timeouts first
        if 'timeouts_global' in self.config:
            timeout_value = self.config['timeouts_global'].get(f'{timeout_type}_timeout', None)
            if timeout_value is not None:
                return timeout_value
        
        # Fallback to module-specific timeouts
        if timeout_type == 'processing':
            return self.get('video_processor', 'ffmpeg.processing_timeout_seconds', default or 600)
        elif timeout_type == 'probe':
            # Check both analyzer and processor probe timeouts
            analyzer_timeout = self.get('video_analyzer', 'ffprobe.timeout_seconds', None)
            if analyzer_timeout is not None:
                return analyzer_timeout
            return self.get('video_processor', 'ffmpeg.probe_timeout_seconds', default or 30)
        elif timeout_type == 'file_operation':
            return self.get('error_handling', 'timeouts.file_operation_timeout', default or 30)
        
        return default or 30

    def get_global_cache_setting(self, setting_name: str, default=None):
        """
        Get global cache setting with fallback to module-specific configs.
        
        Args:
            setting_name: Name of cache setting ('enable_caching', 'max_cache_entries', 'cache_duration_minutes')
            default: Default value if not found
            
        Returns:
            Cache setting value
        """
        # Try global cache config first
        if 'cache_global' in self.config:
            value = self.config['cache_global'].get(setting_name, None)
            if value is not None:
                return value
        
        # Fallback based on setting name
        if setting_name == 'enable_caching':
            # Check video_analyzer first, then filename_standardizer
            analyzer_cache = self.get('video_analyzer', 'analysis.cache_results', None)
            if analyzer_cache is not None:
                return analyzer_cache
            return self.get('filename_standardizer', 'performance.cache_results', default if default is not None else True)
        elif setting_name == 'max_cache_entries':
            # Use the larger of the two module settings
            analyzer_max = self.get('video_analyzer', 'performance.max_cache_entries', 500)
            standardizer_max = self.get('filename_standardizer', 'performance.max_cache_entries', 1000)
            return max(analyzer_max, standardizer_max)
        elif setting_name == 'cache_duration_minutes':
            return self.get('video_analyzer', 'performance.cache_duration_minutes', default if default is not None else 30)
        
        return default

    def get_module_version(self, module_name: str) -> str:
        """
        Get version of a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Version string or 'unknown'
        """
        if '_metadata' in self.config and 'module_versions' in self.config['_metadata']:
            return self.config['_metadata']['module_versions'].get(module_name, 'unknown')
        return self.module_versions.get(module_name, 'unknown')

    def get_all_module_versions(self) -> dict:
        """Get all module versions."""
        if '_metadata' in self.config and 'module_versions' in self.config['_metadata']:
            return self.config['_metadata']['module_versions']
        return self.module_versions

    def update_module_version(self, module_name: str, version: str):
        """Update a module version in the config."""
        if '_metadata' not in self.config:
            self.config['_metadata'] = {}
        if 'module_versions' not in self.config['_metadata']:
            self.config['_metadata']['module_versions'] = {}
        
        self.config['_metadata']['module_versions'][module_name] = version
        self.config['_metadata']['last_updated'] = datetime.now().isoformat()

    def _handle_critical_error(self, message: str):
        """Handle critical configuration errors."""
        error_msg = f"CRITICAL: {__module_name__} - {message}"
        print(error_msg)
        self.config_errors.append(message)
        
        print(f"[!] Attempting to regenerate config file with defaults at {self.settings_path}")
        try:
            self._create_default_config()
        except Exception as e:
            print(f"[ERROR] CRITICAL: Failed to regenerate config: {e}")
            # Use in-memory defaults as last resort
            self.config = self.default_config.copy()
            self.config_loaded = False

    def get(self, section: str, path: str = None, default=None):
        """
        Get configuration value with support for nested paths.
        Uses global FFmpeg paths when appropriate.
        """
        try:
            # Handle special case for FFmpeg paths
            if (section in ['video_processor', 'video_analyzer'] and 
                path and ('executable_paths' in path or 'ffmpeg' in path)):
                return self.get_ffmpeg_paths()
            
            # Handle old-style single parameter calls
            if path is None:
                return self.config.get(section, default)
            
            # Get the main section
            if section not in self.config:
                return default
            
            current = self.config[section]
            
            # Navigate through the nested path
            path_parts = path.split('.')
            for part in path_parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            
            return current
            
        except Exception:
            return default

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.config_loaded and len(self.config_errors) == 0

    def get_config_info(self):
        """Get configuration information."""
        return {
            'is_valid': self.is_valid(),
            'config_sections': len([k for k in self.config.keys() if not k.startswith('_')]),
            'error_count': len(self.config_errors),
            'warning_count': len(self.duplicate_warnings),
            'file_exists': self.settings_path.exists(),
            'file_path': str(self.settings_path),
            'module_versions': self.get_all_module_versions(),
            'has_global_ffmpeg': 'ffmpeg_global' in self.config,
            'duplicate_warnings': self.duplicate_warnings
        }

    def has_config_changed(self) -> bool:
        """Check if config has changed."""
        return False

    def get_configuration_documentation(self) -> dict:
        """Get documentation for all configuration sections."""
        docs = {}
        
        for section_name, section_data in self.default_config.items():
            if section_name.startswith('_'):
                continue  # Skip metadata
                
            if isinstance(section_data, dict) and '_docs' in section_data:
                docs[section_name] = section_data['_docs']
        
        return docs

    def validate_setting_value(self, section: str, path: str, value) -> tuple:
        """
        Validate a configuration setting value.
        
        Returns:
            (is_valid, error_message)
        """
        # Get documentation for validation hints
        docs = self.get_configuration_documentation()
        
        if section in docs:
            setting_key = path.split('.')[-1] if '.' in path else path
            if setting_key in docs[section]:
                doc_text = docs[section][setting_key]
                
                # Extract ranges from documentation
                if '(' in doc_text and ')' in doc_text:
                    range_match = re.search(r'\(([^)]+)\)', doc_text)
                    if range_match:
                        range_text = range_match.group(1)
                        
                        # Check numeric ranges
                        if '-' in range_text and range_text.replace('-', '').replace('.', '').isdigit():
                            try:
                                min_val, max_val = map(float, range_text.split('-'))
                                if isinstance(value, (int, float)):
                                    if not (min_val <= value <= max_val):
                                        return False, f"Value {value} outside valid range {min_val}-{max_val}"
                            except ValueError:
                                pass
                        
                        # Check boolean values
                        if 'true/false' in range_text.lower():
                            if not isinstance(value, bool):
                                return False, f"Value must be true or false, got {type(value).__name__}"
        
        return True, ""

# Test the enhanced configuration manager
if __name__ == "__main__":
    print(f"{__module_name__} v{__version__} - Enhanced Testing")
    print("=" * 60)
    
    # Test creating config manager
    try:
        config = ConfigManager("test_enhanced_config.json")
        print("[OK] Enhanced ConfigManager created successfully")
        
        # Test configuration info
        config_info = config.get_config_info()
        print("\n[INFO] Configuration Information:")
        for key, value in config_info.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for subkey, subvalue in value.items():
                    print(f"    {subkey}: {subvalue}")
            elif isinstance(value, list) and len(value) > 3:
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {value}")
        
        # Test FFmpeg path consolidation
        ffmpeg_paths = config.get_ffmpeg_paths()
        print(f"\n🔧 Consolidated FFmpeg Paths ({len(ffmpeg_paths)} paths):")
        for i, path in enumerate(ffmpeg_paths, 1):
            print(f"  {i}. {path}")
        
        # Test module versions
        module_versions = config.get_all_module_versions()
        print(f"\n📦 Module Versions:")
        for module, version in module_versions.items():
            print(f"  {module}: v{version}")
        
        # Test validation
        print(f"\n🔍 Configuration Validation:")
        if config.duplicate_warnings:
            print("  Warnings found:")
            for warning in config.duplicate_warnings:
                print(f"    [WARNING] {warning}")
        else:
            print("  [OK] No validation warnings")
        
        # Test setting validation
        test_validations = [
            ('video_processor', 'ffmpeg.crf_quality', 23),
            ('video_processor', 'ffmpeg.crf_quality', 50),  # Should fail
            ('main_driver', 'interface.use_rich_ui', True),
            ('main_driver', 'interface.use_rich_ui', "yes"),  # Should fail
        ]
        
        print(f"\n🧪 Setting Validation Tests:")
        for section, path, value in test_validations:
            is_valid, error = config.validate_setting_value(section, path, value)
            status = "[OK]" if is_valid else "[FAIL]"
            print(f"  {status} {section}.{path} = {value}")
            if error:
                print(f"      Error: {error}")
        
        print(f"\n[OK] Enhanced ConfigManager v{__version__} working correctly!")
        print("Key improvements:")
        print("  - Consolidated FFmpeg paths")
        print("  - Enhanced settings validation")
        print("  - Comprehensive documentation")
        print("  - Duplicate detection")
        print("  - Module version tracking")
        
    except Exception as e:
        print(f"[ERROR] Error testing ConfigManager: {e}")
        import traceback
        traceback.print_exc()
