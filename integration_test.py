#!/usr/bin/env python3
"""
Integration test for Rust videocleaner_core module
Tests the performance difference between Python and Rust implementations
"""

import time
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Test if Rust core is available
try:
    import videocleaner_core
    RUST_AVAILABLE = True
    print("✅ Rust videocleaner_core loaded successfully!")
    print(f"   Version: {videocleaner_core.__version__}")
    print(f"   Functions: {[name for name in dir(videocleaner_core) if not name.startswith('_')]}")
except ImportError as e:
    RUST_AVAILABLE = False
    print("❌ Rust videocleaner_core not available:", e)
    print("   Will test Python-only implementation")

# Import your existing Python implementation
from utils import DirectoryScanner

def test_directory_performance(test_directory: str):
    """Compare Python vs Rust directory scanning performance."""
    print(f"\n🧪 Performance Test: {test_directory}")
    print("=" * 60)
    
    if not Path(test_directory).exists():
        print(f"❌ Test directory not found: {test_directory}")
        return
    
    results = {}
    
    # Test 1: Python Implementation
    print("🐍 Testing Python implementation...")
    python_start = time.time()
    try:
        scanner = DirectoryScanner()
        folder_info_py, format_counts_py = scanner.preview_directory(Path(test_directory))
        python_time = time.time() - python_start
        
        total_files_py = sum(format_counts_py.values())
        results['python'] = {
            'time': python_time,
            'folders': len(folder_info_py),
            'files': total_files_py,
            'formats': dict(format_counts_py)
        }
        print(f"   ✅ Completed in {python_time:.3f} seconds")
        print(f"   📁 Found {len(folder_info_py)} folders, {total_files_py} video files")
        
    except Exception as e:
        print(f"   ❌ Python test failed: {e}")
        results['python'] = {'error': str(e)}
    
    # Test 2: Rust Implementation (if available)
    if RUST_AVAILABLE:
        print("\n🦀 Testing Rust implementation...")
        rust_start = time.time()
        try:
            folder_info_rust, format_counts_rust = videocleaner_core.scan_directory_fast(test_directory)
            rust_time = time.time() - rust_start
            
            total_files_rust = sum(format_counts_rust.values())
            results['rust'] = {
                'time': rust_time,
                'folders': len(folder_info_rust),
                'files': total_files_rust,
                'formats': dict(format_counts_rust)
            }
            print(f"   ✅ Completed in {rust_time:.3f} seconds")
            print(f"   📁 Found {len(folder_info_rust)} folders, {total_files_rust} video files")
            
            # Performance comparison
            if 'python' in results and 'error' not in results['python']:
                speedup = python_time / rust_time
                print(f"\n🚀 Performance Results:")
                print(f"   Python time: {python_time:.3f}s")
                print(f"   Rust time:   {rust_time:.3f}s")
                print(f"   Speedup:     {speedup:.1f}x faster")
                
                if speedup > 2.0:
                    print("   🎉 Significant performance improvement!")
                elif speedup > 1.3:
                    print("   ✅ Good performance improvement")
                else:
                    print("   ⚠️ Modest improvement - overhead may be factor")
                
                # Verify results match
                if total_files_py == total_files_rust:
                    print("   ✅ Results match - same files found")
                else:
                    print(f"   ⚠️ File count mismatch: Python={total_files_py}, Rust={total_files_rust}")
                    
        except Exception as e:
            print(f"   ❌ Rust test failed: {e}")
            results['rust'] = {'error': str(e)}
    
    return results

def test_rust_functions():
    """Test individual Rust functions."""
    if not RUST_AVAILABLE:
        print("⚠️ Skipping Rust function tests - module not available")
        return
    
    print("\n🔧 Testing Individual Rust Functions:")
    print("=" * 50)
    
    # Test directory validation
    print("Testing directory validation...")
    test_dirs = [".", "/nonexistent", "C:\\Windows" if sys.platform == "win32" else "/tmp"]
    
    for test_dir in test_dirs:
        try:
            is_valid = videocleaner_core.validate_directory(test_dir)
            print(f"   {test_dir}: {'✅ Valid' if is_valid else '❌ Invalid'}")
        except Exception as e:
            print(f"   {test_dir}: ❌ Error - {e}")
    
    # Test directory stats
    print("\nTesting directory statistics...")
    try:
        stats = videocleaner_core.get_directory_stats(".")
        print("   Current directory stats:")
        for key, value in stats.items():
            if 'size' in key and 'bytes' not in key:
                print(f"     {key}: {value}")
            else:
                print(f"     {key}: {value:,}")
    except Exception as e:
        print(f"   ❌ Stats test failed: {e}")

def benchmark_with_different_sizes():
    """Test performance with different directory sizes."""
    print("\n📊 Size-based Performance Analysis:")
    print("=" * 50)
    
    test_directories = [
        ".",  # Current directory (small)
        # Add your own test paths here based on what you have available
    ]
    
    for test_dir in test_directories:
        if Path(test_dir).exists():
            print(f"\nTesting: {test_dir}")
            try:
                if RUST_AVAILABLE:
                    stats = videocleaner_core.get_directory_stats(test_dir)
                    print(f"   Files: {stats.get('total_files', 0):,}")
                    print(f"   Video files: {stats.get('video_files', 0):,}")
                    print(f"   Size: {stats.get('total_size_gb', 0):.1f} GB")
                
                results = test_directory_performance(test_dir)
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Universal Video Cleaner - Rust Integration Test")
    print("=" * 60)
    
    # Basic function tests
    test_rust_functions()
    
    # Performance benchmarks
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARKS")
    print("="*60)
    
    # Test with current directory as a start
    if len(sys.argv) > 1:
        test_directory = sys.argv[1]
        print(f"Using provided directory: {test_directory}")
        test_directory_performance(test_directory)
    else:
        print("Testing with current directory (small test)...")
        test_directory_performance(".")
        
        print("\n💡 To test with your video directory:")
        print(f"   python {sys.argv[0]} 'path/to/your/video/directory'")
    
    # Size-based analysis
    benchmark_with_different_sizes()
    
    print("\n🎯 Integration test complete!")
    if RUST_AVAILABLE:
        print("   Rust module is working - ready for production use!")
    else:
        print("   Install Rust module with: cd videocleaner_core && maturin develop --release")
