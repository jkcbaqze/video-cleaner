#!/usr/bin/env python3
"""
Complete Universal Video Cleaner - Main Driver v3.3
Professional video processing with integrated configuration management,
session tracking, enhanced logging, and improved menu validation.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple

__module_name__ = "Video Cleaner"
__version__ = "3.3"

def module_ping():
    """Module health check for dry run reporting."""
    return f"{__module_name__} v{__version__} - READY"

# Load configuration FIRST before anything else
try:
    from config_manager import ConfigManager
    config_manager = ConfigManager()
    if not config_manager.is_valid():
        print("❌ Configuration validation failed - check master_config.json")
        sys.exit(1)
except Exception as e:
    print(f"🚨 CRITICAL: Cannot load configuration system: {e}")
    print("Please ensure config_manager.py and master_config.json are present")
    sys.exit(1)

# Rich imports with fallback (controlled by config)
USE_RICH_UI = config_manager.get('main_driver', 'interface.use_rich_ui', True)
FALLBACK_TO_BASIC = config_manager.get('main_driver', 'interface.fallback_to_basic', True)

try:
    if USE_RICH_UI:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt, Confirm
        from rich.tree import Tree
        from rich.table import Table
        from rich.progress import Progress, TaskID
        RICH_AVAILABLE = True
    else:
        raise ImportError("Rich UI disabled in configuration")
except ImportError:
    if FALLBACK_TO_BASIC:
        RICH_AVAILABLE = False
        class Console:
            def print(self, *args, **kwargs):
                style = kwargs.get('style', '')
                if 'red' in str(style):
                    print('ERROR:', *args)
                elif 'green' in str(style):
                    print('SUCCESS:', *args)
                elif 'yellow' in str(style):
                    print('WARNING:', *args)
                else:
                    print(*args)
    else:
        print("❌ Rich UI required but not available - check configuration")
        sys.exit(1)

# Import worker modules with version checking
worker_modules = {}
try:
    from logger import ProfessionalLogger
    worker_modules['logger'] = ProfessionalLogger
    
    from analyzer import VideoAnalyzer
    worker_modules['analyzer'] = VideoAnalyzer
    
    from processor import VideoProcessor
    worker_modules['processor'] = VideoProcessor
    
    from standardizer import FilenameStandardizer
    worker_modules['standardizer'] = FilenameStandardizer
    
    from utils import DirectoryScanner, EpisodeTracker, format_size, validate_directory_path, validate_drive
    worker_modules['utils'] = 'multiple_classes'
    
    from size_checker import VideoSizeChecker
    worker_modules['size_checker'] = VideoSizeChecker
    
    from recovery_manager import RecoveryManager
    worker_modules['recovery_manager'] = RecoveryManager
    
except ImportError as e:
    print(f"ERROR: Missing worker module: {e}")
    print("\nRequired modules:")
    print("- logger.py (Professional Logger)")
    print("- analyzer.py (Video Analyzer)")
    print("- processor.py (Video Processor)")  
    print("- standardizer.py (Filename Standardizer)")
    print("- utils.py (Directory Scanner & Utilities)")
    print("- size_checker.py (Video Size Checker)")
    print("- recovery_manager.py (Recovery Manager)")
    print("\nPlease ensure all modules are in the same directory.")
    sys.exit(1)

def cleanup_python_cache():
    """Clean Python cache at startup if configured."""
    if not config_manager.get('main_driver', 'application.exit_cleanup_cache', True):
        return
        
    import shutil
    try:
        cache_path = Path("__pycache__")
        if cache_path.exists():
            shutil.rmtree(cache_path)
            print("✅ Cleared Python cache for fresh start")
    except Exception:
        # Don't crash if cleanup fails - just continue
        pass

def validate_ffmpeg_installation() -> Tuple[bool, str, Dict[str, str]]:
    """
    Validate FFmpeg installation before starting the application.
    
    Returns:
        (is_valid, error_message, paths_found)
    """
    import shutil
    
    ffmpeg_paths = config_manager.get_ffmpeg_paths()
    found_paths = {}
    
    # Check for both ffmpeg and ffprobe
    required_tools = ['ffmpeg', 'ffprobe']
    
    for tool in required_tools:
        found = False
        
        # Try each configured path
        for base_path in ffmpeg_paths:
            if tool in base_path.lower():
                # Direct path to specific tool
                if Path(base_path).exists():
                    found_paths[tool] = base_path
                    found = True
                    break
            else:
                # Base path - try to find tool
                tool_exe = f"{tool}.exe"
                
                # Try as directory
                if Path(base_path).is_dir():
                    tool_path = Path(base_path) / tool_exe
                    if tool_path.exists():
                        found_paths[tool] = str(tool_path)
                        found = True
                        break
                
                # Try using shutil.which
                try:
                    which_result = shutil.which(tool)
                    if which_result:
                        found_paths[tool] = which_result
                        found = True
                        break
                except Exception:
                    continue
        
        # If not found in configured paths, try system PATH
        if not found:
            try:
                which_result = shutil.which(tool)
                if which_result:
                    found_paths[tool] = which_result
                    found = True
            except Exception:
                pass
        
        if not found:
            error_msg = f"""
❌ CRITICAL: {tool.upper()} not found!

Video processing requires both FFmpeg and FFprobe to be installed.

INSTALLATION OPTIONS:

1. CHOCOLATEY (Recommended for Windows):
   choco install ffmpeg

2. MANUAL INSTALLATION:
   - Download: https://ffmpeg.org/download.html#build-windows
   - Extract to: C:\\ffmpeg\\
   - Add to PATH: C:\\ffmpeg\\bin

3. PORTABLE INSTALLATION:
   - Download FFmpeg Windows build
   - Extract anywhere (e.g., C:\\tools\\ffmpeg\\)
   - Update master_config.json with correct paths

CURRENT SEARCH PATHS:
{chr(10).join(f"  - {path}" for path in ffmpeg_paths)}

After installation, restart the script.
"""
            return False, error_msg, found_paths
    
    return True, "", found_paths

class SessionTracker:
    """Tracks session activity for enhanced goodbye message."""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.iterations = []
        self.total_files_processed = 0
        self.total_space_saved = 0
        self.last_activity = datetime.now()
        
        # Get session limits from config
        self.max_iterations = config_manager.get('main_driver', 'session.max_iterations', 50)
        self.session_timeout_minutes = config_manager.get('main_driver', 'session.session_timeout_minutes', 120)
        self.track_statistics = config_manager.get('main_driver', 'session.track_statistics', True)
        self.enhanced_goodbye = config_manager.get('main_driver', 'session.enhanced_goodbye', True)
    
    def add_iteration(self, iteration_type: str, mode: str, directory: str, 
                     files_count: int = 0, space_saved: int = 0):
        """Add an iteration to the session history."""
        iteration = {
            'timestamp': datetime.now(),
            'type': iteration_type,  # 'dry_run' or 'processing'
            'mode': mode,           # 'tv' or 'movie'
            'directory': Path(directory).name,
            'files_count': files_count,
            'space_saved': space_saved
        }
        self.iterations.append(iteration)
        self.total_files_processed += files_count
        self.total_space_saved += space_saved
        self.last_activity = datetime.now()
        
        # Check session limits
        if len(self.iterations) >= self.max_iterations:
            print(f"⚠️ Maximum iterations ({self.max_iterations}) reached")
        
        session_duration = self.get_session_duration()
        if session_duration.total_seconds() > (self.session_timeout_minutes * 60):
            print(f"⚠️ Session timeout ({self.session_timeout_minutes} minutes) approached")
    
    def get_session_duration(self) -> timedelta:
        """Get total session duration."""
        return datetime.now() - self.session_start
    
    def get_time_since_last_activity(self) -> timedelta:
        """Get time since last activity."""
        return datetime.now() - self.last_activity
    
    def generate_goodbye_message(self) -> str:
        """Generate enhanced goodbye message with session statistics."""
        if not self.enhanced_goodbye:
            return "👋 Goodbye! Thanks for using Universal Video Cleaner!"
            
        duration = self.get_session_duration()
        last_activity = self.get_time_since_last_activity()
        
        # Format duration
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"
        
        # Build message
        panel_width = config_manager.get('main_driver', 'interface.panel_width', 80)
        message_lines = [
            "=" * panel_width,
            "SESSION SUMMARY",
            "=" * panel_width,
            f"Script active for: {duration_str}",
            f"Total iterations: {len(self.iterations)}"
        ]
        
        # Add iteration details if tracking enabled
        if self.track_statistics and self.iterations:
            for i, iteration in enumerate(self.iterations, 1):
                timestamp = iteration['timestamp'].strftime('%H:%M')
                iter_type = "Dry Run" if iteration['type'] == 'dry_run' else "Processing"
                mode = iteration['mode'].title()
                directory = iteration['directory']
                
                if iteration['files_count'] > 0:
                    message_lines.append(f"  [{timestamp}] {iter_type} - {mode} - {directory} ({iteration['files_count']} files)")
                else:
                    message_lines.append(f"  [{timestamp}] {iter_type} - {mode} - {directory}")
        
        # Add totals if any processing occurred
        if self.total_files_processed > 0:
            message_lines.extend([
                f"Files processed this session: {self.total_files_processed}",
                f"Space saved this session: {format_size(self.total_space_saved)}"
            ])
        
        # Add last activity time
        last_activity_seconds = int(last_activity.total_seconds())
        if last_activity_seconds > 60:
            last_activity_minutes = last_activity_seconds // 60
            message_lines.append(f"Last activity: {last_activity_minutes} minutes ago")
        elif last_activity_seconds > 10:
            message_lines.append(f"Last activity: {last_activity_seconds} seconds ago")
        
        # Add hero status for fun
        if self.total_files_processed > 0:
            message_lines.append(f"HERO STATUS: You've rescued {self.total_files_processed} video files from format chaos! 🦸‍♂️")
        
        message_lines.extend([
            "=" * panel_width,
            "",
            "👋 Goodbye! Thanks for using Universal Video Cleaner!",
            "May your codecs be forever compatible! 🎬✨"
        ])
        
        return "\n".join(message_lines)

class VideoCleanerConfig:
    """Configuration container that pulls from master config."""
    
    def __init__(self):
        # Directory settings
        self.main_directory: Optional[Path] = None
        self.recovery_drive: Optional[Path] = None
        
        # Processing mode
        self.processing_mode = "tv"  # Default value
        self.mode_explicitly_set = False  # Track if user has explicitly chosen mode
        
        # Load settings from master config
        self.protection_level = config_manager.get('protection_system', 'rollback.enable_rollback_protection', True)
        
        # Processing options from config
        self.remove_all_subtitles = False  # Set during configuration
        self.convert_to_h265 = config_manager.get('video_processor', 'conversion.force_h265_conversion', True)
        self.clean_filenames = config_manager.get('filename_standardizer', 'cleaning.aggressive_cleaning', True)
        
        # Size checking options from config
        self.enable_size_checking = config_manager.get('size_checker', 'tv_shows.enable_size_checking', True)
        
        # Performance settings from config
        self.enable_integrity_checks = config_manager.get('protection_system', 'integrity.verify_after_processing', True)
        self.processing_timeout = config_manager.get('video_processor', 'ffmpeg.processing_timeout_seconds', 600)
        
        # Logging from config
        self.log_filename = ""
        self.verbose_logging = config_manager.get('logger', 'output.file_output', True)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary for logging."""
        protection_desc = "Rollback + Recovery" if 'recovery' in str(self.protection_level) else "Rollback Only"
        
        return {
            'processing_mode': self.processing_mode.title(),
            'protection_level': protection_desc,
            'recovery_enabled': 'recovery' in str(self.protection_level),
            'rollback_enabled': bool(self.protection_level),
            'recovery_path': str(self.recovery_drive) if self.recovery_drive else "Disabled",
            'convert_h265': self.convert_to_h265,
            'remove_all_subs': self.remove_all_subtitles,
            'clean_filenames': self.clean_filenames,
            'integrity_checks': self.enable_integrity_checks,
            'size_checking': self.enable_size_checking,
            'timeout': f"{self.processing_timeout}s",
            'config_source': 'master_config.json'
        }

class EnhancedUniversalVideoCleaner:
    """Enhanced main video cleaner orchestrator with integrated configuration."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else Console()
        self.config = VideoCleanerConfig()
        self.session_tracker = SessionTracker()
        
        # Worker modules (initialized when needed)
        self.logger: Optional[ProfessionalLogger] = None
        self.analyzer: Optional[VideoAnalyzer] = None
        self.processor: Optional[VideoProcessor] = None
        self.standardizer: Optional[FilenameStandardizer] = None
        self.scanner: Optional[DirectoryScanner] = None
        self.episode_tracker: Optional[EpisodeTracker] = None
        self.size_checker: Optional[VideoSizeChecker] = None
        self.recovery_manager: Optional[RecoveryManager] = None
        
        # Statistics
        self.session_stats = {
            'session_start': datetime.now(),
            'files_found': 0,
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'files_rb_marked': 0,
            'files_size_flagged': 0,
            'total_space_saved': 0,
            'total_processing_time': 0.0
        }
    
    def show_welcome(self):
        """Display enhanced welcome screen with version from config."""
        app_name = config_manager.get('main_driver', 'application.name', 'Universal Video Cleaner')
        show_version = config_manager.get('main_driver', 'application.version_display', True)
        show_panel = config_manager.get('main_driver', 'application.show_welcome_panel', True)
        
        version_text = f" v{__version__}" if show_version else ""
        
        if RICH_AVAILABLE and show_panel:
            welcome_panel = Panel.fit(
                f"[bold blue]{app_name}{version_text}[/bold blue]\n"
                "[cyan]Enhanced with Smart Size Detection & Session Tracking[/cyan]\n\n"
                "[green]Features:[/green]\n"
                "• Language cleaning & filename standardization\n"
                "• Universal format conversion → H.265 MKV\n"
                "• Smart size anomaly detection (configurable)\n"
                "• Recovery + Rollback protection system\n"
                "• Missing episode detection\n"
                "• Professional logging with session tracking\n"
                "• Module version verification & health checks\n\n"
                "[yellow]Supported: MKV, MP4, AVI, MOV, M4V, WMV, FLV, WebM, OGV[/yellow]\n"
                "[dim]Perfect for desktop processing - one directory at a time![/dim]",
                style="bold",
                title="🎬 Professional Video Processing"
            )
            self.console.print(welcome_panel)
        else:
            self.console.print(f"{app_name}{version_text}")
            self.console.print("=" * 70)
            self.console.print("Enhanced with Smart Size Detection & Session Tracking")
            self.console.print("Features: Language cleaning, format conversion, size checking")
            self.console.print("Supported: MKV, MP4, AVI, MOV, M4V, WMV, FLV, WebM, OGV")
            self.console.print("Perfect for desktop processing - one directory at a time!")
    
    def check_configuration_health(self) -> Dict[str, str]:
        """Check configuration system health."""
        health_report = {}
        
        try:
            # Check config file status
            config_info = config_manager.get_config_info()
            
            if config_info['is_valid']:
                health_report['master_config.json'] = f"v{config_manager.get('_metadata.config_version', 'unknown')} - LOADED ✓"
            else:
                health_report['master_config.json'] = f"VALIDATION ERRORS ⚠️ ({config_info['error_count']} errors)"
            
            # Check for config changes
            if config_manager.has_config_changed():
                health_report['config_status'] = "CHANGED - Reload recommended ⚠️"
            else:
                health_report['config_status'] = "CURRENT ✓"
                
        except Exception as e:
            health_report['master_config.json'] = f"ERROR ❌ ({str(e)[:50]})"
        
        return health_report
    
    def check_module_health(self) -> Dict[str, str]:
        """Check all worker modules and their versions with detailed context."""
        health_report = {}
        
        # First check configuration health
        config_health = self.check_configuration_health()
        health_report.update(config_health)
        
        # Check FFmpeg installation first (critical requirement)
        ffmpeg_valid, ffmpeg_error, ffmpeg_paths = validate_ffmpeg_installation()
        
        if ffmpeg_valid:
            health_report['FFmpeg'] = f"✓ FOUND - FFmpeg: {ffmpeg_paths.get('ffmpeg', 'Unknown')}"
            health_report['FFprobe'] = f"✓ FOUND - FFprobe: {ffmpeg_paths.get('ffprobe', 'Unknown')}"
        else:
            health_report['FFmpeg'] = "❌ MISSING - Cannot process videos"
            health_report['FFprobe'] = "❌ MISSING - Cannot analyze videos"
        
        # Import modules to check their versions directly
        import sys
        
        # Check each module with enhanced context
        modules_to_check = [
            ('logger', 'ProfessionalLogger', 'Logging and session tracking'),
            ('analyzer', 'VideoAnalyzer', 'Video file analysis with FFprobe'), 
            ('processor', 'VideoProcessor', 'Video processing orchestration'),
            ('standardizer', 'FilenameStandardizer', 'Filename cleaning and standardization'),
            ('utils', 'DirectoryScanner & Utilities', 'Directory scanning and episode tracking'),
            ('size_checker', 'VideoSizeChecker', 'Size anomaly detection')
        ]
        
        for module_name, class_name, description in modules_to_check:
            try:
                # Get the actual module from sys.modules to read __version__
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    version = getattr(module, '__version__', 'unknown')
                    
                    # Test module functionality with ping
                    try:
                        if hasattr(module, 'module_ping'):
                            ping_result = module.module_ping()
                            health_report[f"{module_name}.py"] = f"v{version} - READY ✓ ({description})"
                        else:
                            health_report[f"{module_name}.py"] = f"v{version} - LOADED ✓ ({description})"
                    except Exception as ping_error:
                        health_report[f"{module_name}.py"] = f"v{version} - PING FAILED ⚠️ ({str(ping_error)[:30]})"
                else:
                    health_report[f"{module_name}.py"] = f"FAILED TO LOAD ❌ ({description})"
            except Exception as e:
                health_report[f"{module_name}.py"] = f"ERROR ❌ ({str(e)[:50]})"
        
        return health_report

    def get_main_directory(self) -> bool:
        """Get and validate main directory from user."""
        while True:
            try:
                if RICH_AVAILABLE:
                    main_dir_input = Prompt.ask("🗂️ Enter directory path to process")
                else:
                    main_dir_input = input("Enter directory path to process: ").strip()
                
                self.config.main_directory = validate_directory_path(main_dir_input)
                
                # Initialize scanner to show preview
                self.scanner = DirectoryScanner()
                
                if self.show_directory_preview():
                    self.console.print(f"[green]✅ Directory confirmed: {self.config.main_directory}[/green]")
                    return True
                else:
                    self.console.print("[yellow]Please enter a different directory path.[/yellow]")
            except ValueError as e:
                self.console.print(f"[red]❌ Error: {e}[/red]")
                self.console.print("[yellow]Please try again.[/yellow]")
    
    def show_directory_preview(self) -> bool:
        """Show enhanced directory structure preview."""
        if RICH_AVAILABLE:
            self.console.print(Panel.fit("📂 Directory Structure Preview", style="bold blue"))
        else:
            self.console.print("\n📂 Directory Structure Preview")
            self.console.print("-" * 40)
        
        try:
            folder_info, format_counts = self.scanner.preview_directory(self.config.main_directory)
            
            if RICH_AVAILABLE:
                tree = Tree(f"📁 [bold blue]{self.config.main_directory}[/bold blue]")
                
                for folder_name, formats in folder_info.items():
                    if formats:
                        format_str = ", ".join([f"[cyan]{count} {fmt}[/cyan]" for fmt, count in formats.items()])
                        tree.add(f"📁 {folder_name}/ ({format_str})")
                
                self.console.print(tree)
                
                if format_counts:
                    format_table = Table(title="📊 Format Summary", show_header=True, header_style="bold magenta")
                    format_table.add_column("Format", style="cyan")
                    format_table.add_column("Count", style="green")
                    
                    for fmt, count in sorted(format_counts.items()):
                        format_table.add_row(fmt, str(count))
                    
                    self.console.print(format_table)
            else:
                for folder_name, formats in folder_info.items():
                    if formats:
                        format_str = ", ".join([f"{count} {fmt}" for fmt, count in formats.items()])
                        self.console.print(f"  📁 {folder_name}/ ({format_str})")
                
                if format_counts:
                    self.console.print("\nFormat Summary:")
                    for fmt, count in sorted(format_counts.items()):
                        self.console.print(f"  {fmt}: {count}")
            
            total_files = sum(format_counts.values())
            self.console.print(f"\n[bold]Total: {len(folder_info)} folders, {total_files} video files[/bold]")
            
            if RICH_AVAILABLE:
                return Confirm.ask("\nProcess this directory?")
            else:
                response = input("\nProcess this directory? (y/n): ").strip().lower()
                return response == 'y'
                
        except Exception as e:
            self.console.print(f"[red]Error reading directory: {e}[/red]")
            return False

    def initialize_workers(self, is_dry_run: bool = False):
        """Initialize all worker modules with current configuration."""
        # Create log filename from directory name
        dir_name = self.config.main_directory.name
        clean_name = "".join(c for c in dir_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_').lower()
        timestamp = datetime.now().strftime('%m%d%H%M')
        
        if is_dry_run:
            self.config.log_filename = f"{clean_name}-dry_run-{timestamp}.log"
        else:
            self.config.log_filename = f"{clean_name}-{timestamp}.log"
        
        # Initialize logger with config
        self.logger = ProfessionalLogger(
            log_filename=self.config.log_filename,
            directory_name=str(self.config.main_directory),
            mode=self.config.processing_mode,
            config_manager=config_manager
        )
        
        # Log configuration with dry run indicator
        config_dict = self.config.to_dict()
        if is_dry_run:
            config_dict['mode_type'] = "DRY RUN - FOR ANALYSIS ONLY"
        
        if hasattr(self.logger, 'log_configuration'):
            self.logger.log_configuration(config_dict, is_dry_run)
        else:
            self.logger.info(f"Configuration: {config_dict}")
        
        # Log module health check
        health_report = self.check_module_health()
        if hasattr(self.logger, 'log_module_health_check'):
            self.logger.log_module_health_check(health_report)
        else:
            self.logger.info(f"Module health: {health_report}")
        
        # Initialize other workers with config
        self.analyzer = VideoAnalyzer(logger=self.logger, config_manager=config_manager)
        self.standardizer = FilenameStandardizer(
            processing_mode=self.config.processing_mode,
            logger=self.logger,
            config_manager=config_manager
        )
        
        # Initialize size checker with main config integration
        if self.config.enable_size_checking:
            self.size_checker = VideoSizeChecker(
                logger=self.logger,
                config_manager=config_manager
            )
        
        self.processor = VideoProcessor(
            config=self.config,
            logger=self.logger,
            standardizer=self.standardizer,
            analyzer=self.analyzer,
            size_checker=self.size_checker,
            config_manager=config_manager
        )
        
        # Initialize episode tracker for TV mode
        if self.config.processing_mode == "tv":
            self.episode_tracker = EpisodeTracker(logger=self.logger)
        
        # Initialize recovery manager for bulletproof operation
        state_filename = f"{clean_name}_recovery_state.json"
        self.recovery_manager = RecoveryManager(
            state_file_path=state_filename,
            logger=self.logger,
            config_manager=config_manager
        )
        
        self.console.print(f"[bold blue]📝 Logging to: {self.config.log_filename}[/bold blue]")
        self.console.print(f"[bold green]🔄 Recovery enabled: {state_filename}[/bold green]")

    def validate_ready_for_processing(self) -> Tuple[bool, str]:
        """
        Validate that all required settings are configured before processing.
        
        Returns:
            (is_ready, missing_requirement_message)
        """
        if not self.config.main_directory:
            return False, "❌ Please set processing directory first (option 1)"
        
        # Check if processing mode has been explicitly set by user
        if not getattr(self.config, 'mode_explicitly_set', False):
            return False, "❌ Please configure processing mode first (option 2)"
        
        # Validate directory still exists
        if not self.config.main_directory.exists():
            return False, f"❌ Directory no longer exists: {self.config.main_directory}"
        
        return True, ""

    def configure_processing_mode(self):
        """Configure TV vs Movie processing mode."""
        if RICH_AVAILABLE:
            self.console.print("\n[bold blue]📺 Processing Mode Configuration[/bold blue]")
            current_mode = self.config.processing_mode
            self.console.print(f"Current mode: [cyan]{current_mode.upper()}[/cyan]")
            
            # Show directory context to help user decide
            if self.config.main_directory:
                self.console.print(f"Directory: [dim]{self.config.main_directory}[/dim]")
                self.console.print("[yellow]Hint: Check your directory name/structure to determine content type[/yellow]")
            
            mode = Prompt.ask(
                "Select processing mode",
                choices=["tv", "movie"],
                default=current_mode
            )
        else:
            print(f"\nCurrent mode: {self.config.processing_mode.upper()}")
            if self.config.main_directory:
                print(f"Directory: {self.config.main_directory}")
                print("Hint: Check your directory name/structure to determine content type")
            
            while True:
                mode = input("Select processing mode (tv/movie): ").strip().lower()
                if mode in ["tv", "movie"]:
                    break
                print("Please enter 'tv' or 'movie'")
        
        # Update mode and mark as explicitly set
        old_mode = self.config.processing_mode
        self.config.processing_mode = mode
        self.config.mode_explicitly_set = True  # Flag to track user has set this
        
        if old_mode != mode:
            self.console.print(f"[green]✅ Processing mode changed: {old_mode.upper()} → {mode.upper()}[/green]")
        else:
            self.console.print(f"[green]✅ Processing mode confirmed: {mode.upper()}[/green]")

    def show_menu_with_status(self):
        """Show menu with current configuration status."""
        if RICH_AVAILABLE:
            self.console.print("\n" + "="*50)
            self.console.print("[bold cyan]📋 MAIN MENU[/bold cyan]")
            self.console.print("="*50)
            
            # Show current status
            dir_status = "✅ Set" if self.config.main_directory else "❌ Not set"
            mode_status = "✅ Set" if getattr(self.config, 'mode_explicitly_set', False) else "❌ Not set"
            
            self.console.print(f"[dim]Directory: {dir_status} | Processing Mode: {mode_status}[/dim]")
            self.console.print()
            
            self.console.print("[green]1.[/green] Set Processing Directory")
            self.console.print("[green]2.[/green] Configure Processing Mode (TV/Movie)")
            self.console.print("[green]3.[/green] Run Dry Analysis (Preview Only)")
            self.console.print("[green]4.[/green] Start Processing")
            self.console.print("[green]5.[/green] Show Module Health")
            self.console.print("[green]6.[/green] Show Session Stats")
            self.console.print("[green]7.[/green] Show Recovery Status")
            self.console.print("[green]0.[/green] Exit")
            
            choice = Prompt.ask("\n🎯 Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7"])
        else:
            print("\n" + "="*50)
            print("MAIN MENU")
            print("="*50)
            
            # Show current status
            dir_status = "Set" if self.config.main_directory else "Not set"
            mode_status = "Set" if getattr(self.config, 'mode_explicitly_set', False) else "Not set"
            print(f"Directory: {dir_status} | Processing Mode: {mode_status}")
            print()
            
            print("1. Set Processing Directory")
            print("2. Configure Processing Mode (TV/Movie)")
            print("3. Run Dry Analysis (Preview Only)")
            print("4. Start Processing")
            print("5. Show Module Health")
            print("6. Show Session Stats")
            print("7. Show Recovery Status")
            print("0. Exit")
            
            choice = input("\nSelect option (0-7): ").strip()
        
        return choice

    def main_menu(self):
        """Enhanced main menu with configuration integration and validation."""
        try:
            # Show welcome screen
            show_welcome = config_manager.get('main_driver', 'application.show_welcome_panel', True)
            if show_welcome:
                self.show_welcome()
            
            # Main processing loop
            while True:
                try:
                    # Check for session limits
                    if len(self.session_tracker.iterations) >= self.session_tracker.max_iterations:
                        self.console.print("[yellow]⚠️ Maximum iterations reached. Starting fresh session.[/yellow]")
                        self.session_tracker = SessionTracker()
                    
                    # Show menu with status
                    choice = self.show_menu_with_status()
                    
                    # Handle menu choices
                    if choice == "0":
                        # Exit
                        goodbye_message = self.session_tracker.generate_goodbye_message()
                        self.console.print(goodbye_message)
                        break
                        
                    elif choice == "1":
                        # Set directory
                        if self.get_main_directory():
                            self.console.print("[green]✅ Directory set successfully[/green]")
                        
                    elif choice == "2":
                        # Configure mode
                        self.configure_processing_mode()
                        
                    elif choice == "3":
                        # Dry run analysis - validate first
                        is_ready, error_msg = self.validate_ready_for_processing()
                        if is_ready:
                            self.run_dry_analysis()
                        else:
                            self.console.print(f"[red]{error_msg}[/red]")
                            
                            # Auto-suggest next step
                            if "directory" in error_msg.lower():
                                self.console.print("[yellow]💡 Choose option 1 to set your directory[/yellow]")
                            elif "processing mode" in error_msg.lower():
                                self.console.print("[yellow]💡 Choose option 2 to configure TV/Movie mode[/yellow]")
                            
                    elif choice == "4":
                        # Start processing - validate first
                        is_ready, error_msg = self.validate_ready_for_processing()
                        if is_ready:
                            self.run_processing()
                        else:
                            self.console.print(f"[red]{error_msg}[/red]")
                            
                            # Auto-suggest next step
                            if "directory" in error_msg.lower():
                                self.console.print("[yellow]💡 Choose option 1 to set your directory[/yellow]")
                            elif "processing mode" in error_msg.lower():
                                self.console.print("[yellow]💡 Choose option 2 to configure TV/Movie mode[/yellow]")
                            
                    elif choice == "5":
                        # Module health
                        self.show_module_health()
                        
                    elif choice == "6":
                        # Session stats
                        self.show_session_stats()
                        
                    elif choice == "7":
                        # Recovery status
                        self.show_recovery_status()
                        
                    else:
                        self.console.print("[red]❌ Invalid choice. Please select 0-7.[/red]")
                        
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]⚠️ Interrupted. Returning to main menu.[/yellow]")
                    continue
                    
        except Exception as e:
            self.console.print(f"[red]❌ Menu error: {e}[/red]")
            if self.logger:
                self.logger.error(f"Main menu error: {e}")

    def run_dry_analysis(self):
        """Run dry analysis without making changes."""
        self.console.print("\n[bold blue]🔍 DRY RUN ANALYSIS[/bold blue]")
        self.console.print("[yellow]This will analyze files without making any changes[/yellow]")
        
        try:
            # Initialize workers for dry run
            self.initialize_workers(is_dry_run=True)
            
            # Get all video files in directory
            video_files = self.scanner._find_all_video_files_simple(self.config.main_directory)
            
            if not video_files:
                self.console.print("[red]❌ No video files found in directory[/red]")
                return
            
            self.console.print(f"[cyan]📁 Found {len(video_files)} video files[/cyan]")
            
            # Analyze each file
            analysis_results = []
            for i, file_path in enumerate(video_files, 1):
                self.console.print(f"[dim]Analyzing {i}/{len(video_files)}: {file_path.name}[/dim]")
                
                # Analyze file
                result = self.processor.process_file(file_path, dry_run=True)
                analysis_results.append(result)
            
            # Show summary
            self.show_dry_run_summary(analysis_results)
            
            # Track session
            self.session_tracker.add_iteration(
                'dry_run', 
                self.config.processing_mode, 
                str(self.config.main_directory),
                len(video_files)
            )
            
        except Exception as e:
            self.console.print(f"[red]❌ Dry run failed: {e}[/red]")
            if self.logger:
                self.logger.error(f"Dry run error: {e}")

    def run_processing(self):
        """Run actual file processing."""
        self.console.print("\n[bold red]⚡ PROCESSING MODE[/bold red]")
        self.console.print("[yellow]This will modify your video files![/yellow]")
        
        if RICH_AVAILABLE:
            proceed = Confirm.ask("Are you sure you want to proceed with processing?")
        else:
            proceed = input("Are you sure you want to proceed? (y/n): ").strip().lower() == 'y'
        
        if not proceed:
            self.console.print("[yellow]Processing cancelled[/yellow]")
            return
        
        try:
            # Initialize workers for real processing
            self.initialize_workers(is_dry_run=False)
            
            # Get all video files
            video_files = self.scanner._find_all_video_files_simple(self.config.main_directory)
            
            if not video_files:
                self.console.print("[red]❌ No video files found in directory[/red]")
                return
            
            # Start recovery session
            video_file_paths = [str(f) for f in video_files]
            session_id = self.recovery_manager.start_session(
                self.config.processing_mode,
                str(self.config.main_directory),
                video_file_paths
            )
            
            # Check if we can resume an existing session
            if self.recovery_manager.can_resume_session():
                self.console.print(f"[yellow]🔄 Resuming previous session: {session_id}[/yellow]")
                pending_files = self.recovery_manager.get_pending_files()
                self.console.print(f"[cyan]📋 {len(pending_files)} files remaining to process[/cyan]")
                video_files = [Path(f) for f in pending_files]
            else:
                self.console.print(f"[cyan]🚀 Processing {len(video_files)} video files[/cyan]")
            
            # Process each file
            processing_results = []
            successful = 0
            failed = 0
            skipped = 0
            
            for i, file_path in enumerate(video_files, 1):
                self.console.print(f"\n[bold]Processing {i}/{len(video_files)}: {file_path.name}[/bold]")
                
                # Mark file as in progress
                self.recovery_manager.mark_file_in_progress(str(file_path))
                
                # Get original file size for tracking
                original_size = file_path.stat().st_size if file_path.exists() else 0
                processing_start_time = time.time()
                
                try:
                    # Process file
                    result = self.processor.process_file(file_path, dry_run=False)
                    processing_results.append(result)
                    processing_time = time.time() - processing_start_time
                    
                    # Update recovery state based on result
                    status = result.get('status', 'unknown')
                    if status in ['success', 'completed']:
                        successful += 1
                        self.console.print("[green]✅ Success[/green]")
                        
                        # Get processed file size if available
                        processed_size = result.get('output_size', original_size)
                        self.recovery_manager.mark_file_completed(
                            str(file_path), 
                            processing_time=processing_time,
                            original_size=original_size,
                            processed_size=processed_size
                        )
                    elif status in ['skipped', 'blocked']:
                        skipped += 1
                        self.console.print("[yellow]⏭️ Skipped[/yellow]")
                        
                        skip_reason = result.get('message', 'Unknown reason')
                        self.recovery_manager.mark_file_skipped(str(file_path), skip_reason)
                    else:
                        failed += 1
                        self.console.print("[red]❌ Failed[/red]")
                        
                        error_message = result.get('message', 'Unknown error')
                        self.recovery_manager.mark_file_failed(
                            str(file_path), 
                            error_message,
                            processing_time=processing_time
                        )
                
                except Exception as e:
                    # Handle unexpected errors
                    failed += 1
                    processing_time = time.time() - processing_start_time
                    self.console.print(f"[red]❌ Exception: {e}[/red]")
                    
                    self.recovery_manager.mark_file_failed(
                        str(file_path), 
                        f"Exception: {str(e)}",
                        processing_time=processing_time
                    )
            
            # Complete recovery session
            self.recovery_manager.complete_session()
            
            # Show final summary with recovery stats
            session_summary = self.recovery_manager.get_session_summary()
            
            self.console.print(f"\n[bold]🏁 PROCESSING COMPLETE[/bold]")
            self.console.print(f"[green]✅ Successful: {successful}[/green]")
            self.console.print(f"[yellow]⏭️ Skipped: {skipped}[/yellow]")
            self.console.print(f"[red]❌ Failed: {failed}[/red]")
            
            # Show space savings if available
            total_space_saved = session_summary['statistics'].get('total_space_saved', 0)
            if total_space_saved > 0:
                space_saved_mb = total_space_saved / (1024 * 1024)
                self.console.print(f"[cyan]💾 Space saved: {space_saved_mb:.1f} MB[/cyan]")
            
            # Show processing time
            total_time = session_summary['statistics'].get('total_processing_time', 0)
            if total_time > 0:
                self.console.print(f"[cyan]⏱️ Total processing time: {total_time:.1f} seconds[/cyan]")
            
            # Track session
            self.session_tracker.add_iteration(
                'processing',
                self.config.processing_mode,
                str(self.config.main_directory),
                len(video_files)
            )
            
        except Exception as e:
            self.console.print(f"[red]❌ Processing failed: {e}[/red]")
            if self.logger:
                self.logger.error(f"Processing error: {e}")

    def show_dry_run_summary(self, results: List[Dict]):
        """Show summary of dry run analysis."""
        needs_conversion = 0
        already_optimized = 0
        problematic = 0
        total_current_size = 0
        estimated_final_size = 0
        
        for result in results:
            if result.get('status') == 'needs_conversion':
                needs_conversion += 1
            elif result.get('status') == 'skipped':
                if 'already' in result.get('message', '').lower():
                    already_optimized += 1
                else:
                    problematic += 1
            
            # Size calculations if available
            current_size = result.get('file_size_bytes', 0)
            estimated_savings = result.get('estimated_savings_bytes', 0)
            total_current_size += current_size
            estimated_final_size += (current_size - estimated_savings)
        
        self.console.print(f"\n[bold blue]📊 DRY RUN SUMMARY[/bold blue]")
        self.console.print(f"[green]🔄 Need conversion: {needs_conversion}[/green]")
        self.console.print(f"[cyan]✅ Already optimized: {already_optimized}[/cyan]")
        self.console.print(f"[yellow]⚠️ Problematic: {problematic}[/yellow]")
        
        if total_current_size > 0:
            current_gb = total_current_size / (1024**3)
            final_gb = estimated_final_size / (1024**3)
            savings_gb = current_gb - final_gb
            savings_percent = (savings_gb / current_gb) * 100
            
            self.console.print(f"\n[bold]💾 SPACE ANALYSIS[/bold]")
            self.console.print(f"Current size: {current_gb:.1f} GB")
            self.console.print(f"Estimated final: {final_gb:.1f} GB")
            self.console.print(f"[green]Potential savings: {savings_gb:.1f} GB ({savings_percent:.1f}%)[/green]")

    def show_module_health(self):
        """Display module health status."""
        health_report = self.check_module_health()
        
        if RICH_AVAILABLE:
            health_table = Table(title="🏥 Module Health Report", show_header=True)
            health_table.add_column("Module", style="cyan")
            health_table.add_column("Status", style="green")
            
            for module, status in health_report.items():
                health_table.add_row(module, status)
            
            self.console.print(health_table)
        else:
            print("\n🏥 Module Health Report")
            print("-" * 40)
            for module, status in health_report.items():
                print(f"{module}: {status}")

    def show_session_stats(self):
        """Show current session statistics."""
        stats = self.session_stats
        duration = datetime.now() - stats['session_start']
        
        self.console.print(f"\n[bold blue]📈 SESSION STATISTICS[/bold blue]")
        self.console.print(f"Session duration: {duration}")
        self.console.print(f"Iterations completed: {len(self.session_tracker.iterations)}")
        
        if stats['files_processed'] > 0:
            self.console.print(f"Files processed: {stats['files_processed']}")
            self.console.print(f"Success rate: {(stats['files_successful']/stats['files_processed']*100):.1f}%")

    def show_recovery_status(self):
        """Show recovery manager status and session information."""
        if not self.recovery_manager:
            self.console.print("[yellow]⚠️ Recovery manager not initialized. Set directory and processing mode first.[/yellow]")
            return
        
        try:
            session_summary = self.recovery_manager.get_session_summary()
            
            self.console.print(f"\n[bold blue]🔄 RECOVERY STATUS[/bold blue]")
            
            # Session info
            session_info = session_summary['session_info']
            if session_info.get('session_id'):
                self.console.print(f"Current session: {session_info['session_id']}")
                self.console.print(f"Processing mode: {session_info.get('processing_mode', 'Unknown')}")
                self.console.print(f"Directory: {session_info.get('directory_path', 'Unknown')}")
                
                # Show session status
                if session_info.get('session_completed'):
                    self.console.print("[green]✅ Session completed[/green]")
                elif session_summary['can_resume']:
                    self.console.print("[yellow]🔄 Session can be resumed[/yellow]")
                else:
                    self.console.print("[blue]📋 Session active[/blue]")
                
                # Show progress
                progress = session_summary.get('progress_percentage', 0)
                self.console.print(f"Progress: {progress:.1f}%")
                
                # Show statistics
                stats = session_summary['statistics']
                self.console.print(f"\n[bold]File Statistics:[/bold]")
                self.console.print(f"  Pending: {stats['files_pending']}")
                self.console.print(f"  In Progress: {stats['files_in_progress']}")
                self.console.print(f"  Completed: {stats['files_completed']}")
                self.console.print(f"  Failed: {stats['files_failed']}")
                self.console.print(f"  Skipped: {stats['files_skipped']}")
                self.console.print(f"  Corrupted: {stats['files_corrupted']}")
                self.console.print(f"  RB Marked: {stats['files_rb_marked']}")
                
                # Show space savings
                space_saved = stats.get('total_space_saved', 0)
                if space_saved > 0:
                    space_mb = space_saved / (1024 * 1024)
                    self.console.print(f"  Space saved: {space_mb:.1f} MB")
                
                # Show recent errors
                recent_errors = session_summary.get('recent_errors', [])
                if recent_errors:
                    self.console.print(f"\n[bold red]Recent Errors:[/bold red]")
                    for error in recent_errors[-3:]:  # Show last 3 errors
                        timestamp = error.get('timestamp', 'Unknown')
                        file_name = Path(error.get('file', '')).name
                        error_msg = error.get('error', 'Unknown error')
                        self.console.print(f"  {timestamp}: {file_name} - {error_msg}")
                
                # Show estimated time remaining
                eta = session_summary.get('estimated_time_remaining')
                if eta and eta > 0:
                    eta_minutes = eta / 60
                    self.console.print(f"\nEstimated time remaining: {eta_minutes:.1f} minutes")
            
            else:
                self.console.print("[dim]No active recovery session[/dim]")
                
        except Exception as e:
            self.console.print(f"[red]❌ Error retrieving recovery status: {e}[/red]")

def main():
    """Enhanced application entry point with FFmpeg validation."""
    # Clean Python cache if configured
    cleanup_python_cache()
    
    try:
        app_name = config_manager.get('main_driver', 'application.name', 'Universal Video Cleaner')
        print(f"{app_name} v{__version__} - Starting up...")
        
        # Check configuration health first
        config_info = config_manager.get_config_info()
        if not config_info['is_valid']:
            print(f"⚠️ Configuration has {config_info['error_count']} validation errors")
            print("Proceeding with fallback defaults...")
        
        print("Module health check:")
        
        # Quick module ping
        health_check = {
            'video_cleaner.py': module_ping(),
            'master_config.json': f"Loaded - {config_info['config_sections']} sections"
        }
        
        for module, status in health_check.items():
            print(f"  {module}: {status}")
        
        # CRITICAL: Validate FFmpeg before proceeding
        print("\nFFmpeg validation:")
        ffmpeg_valid, ffmpeg_error, ffmpeg_paths = validate_ffmpeg_installation()
        
        if not ffmpeg_valid:
            print(ffmpeg_error)
            print("\n" + "="*60)
            print("❌ APPLICATION CANNOT CONTINUE WITHOUT FFMPEG")
            print("="*60)
            print("\nPlease install FFmpeg and restart the application.")
            
            # Wait for user acknowledgment
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        # FFmpeg found - show paths and continue
        print("  ✅ FFmpeg validation successful:")
        for tool, path in ffmpeg_paths.items():
            print(f"    {tool}: {path}")
        
        print()
        
        cleaner = EnhancedUniversalVideoCleaner()
        cleaner.main_menu()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        print("Session ended gracefully. 👋")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Please check configuration and try again.")
        print("Check master_config.json and ensure all worker modules are present.")

if __name__ == "__main__":
    main()
