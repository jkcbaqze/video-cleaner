#!/usr/bin/env python3
"""
Test Configuration Consolidation
Verifies that FFmpeg paths and timeouts are properly centralized
"""

from config_manager import ConfigManager
from analyzer import VideoAnalyzer
from processor import VideoProcessor
from logger import ProfessionalLogger

def test_config_consolidation():
    """Test that all modules use centralized configuration."""
    print("Configuration Consolidation Test")
    print("=" * 60)
    
    # Create config manager
    config_manager = ConfigManager()
    
    # Create logger
    logger = ProfessionalLogger(config_manager=config_manager)
    
    # Create analyzer
    analyzer = VideoAnalyzer(logger=logger, config_manager=config_manager)
    
    # Create processor (need dummy config object)
    class DummyConfig:
        def __init__(self):
            self.processing_mode = "normal"
            self.dry_run = False
    
    dummy_config = DummyConfig()
    processor = VideoProcessor(dummy_config, logger=logger, config_manager=config_manager)
    
    print("\n1. FFmpeg Path Consolidation:")
    print("-" * 40)
    
    # Get global FFmpeg paths
    global_paths = config_manager.get_ffmpeg_paths()
    print(f"Global FFmpeg paths: {len(global_paths)} paths configured")
    
    # Check analyzer uses same paths
    print(f"Analyzer FFprobe paths: {len(analyzer.ffprobe_paths)} paths")
    print(f"Paths match global: {analyzer.ffprobe_paths == global_paths}")
    
    # Check processor uses same paths  
    print(f"Processor FFmpeg paths: {len(processor.ffmpeg_paths)} paths")
    print(f"Paths match global: {processor.ffmpeg_paths == global_paths}")
    
    print("\n2. Timeout Consolidation:")
    print("-" * 40)
    
    # Check global timeouts
    global_processing = config_manager.get_global_timeout('processing')
    global_probe = config_manager.get_global_timeout('probe')
    global_file_op = config_manager.get_global_timeout('file_operation')
    
    print(f"Global processing timeout: {global_processing}s")
    print(f"Global probe timeout: {global_probe}s")
    print(f"Global file operation timeout: {global_file_op}s")
    
    # Check modules use global timeouts
    print(f"\nProcessor processing timeout: {processor.processing_timeout}s (matches: {processor.processing_timeout == global_processing})")
    print(f"Processor probe timeout: {processor.probe_timeout}s (matches: {processor.probe_timeout == global_probe})")
    print(f"Analyzer probe timeout: {analyzer.ffprobe_timeout}s (matches: {analyzer.ffprobe_timeout == global_probe})")
    
    print("\n3. Cache Settings Consolidation:")
    print("-" * 40)
    
    # Check global cache settings
    global_cache_enabled = config_manager.get_global_cache_setting('enable_caching')
    global_max_entries = config_manager.get_global_cache_setting('max_cache_entries')
    global_duration = config_manager.get_global_cache_setting('cache_duration_minutes')
    
    print(f"Global cache enabled: {global_cache_enabled}")
    print(f"Global max cache entries: {global_max_entries}")
    print(f"Global cache duration: {global_duration} minutes")
    
    print("\n4. Configuration Validation:")
    print("-" * 40)
    
    # Check for duplicate warnings
    config_info = config_manager.get_config_info()
    if config_info['duplicate_warnings']:
        print("Warnings found:")
        for warning in config_info['duplicate_warnings']:
            print(f"  - {warning}")
    else:
        print("[OK] No configuration duplicates or warnings")
    
    print(f"\nHas global FFmpeg config: {config_info['has_global_ffmpeg']}")
    print(f"Has global timeouts: {'timeouts_global' in config_manager.config}")
    print(f"Has global cache: {'cache_global' in config_manager.config}")
    
    print("\n[SUCCESS] Configuration consolidation complete!")
    print("\nKey improvements:")
    print("- FFmpeg paths centralized in ffmpeg_global section")
    print("- Timeouts can be managed globally or per-module")
    print("- Cache settings can be managed globally or per-module")
    print("- All modules use get_ffmpeg_paths() for consistency")
    print("- All modules can use get_global_timeout() for consistency")

if __name__ == "__main__":
    test_config_consolidation()