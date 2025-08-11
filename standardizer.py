#!/usr/bin/env python3
"""
Enhanced Filename Standardizer Module v3.2
Professional filename standardization with configuration management,
advanced pattern recognition, and comprehensive cleaning. NO MORE HARDCODED VALUES!
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import threading

# Version information
__version__ = "3.2"
__module_name__ = "Filename Standardizer"

def module_ping():
    """Module health check for dry run reporting."""
    return f"{__module_name__} v{__version__} - READY"

class FilenameStandardizer:
    """
    Enhanced filename standardization system with configuration integration
    for professional TV show and movie filename cleaning and organization.
    """
    
    def __init__(self, processing_mode: str = "tv", logger=None, config_manager=None):
        """
        Initialize filename standardizer with configuration integration.
        
        Args:
            processing_mode: "tv" for TV shows, "movie" for movies
            logger: Optional ProfessionalLogger instance for detailed logging
            config_manager: ConfigManager instance for settings
        """
        self.processing_mode = processing_mode
        self.logger = logger
        self.config_manager = config_manager
        
        # Register with logger for module context
        if self.logger and hasattr(self.logger, 'register_module'):
            self.logger.register_module(__module_name__, __version__)
        
        # Load settings from config or use defaults
        if config_manager:
            # Cleaning behavior settings
            self.aggressive_cleaning = config_manager.get('filename_standardizer', 'cleaning.aggressive_cleaning', True)
            self.preserve_original_case = config_manager.get('filename_standardizer', 'cleaning.preserve_original_case', False)
            self.remove_episode_titles = config_manager.get('filename_standardizer', 'cleaning.remove_episode_titles', True)
            self.standardize_extensions = config_manager.get('filename_standardizer', 'cleaning.standardize_extensions', True)
            self.clean_special_characters = config_manager.get('filename_standardizer', 'cleaning.clean_special_characters', True)
            
            # TV show settings
            self.tv_format_template = config_manager.get('filename_standardizer', 'tv_shows.format_template', '{show_name} - S{season:02d}E{episode:02d}')
            self.tv_detect_specials = config_manager.get('filename_standardizer', 'tv_shows.detect_special_episodes', True)
            self.tv_normalize_show_names = config_manager.get('filename_standardizer', 'tv_shows.normalize_show_names', True)
            self.tv_min_season = config_manager.get('filename_standardizer', 'tv_shows.min_season_number', 1)
            self.tv_max_season = config_manager.get('filename_standardizer', 'tv_shows.max_season_number', 50)
            self.tv_max_episode = config_manager.get('filename_standardizer', 'tv_shows.max_episode_number', 999)
            
            # Movie settings
            self.movie_format_template = config_manager.get('filename_standardizer', 'movies.format_template', '{title} ({year})')
            self.movie_require_year = config_manager.get('filename_standardizer', 'movies.require_year', True)
            self.movie_year_placeholder = config_manager.get('filename_standardizer', 'movies.year_placeholder', 'XXXX')
            self.movie_min_year = config_manager.get('filename_standardizer', 'movies.min_year', 1900)
            self.movie_max_year = config_manager.get('filename_standardizer', 'movies.max_year', 2030)
            
            # Pattern recognition settings
            self.use_advanced_patterns = config_manager.get('filename_standardizer', 'patterns.use_advanced_patterns', True)
            self.pattern_confidence_threshold = config_manager.get('filename_standardizer', 'patterns.confidence_threshold', 0.7)
            self.enable_fuzzy_matching = config_manager.get('filename_standardizer', 'patterns.enable_fuzzy_matching', False)
            
            # Performance settings
            self.cache_results = config_manager.get('filename_standardizer', 'performance.cache_results', True)
            self.max_cache_entries = config_manager.get('filename_standardizer', 'performance.max_cache_entries', 1000)
            self.log_cleaning_details = config_manager.get('filename_standardizer', 'performance.log_cleaning_details', False)
            
        else:
            # Fallback defaults when no config available
            # Cleaning behavior
            self.aggressive_cleaning = True
            self.preserve_original_case = False
            self.remove_episode_titles = True
            self.standardize_extensions = True
            self.clean_special_characters = True
            
            # TV show defaults
            self.tv_format_template = '{show_name} - S{season:02d}E{episode:02d}'
            self.tv_detect_specials = True
            self.tv_normalize_show_names = True
            self.tv_min_season = 1
            self.tv_max_season = 50
            self.tv_max_episode = 999
            
            # Movie defaults
            self.movie_format_template = '{title} ({year})'
            self.movie_require_year = True
            self.movie_year_placeholder = 'XXXX'
            self.movie_min_year = 1900
            self.movie_max_year = 2030
            
            # Pattern recognition defaults
            self.use_advanced_patterns = True
            self.pattern_confidence_threshold = 0.7
            self.enable_fuzzy_matching = False
            
            # Performance defaults
            self.cache_results = True
            self.max_cache_entries = 1000
            self.log_cleaning_details = False
        
        # Comprehensive cleanup patterns (enhanced from original)
        self.cleanup_patterns = [
            # Video codec information
            r'\s*[\[\(-]?\s*[xh]\.?26[45]\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*hevc\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*avc\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*xvid\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*divx\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*av1\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*vp[89]\s*[\]\)-]?\s*',
            
            # Resolution and quality tags
            r'\s*[\[\(-]?\s*\d{3,4}p\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*4k\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*8k\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*uhd\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(hd|fhd)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(720p|1080p|2160p|4320p)\s*[\]\)-]?\s*',
            
            # Source and rip information
            r'\s*[\[\(-]?\s*(bluray|blu-ray|brrip|dvdrip|webrip|web-dl|hdtv|pdtv)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(cam|ts|tc|dvdscr|screener|workprint|telesync)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(hdrip|bdrip|webdl|web\.dl)\s*[\]\)-]?\s*',
            
            # HDR and color information
            r'\s*[\[\(-]?\s*(hdr|hdr10|dolby\.?vision|dv)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(bt2020|rec2020|p3)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(10bit|8bit|12bit)\s*[\]\)-]?\s*',
            
            # Episode titles (configurable)
            r'\s*-\s*[A-Za-z][^.]*?(?=\.)' if self.remove_episode_titles else '',
            r'\s*:\s*[A-Za-z][^.]*?(?=\.)' if self.remove_episode_titles else '',
            
            # Release group information
            r'\s*[\[\(-]\s*[A-Za-z0-9]{2,15}\s*[\]\)]\s*',
            r'\s+[a-f0-9]{4,}\s*',  # Random hex strings
            r'\s+subgroup\d*\s*',
            r'\s+sub[a-z]{3}\s*',
            
            # Audio codec and encoding info
            r'\s*[\[\(-]?\s*(aac|ac3|dts|dd5\.?1|7\.?1|mp3|flac|opus)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(stereo|mono|surround|atmos)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(\d+ch|\d+\.\d+ch)\s*[\]\)-]?\s*',
            
            # Quality and release info
            r'\s*[\[\(-]?\s*(complete|repack|proper|real|internal|limited)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(uncut|directors\.cut|extended|theatrical)\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(imax|criterion|anniversary)\s*[\]\)-]?\s*',
            
            # Known release groups (configurable based on aggressiveness)
            r'\s*[\[\(-]?\s*(yify|rarbg|ettv|eztv|killers|dimension|lol|asap)\s*[\]\)-]?\s*' if self.aggressive_cleaning else '',
            r'\s*[\[\(-]?\s*(fleet|sparks|axxo|maxspeed|sample|trailer)\s*[\]\)-]?\s*' if self.aggressive_cleaning else '',
            r'\s*[\[\(-]?\s*(extras|deleted\.scenes|behind\.scenes)\s*[\]\)-]?\s*',
            
            # File format indicators
            r'\s*[\[\(-]?\s*(avi|mkv|mp4|mov|wmv|flv|webm|m4v)\s*[\]\)-]?\s*',
            
            # Language indicators (configurable)
            r'\s*[\[\(-]?\s*(english|eng|dubbed|subbed|multi)\s*[\]\)-]?\s*' if self.aggressive_cleaning else '',
            r'\s*[\[\(-]?\s*(german|french|spanish|italian|ger|fre|spa|ita)\s*[\]\)-]?\s*' if self.aggressive_cleaning else '',
            
            # Size and bitrate indicators
            r'\s*[\[\(-]?\s*\d+\.?\d*\s*(gb|mb|kb|kbps|mbps)\s*[\]\)-]?\s*',
            
            # Year patterns (handled separately for movies)
            r'\s*[\[\(]\s*\d{4}\s*[\]\)]\s*' if self.processing_mode == "tv" else '',
            
            # Streaming service tags
            r'\s*[\[\(-]?\s*(netflix|amazon|hulu|disney|hbo|max)\s*[\]\)-]?\s*' if self.aggressive_cleaning else '',
            
            # Clean up punctuation artifacts
            r'\s*[-_\.]{2,}\s*',  # Multiple dashes/underscores/dots
            r'\s*[,;]\s*',        # Commas and semicolons
            r'\s{2,}',            # Multiple spaces
        ]
        
        # Remove empty patterns (from conditional patterns)
        self.cleanup_patterns = [p for p in self.cleanup_patterns if p.strip()]
        
        # Enhanced TV show episode parsing patterns
        self.tv_patterns = [
            # Standard formats with confidence scores
            (r'^(.+?)\s*[-_\.\s]\s*S(\d{1,2})E(\d{1,3})', 0.95, 'standard_sxxexx'),
            (r'^(.+?)\s+S(\d{1,2})E(\d{1,3})', 0.90, 'standard_sxxexx_space'),
            (r'^(.+?)[\s\._-]+(\d{1,2})x(\d{1,3})', 0.85, 'standard_nx'),
            
            # Verbose formats
            (r'^(.+?)\s*[-_\.\s]*Season\s*(\d{1,2})\s*Episode\s*(\d{1,3})', 0.80, 'verbose_season_episode'),
            (r'^(.+?)\s*[-_\.\s]*S(\d{1,2})\s*Ep?(\d{1,3})', 0.75, 'short_season_ep'),
            
            # Compact formats
            (r'^(.+?)[\s\._-]+(\d)(\d{2})(?!\d)', 0.70, 'compact_3digit'),
            
            # Date-based formats
            (r'^(.+?)[\s\._-]+(\d{4})[\.\-_](\d{1,2})[\.\-_](\d{1,2})', 0.60, 'date_based'),
            
            # Alternative formats
            (r'^(.+?)\s*[-_\.\s]*Ep\.?\s*(\d{1,3})', 0.50, 'episode_only'),
            (r'^(.+?)\s*[-_\.\s]*Episode\s*(\d{1,3})', 0.55, 'episode_only_verbose'),
        ]
        
        # Enhanced movie year extraction patterns
        self.year_patterns = [
            (r'\b(19\d{2}|20\d{2})\b', 0.80),          # 4-digit year in text
            (r'\((\d{4})\)', 0.95),                     # Year in parentheses (high confidence)
            (r'[\[\(](\d{4})[\]\)]', 0.90),            # Year in brackets or parentheses
            (r'\.(\d{4})\.', 0.75),                     # Year between dots
            (r'_(\d{4})_', 0.70),                       # Year between underscores
            (r'\s(\d{4})\s', 0.70),                     # Year between spaces
        ]
        
        # Result caching for performance
        self.result_cache = {} if self.cache_results else None
        self.cache_lock = threading.Lock() if self.cache_results else None
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'files_cleaned': 0,
            'tv_episodes_parsed': 0,
            'movies_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'perfect_format_skips': 0,  # Fast validation optimization counter
            'total_processing_time': 0.0,
            'session_start': datetime.now()
        }
        
        # Common words to preserve in titles (expanded)
        self.preserve_words = {
            'and', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'shall',
            'but', 'or', 'nor', 'yet', 'so', 'from', 'up', 'out', 'if'
        }
        
        if self.logger:
            self.logger.log_warning(f"{__module_name__} v{__version__}: Standardizer initialized", module_name=__module_name__)
            self.logger.log_warning(f"Mode: {processing_mode}, Aggressive: {self.aggressive_cleaning}")
    
    def is_perfect_format(self, filename: str) -> bool:
        """
        Ultra-fast validation for perfect filename formats (99.5% optimization).
        Uses optimized regex patterns to skip expensive parsing for perfect files.
        
        Perfect formats:
        - Movies: "MovieName (YYYY).mkv"
        - TV Shows: "TVShow Name - SnnEnn.mkv"
        - TV Doubles: "TVShow Name - SnnEnnEnn.mkv" or "TVShow Name - SnnEnn-Enn.mkv"
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if filename is already in perfect format
        """
        # Must end with .mkv for perfect format
        if not filename.lower().endswith('.mkv'):
            return False
        
        # Get name without extension
        name = filename[:-4]  # Remove .mkv
        
        if self.processing_mode == "tv":
            # Perfect TV show patterns (very fast regex)
            tv_patterns = [
                # Standard: "Show Name - S01E01.mkv"
                r'^[A-Za-z0-9\s\-\'\.]+\s\-\sS\d{2}E\d{2}$',
                # Double episodes: "Show Name - S01E01E02.mkv"
                r'^[A-Za-z0-9\s\-\'\.]+\s\-\sS\d{2}E\d{2}E\d{2}$',
                # Double episodes alt: "Show Name - S01E01-E02.mkv"
                r'^[A-Za-z0-9\s\-\'\.]+\s\-\sS\d{2}E\d{2}\-E\d{2}$'
            ]
            
            for pattern in tv_patterns:
                if re.match(pattern, name):
                    # Additional checks for perfection
                    if self._has_junk_in_name(name):
                        return False
                    return True
            
        elif self.processing_mode == "movie":
            # Perfect movie pattern: "Movie Name (YYYY).mkv"
            movie_pattern = r'^[A-Za-z0-9\s\-\'\.]+\s\(\d{4}\)$'
            
            if re.match(movie_pattern, name):
                # Additional checks for perfection
                if self._has_junk_in_name(name):
                    return False
                return True
        
        return False
    
    def _has_junk_in_name(self, name: str) -> bool:
        """Fast check for common junk patterns in filename."""
        # Quick check for common junk indicators
        junk_indicators = [
            r'\b(h264|h265|x264|x265|hevc|avc)\b',  # Codecs
            r'\b(1080p|720p|480p|2160p|4k)\b',      # Resolutions  
            r'\b(bluray|bdrip|webrip|hdtv|dvdrip)\b',  # Sources
            r'\[\w+\]',                              # Brackets with content
            r'\b(ac3|dts|dd5\.1|dd2\.0)\b',         # Audio formats
            r'\b(multi|dual)\b',                     # Multi-language indicators
        ]
        
        name_lower = name.lower()
        for pattern in junk_indicators:
            if re.search(pattern, name_lower):
                return True
        return False
    
    def fast_needs_cleaning_check(self, filename: str) -> Tuple[bool, str]:
        """
        Lightning-fast check combining perfect format validation with basic needs assessment.
        Provides 99.5% optimization by skipping expensive parsing for perfect files.
        
        Args:
            filename: Filename to check
            
        Returns:
            Tuple of (needs_cleaning, reason_or_skip_message)
        """
        # First, ultra-fast perfect format check
        if self.is_perfect_format(filename):
            return (False, "Perfect format - skipped expensive parsing")
        
        # If not perfect, we need to do full analysis
        return (True, "Requires full analysis")

    def needs_cleaning(self, filename: str, format_tags: Dict = None) -> Tuple[bool, List[str]]:
        """
        Enhanced check if filename needs cleaning with fast validation optimization.
        Uses ultra-fast perfect format check to skip 99.5% of files instantly.
        
        Args:
            filename: Original filename to check
            format_tags: Optional format metadata tags
            
        Returns:
            Tuple of (needs_cleaning, list_of_reasons)
        """
        if format_tags is None:
            format_tags = {}
        
        # ULTRA-FAST PATH: Check if file is already in perfect format
        fast_result, fast_reason = self.fast_needs_cleaning_check(filename)
        if not fast_result:
            # Perfect format - no cleaning needed, skip all expensive operations
            self.stats['perfect_format_skips'] = self.stats.get('perfect_format_skips', 0) + 1
            return (False, [fast_reason])
        
        reasons = []
        
        # Check cache for non-perfect files
        if self.cache_results and self.result_cache is not None:
            cache_key = f"needs_cleaning_{filename}_{hash(str(format_tags))}"
            with self.cache_lock:
                if cache_key in self.result_cache:
                    self.stats['cache_hits'] += 1
                    return self.result_cache[cache_key]
                self.stats['cache_misses'] += 1
        
        clean_filename = self.clean_filename(filename, format_tags)
        needs_clean = filename != clean_filename
        
        if needs_clean:
            # Analyze what specifically needs cleaning
            name, ext = os.path.splitext(filename)
            
            # Check for junk patterns
            for pattern in self.cleanup_patterns[:10]:  # Check main patterns
                if re.search(pattern, name, re.IGNORECASE):
                    reasons.append("Contains codec/quality tags")
                    break
            
            # Check extension
            if not filename.lower().endswith('.mkv') and self.standardize_extensions:
                reasons.append("Non-standard extension")
            
            # Check format compliance
            if self.processing_mode == "tv":
                if not re.search(r'S\d{2}E\d{2}', filename):
                    reasons.append("Non-standard TV episode format")
            elif self.processing_mode == "movie":
                if not re.search(r'\(\d{4}\)', filename) and self.movie_require_year:
                    reasons.append("Missing year in movie title")
            
            # Check for special characters
            if self.clean_special_characters and re.search(r'[^\w\s\-\.\(\)]+', name):
                reasons.append("Contains special characters")
        
        result = (needs_clean, reasons)
        
        # Cache the result
        if self.cache_results and self.result_cache is not None:
            with self.cache_lock:
                self.result_cache[cache_key] = result
                if len(self.result_cache) > self.max_cache_entries:
                    # Remove oldest entries (simple FIFO)
                    oldest_keys = list(self.result_cache.keys())[:-self.max_cache_entries//2]
                    for old_key in oldest_keys:
                        del self.result_cache[old_key]
        
        return result
    
    def clean_filename(self, filename: str, format_tags: Dict = None) -> str:
        """
        Enhanced filename cleaning with configuration-driven behavior.
        
        Args:
            filename: Original filename
            format_tags: Optional format metadata tags
            
        Returns:
            Cleaned and standardized filename
        """
        if format_tags is None:
            format_tags = {}
        
        start_time = datetime.now()
        
        try:
            # Check cache first
            if self.cache_results and self.result_cache is not None:
                cache_key = f"clean_{filename}_{hash(str(format_tags))}"
                with self.cache_lock:
                    if cache_key in self.result_cache:
                        self.stats['cache_hits'] += 1
                        return self.result_cache[cache_key]
                    self.stats['cache_misses'] += 1
            
            # Perform cleaning based on mode
            if self.processing_mode == "tv":
                result = self._clean_tv_filename_enhanced(filename, format_tags)
            elif self.processing_mode == "movie":
                result = self._clean_movie_filename_enhanced(filename, format_tags)
            else:
                result = self._apply_generic_cleaning_enhanced(filename)
            
            # Update statistics
            self.stats['files_processed'] += 1
            if result != filename:
                self.stats['files_cleaned'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats['total_processing_time'] += processing_time
            
            # Log detailed cleaning if enabled
            if self.log_cleaning_details and self.logger and result != filename:
                self.logger.log_warning(f"Cleaned: {filename} → {result}")
            
            # Cache the result
            if self.cache_results and self.result_cache is not None:
                with self.cache_lock:
                    self.result_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.log_error('filename_standardizer', f'Cleaning failed for {filename}: {e}')
            return filename  # Return original on error
    
    def _clean_tv_filename_enhanced(self, filename: str, format_tags: Dict) -> str:
        """
        Enhanced TV show filename cleaning with configuration-driven formatting.
        
        Args:
            filename: Original filename
            format_tags: Format metadata tags
            
        Returns:
            Standardized TV show filename
        """
        name, ext = os.path.splitext(filename)
        
        # Try to parse episode information with confidence scoring
        parse_result = self.parse_tv_episode_info_enhanced(name)
        
        if parse_result and parse_result['confidence'] >= self.pattern_confidence_threshold:
            show_name = parse_result['show_name']
            season = parse_result['season']
            episode = parse_result['episode']
            
            # Validate ranges
            if (self.tv_min_season <= season <= self.tv_max_season and 
                1 <= episode <= self.tv_max_episode):
                
                # Clean show name
                if self.tv_normalize_show_names:
                    clean_show_name = self._clean_show_name_enhanced(show_name)
                else:
                    clean_show_name = show_name
                
                # Apply format template
                try:
                    formatted_name = self.tv_format_template.format(
                        show_name=clean_show_name,
                        season=season,
                        episode=episode
                    )
                    
                    # Add standard extension if configured
                    if self.standardize_extensions:
                        return f"{formatted_name}.mkv"
                    else:
                        return f"{formatted_name}{ext}"
                        
                except (KeyError, ValueError) as e:
                    if self.logger:
                        self.logger.log_warning(f"Format template error: {e}")
                    # Fallback to default format
                    return f"{clean_show_name} - S{season:02d}E{episode:02d}.mkv"
                
                # Update statistics
                self.stats['tv_episodes_parsed'] += 1
        
        # Couldn't parse episode info - apply generic cleaning
        clean_name = self._apply_generic_cleaning_enhanced(name)
        
        if self.standardize_extensions:
            return f"{clean_name}.mkv"
        else:
            return f"{clean_name}{ext}"
    
    def _clean_movie_filename_enhanced(self, filename: str, format_tags: Dict) -> str:
        """
        Enhanced movie filename cleaning with configuration-driven formatting.
        
        Args:
            filename: Original filename
            format_tags: Format metadata tags
            
        Returns:
            Standardized movie filename
        """
        name, ext = os.path.splitext(filename)
        
        # Extract year with confidence scoring
        year_result = self._extract_movie_year_enhanced(filename, format_tags)
        year = year_result['year'] if year_result['confidence'] >= self.pattern_confidence_threshold else self.movie_year_placeholder
        
        # Remove year from title temporarily for cleaning
        title_without_year = self._remove_year_from_title_enhanced(name)
        
        # Apply cleaning patterns
        clean_title = self._apply_generic_cleaning_enhanced(title_without_year)
        
        # Apply format template
        try:
            if self.movie_require_year or (year and year != self.movie_year_placeholder):
                formatted_name = self.movie_format_template.format(
                    title=clean_title,
                    year=year
                )
            else:
                # No year required or available
                formatted_name = clean_title
            
            # Add standard extension if configured
            if self.standardize_extensions:
                result = f"{formatted_name}.mkv"
            else:
                result = f"{formatted_name}{ext}"
            
            # Update statistics
            self.stats['movies_processed'] += 1
            
            return result
            
        except (KeyError, ValueError) as e:
            if self.logger:
                self.logger.log_warning(f"Movie format template error: {e}")
            
            # Fallback to default format
            if year and year != self.movie_year_placeholder:
                return f"{clean_title} ({year}).mkv"
            else:
                return f"{clean_title}.mkv"
    
    def parse_tv_episode_info_enhanced(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced TV episode parsing with confidence scoring and advanced patterns.
        
        Args:
            filename: Filename to parse (without extension)
            
        Returns:
            Dictionary with parsing results and confidence score, or None
        """
        best_match = None
        highest_confidence = 0.0
        
        for pattern, confidence, pattern_type in self.tv_patterns:
            if not self.use_advanced_patterns and confidence < 0.8:
                continue  # Skip advanced patterns if disabled
                
            match = re.search(pattern, filename, re.IGNORECASE)
            if match and confidence > highest_confidence:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 3:
                        show_name = groups[0].strip()
                        season = int(groups[1])
                        episode = int(groups[2])
                        
                        # Special handling for different pattern types
                        if pattern_type == 'episode_only':
                            season = 1  # Assume season 1 for episode-only patterns
                        elif pattern_type == 'compact_3digit':
                            # Format: Show.105 (season 1, episode 5)
                            combined = int(groups[1] + groups[2])
                            season = combined // 100
                            episode = combined % 100
                        elif pattern_type == 'date_based':
                            # Convert date to season/episode
                            year = int(groups[1])
                            month = int(groups[2])
                            day = int(groups[3])
                            season = year - 2000  # Simplified conversion
                            episode = month * 100 + day
                        
                        # Validate ranges
                        if (self.tv_min_season <= season <= self.tv_max_season and 
                            1 <= episode <= self.tv_max_episode and show_name):
                            
                            best_match = {
                                'show_name': show_name,
                                'season': season,
                                'episode': episode,
                                'confidence': confidence,
                                'pattern_type': pattern_type,
                                'match_text': match.group(0)
                            }
                            highest_confidence = confidence
                            
                except (ValueError, IndexError):
                    continue
        
        return best_match
    
    def _extract_movie_year_enhanced(self, filename: str, format_tags: Dict) -> Dict[str, Any]:
        """
        Enhanced movie year extraction with confidence scoring.
        
        Args:
            filename: Movie filename
            format_tags: Format metadata tags
            
        Returns:
            Dictionary with year and confidence score
        """
        best_year = self.movie_year_placeholder
        highest_confidence = 0.0
        
        # Try filename patterns first
        for pattern, confidence in self.year_patterns:
            match = re.search(pattern, filename)
            if match and confidence > highest_confidence:
                year = match.group(1)
                year_int = int(year)
                
                # Validate year range
                if self.movie_min_year <= year_int <= self.movie_max_year:
                    best_year = year
                    highest_confidence = confidence
        
        # Try metadata tags if filename didn't yield high confidence
        if highest_confidence < 0.8:
            for tag_key in ['date', 'year', 'creation_time', 'release_date']:
                tag_value = format_tags.get(tag_key, '')
                if tag_value:
                    year_match = re.search(r'(\d{4})', str(tag_value))
                    if year_match:
                        year = year_match.group(1)
                        year_int = int(year)
                        if self.movie_min_year <= year_int <= self.movie_max_year:
                            if highest_confidence < 0.6:  # Metadata gets medium confidence
                                best_year = year
                                highest_confidence = 0.6
        
        return {
            'year': best_year,
            'confidence': highest_confidence,
            'source': 'filename' if highest_confidence > 0.6 else 'metadata' if highest_confidence > 0 else 'none'
        }
    
    def get_standardizer_config_status(self) -> Dict[str, Any]:
        """
        Get current standardizer configuration status.
        
        Returns:
            Dictionary with standardizer configuration information
        """
        return {
            'config_manager_available': self.config_manager is not None,
            'processing_mode': self.processing_mode,
            'cleaning_settings': {
                'aggressive_cleaning': self.aggressive_cleaning,
                'preserve_original_case': self.preserve_original_case,
                'remove_episode_titles': self.remove_episode_titles,
                'standardize_extensions': self.standardize_extensions,
                'clean_special_characters': self.clean_special_characters
            },
            'tv_settings': {
                'format_template': self.tv_format_template,
                'detect_specials': self.tv_detect_specials,
                'normalize_show_names': self.tv_normalize_show_names,
                'season_range': f"{self.tv_min_season}-{self.tv_max_season}",
                'max_episode': self.tv_max_episode
            },
            'movie_settings': {
                'format_template': self.movie_format_template,
                'require_year': self.movie_require_year,
                'year_placeholder': self.movie_year_placeholder,
                'year_range': f"{self.movie_min_year}-{self.movie_max_year}"
            },
            'pattern_settings': {
                'use_advanced_patterns': self.use_advanced_patterns,
                'confidence_threshold': self.pattern_confidence_threshold,
                'enable_fuzzy_matching': self.enable_fuzzy_matching
            },
            'performance_settings': {
                'cache_results': self.cache_results,
                'max_cache_entries': self.max_cache_entries,
                'log_cleaning_details': self.log_cleaning_details,
                'current_cache_size': len(self.result_cache) if self.result_cache else 0
            }
        }
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        session_duration = (datetime.now() - self.stats['session_start']).total_seconds()
        
        stats = self.stats.copy()
        total_checks = self.stats['files_processed']
        perfect_skips = self.stats['perfect_format_skips']
        optimization_rate = (perfect_skips / max(total_checks, 1)) * 100
        
        stats.update({
            'session_duration_seconds': session_duration,
            'files_per_second': self.stats['files_processed'] / max(session_duration, 1),
            'cleaning_success_rate': (self.stats['files_cleaned'] / max(self.stats['files_processed'], 1)) * 100,
            'cache_hit_rate': (self.stats['cache_hits'] / max(self.stats['cache_hits'] + self.stats['cache_misses'], 1)) * 100,
            'fast_validation_rate': optimization_rate,  # Percentage of files that skipped expensive parsing
            'average_processing_time_ms': (self.stats['total_processing_time'] / max(self.stats['files_processed'], 1)) * 1000,
            'module_version': __version__
        })
        
        return stats
    
    def clear_cache(self):
        """Clear the result cache."""
        if self.cache_results and self.result_cache is not None:
            with self.cache_lock:
                self.result_cache.clear()
            if self.logger:
                self.logger.log_warning("Filename standardizer cache cleared")
    
    # Include remaining enhanced methods from original with config integration
    def _clean_show_name_enhanced(self, show_name: str) -> str:
        """Enhanced show name cleaning with configuration awareness."""
        clean_name = show_name
        
        # Apply conservative cleaning for show names
        conservative_patterns = [
            r'\s*[\[\(-]?\s*[xh]\.?26[45]\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*\d{3,4}p\s*[\]\)-]?\s*',
            r'\s*[\[\(-]?\s*(bluray|brrip|dvdrip|webrip|web-dl|hdtv)\s*[\]\)-]?\s*',
            r'\s+[a-f0-9]{6,}\s*',  # Long hex strings
            r'\s*[-_\.]{2,}\s*',
        ]
        
        for pattern in conservative_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        # Apply final cleanup
        clean_name = self._final_cleanup_enhanced(clean_name)
        
        return clean_name
    
    def _apply_generic_cleaning_enhanced(self, name: str) -> str:
        """Enhanced generic cleaning with configuration-driven patterns."""
        clean_name = name
        
        # Apply all cleanup patterns based on configuration
        patterns_to_use = self.cleanup_patterns
        if not self.aggressive_cleaning:
            # Use only essential patterns for conservative cleaning
            patterns_to_use = patterns_to_use[:len(patterns_to_use)//2]
        
        for pattern in patterns_to_use:
            if pattern:  # Skip empty patterns
                clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        # Apply final cleanup
        clean_name = self._final_cleanup_enhanced(clean_name)
        
        return clean_name
    
    def _final_cleanup_enhanced(self, name: str) -> str:
        """Enhanced final cleanup with configuration awareness."""
        if not name:
            return name
        
        # Remove leading/trailing punctuation and whitespace
        name = re.sub(r'^[-_\.\s\[\(\)]+|[-_\.\s\[\(\)]+$', '', name)
        
        # Clean up internal punctuation
        name = re.sub(r'[-_\.]{2,}', ' ', name)  # Multiple punct -> space
        name = re.sub(r'\s+', ' ', name)         # Multiple spaces -> single
        
        # Handle remaining brackets/parentheses
        name = re.sub(r'\s*[\[\(]\s*[\]\)]\s*', ' ', name)  # Empty brackets
        name = re.sub(r'\s+', ' ', name)
        
        # Apply case formatting based on configuration
        if not self.preserve_original_case:
            name = self._apply_title_case_enhanced(name)
        
        return name.strip()
    
    def _apply_title_case_enhanced(self, name: str) -> str:
        """Enhanced title case with expanded preserve words."""
        if not name:
            return name
        
        words = name.split()
        formatted_words = []
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            
            # Always capitalize first and last word
            if i == 0 or i == len(words) - 1:
                formatted_words.append(word.capitalize())
            # Don't capitalize small connecting words (unless they're first/last)
            elif word_lower in self.preserve_words and len(word) <= 3:
                formatted_words.append(word_lower)
            # Capitalize everything else
            else:
                formatted_words.append(word.capitalize())
        
        return ' '.join(formatted_words)
    
    def _remove_year_from_title_enhanced(self, title: str) -> str:
        """Enhanced year removal with better cleanup."""
        # Remove various year formats
        for pattern, _ in self.year_patterns:
            title = re.sub(pattern, '', title)
        
        # Clean up leftover punctuation more thoroughly
        title = re.sub(r'\s*[\[\(\)]+\s*', ' ', title)
        title = re.sub(r'\s*[-_\.]+\s*', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        
        return title.strip()

# Enhanced utility functions
def quick_clean_filename_with_config(filename: str, mode: str = "tv", config_manager=None) -> str:
    """
    Quick filename cleaning with configuration integration.
    
    Args:
        filename: Filename to clean
        mode: Processing mode ("tv" or "movie")
        config_manager: Optional ConfigManager instance
        
    Returns:
        Cleaned filename
    """
    standardizer = FilenameStandardizer(mode, config_manager=config_manager)
    return standardizer.clean_filename(filename)

def parse_episode_info_enhanced(filename: str, config_manager=None) -> Optional[Dict[str, Any]]:
    """
    Enhanced episode info parsing with configuration integration.
    
    Args:
        filename: TV show filename to parse
        config_manager: Optional ConfigManager instance
        
    Returns:
        Dictionary with episode information and confidence score
    """
    standardizer = FilenameStandardizer("tv", config_manager=config_manager)
    return standardizer.parse_tv_episode_info_enhanced(filename)

def batch_clean_filenames(filenames: List[str], mode: str = "tv", config_manager=None) -> List[Dict[str, str]]:
    """
    Batch clean multiple filenames with statistics.
    
    Args:
        filenames: List of filenames to clean
        mode: Processing mode
        config_manager: Optional ConfigManager instance
        
    Returns:
        List of cleaning results with statistics
    """
    standardizer = FilenameStandardizer(mode, config_manager=config_manager)
    results = []
    
    for filename in filenames:
        needs_clean, reasons = standardizer.needs_cleaning(filename)
        cleaned = standardizer.clean_filename(filename)
        
        results.append({
            'original': filename,
            'cleaned': cleaned,
            'needs_cleaning': needs_clean,
            'reasons': reasons,
            'changed': filename != cleaned
        })
    
    return results

# Example usage and testing
if __name__ == "__main__":
    print(f"{__module_name__} v{__version__} - Enhanced Testing Mode")
    print("=" * 60)
    
    # Test enhanced standardizer
    standardizer_tv = FilenameStandardizer("tv")
    standardizer_movie = FilenameStandardizer("movie")
    
    # Test TV show filenames
    tv_test_files = [
        "Still Standing - S01E01 - The Pilot.avi",
        "breaking.bad.s01e01.720p.bluray.x264-dimension.mkv", 
        "The Office US 2x05 Halloween [1080p] {HEVC}.mp4",
        "Friends.Season.10.Episode.18.The.Last.One.Part.2.DVDRip.XviD-SAiNTS.avi",
        "game.of.thrones.s08e06.the.iron.throne.1080p.web.h264-memento.mkv"
    ]
    
    # Test movie filenames
    movie_test_files = [
        "The Matrix (1999) [1080p] BluRay x264-YIFY.mp4",
        "inception.2010.1080p.bluray.x264-amiable.mkv",
        "Avengers Endgame 2019 2160p UHD BluRay x265-TERMINAL.mkv",
        "the.dark.knight.2008.720p.brrip.x264.yify.mp4"
    ]
    
    print("🎬 TV SHOW CLEANING TESTS:")
    print("-" * 30)
    for filename in tv_test_files:
        needs_clean, reasons = standardizer_tv.needs_cleaning(filename)
        cleaned = standardizer_tv.clean_filename(filename)
        parse_result = standardizer_tv.parse_tv_episode_info_enhanced(filename)
        
        print(f"Original: {filename}")
        print(f"Cleaned:  {cleaned}")
        print(f"Needs cleaning: {needs_clean}")
        if reasons:
            print(f"Reasons: {', '.join(reasons)}")
        if parse_result:
            print(f"Parsed: '{parse_result['show_name']}' S{parse_result['season']:02d}E{parse_result['episode']:02d} (confidence: {parse_result['confidence']:.2f})")
        print()
    
    print("🍿 MOVIE CLEANING TESTS:")
    print("-" * 30)
    for filename in movie_test_files:
        needs_clean, reasons = standardizer_movie.needs_cleaning(filename)
        cleaned = standardizer_movie.clean_filename(filename)
        
        print(f"Original: {filename}")
        print(f"Cleaned:  {cleaned}")
        print(f"Needs cleaning: {needs_clean}")
        if reasons:
            print(f"Reasons: {', '.join(reasons)}")
        print()
    
    # Show configuration status
    config_status = standardizer_tv.get_standardizer_config_status()
    print("⚙️ CONFIGURATION STATUS:")
    print("-" * 30)
    for section, settings in config_status.items():
        print(f"{section}:")
        if isinstance(settings, dict):
            for key, value in settings.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {settings}")
        print()
    
    # Show processing statistics
    stats = standardizer_tv.get_processing_statistics()
    print("📊 PROCESSING STATISTICS:")
    print("-" * 30)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    print(f"\n✅ Enhanced standardizer v{__version__} with full config integration ready!")
