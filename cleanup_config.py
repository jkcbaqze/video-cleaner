#!/usr/bin/env python3
"""
Configuration Cleanup Script
Removes duplicate FFmpeg paths and consolidates settings
"""

import json
from pathlib import Path

def cleanup_config(config_path="master_config.json"):
    """Remove duplicate FFmpeg paths from config."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return
    
    # Load config
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    changes_made = []
    
    # Remove FFmpeg paths from video_processor if present
    if 'video_processor' in config and 'ffmpeg' in config['video_processor']:
        if 'executable_paths' in config['video_processor']['ffmpeg']:
            del config['video_processor']['ffmpeg']['executable_paths']
            changes_made.append("Removed video_processor.ffmpeg.executable_paths")
    
    # Remove FFprobe paths from video_analyzer if present
    if 'video_analyzer' in config and 'ffprobe' in config['video_analyzer']:
        if 'executable_paths' in config['video_analyzer']['ffprobe']:
            del config['video_analyzer']['ffprobe']['executable_paths']
            changes_made.append("Removed video_analyzer.ffprobe.executable_paths")
    
    # Ensure ffmpeg_global exists
    if 'ffmpeg_global' not in config:
        print("Warning: ffmpeg_global section missing, adding it")
        config['ffmpeg_global'] = {
            "_docs": {
                "description": "GLOBAL FFmpeg configuration - used by all modules",
                "executable_paths": "Search paths for FFmpeg/FFprobe executables",
                "note": "This replaces separate FFmpeg configs in other modules",
                "path_priority": "Paths are tried in order until working executable found"
            },
            "executable_paths": [
                "ffmpeg",
                "ffprobe",
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\ffmpeg\\bin\\ffprobe.exe",
                "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe"
            ],
            "verify_installation": True,
            "required_tools": ["ffmpeg", "ffprobe"]
        }
        changes_made.append("Added ffmpeg_global section")
    
    if changes_made:
        # Backup original
        backup_path = config_file.with_suffix('.json.bak')
        with open(backup_path, 'w', encoding='utf-8') as f:
            with open(config_file, 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        print(f"[OK] Backed up original config to: {backup_path}")
        
        # Write cleaned config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False, sort_keys=False)
        
        print("[OK] Configuration cleaned up!")
        print("Changes made:")
        for change in changes_made:
            print(f"  - {change}")
    else:
        print("[OK] No cleanup needed - config already using centralized FFmpeg paths")
    
    # Report on timeout consolidation opportunities
    print("\nTimeout Settings Analysis:")
    timeout_settings = []
    
    if 'video_processor' in config and 'ffmpeg' in config['video_processor']:
        if 'processing_timeout_seconds' in config['video_processor']['ffmpeg']:
            timeout_settings.append(("video_processor.ffmpeg.processing_timeout_seconds", 
                                   config['video_processor']['ffmpeg']['processing_timeout_seconds']))
        if 'probe_timeout_seconds' in config['video_processor']['ffmpeg']:
            timeout_settings.append(("video_processor.ffmpeg.probe_timeout_seconds", 
                                   config['video_processor']['ffmpeg']['probe_timeout_seconds']))
    
    if 'video_analyzer' in config and 'ffprobe' in config['video_analyzer']:
        if 'timeout_seconds' in config['video_analyzer']['ffprobe']:
            timeout_settings.append(("video_analyzer.ffprobe.timeout_seconds", 
                                   config['video_analyzer']['ffprobe']['timeout_seconds']))
    
    if 'video_analyzer' in config and 'performance' in config['video_analyzer']:
        if 'analysis_timeout_seconds' in config['video_analyzer']['performance']:
            timeout_settings.append(("video_analyzer.performance.analysis_timeout_seconds", 
                                   config['video_analyzer']['performance']['analysis_timeout_seconds']))
    
    if 'error_handling' in config and 'timeouts' in config['error_handling']:
        if 'file_operation_timeout' in config['error_handling']['timeouts']:
            timeout_settings.append(("error_handling.timeouts.file_operation_timeout", 
                                   config['error_handling']['timeouts']['file_operation_timeout']))
    
    if timeout_settings:
        print("Found multiple timeout settings:")
        for path, value in timeout_settings:
            print(f"  - {path}: {value}s")
        print("Consider consolidating these under a global timeout section")
    
    return config

if __name__ == "__main__":
    print("Video Cleaner Configuration Cleanup")
    print("=" * 50)
    cleanup_config()