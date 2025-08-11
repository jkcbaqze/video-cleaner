#!/usr/bin/env python3
"""
Test script to verify subdirectory scanning works correctly
"""

from pathlib import Path
import tempfile
import os

# Simulate the enhanced directory scanner
class TestDirectoryScanner:
    def __init__(self):
        self.video_formats = {'.mkv', '.mp4', '.avi', '.mov'}
        self.max_depth = 10
        self.follow_symlinks = False
        
    def find_all_video_files_enhanced(self, directory_path: Path) -> list:
        """Enhanced video file discovery with explicit subdirectory handling."""
        video_files = []
        directories_to_scan = [(directory_path, 0)]  # (path, depth)
        
        print(f"Starting scan of: {directory_path}")
        
        while directories_to_scan:
            current_dir, depth = directories_to_scan.pop(0)
            print(f"  Scanning depth {depth}: {current_dir.name}")
            
            # Check depth limit
            if depth > self.max_depth:
                print(f"    ⚠️  Depth limit reached at {current_dir}")
                continue
            
            try:
                for item in current_dir.iterdir():
                    try:
                        # Skip hidden files
                        if item.name.startswith('.'):
                            continue
                            
                        if item.is_file():
                            # Check if it's a video file
                            if item.suffix.lower() in self.video_formats:
                                video_files.append(item)
                                print(f"    ✅ Found video: {item.name}")
                                
                        elif item.is_dir():
                            # 🔑 KEY FIX: Add subdirectory to scan queue
                            if self.follow_symlinks or not item.is_symlink():
                                directories_to_scan.append((item, depth + 1))
                                print(f"    📁 Added subdirectory to queue: {item.name}")
                                
                    except (PermissionError, OSError) as e:
                        print(f"    ❌ Access denied: {item} - {e}")
                        continue
                        
            except (PermissionError, OSError) as e:
                print(f"    ❌ Cannot access directory: {current_dir} - {e}")
                continue
        
        return video_files

def create_test_directory_structure():
    """Create a test directory structure to verify subdirectory scanning."""
    # Create temporary directory
    test_dir = Path(tempfile.mkdtemp(prefix="video_scan_test_"))
    
    # Create directory structure
    structure = {
        "root_video.mkv": "video",
        "Season 1": {
            "S01E01.mkv": "video",
            "S01E02.mp4": "video",
            "subtitle.srt": "text"
        },
        "Season 2": {
            "S02E01.avi": "video",
            "Nested Folder": {
                "S02E02.mov": "video",
                "Deep Nested": {
                    "S02E03.mkv": "video"
                }
            }
        },
        "Movies": {
            "Movie1.mp4": "video",
            "Movie2.wmv": "video"  # Not in our test formats, should be skipped
        },
        "Other Files": {
            "document.txt": "text",
            "image.jpg": "image"
        }
    }
    
    def create_structure(base_path, structure_dict):
        for name, content in structure_dict.items():
            item_path = base_path / name
            
            if isinstance(content, dict):
                # It's a directory
                item_path.mkdir()
                create_structure(item_path, content)
            else:
                # It's a file
                item_path.write_text(f"Test {content} file content")
    
    create_structure(test_dir, structure)
    return test_dir

def test_subdirectory_scanning():
    """Test that subdirectory scanning works correctly."""
    print("🧪 Testing Subdirectory Scanning")
    print("=" * 50)
    
    # Create test directory structure
    test_dir = create_test_directory_structure()
    print(f"Created test directory: {test_dir}")
    
    # Show directory structure
    print(f"\n📁 Test Directory Structure:")
    for root, dirs, files in os.walk(test_dir):
        level = root.replace(str(test_dir), '').count(os.sep)
        indent = '  ' * level
        print(f"{indent}{Path(root).name}/")
        subindent = '  ' * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
    
    # Test the scanner
    print(f"\n🔍 Scanning for video files...")
    scanner = TestDirectoryScanner()
    found_videos = scanner.find_all_video_files_enhanced(test_dir)
    
    # Report results
    print(f"\n📊 Scan Results:")
    print(f"Total video files found: {len(found_videos)}")
    
    # Expected files (based on our test structure and supported formats)
    expected_videos = [
        "root_video.mkv",
        "S01E01.mkv", 
        "S01E02.mp4",
        "S02E01.avi",
        "S02E02.mov",
        "S02E03.mkv",  # Deep nested
        "Movie1.mp4"
        # Movie2.wmv should be skipped (not in video_formats)
    ]
    
    found_names = [f.name for f in found_videos]
    found_names.sort()
    expected_videos.sort()
    
    print(f"\nExpected videos: {len(expected_videos)}")
    for video in expected_videos:
        print(f"  ✓ {video}")
    
    print(f"\nActually found: {len(found_names)}")
    for video in found_names:
        print(f"  ✓ {video}")
    
    # Check if all expected videos were found
    missing = set(expected_videos) - set(found_names)
    unexpected = set(found_names) - set(expected_videos)
    
    if not missing and not unexpected:
        print(f"\n✅ SUCCESS: All expected videos found, no unexpected files!")
        print(f"✅ Subdirectory scanning is working correctly!")
    else:
        if missing:
            print(f"\n❌ MISSING videos:")
            for video in missing:
                print(f"  - {video}")
        if unexpected:
            print(f"\n❌ UNEXPECTED videos:")
            for video in unexpected:
                print(f"  + {video}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\n🧹 Cleaned up test directory")
    
    return len(missing) == 0 and len(unexpected) == 0

if __name__ == "__main__":
    success = test_subdirectory_scanning()
    
    if success:
        print(f"\n🎉 SUBDIRECTORY SCANNING TEST PASSED!")
        print(f"The enhanced utils.py should correctly find videos in all subdirectories.")
    else:
        print(f"\n💥 SUBDIRECTORY SCANNING TEST FAILED!")
        print(f"There may still be issues with the scanning logic.")
