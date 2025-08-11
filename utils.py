#!/usr/bin/env python3
"""
Enhanced Bulletproof Simple Utilities Module with Rust Integration
Reliable utilities with Rust-powered directory scanning for industrial performance.
Graceful fallback to Python if Rust is not available.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from collections import defaultdict

# Version information
__version__ = "3.3"
__module_name__ = "Enhanced Utilities with Rust Core"

# Try to import Rust core for performance
try:
    import videocleaner_core
    RUST_CORE_AVAILABLE = True
    RUST_VERSION = getattr(videocleaner_core, '__version__', 'unknown')
except ImportError:
    RUST_CORE_AVAILABLE = False
    RUST_VERSION = None

def module_ping():
    """Module health check for dry run reporting."""
    rust_status = f"+ Rust v{RUST_VERSION}" if RUST_CORE_AVAILABLE else "Python fallback"
    return f"{__module_name__} v{__version__} ({rust_status}) - READY"

class DirectoryScanner:
    def __init__(self, logger=None):
        self.logger = logger
        self.video_formats = {
            '.mkv', '.mp4', '.avi', '.mov', '.m4v', '.wmv',
            '.flv', '.webm', '.ogv', '.ts', '.m2ts'
        }
        
        # Performance tracking
        self.scan_method_used = None
        self.last_scan_time = 0.0
        
        if self.logger:
            rust_status = "with Rust acceleration" if RUST_CORE_AVAILABLE else "Python-only mode"
            self.logger.log_warning(f"{__module_name__} v{__version__}: DirectoryScanner initialized {rust_status}")

    def preview_directory(self, directory_path: Path) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
        """Enhanced directory preview with Rust acceleration when available."""
        if self.logger:
            scan_method = "Rust-accelerated" if RUST_CORE_AVAILABLE else "Python fallback"
            self.logger.log_warning(f"{__module_name__}: Starting {scan_method} recursive scan of {directory_path}")

        start_time = datetime.now()

        try:
            if RUST_CORE_AVAILABLE:
                # Use lightning-fast Rust implementation
                folder_info, total_format_counts = self._preview_directory_rust(directory_path)
                self.scan_method_used = "rust"
            else:
                # Fallback to reliable Python implementation
                folder_info, total_format_counts = self._preview_directory_python(directory_path)
                self.scan_method_used = "python"
            
            # Record performance metrics
            scan_duration = (datetime.now() - start_time).total_seconds()
            self.last_scan_time = scan_duration
            
            total_files = sum(total_format_counts.values())
            
            if self.logger:
                method_emoji = "🦀" if self.scan_method_used == "rust" else "🐍"
                self.logger.log_warning(f"{__module_name__}: {method_emoji} Scan completed in {scan_duration:.2f}s - {total_files} files found")

            return folder_info, total_format_counts

        except Exception as e:
            if self.logger:
                self.logger.log_error('directory_scanner', f'Scan failed: {str(e)}')
            
            # If Rust failed, try Python fallback
            if RUST_CORE_AVAILABLE and self.scan_method_used != "python":
                if self.logger:
                    self.logger.log_warning("Rust scan failed, attempting Python fallback...")
                try:
                    folder_info, total_format_counts = self._preview_directory_python(directory_path)
                    self.scan_method_used = "python_fallback"
                    return folder_info, total_format_counts
                except Exception as fallback_error:
                    if self.logger:
                        self.logger.log_error('directory_scanner', f'Python fallback also failed: {str(fallback_error)}')
            
            return {}, {}

    def _preview_directory_rust(self, directory_path: Path) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
        """Rust-accelerated directory scanning."""
        folder_info_rust, total_format_counts_rust = videocleaner_core.scan_directory_fast(str(directory_path))
        
        # Convert to the format expected by the rest of the application
        folder_info = {folder: dict(counts) for folder, counts in folder_info_rust.items()}
        total_format_counts = dict(total_format_counts_rust)
        
        return folder_info, total_format_counts

    def _preview_directory_python(self, directory_path: Path) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
        """Python fallback implementation - your original reliable code."""
        folder_info = {}
        total_format_counts = defaultdict(int)
        all_video_files = self._find_all_video_files_simple(directory_path)

        if self.logger:
            self.logger.log_warning(f"{__module_name__}: Python scan found {len(all_video_files)} total video files")

        for video_file in all_video_files:
            parent_folder = video_file.parent.name
            file_ext = video_file.suffix.upper()
            folder_info.setdefault(parent_folder, defaultdict(int))[file_ext] += 1
            total_format_counts[file_ext] += 1

        clean_folder_info = {folder: dict(counts) for folder, counts in folder_info.items()}
        return clean_folder_info, dict(total_format_counts)

    def _find_all_video_files_simple(self, directory_path: Path) -> List[Path]:
        """Your original reliable Python file finder."""
        video_files = []
        try:
            for file_path in directory_path.rglob('*'):
                try:
                    if not file_path.is_file():
                        continue
                    if file_path.name.startswith('.') or file_path.suffix.lower() == '.rb':
                        continue
                    if file_path.suffix.lower() in self.video_formats:
                        video_files.append(file_path)
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"{__module_name__}: Recursive scan error: {str(e)}")
        return video_files

    def find_all_video_files(self, directory_path: Path) -> List[Path]:
        """Public method to get all video files with Rust acceleration."""
        if RUST_CORE_AVAILABLE:
            try:
                # Use Rust for file listing
                file_paths_str = videocleaner_core.find_video_files(str(directory_path))
                return [Path(path) for path in file_paths_str]
            except Exception as e:
                if self.logger:
                    self.logger.log_warning(f"Rust file listing failed, using Python: {e}")
        
        # Python fallback
        return self._find_all_video_files_simple(directory_path)

    def validate_directory_fast(self, directory_path: Path) -> bool:
        """Fast directory validation using Rust if available."""
        if RUST_CORE_AVAILABLE:
            try:
                return videocleaner_core.validate_directory(str(directory_path))
            except Exception:
                pass
        
        # Python fallback
        return directory_path.exists() and directory_path.is_dir()

    def get_directory_statistics(self, directory_path: Path) -> Dict[str, Any]:
        """Get comprehensive directory statistics."""
        if RUST_CORE_AVAILABLE:
            try:
                rust_stats = videocleaner_core.get_directory_stats(str(directory_path))
                rust_stats['scan_method'] = 'rust'
                rust_stats['rust_version'] = RUST_VERSION
                return rust_stats
            except Exception as e:
                if self.logger:
                    self.logger.log_warning(f"Rust stats failed, using Python: {e}")
        
        # Python fallback - basic stats
        stats = {
            'scan_method': 'python',
            'rust_available': False,
            'total_files': 0,
            'video_files': 0,
            'total_size_bytes': 0,
            'total_size_gb': 0
        }
        
        try:
            video_files = self._find_all_video_files_simple(directory_path)
            stats['video_files'] = len(video_files)
            
            total_size = 0
            for video_file in video_files:
                try:
                    total_size += video_file.stat().st_size
                except (OSError, PermissionError):
                    continue
            
            stats['total_size_bytes'] = total_size
            stats['total_size_gb'] = total_size / (1024 * 1024 * 1024)
            
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Python stats calculation failed: {e}")
        
        return stats

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics including Rust integration status."""
        return {
            'module_version': __version__,
            'rust_core_available': RUST_CORE_AVAILABLE,
            'rust_version': RUST_VERSION,
            'scanner_type': 'rust_accelerated' if RUST_CORE_AVAILABLE else 'python_fallback',
            'last_scan_method': self.scan_method_used,
            'last_scan_time': self.last_scan_time,
            'caching_enabled': False,
            'complexity_level': 'industrial_strength_with_rust'
        }

    def clear_cache(self):
        """Clear any caches (none in this implementation)."""
        if self.logger:
            self.logger.log_warning(f"{__module_name__}: No cache to clear")

# Keep your existing EpisodeTracker class unchanged
class EpisodeTracker:
    def __init__(self, logger=None, config_manager=None):
        self.logger = logger
        self.config_manager = config_manager
        self.episode_patterns = [
            (r'[Ss](\d{1,2})[Ee](\d{1,3})', 'season_episode'),
            (r'(\d{1,2})x(\d{1,3})', 'season_episode'),
            (r'[Ss]eason\s*(\d{1,2}).*?[Ee]pisode\s*(\d{1,3})', 'season_episode')
        ]
        if self.logger:
            self.logger.log_warning(f"{__module_name__}: EpisodeTracker initialized")

    def track_episodes(self, file_paths: List[Path]) -> Dict[str, List[Tuple[int, int]]]:
        show_episodes = defaultdict(list)
        try:
            for file_path in file_paths:
                info = self._extract_episode_info_simple(file_path)
                if info:
                    show_episodes[info['show_name']].append((info['season'], info['episode']))
            return dict(show_episodes)
        except Exception as e:
            if self.logger:
                self.logger.log_error('episode_tracker', f'Tracking failed: {str(e)}')
            return {}

    def find_missing_episodes(self, show_episodes: Dict[str, List[Tuple[int, int]]]) -> Dict[str, List[Tuple[int, int]]]:
        missing = {}
        try:
            for show, eps in show_episodes.items():
                if len(eps) < 2:
                    continue
                sorted_eps = sorted(set(eps))
                by_season = defaultdict(list)
                for season, episode in sorted_eps:
                    by_season[season].append(episode)
                gaps = []
                for season, ep_list in by_season.items():
                    for i in range(min(ep_list), max(ep_list) + 1):
                        if i not in ep_list:
                            gaps.append((season, i))
                if gaps:
                    missing[show] = gaps
            return missing
        except Exception as e:
            if self.logger:
                self.logger.log_error('episode_tracker', f'Missing detection failed: {str(e)}')
            return {}

    def _extract_episode_info_simple(self, file_path: Path) -> Optional[Dict[str, Any]]:
        filename = file_path.name
        for pattern, _ in self.episode_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    season, episode = int(match.group(1)), int(match.group(2))
                    show_name = re.sub(r'[.\-_]+', ' ', filename[:match.start()].strip()).title()
                    return {
                        'show_name': show_name,
                        'season': season,
                        'episode': episode
                    }
                except (ValueError, IndexError):
                    continue
        return None

# Keep all your existing utility functions
def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"

def validate_directory_path(path_input: str) -> Path:
    if not path_input or not path_input.strip():
        raise ValueError("Directory path cannot be empty")
    cleaned = path_input.strip().strip('\"\'')
    path_obj = Path(cleaned).resolve()
    if not path_obj.exists() or not path_obj.is_dir():
        raise ValueError(f"Invalid directory: {path_obj}")
    return path_obj

def validate_drive(drive_input: str) -> Path:
    if not drive_input or not drive_input.strip():
        raise ValueError("Drive path cannot be empty")
    cleaned = drive_input.strip().strip('\"\'')
    drive_path = Path(cleaned).resolve()
    if not drive_path.exists() or not drive_path.is_dir():
        raise ValueError(f"Invalid drive: {drive_path}")
    return drive_path

def get_utils_performance_stats() -> Dict[str, Any]:
    return {
        'module_version': __version__,
        'rust_core_available': RUST_CORE_AVAILABLE,
        'rust_version': RUST_VERSION,
        'scanner_type': 'rust_accelerated' if RUST_CORE_AVAILABLE else 'python_fallback',
        'caching_enabled': False,
        'complexity_level': 'industrial_strength_with_rust'
    }

def clear_all_caches():
    """Clear all utility caches."""
    pass

if __name__ == "__main__":
    print(f"{__module_name__} v{__version__} - Enhanced Test Mode")
    print("=" * 60)
    
    # Show Rust integration status
    if RUST_CORE_AVAILABLE:
        print(f"🦀 Rust core available: v{RUST_VERSION}")
        print("   Functions available:")
        for func in dir(videocleaner_core):
            if not func.startswith('_'):
                print(f"     - {func}")
    else:
        print("🐍 Python-only mode (Rust core not available)")
    
    # Basic functionality test
    scanner = DirectoryScanner()
    tracker = EpisodeTracker()
    
    print(f"\nScanner performance stats:")
    stats = scanner.get_performance_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\nTesting format_size function:")
    for s in [1024, 1024**2, 1024**3]:
        print(f"  {s} bytes = {format_size(s)}")
    
    print("\n✅ Enhanced utilities test complete!")
    
    if RUST_CORE_AVAILABLE:
        print("🚀 Ready for high-performance 50TB processing!")
    else:
        print("⚠️ Install Rust core for maximum performance:")
        print("   cd videocleaner_core && maturin develop --release")
