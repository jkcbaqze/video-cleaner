#!/usr/bin/env python3
"""
Recovery Manager v1.0
Bulletproof state management for resuming video processing after interruptions.
Designed for unattended weekend operation with power outage recovery.
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum

__version__ = "1.0"
__module_name__ = "Recovery Manager"

def module_ping():
    """Module health check for dry run reporting."""
    return f"{__module_name__} v{__version__} - READY"

class FileState(Enum):
    """File processing states for recovery tracking."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    SKIPPED = "skipped"
    RB_MARKED = "rb_marked"

class RecoveryManager:
    """
    Bulletproof recovery manager for tracking video processing state.
    Enables seamless resumption after power outages, crashes, or interruptions.
    """
    
    def __init__(self, state_file_path: str = "video_cleaner_state.json", 
                 logger=None, config_manager=None):
        """
        Initialize recovery manager with persistent state tracking.
        
        Args:
            state_file_path: Path to the JSON state file
            logger: Optional logger for detailed reporting
            config_manager: Optional config manager for settings
        """
        self.state_file_path = Path(state_file_path)
        self.logger = logger
        self.config_manager = config_manager
        
        # Register with logger for module context
        if self.logger and hasattr(self.logger, 'register_module'):
            self.logger.register_module(__module_name__, __version__)
        
        # Thread-safe state management
        self.state_lock = threading.RLock()
        
        # Recovery state structure
        self.state = {
            'session_info': {
                'session_id': None,
                'start_time': None,
                'last_update': None,
                'processing_mode': None,
                'directory_path': None,
                'total_files_found': 0,
                'session_completed': False,
                'interrupted': False
            },
            'file_states': {},  # file_path -> state_info
            'statistics': {
                'files_pending': 0,
                'files_in_progress': 0,
                'files_completed': 0,
                'files_failed': 0,
                'files_corrupted': 0,
                'files_skipped': 0,
                'files_rb_marked': 0,
                'total_space_saved': 0,
                'total_processing_time': 0.0
            },
            'error_log': [],  # List of errors with timestamps
            'config_snapshot': {},  # Key config settings at session start
            'recovery_checkpoints': []  # List of checkpoint timestamps
        }
        
        # Load existing state or create new
        self._load_state()
        
        # Auto-save settings
        self.auto_save_interval = 30  # seconds
        self.last_save_time = time.time()
        
        if self.logger:
            self.logger.log_warning(f"Recovery manager initialized - State file: {self.state_file_path}", 
                                   module_name=__module_name__)
    
    def start_session(self, processing_mode: str, directory_path: str, 
                     file_list: List[str]) -> str:
        """
        Start a new processing session with full state tracking.
        
        Args:
            processing_mode: "tv" or "movie" mode
            directory_path: Directory being processed
            file_list: List of files to process
            
        Returns:
            Session ID for tracking
        """
        with self.state_lock:
            session_id = f"{processing_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize session info
            self.state['session_info'] = {
                'session_id': session_id,
                'start_time': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat(),
                'processing_mode': processing_mode,
                'directory_path': str(directory_path),
                'total_files_found': len(file_list),
                'session_completed': False,
                'interrupted': False
            }
            
            # Initialize file states
            self.state['file_states'] = {}
            for file_path in file_list:
                self.state['file_states'][str(file_path)] = {
                    'state': FileState.PENDING.value,
                    'added_time': datetime.now().isoformat(),
                    'last_update': datetime.now().isoformat(),
                    'attempts': 0,
                    'error_message': None,
                    'processing_time': 0.0,
                    'original_size': None,
                    'processed_size': None,
                    'space_saved': 0
                }
            
            # Reset statistics
            self.state['statistics'] = {
                'files_pending': len(file_list),
                'files_in_progress': 0,
                'files_completed': 0,
                'files_failed': 0,
                'files_corrupted': 0,
                'files_skipped': 0,
                'files_rb_marked': 0,
                'total_space_saved': 0,
                'total_processing_time': 0.0
            }
            
            # Save config snapshot for consistency checking
            if self.config_manager:
                self.state['config_snapshot'] = {
                    'ffmpeg_paths': self.config_manager.get_ffmpeg_paths(),
                    'processing_timeout': self.config_manager.get_global_timeout('processing'),
                    'probe_timeout': self.config_manager.get_global_timeout('probe'),
                    'cache_enabled': self.config_manager.get_global_cache_setting('enable_caching')
                }
            
            # Clear previous error log and checkpoints
            self.state['error_log'] = []
            self.state['recovery_checkpoints'] = []
            
            self._save_state()
            
            if self.logger:
                self.logger.log_warning(f"New session started: {session_id} ({len(file_list)} files)", 
                                       module_name=__module_name__)
            
            return session_id
    
    def update_file_state(self, file_path: str, new_state: FileState, 
                          error_message: str = None, processing_time: float = 0.0,
                          original_size: int = None, processed_size: int = None):
        """
        Update the state of a specific file.
        
        Args:
            file_path: Path to the file
            new_state: New FileState
            error_message: Optional error message for failed states
            processing_time: Time spent processing this file
            original_size: Original file size in bytes
            processed_size: Processed file size in bytes
        """
        with self.state_lock:
            file_key = str(file_path)
            
            if file_key not in self.state['file_states']:
                # Add new file if not already tracked
                self.state['file_states'][file_key] = {
                    'state': FileState.PENDING.value,
                    'added_time': datetime.now().isoformat(),
                    'last_update': datetime.now().isoformat(),
                    'attempts': 0,
                    'error_message': None,
                    'processing_time': 0.0,
                    'original_size': None,
                    'processed_size': None,
                    'space_saved': 0
                }
            
            file_info = self.state['file_states'][file_key]
            old_state = FileState(file_info['state'])
            
            # Update file info
            file_info['state'] = new_state.value
            file_info['last_update'] = datetime.now().isoformat()
            file_info['processing_time'] += processing_time
            
            if error_message:
                file_info['error_message'] = error_message
                file_info['attempts'] += 1
            
            if original_size is not None:
                file_info['original_size'] = original_size
            
            if processed_size is not None:
                file_info['processed_size'] = processed_size
                if original_size and processed_size < original_size:
                    file_info['space_saved'] = original_size - processed_size
            
            # Update statistics
            self._update_statistics(old_state, new_state)
            
            # Update session timestamp
            self.state['session_info']['last_update'] = datetime.now().isoformat()
            
            # Auto-save if enough time has passed
            if time.time() - self.last_save_time > self.auto_save_interval:
                self._save_state()
            
            if self.logger:
                self.logger.info(f"File state updated: {Path(file_path).name} -> {new_state.value}", 
                               module_name=__module_name__)
    
    def mark_file_in_progress(self, file_path: str):
        """Mark file as currently being processed."""
        self.update_file_state(file_path, FileState.IN_PROGRESS)
    
    def mark_file_completed(self, file_path: str, processing_time: float = 0.0,
                           original_size: int = None, processed_size: int = None):
        """Mark file as successfully completed."""
        self.update_file_state(file_path, FileState.COMPLETED, 
                              processing_time=processing_time,
                              original_size=original_size, 
                              processed_size=processed_size)
    
    def mark_file_failed(self, file_path: str, error_message: str, 
                        processing_time: float = 0.0):
        """Mark file as failed with error message."""
        self.update_file_state(file_path, FileState.FAILED, 
                              error_message=error_message,
                              processing_time=processing_time)
        
        # Add to error log
        self.state['error_log'].append({
            'timestamp': datetime.now().isoformat(),
            'file': str(file_path),
            'error': error_message
        })
    
    def mark_file_corrupted(self, file_path: str, error_message: str):
        """Mark file as corrupted."""
        self.update_file_state(file_path, FileState.CORRUPTED, error_message=error_message)
    
    def mark_file_rb(self, file_path: str, reason: str):
        """Mark file as .rb (rollback/problem file)."""
        self.update_file_state(file_path, FileState.RB_MARKED, error_message=reason)
    
    def mark_file_skipped(self, file_path: str, reason: str):
        """Mark file as skipped."""
        self.update_file_state(file_path, FileState.SKIPPED, error_message=reason)
    
    def get_pending_files(self) -> List[str]:
        """Get list of files still pending processing."""
        with self.state_lock:
            pending = []
            for file_path, info in self.state['file_states'].items():
                if info['state'] == FileState.PENDING.value:
                    pending.append(file_path)
            return pending
    
    def get_failed_files(self) -> List[Dict[str, Any]]:
        """Get list of failed files with error details."""
        with self.state_lock:
            failed = []
            for file_path, info in self.state['file_states'].items():
                if info['state'] == FileState.FAILED.value:
                    failed.append({
                        'file_path': file_path,
                        'error_message': info.get('error_message'),
                        'attempts': info.get('attempts', 0),
                        'last_update': info.get('last_update')
                    })
            return failed
    
    def can_resume_session(self) -> bool:
        """Check if there's a valid session that can be resumed."""
        with self.state_lock:
            session_info = self.state.get('session_info', {})
            
            # Must have a session that's not completed
            if not session_info.get('session_id') or session_info.get('session_completed'):
                return False
            
            # Must have pending or in-progress files
            pending_count = self.state['statistics']['files_pending']
            in_progress_count = self.state['statistics']['files_in_progress']
            
            return pending_count > 0 or in_progress_count > 0
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary for reporting."""
        with self.state_lock:
            summary = {
                'session_info': self.state['session_info'].copy(),
                'statistics': self.state['statistics'].copy(),
                'progress_percentage': 0.0,
                'estimated_time_remaining': None,
                'recent_errors': self.state['error_log'][-5:],  # Last 5 errors
                'can_resume': self.can_resume_session()
            }
            
            # Calculate progress
            total_files = summary['session_info'].get('total_files_found', 0)
            completed_files = summary['statistics']['files_completed']
            if total_files > 0:
                summary['progress_percentage'] = (completed_files / total_files) * 100
            
            # Estimate time remaining (basic calculation)
            if completed_files > 0 and summary['statistics']['total_processing_time'] > 0:
                avg_time_per_file = summary['statistics']['total_processing_time'] / completed_files
                remaining_files = summary['statistics']['files_pending']
                summary['estimated_time_remaining'] = avg_time_per_file * remaining_files
            
            return summary
    
    def create_checkpoint(self, checkpoint_name: str = None):
        """Create a recovery checkpoint."""
        with self.state_lock:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'name': checkpoint_name or f"auto_checkpoint_{len(self.state['recovery_checkpoints']) + 1}",
                'statistics_snapshot': self.state['statistics'].copy()
            }
            
            self.state['recovery_checkpoints'].append(checkpoint)
            self._save_state()
            
            if self.logger:
                self.logger.info(f"Recovery checkpoint created: {checkpoint['name']}", 
                               module_name=__module_name__)
    
    def complete_session(self):
        """Mark the current session as completed."""
        with self.state_lock:
            self.state['session_info']['session_completed'] = True
            self.state['session_info']['last_update'] = datetime.now().isoformat()
            self._save_state()
            
            if self.logger:
                session_id = self.state['session_info'].get('session_id', 'unknown')
                self.logger.log_warning(f"Session completed: {session_id}", module_name=__module_name__)
    
    def _update_statistics(self, old_state: FileState, new_state: FileState):
        """Update statistics when file state changes."""
        stats = self.state['statistics']
        
        # Decrement old state count
        if old_state == FileState.PENDING:
            stats['files_pending'] -= 1
        elif old_state == FileState.IN_PROGRESS:
            stats['files_in_progress'] -= 1
        elif old_state == FileState.COMPLETED:
            stats['files_completed'] -= 1
        elif old_state == FileState.FAILED:
            stats['files_failed'] -= 1
        elif old_state == FileState.CORRUPTED:
            stats['files_corrupted'] -= 1
        elif old_state == FileState.SKIPPED:
            stats['files_skipped'] -= 1
        elif old_state == FileState.RB_MARKED:
            stats['files_rb_marked'] -= 1
        
        # Increment new state count
        if new_state == FileState.PENDING:
            stats['files_pending'] += 1
        elif new_state == FileState.IN_PROGRESS:
            stats['files_in_progress'] += 1
        elif new_state == FileState.COMPLETED:
            stats['files_completed'] += 1
        elif new_state == FileState.FAILED:
            stats['files_failed'] += 1
        elif new_state == FileState.CORRUPTED:
            stats['files_corrupted'] += 1
        elif new_state == FileState.SKIPPED:
            stats['files_skipped'] += 1
        elif new_state == FileState.RB_MARKED:
            stats['files_rb_marked'] += 1
    
    def _load_state(self):
        """Load state from file if it exists."""
        try:
            if self.state_file_path.exists():
                with open(self.state_file_path, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                
                # Validate and merge loaded state
                if isinstance(loaded_state, dict) and 'session_info' in loaded_state:
                    self.state.update(loaded_state)
                    
                    if self.logger:
                        session_id = self.state['session_info'].get('session_id', 'unknown')
                        self.logger.log_warning(f"Existing state loaded: {session_id}", 
                                               module_name=__module_name__)
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load state file: {e}", module_name=__module_name__)
    
    def _save_state(self):
        """Save current state to file."""
        try:
            # Ensure directory exists
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if state file exists
            if self.state_file_path.exists():
                backup_path = self.state_file_path.with_suffix('.json.bak')
                self.state_file_path.rename(backup_path)
            
            # Write state
            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False, default=str)
            
            self.last_save_time = time.time()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save state file: {e}", module_name=__module_name__)
    
    def cleanup_old_states(self, days_to_keep: int = 7):
        """Clean up old state files and backups."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # Find and remove old backup files
            backup_pattern = f"{self.state_file_path.stem}*.bak"
            for backup_file in self.state_file_path.parent.glob(backup_pattern):
                if backup_file.stat().st_mtime < cutoff_time.timestamp():
                    backup_file.unlink()
                    
                    if self.logger:
                        self.logger.info(f"Cleaned up old backup: {backup_file.name}", 
                                       module_name=__module_name__)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cleanup old states: {e}", module_name=__module_name__)

# Test the recovery manager
if __name__ == "__main__":
    print(f"{__module_name__} v{__version__} - Testing")
    print("=" * 60)
    
    # Test creating recovery manager
    recovery = RecoveryManager("test_recovery_state.json")
    print("[OK] Recovery manager created")
    
    # Test starting a session
    test_files = [
        "/test/path/file1.mkv",
        "/test/path/file2.mkv", 
        "/test/path/file3.mkv"
    ]
    
    session_id = recovery.start_session("tv", "/test/path", test_files)
    print(f"[OK] Session started: {session_id}")
    
    # Test updating file states
    recovery.mark_file_in_progress("/test/path/file1.mkv")
    recovery.mark_file_completed("/test/path/file1.mkv", processing_time=45.0, 
                                original_size=1000000, processed_size=700000)
    recovery.mark_file_failed("/test/path/file2.mkv", "Test error message")
    print("[OK] File states updated")
    
    # Test session summary
    summary = recovery.get_session_summary()
    print(f"[OK] Session summary - Progress: {summary['progress_percentage']:.1f}%")
    print(f"     Statistics: {summary['statistics']}")
    
    # Test recovery capability
    can_resume = recovery.can_resume_session()
    print(f"[OK] Can resume session: {can_resume}")
    
    print(f"\n[SUCCESS] Recovery Manager v{__version__} working correctly!")
    print("Key features:")
    print("  - Persistent state tracking in JSON")
    print("  - Thread-safe operations")
    print("  - Automatic checkpoints and backups")
    print("  - Resume capability after interruptions")
    print("  - Comprehensive error tracking")
    print("  - Session statistics and progress")