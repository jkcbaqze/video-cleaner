#!/usr/bin/env python3
"""
Enhanced Professional Logger v3.2
Comprehensive logging system with module context, structured logging,
and intelligent message routing. NO MORE ANONYMOUS ERROR MESSAGES!
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import threading
import traceback

__version__ = "3.2"
__module_name__ = "Professional Logger"

def module_ping():
    """Module health check for dry run reporting."""
    return f"{__module_name__} v{__version__} - READY"

class LogLevel:
    """Log level constants for consistency."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ModuleContext:
    """Context information for module-aware logging."""
    
    def __init__(self, module_name: str, version: str = "unknown", instance_id: str = None):
        self.module_name = module_name
        self.version = version
        self.instance_id = instance_id or id(self)
        self.operation_stack = []  # Track nested operations
    
    def push_operation(self, operation: str):
        """Add operation to the context stack."""
        self.operation_stack.append(operation)
    
    def pop_operation(self):
        """Remove the most recent operation from stack."""
        if self.operation_stack:
            return self.operation_stack.pop()
        return None
    
    def get_full_context(self) -> str:
        """Get full context string for logging."""
        context_parts = [self.module_name]
        
        if self.version != "unknown":
            context_parts.append(f"v{self.version}")
        
        if self.operation_stack:
            context_parts.append(f":{'.'.join(self.operation_stack)}")
        
        return "[" + " ".join(context_parts) + "]"

class ProfessionalLogger:
    """
    Enhanced professional logger with module context awareness,
    structured logging, and intelligent message routing.
    """
    
    def __init__(self, log_filename: str = None, directory_name: str = None, 
                 mode: str = "tv", config_manager=None):
        """
        Initialize enhanced logger with module context support.
        
        Args:
            log_filename: Optional log file name
            directory_name: Directory being processed
            mode: Processing mode ("tv" or "movie")
            config_manager: ConfigManager instance for settings
        """
        self.config_manager = config_manager
        self.directory_name = directory_name
        self.mode = mode
        
        # Load settings from config
        if config_manager:
            self.file_output = config_manager.get('logger', 'output.file_output', True)
            self.console_output = config_manager.get('logger', 'output.console_output', True)
            self.log_level = config_manager.get('logger', 'settings.log_level', 'INFO')
            self.include_timestamps = config_manager.get('logger', 'format.include_timestamps', True)
            self.include_module_context = config_manager.get('logger', 'format.include_module_context', True)
            self.include_operation_stack = config_manager.get('logger', 'format.include_operation_stack', True)
            self.color_console_output = config_manager.get('logger', 'format.color_console_output', True)
            self.max_log_file_size_mb = config_manager.get('logger', 'files.max_log_file_size_mb', 50)
            self.keep_log_files = config_manager.get('logger', 'files.keep_log_files', 5)
            self.structured_logging = config_manager.get('logger', 'advanced.structured_logging', False)
        else:
            # Fallback defaults
            self.file_output = True
            self.console_output = True
            self.log_level = 'INFO'
            self.include_timestamps = True
            self.include_module_context = True
            self.include_operation_stack = True
            self.color_console_output = True
            self.max_log_file_size_mb = 50
            self.keep_log_files = 5
            self.structured_logging = False
        
        # Setup log file
        self.log_file = None
        if self.file_output and log_filename:
            self.log_file = Path("logs") / log_filename
            self.log_file.parent.mkdir(exist_ok=True)
        
        # Module context registry
        self.module_contexts: Dict[str, ModuleContext] = {}
        self.context_lock = threading.Lock()
        
        # Session information
        self.session_start = datetime.now()
        self.session_stats = {
            'total_messages': 0,
            'messages_by_level': {level: 0 for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
            'messages_by_module': {},
            'session_start': self.session_start
        }
        
        # Console color codes
        self.color_codes = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[37m',     # White  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m',     # Reset
            'BOLD': '\033[1m',      # Bold
            'MODULE': '\033[32m',   # Green for module names
        } if self.color_console_output else {}
        
        # Initialize with main logger context
        self.register_module("logger", __version__)
        
        if self.console_output and self._should_log('INFO'):
            self.log('INFO', f"Enhanced logging initialized - Module context: {'enabled' if self.include_module_context else 'disabled'}", 
                    module_context=self.module_contexts.get('logger'))

    def register_module(self, module_name: str, version: str = "unknown", instance_id: str = None) -> ModuleContext:
        """
        Register a module for context-aware logging.
        
        Args:
            module_name: Name of the module
            version: Module version
            instance_id: Optional instance identifier
            
        Returns:
            ModuleContext object for the module
        """
        with self.context_lock:
            context = ModuleContext(module_name, version, instance_id)
            self.module_contexts[module_name] = context
            
            # Initialize stats for this module
            if module_name not in self.session_stats['messages_by_module']:
                self.session_stats['messages_by_module'][module_name] = 0
            
            return context

    def get_module_logger(self, module_name: str, version: str = "unknown") -> 'ModuleLogger':
        """
        Get a module-specific logger interface.
        
        Args:
            module_name: Name of the module
            version: Module version
            
        Returns:
            ModuleLogger instance for the specific module
        """
        context = self.register_module(module_name, version)
        return ModuleLogger(self, context)

    def _should_log(self, level: str) -> bool:
        """Check if message should be logged based on log level."""
        level_priority = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }
        
        return level_priority.get(level, 0) >= level_priority.get(self.log_level, 20)

    def _format_message(self, level: str, message: str, module_context: ModuleContext = None, 
                       filename: str = None, extra_data: Dict = None) -> str:
        """
        Format log message with enhanced context information.
        
        Args:
            level: Log level
            message: Log message
            module_context: Module context information
            filename: Optional filename being processed
            extra_data: Optional additional data
            
        Returns:
            Formatted log message
        """
        parts = []
        
        # Timestamp
        if self.include_timestamps:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            parts.append(f"[{timestamp}]")
        
        # Log level
        if self.color_codes and level in self.color_codes:
            level_colored = f"{self.color_codes[level]}{level}{self.color_codes['RESET']}"
            parts.append(f"[{level_colored}]")
        else:
            parts.append(f"[{level}]")
        
        # Module context
        if self.include_module_context and module_context:
            context_str = module_context.get_full_context()
            if self.color_codes:
                context_colored = f"{self.color_codes['MODULE']}{context_str}{self.color_codes['RESET']}"
                parts.append(context_colored)
            else:
                parts.append(context_str)
        
        # Filename being processed
        if filename:
            parts.append(f"[{filename}]")
        
        # Main message
        if self.color_codes and level == 'CRITICAL':
            message = f"{self.color_codes['BOLD']}{message}{self.color_codes['RESET']}"
        
        parts.append(message)
        
        # Extra data (for structured logging)
        if extra_data and self.structured_logging:
            extra_str = json.dumps(extra_data, separators=(',', ':'))
            parts.append(f"DATA:{extra_str}")
        
        return " ".join(parts)

    def _write_log(self, formatted_message: str, level: str):
        """Write formatted message to configured outputs."""
        # Console output - only show ERROR and CRITICAL to console
        if self.console_output and level in ['ERROR', 'CRITICAL']:
            print(formatted_message)
        
        # File output
        if self.file_output and self.log_file:
            try:
                # Remove color codes for file output
                clean_message = formatted_message
                for code in self.color_codes.values():
                    clean_message = clean_message.replace(code, '')
                
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(clean_message + '\n')
                
                # Check file size and rotate if needed
                self._check_log_rotation()
                
            except Exception as e:
                # Fallback to console if file writing fails
                print(f"[LOGGER ERROR] Failed to write to log file: {e}")

    def _check_log_rotation(self):
        """Check if log file needs rotation."""
        try:
            if self.log_file and self.log_file.exists():
                size_mb = self.log_file.stat().st_size / (1024 * 1024)
                if size_mb > self.max_log_file_size_mb:
                    self._rotate_log_file()
        except Exception:
            pass  # Don't crash on rotation issues

    def _rotate_log_file(self):
        """Rotate log file when it gets too large."""
        try:
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{self.log_file.stem}_{timestamp}.log"
            backup_path = self.log_file.parent / backup_name
            
            # Move current log to backup
            self.log_file.rename(backup_path)
            
            # Clean up old log files
            self._cleanup_old_logs()
            
        except Exception:
            pass  # Don't crash on rotation issues

    def _cleanup_old_logs(self):
        """Remove old log files beyond the keep limit."""
        try:
            if not self.log_file:
                return
                
            log_pattern = f"{self.log_file.stem}_*.log"
            log_files = sorted(self.log_file.parent.glob(log_pattern))
            
            # Remove oldest files beyond limit
            while len(log_files) > self.keep_log_files:
                oldest = log_files.pop(0)
                oldest.unlink()
                
        except Exception:
            pass  # Don't crash on cleanup issues

    def log(self, level: str, message: str, module_name: str = None, filename: str = None, 
            extra_data: Dict = None):
        """
        Enhanced logging method with full context support.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            module_name: Name of the module generating the message
            filename: Optional filename being processed
            extra_data: Optional additional structured data
        """
        if not self._should_log(level):
            return
        
        # Get module context
        module_context = None
        if module_name and self.include_module_context:
            with self.context_lock:
                module_context = self.module_contexts.get(module_name)
                if not module_context:
                    module_context = self.register_module(module_name)
        
        # Format and write message
        formatted_message = self._format_message(level, message, module_context, filename, extra_data)
        self._write_log(formatted_message, level)
        
        # Update statistics
        self.session_stats['total_messages'] += 1
        self.session_stats['messages_by_level'][level] += 1
        if module_name:
            self.session_stats['messages_by_module'][module_name] = \
                self.session_stats['messages_by_module'].get(module_name, 0) + 1

    # Convenience methods with automatic module detection
    def debug(self, message: str, module_name: str = None, filename: str = None, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, module_name, filename, kwargs)

    def info(self, message: str, module_name: str = None, filename: str = None, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, message, module_name, filename, kwargs)

    def warning(self, message: str, module_name: str = None, filename: str = None, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, module_name, filename, kwargs)

    def error(self, message: str, module_name: str = None, filename: str = None, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, message, module_name, filename, kwargs)

    def critical(self, message: str, module_name: str = None, filename: str = None, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, module_name, filename, kwargs)

    # Legacy compatibility methods (for existing code)
    def log_error(self, source: str, message: str, filename: str = None):
        """Legacy error logging method."""
        self.error(message, module_name=source, filename=filename)

    def log_warning(self, message: str, module_name: str = None):
        """Legacy warning logging method - now logs as INFO for initialization messages."""
        # Check if this is an initialization message
        if 'initialized' in message.lower():
            self.info(message, module_name=module_name)
        else:
            self.warning(message, module_name=module_name)

    def log_file_start(self, filename: str, module_name: str = None):
        """Log file processing start."""
        self.info(f"Processing started: {filename}", module_name=module_name, filename=filename)

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        stats = self.session_stats.copy()
        stats.update({
            'session_duration_seconds': session_duration,
            'messages_per_minute': (self.session_stats['total_messages'] / max(session_duration / 60, 1)),
            'active_modules': len(self.module_contexts),
            'log_file': str(self.log_file) if self.log_file else None,
            'log_file_size_mb': self.log_file.stat().st_size / (1024 * 1024) if self.log_file and self.log_file.exists() else 0
        })
        
        return stats

class ModuleLogger:
    """
    Module-specific logger interface that automatically includes module context.
    """
    
    def __init__(self, base_logger: ProfessionalLogger, context: ModuleContext):
        self.base_logger = base_logger
        self.context = context
        self.module_name = context.module_name

    def push_operation(self, operation: str):
        """Add operation to the context stack."""
        self.context.push_operation(operation)

    def pop_operation(self):
        """Remove operation from the context stack."""
        return self.context.pop_operation()

    def debug(self, message: str, filename: str = None, **kwargs):
        """Log debug message with module context."""
        self.base_logger.debug(message, self.module_name, filename, **kwargs)

    def info(self, message: str, filename: str = None, **kwargs):
        """Log info message with module context."""
        self.base_logger.info(message, self.module_name, filename, **kwargs)

    def warning(self, message: str, filename: str = None, **kwargs):
        """Log warning message with module context."""
        self.base_logger.warning(message, self.module_name, filename, **kwargs)

    def error(self, message: str, filename: str = None, **kwargs):
        """Log error message with module context."""
        self.base_logger.error(message, self.module_name, filename, **kwargs)

    def critical(self, message: str, filename: str = None, **kwargs):
        """Log critical message with module context."""
        self.base_logger.critical(message, self.module_name, filename, **kwargs)

    # Convenience methods for common operations
    def log_analysis_start(self, filename: str):
        """Log analysis start with operation context."""
        self.push_operation("analysis")
        self.info(f"Starting analysis", filename=filename)

    def log_analysis_complete(self, filename: str, result: str = "success"):
        """Log analysis completion."""
        self.info(f"Analysis completed: {result}", filename=filename)
        self.pop_operation()

    def log_processing_start(self, filename: str, action: str):
        """Log processing start with operation context."""
        self.push_operation(f"processing:{action}")
        self.info(f"Starting {action}", filename=filename)

    def log_processing_complete(self, filename: str, action: str, result: str = "success"):
        """Log processing completion."""
        self.info(f"Completed {action}: {result}", filename=filename)
        self.pop_operation()

# Global logger instance for backward compatibility
_global_logger: Optional[ProfessionalLogger] = None

def get_global_logger() -> ProfessionalLogger:
    """Get or create global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = ProfessionalLogger()
    return _global_logger

def set_global_logger(logger: ProfessionalLogger):
    """Set the global logger instance."""
    global _global_logger
    _global_logger = logger

# Example usage and testing
if __name__ == "__main__":
    print(f"{__module_name__} v{__version__} - Enhanced Context Logging Test")
    print("=" * 70)
    
    # Create enhanced logger
    logger = ProfessionalLogger("test_enhanced.log", "test_directory", "tv")
    
    # Test module registration and context logging
    analyzer_logger = logger.get_module_logger("video_analyzer", "3.1")
    processor_logger = logger.get_module_logger("video_processor", "3.1")
    
    # Test context-aware logging
    print("\n🧪 Testing Context-Aware Logging:")
    
    analyzer_logger.info("Module initialized successfully")
    analyzer_logger.log_analysis_start("test_video.mkv")
    analyzer_logger.warning("Found unusual codec configuration", filename="test_video.mkv")
    analyzer_logger.log_analysis_complete("test_video.mkv", "completed with warnings")
    
    processor_logger.info("Module initialized successfully")
    processor_logger.log_processing_start("test_video.mkv", "h265_conversion")
    processor_logger.error("FFmpeg timeout occurred", filename="test_video.mkv")
    processor_logger.log_processing_complete("test_video.mkv", "h265_conversion", "failed")
    
    # Test legacy compatibility
    print("\n🔄 Testing Legacy Compatibility:")
    logger.log_error("size_checker", "File size anomaly detected", "problem_video.mkv")
    logger.log_warning("File marked as .rb for safety")
    
    # Show session statistics
    stats = logger.get_session_statistics()
    print(f"\n📊 Session Statistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subvalue in value.items():
                print(f"    {subkey}: {subvalue}")
        elif isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n✅ Enhanced logging v{__version__} with module context ready!")
    print("Key features:")
    print("  - Module-aware logging with context")
    print("  - Operation stack tracking")
    print("  - Colored console output")
    print("  - Legacy compatibility")
    print("  - Session statistics")
    print("  - Automatic log rotation")
