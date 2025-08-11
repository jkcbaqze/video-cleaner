#!/usr/bin/env python3
"""
Smart Video Size Checker Module v3.1
Intelligent file size anomaly detection integrated with main configuration system.
NO MORE SEPARATE JSON FILES - uses master_config.json for all settings!
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import statistics

# Version loaded from config or default
__version__ = "3.1"
__module_name__ = "Video Size Checker"

def module_ping():
    """Module health check for dry run reporting."""
    return f"{__module_name__} v{__version__} - READY"

class VideoSizeChecker:
    """
    Intelligent video file size checker integrated with main configuration system.
    NO MORE separate JSON file - everything comes from master_config.json!
    """
    
    def __init__(self, logger=None, config_manager=None):
        """
        Initialize the size checker with main configuration integration.
        
        Args:
            logger: Optional logger instance for reporting
            config_manager: ConfigManager instance for all settings
        """
        self.logger = logger
        self.config_manager = config_manager
        self.episode_cache = {}  # Cache for episode pattern analysis
        
        # Load all settings from main config or use defaults
        if config_manager:
            # TV show settings
            self.tv_enable_checking = config_manager.get('size_checker', 'tv_shows.enable_size_checking', True)
            self.tv_max_multiplier = config_manager.get('size_checker', 'tv_shows.max_size_multiplier', 2.5)
            self.tv_min_multiplier = config_manager.get('size_checker', 'tv_shows.min_size_multiplier', 0.3)
            self.tv_warning_threshold = config_manager.get('size_checker', 'tv_shows.warning_threshold', 1.5)
            self.tv_consistency_checking = config_manager.get('size_checker', 'tv_shows.consistency_checking', True)
            self.tv_episode_cache_size = config_manager.get('size_checker', 'tv_shows.episode_cache_size', 10)
            
            # Movie settings
            self.movie_enable_checking = config_manager.get('size_checker', 'movies.enable_size_checking', True)
            self.movie_max_multiplier = config_manager.get('size_checker', 'movies.max_size_multiplier', 3.0)
            self.movie_min_multiplier = config_manager.get('size_checker', 'movies.min_size_multiplier', 0.2)
            self.movie_warning_threshold = config_manager.get('size_checker', 'movies.warning_threshold', 2.0)
            self.movie_consistency_checking = config_manager.get('size_checker', 'movies.consistency_checking', False)
            
            # Size standards
            self.tv_duration_minutes = config_manager.get('size_checker', 'standards.tv_episode_duration_minutes', 43)
            self.tv_mb_per_minute = config_manager.get('size_checker', 'standards.tv_size_mb_per_minute', 12.0)
            self.movie_duration_minutes = config_manager.get('size_checker', 'standards.movie_duration_minutes', 120)
            self.movie_mb_per_minute = config_manager.get('size_checker', 'standards.movie_size_mb_per_minute', 14.0)
            
            # Detection settings
            self.enable_learning = config_manager.get('size_checker', 'detection.enable_learning', True)
            self.cache_patterns = config_manager.get('size_checker', 'detection.cache_episode_patterns', True)
            self.confidence_threshold = config_manager.get('size_checker', 'detection.confidence_threshold', 0.7)
            self.auto_mark_rb = config_manager.get('size_checker', 'detection.auto_mark_rb_on_anomaly', True)
            
        else:
            # Fallback defaults when no config available
            # TV show defaults
            self.tv_enable_checking = True
            self.tv_max_multiplier = 2.5
            self.tv_min_multiplier = 0.3
            self.tv_warning_threshold = 1.5
            self.tv_consistency_checking = True
            self.tv_episode_cache_size = 10
            
            # Movie defaults
            self.movie_enable_checking = True
            self.movie_max_multiplier = 3.0
            self.movie_min_multiplier = 0.2
            self.movie_warning_threshold = 2.0
            self.movie_consistency_checking = False
            
            # Size standards defaults
            self.tv_duration_minutes = 43
            self.tv_mb_per_minute = 12.0
            self.movie_duration_minutes = 120
            self.movie_mb_per_minute = 14.0
            
            # Detection defaults
            self.enable_learning = True
            self.cache_patterns = True
            self.confidence_threshold = 0.7
            self.auto_mark_rb = True
        
        # Episode parsing patterns (simplified from original complex JSON)
        self.tv_patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,3})',           # S01E05 - most reliable
            r'(\d{1,2})x(\d{1,3})',                  # 1x05 - common
            r'[Ss]eason\s*(\d{1,2}).*?[Ee]pisode\s*(\d{1,3})'  # Season 1 Episode 5
        ]
        
        # Quality multipliers (simplified)
        self.quality_multipliers = {
            '480p': 0.5,
            '720p': 1.0,
            '1080p': 2.0,
            '4k': 4.0,
            'unknown': 1.0
        }
        
        # Codec efficiency multipliers (simplified)
        self.codec_multipliers = {
            'h264': 1.0,
            'h265': 0.6,
            'hevc': 0.6,
            'mpeg4': 1.4,
            'xvid': 1.2,
            'avi': 1.5,
            'unknown': 1.0
        }
        
        if self.logger:
            self.logger.log_warning(f"Size checker initialized with main config integration")
            self.logger.log_warning(f"TV checking: {self.tv_enable_checking}, Movie checking: {self.movie_enable_checking}")
    
    def check_file_size(self, file_path: Path, processing_mode: str = "tv") -> Dict[str, Any]:
        """
        Check if a file's size is within expected parameters using main config settings.
        
        Args:
            file_path: Path to the video file to check
            processing_mode: Either "tv" or "movie"
            
        Returns:
            Dictionary with analysis results including is_abnormal, reason, etc.
        """
        try:
            if not file_path.exists():
                return self._create_error_result("File not found")
            
            # Check if size checking is enabled for this mode
            if processing_mode == "tv" and not self.tv_enable_checking:
                return self._create_normal_result("TV size checking disabled")
            elif processing_mode == "movie" and not self.movie_enable_checking:
                return self._create_normal_result("Movie size checking disabled")
            
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            filename = file_path.name
            
            # Analyze filename for content information
            content_analysis = self._analyze_filename(filename, processing_mode)
            
            # Calculate expected size based on content and config
            expected_size = self._calculate_expected_size(content_analysis, processing_mode)
            
            # Perform size comparison using config thresholds
            size_ratio = file_size_mb / expected_size if expected_size > 0 else 0
            result = self._evaluate_size_ratio(size_ratio, file_size_mb, expected_size, 
                                             content_analysis, processing_mode)
            
            # Add file-specific information
            result.update({
                'filename': filename,
                'actual_size_bytes': file_size_bytes,
                'actual_size_mb': file_size_mb,
                'expected_size_mb': expected_size,
                'size_ratio': size_ratio,
                'content_analysis': content_analysis,
                'processing_mode': processing_mode,
                'config_source': 'master_config.json'
            })
            
            # Log result if abnormal and logging enabled
            if result.get('is_abnormal') and self.logger:
                if self.config_manager and self.config_manager.get('logger', 'content.log_size_checks', True):
                    self.logger.log_size_check_result(filename, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Size check failed: {str(e)}"
            if self.logger:
                self.logger.log_error(str(file_path.name), error_msg)
            return self._create_error_result(error_msg)
    
    def _analyze_filename(self, filename: str, mode: str) -> Dict[str, Any]:
        """
        Analyze filename to extract quality, codec, and content information.
        Simplified version using main config patterns.
        """
        analysis = {
            'quality': 'unknown',
            'codec': 'unknown',
            'duration_category': 'standard',
            'is_tv_episode': False,
            'season': None,
            'episode': None,
            'show_name': None
        }
        
        filename_lower = filename.lower()
        
        # Detect quality (simplified patterns)
        if any(pattern in filename_lower for pattern in ['480p', 'sd', 'dvd']):
            analysis['quality'] = '480p'
        elif any(pattern in filename_lower for pattern in ['720p', 'hd']):
            analysis['quality'] = '720p'
        elif any(pattern in filename_lower for pattern in ['1080p', 'full.hd', 'fhd']):
            analysis['quality'] = '1080p'
        elif any(pattern in filename_lower for pattern in ['4k', '2160p', 'uhd', 'ultra.hd']):
            analysis['quality'] = '4k'
        
        # Detect codec (simplified patterns)
        if any(pattern in filename_lower for pattern in ['h.264', 'avc', 'x264']):
            analysis['codec'] = 'h264'
        elif any(pattern in filename_lower for pattern in ['h.265', 'hevc', 'x265']):
            analysis['codec'] = 'h265'
        elif any(pattern in filename_lower for pattern in ['mpeg-4', 'mp4', 'divx']):
            analysis['codec'] = 'mpeg4'
        elif any(pattern in filename_lower for pattern in ['xvid']):
            analysis['codec'] = 'xvid'
        elif filename_lower.endswith('.avi'):
            analysis['codec'] = 'avi'
        
        # For TV mode, try to extract episode information
        if mode == "tv":
            for pattern in self.tv_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    try:
                        analysis['is_tv_episode'] = True
                        analysis['season'] = int(match.group(1))
                        analysis['episode'] = int(match.group(2))
                        
                        # Extract show name (everything before the episode pattern)
                        show_match = re.search(f"^(.+?){pattern}", filename, re.IGNORECASE)
                        if show_match:
                            show_name = show_match.group(1).strip(' .-_')
                            analysis['show_name'] = show_name
                        break
                    except (ValueError, IndexError):
                        continue
        
        return analysis
    
    def _calculate_expected_size(self, content_analysis: Dict[str, Any], mode: str) -> float:
        """
        Calculate expected file size based on content analysis and config settings.
        """
        try:
            # Get base size from config
            if mode == "tv":
                base_minutes = self.tv_duration_minutes
                mb_per_minute = self.tv_mb_per_minute
            else:
                base_minutes = self.movie_duration_minutes
                mb_per_minute = self.movie_mb_per_minute
            
            base_size = base_minutes * mb_per_minute
            
            # Apply quality multiplier
            quality = content_analysis.get('quality', 'unknown')
            quality_multiplier = self.quality_multipliers.get(quality, 1.0)
            
            # Apply codec efficiency
            codec = content_analysis.get('codec', 'unknown')
            codec_multiplier = self.codec_multipliers.get(codec, 1.0)
            
            # Calculate final expected size
            expected_size = base_size * quality_multiplier * codec_multiplier
            
            return max(expected_size, 50.0)  # Minimum reasonable size
            
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Size calculation error: {e}")
            return 200.0  # Fallback default
    
    def _evaluate_size_ratio(self, ratio: float, actual_mb: float, expected_mb: float, 
                           analysis: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        Evaluate if the size ratio indicates an anomaly using config thresholds.
        """
        # Get thresholds from config based on mode
        if mode == "tv":
            max_multiplier = self.tv_max_multiplier
            min_multiplier = self.tv_min_multiplier
            warning_threshold = self.tv_warning_threshold
            consistency_checking = self.tv_consistency_checking
        else:
            max_multiplier = self.movie_max_multiplier
            min_multiplier = self.movie_min_multiplier
            warning_threshold = self.movie_warning_threshold
            consistency_checking = self.movie_consistency_checking
        
        is_abnormal = False
        severity = "normal"
        reason = "File size within expected parameters"
        recommendation = "proceed"
        
        # Check for oversized files
        if ratio > max_multiplier:
            is_abnormal = True
            severity = "critical"
            percentage_over = (ratio - 1) * 100
            reason = f"{percentage_over:.0f}% over expected size threshold"
            recommendation = "mark_rb" if self.auto_mark_rb else "review"
            
        elif ratio > warning_threshold:
            is_abnormal = True
            severity = "warning"
            percentage_over = (ratio - 1) * 100
            reason = f"{percentage_over:.0f}% larger than expected"
            recommendation = "review"
        
        # Check for undersized files (potential corruption)
        elif ratio < min_multiplier:
            is_abnormal = True
            severity = "critical"
            percentage_under = (1 - ratio) * 100
            reason = f"{percentage_under:.0f}% smaller than expected (possible corruption)"
            recommendation = "mark_rb" if self.auto_mark_rb else "review"
        
        # Special handling for TV episodes (consistency checking)
        if mode == "tv" and analysis.get('is_tv_episode') and consistency_checking:
            consistency_result = self._check_episode_consistency(analysis, actual_mb)
            if consistency_result['is_inconsistent']:
                is_abnormal = True
                if severity == "normal":
                    severity = consistency_result['severity']
                reason += f" + {consistency_result['reason']}"
        
        return {
            'is_abnormal': is_abnormal,
            'severity': severity,
            'reason': reason,
            'recommendation': recommendation,
            'size_ratio': ratio,
            'threshold_max': max_multiplier,
            'threshold_min': min_multiplier,
            'threshold_warning': warning_threshold
        }
    
    def _check_episode_consistency(self, analysis: Dict[str, Any], actual_mb: float) -> Dict[str, Any]:
        """
        Check TV episode size consistency within the same show using config settings.
        """
        show_name = analysis.get('show_name')
        if not show_name or not self.cache_patterns:
            return {'is_inconsistent': False, 'reason': '', 'severity': 'normal'}
        
        # Get or create episode cache for this show
        if show_name not in self.episode_cache:
            self.episode_cache[show_name] = {'sizes': [], 'last_updated': datetime.now()}
        
        show_cache = self.episode_cache[show_name]
        show_cache['sizes'].append(actual_mb)
        
        # Keep only recent episodes for pattern analysis (using config limit)
        max_episodes = self.tv_episode_cache_size
        if len(show_cache['sizes']) > max_episodes:
            show_cache['sizes'] = show_cache['sizes'][-max_episodes:]
        
        # Need at least 3 episodes for consistency analysis
        if len(show_cache['sizes']) < 3:
            return {'is_inconsistent': False, 'reason': '', 'severity': 'normal'}
        
        # Calculate statistics
        sizes = show_cache['sizes'][:-1]  # Exclude current episode
        mean_size = statistics.mean(sizes)
        
        if len(sizes) > 1:
            try:
                std_dev = statistics.stdev(sizes)
                threshold = self.tv_warning_threshold  # Use warning threshold for consistency
                
                # Check if current episode deviates significantly
                deviation = abs(actual_mb - mean_size) / mean_size if mean_size > 0 else 0
                
                if deviation > threshold:
                    percentage_diff = deviation * 100
                    return {
                        'is_inconsistent': True,
                        'reason': f"inconsistent with other episodes ({percentage_diff:.0f}% different)",
                        'severity': 'warning' if deviation < 2.0 else 'critical'
                    }
            except statistics.StatisticsError:
                # Not enough variation to calculate standard deviation
                pass
        
        return {'is_inconsistent': False, 'reason': '', 'severity': 'normal'}
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            'is_abnormal': False,
            'error': True,
            'reason': error_message,
            'recommendation': 'skip',
            'severity': 'error',
            'config_source': 'master_config.json'
        }
    
    def _create_normal_result(self, message: str) -> Dict[str, Any]:
        """Create standardized normal result."""
        return {
            'is_abnormal': False,
            'error': False,
            'reason': message,
            'recommendation': 'proceed',
            'severity': 'normal',
            'config_source': 'master_config.json'
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get size checker statistics and configuration info."""
        return {
            'version': __version__,
            'config_source': 'master_config.json',
            'config_manager_available': self.config_manager is not None,
            'tv_checking_enabled': self.tv_enable_checking,
            'movie_checking_enabled': self.movie_enable_checking,
            'episode_cache_shows': len(self.episode_cache),
            'total_cached_episodes': sum(len(show['sizes']) for show in self.episode_cache.values()),
            'tv_max_multiplier': self.tv_max_multiplier,
            'movie_max_multiplier': self.movie_max_multiplier,
            'enable_learning': self.enable_learning,
            'cache_patterns': self.cache_patterns,
            'auto_mark_rb': self.auto_mark_rb
        }
    
    def get_size_checker_config_status(self) -> Dict[str, Any]:
        """
        Get current size checker configuration status.
        
        Returns:
            Dictionary with size checker configuration information
        """
        return {
            'config_manager_available': self.config_manager is not None,
            'tv_settings': {
                'enable_checking': self.tv_enable_checking,
                'max_multiplier': self.tv_max_multiplier,
                'min_multiplier': self.tv_min_multiplier,
                'warning_threshold': self.tv_warning_threshold,
                'consistency_checking': self.tv_consistency_checking,
                'episode_cache_size': self.tv_episode_cache_size
            },
            'movie_settings': {
                'enable_checking': self.movie_enable_checking,
                'max_multiplier': self.movie_max_multiplier,
                'min_multiplier': self.movie_min_multiplier,
                'warning_threshold': self.movie_warning_threshold,
                'consistency_checking': self.movie_consistency_checking
            },
            'size_standards': {
                'tv_duration_minutes': self.tv_duration_minutes,
                'tv_mb_per_minute': self.tv_mb_per_minute,
                'movie_duration_minutes': self.movie_duration_minutes,
                'movie_mb_per_minute': self.movie_mb_per_minute
            },
            'detection_settings': {
                'enable_learning': self.enable_learning,
                'cache_patterns': self.cache_patterns,
                'confidence_threshold': self.confidence_threshold,
                'auto_mark_rb': self.auto_mark_rb
            }
        }
    
    def reload_config(self, config_manager):
        """
        Reload configuration from config manager.
        
        Args:
            config_manager: Updated ConfigManager instance
        """
        self.config_manager = config_manager
        
        # Update settings from new config
        if config_manager:
            # TV show settings
            old_tv_enable = self.tv_enable_checking
            self.tv_enable_checking = config_manager.get('size_checker', 'tv_shows.enable_size_checking', self.tv_enable_checking)
            self.tv_max_multiplier = config_manager.get('size_checker', 'tv_shows.max_size_multiplier', self.tv_max_multiplier)
            self.tv_min_multiplier = config_manager.get('size_checker', 'tv_shows.min_size_multiplier', self.tv_min_multiplier)
            self.tv_warning_threshold = config_manager.get('size_checker', 'tv_shows.warning_threshold', self.tv_warning_threshold)
            self.tv_consistency_checking = config_manager.get('size_checker', 'tv_shows.consistency_checking', self.tv_consistency_checking)
            self.tv_episode_cache_size = config_manager.get('size_checker', 'tv_shows.episode_cache_size', self.tv_episode_cache_size)
            
            # Movie settings
            old_movie_enable = self.movie_enable_checking
            self.movie_enable_checking = config_manager.get('size_checker', 'movies.enable_size_checking', self.movie_enable_checking)
            self.movie_max_multiplier = config_manager.get('size_checker', 'movies.max_size_multiplier', self.movie_max_multiplier)
            self.movie_min_multiplier = config_manager.get('size_checker', 'movies.min_size_multiplier', self.movie_min_multiplier)
            self.movie_warning_threshold = config_manager.get('size_checker', 'movies.warning_threshold', self.movie_warning_threshold)
            self.movie_consistency_checking = config_manager.get('size_checker', 'movies.consistency_checking', self.movie_consistency_checking)
            
            # Size standards
            self.tv_duration_minutes = config_manager.get('size_checker', 'standards.tv_episode_duration_minutes', self.tv_duration_minutes)
            self.tv_mb_per_minute = config_manager.get('size_checker', 'standards.tv_size_mb_per_minute', self.tv_mb_per_minute)
            self.movie_duration_minutes = config_manager.get('size_checker', 'standards.movie_duration_minutes', self.movie_duration_minutes)
            self.movie_mb_per_minute = config_manager.get('size_checker', 'standards.movie_size_mb_per_minute', self.movie_mb_per_minute)
            
            # Detection settings
            self.enable_learning = config_manager.get('size_checker', 'detection.enable_learning', self.enable_learning)
            self.cache_patterns = config_manager.get('size_checker', 'detection.cache_episode_patterns', self.cache_patterns)
            self.confidence_threshold = config_manager.get('size_checker', 'detection.confidence_threshold', self.confidence_threshold)
            self.auto_mark_rb = config_manager.get('size_checker', 'detection.auto_mark_rb_on_anomaly', self.auto_mark_rb)
            
            # Clear episode cache if cache settings changed
            if not self.cache_patterns:
                self.episode_cache.clear()
            
            # Log significant changes
            if self.logger:
                if old_tv_enable != self.tv_enable_checking:
                    self.logger.log_warning(f"TV size checking: {old_tv_enable} → {self.tv_enable_checking}")
                if old_movie_enable != self.movie_enable_checking:
                    self.logger.log_warning(f"Movie size checking: {old_movie_enable} → {self.movie_enable_checking}")
                
                self.logger.log_warning("Size checker configuration reloaded from updated config file")
    
    def clear_cache(self):
        """Clear the episode cache to free memory."""
        self.episode_cache.clear()
        if self.logger:
            self.logger.log_warning("Episode size cache cleared")
    
    def update_episode_cache_from_directory(self, directory_path: Path, processing_mode: str = "tv"):
        """
        Pre-populate episode cache by analyzing files in a directory.
        
        Args:
            directory_path: Directory to scan for episodes
            processing_mode: Processing mode ("tv" or "movie")
        """
        if not self.cache_patterns or processing_mode != "tv":
            return
        
        try:
            video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.wmv', '.flv', '.webm', '.ogv'}
            
            for file_path in directory_path.rglob('*'):
                if (file_path.is_file() and 
                    file_path.suffix.lower() in video_extensions and
                    not file_path.name.startswith('.') and
                    file_path.suffix.lower() != '.rb'):
                    
                    # Analyze filename for episode info
                    content_analysis = self._analyze_filename(file_path.name, "tv")
                    
                    if content_analysis.get('is_tv_episode'):
                        show_name = content_analysis.get('show_name')
                        if show_name:
                            file_size_mb = file_path.stat().st_size / (1024 * 1024)
                            
                            # Add to cache without triggering consistency check
                            if show_name not in self.episode_cache:
                                self.episode_cache[show_name] = {'sizes': [], 'last_updated': datetime.now()}
                            
                            self.episode_cache[show_name]['sizes'].append(file_size_mb)
                            
                            # Limit cache size
                            if len(self.episode_cache[show_name]['sizes']) > self.tv_episode_cache_size:
                                self.episode_cache[show_name]['sizes'] = self.episode_cache[show_name]['sizes'][-self.tv_episode_cache_size:]
            
            if self.logger:
                cached_shows = len(self.episode_cache)
                total_episodes = sum(len(show['sizes']) for show in self.episode_cache.values())
                self.logger.log_warning(f"Episode cache populated: {cached_shows} shows, {total_episodes} episodes")
                
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Episode cache population failed: {e}")

# Utility functions for external use
def check_file_size_with_config(file_path: Path, mode: str = "tv", config_manager=None) -> bool:
    """
    Simple size check function with config integration.
    
    Args:
        file_path: Path to video file
        mode: Processing mode ("tv" or "movie")
        config_manager: Optional ConfigManager instance
        
    Returns:
        True if size seems normal, False if abnormal
    """
    checker = VideoSizeChecker(config_manager=config_manager)
    result = checker.check_file_size(file_path, mode)
    return not result.get('is_abnormal', False)

def create_size_checker_with_config(logger=None, config_manager=None) -> VideoSizeChecker:
    """
    Create a VideoSizeChecker instance with configuration integration.
    
    Args:
        logger: Optional logger instance
        config_manager: Optional ConfigManager instance
        
    Returns:
        Configured VideoSizeChecker instance
    """
    return VideoSizeChecker(logger=logger, config_manager=config_manager)

# Example usage and testing
if __name__ == "__main__":
    # Test the enhanced size checker functionality
    print(f"{__module_name__} v{__version__} - Config Integration Test")
    print("=" * 50)
    
    # Test without config manager
    print("Testing size checker without config manager (fallback mode):")
    test_checker = VideoSizeChecker()
    
    config_status = test_checker.get_size_checker_config_status()
    print("Size Checker Status:")
    for section, settings in config_status.items():
        print(f"  {section}:")
        if isinstance(settings, dict):
            for key, value in settings.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {settings}")
    
    # Test filename analysis
    test_files = [
        "Still.Standing.S01E01.720p.x264.mkv",
        "Still.Standing.S01E02.1080p.HEVC.mkv", 
        "Huge.Movie.2024.4K.H265.mp4",
        "Old.Show.1990.DVDRip.XviD.avi"
    ]
    
    print(f"\nTesting filename analysis:")
    for filename in test_files:
        mode = "tv" if "S01E" in filename else "movie"
        analysis = test_checker._analyze_filename(filename, mode)
        print(f"  {filename}:")
        print(f"    Quality: {analysis['quality']}, Codec: {analysis['codec']}")
        if analysis['is_tv_episode']:
            print(f"    Show: {analysis['show_name']}, S{analysis['season']:02d}E{analysis['episode']:02d}")
    
    # Show statistics
    stats = test_checker.get_statistics()
    print(f"\nSize Checker Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\nEnhanced size checker v{__version__} with main config integration ready!")
    print("Key features: No separate JSON, all settings in master_config.json!")
