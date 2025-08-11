# Project Implementation Guide: Data Files & Logging

## Overview
- **Data Sharing**: Use Pickle for fast Python-to-Python data exchange between 9 modules
- **Logging**: Use Python's built-in logging for human-readable debug/monitoring files
- **Benefits**: Maximum performance + clear debugging visibility

---

## 1. Data Sharing Setup (Pickle)

### Basic Implementation
```python
import pickle
import os

# Shared data file
SHARED_DATA_FILE = "shared_stats.pkl"

def save_data(data):
    """Save data to shared file"""
    with open(SHARED_DATA_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_data():
    """Load data from shared file"""
    if os.path.exists(SHARED_DATA_FILE):
        with open(SHARED_DATA_FILE, 'rb') as f:
            return pickle.load(f)
    return {}  # Return empty dict if file doesn't exist
```

### Cross-Platform Thread-Safe Version
```python
import pickle
import time
import os
from pathlib import Path

class CrossPlatformDataManager:
    def __init__(self, filename="shared_stats.pkl"):
        self.filename = Path(filename)
        self.lock_filename = Path(f"{filename}.lock")
    
    def _acquire_lock(self, timeout=5):
        """Simple file-based locking"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(self.lock_filename, 'x') as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                time.sleep(0.1)
        return False
    
    def _release_lock(self):
        """Release the lock"""
        try:
            self.lock_filename.unlink()
        except FileNotFoundError:
            pass
    
    def save_data(self, data):
        """Save data with file locking"""
        if self._acquire_lock():
            try:
                with open(self.filename, 'wb') as f:
                    pickle.dump(data, f)
            finally:
                self._release_lock()
        else:
            raise TimeoutError("Could not acquire lock for writing")
    
    def load_data(self, default=None):
        """Load data safely"""
        if not self.filename.exists():
            return default or {}
        
        try:
            with open(self.filename, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.UnpicklingError):
            return default or {}

# Usage across modules
data_manager = CrossPlatformDataManager("module_stats.pkl")
```

---

## 2. Logging Setup

### Basic Logging Configuration
```python
import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_dir="logs", log_level=logging.INFO):
    """Set up logging for multi-module application"""
    
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    handlers = [
        # Rotating file handler (prevents huge log files)
        logging.handlers.RotatingFileHandler(
            f"{log_dir}/application.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        # Error-only file
        logging.FileHandler(f"{log_dir}/errors.log"),
        # Console output
        logging.StreamHandler()
    ]
    
    # Configure handlers
    handlers[0].setFormatter(detailed_formatter)  # Main log
    handlers[1].setFormatter(detailed_formatter)  # Error log
    handlers[1].setLevel(logging.ERROR)
    handlers[2].setFormatter(simple_formatter)    # Console
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in handlers:
        root_logger.addHandler(handler)

# Call once in main module
setup_logging()
```

### Usage in Each Module
```python
import logging

# In each of your 9 modules
logger = logging.getLogger(__name__)

# Usage examples
logger.info("Module initialized")
logger.debug("Processing data: %s", data_summary)
logger.warning("Temperature reading high: %.2f°C", temperature)
logger.error("Failed to connect to sensor: %s", error_message)

# For exceptions
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")  # Automatically includes traceback
```

---

## 3. Complete Module Template

```python
import logging
import pickle
from pathlib import Path

# Module-specific logger
logger = logging.getLogger(__name__)

# Shared data manager
from your_shared_utils import CrossPlatformDataManager
data_manager = CrossPlatformDataManager("shared_stats.pkl")

class YourModule:
    def __init__(self):
        logger.info("Module %s initialized", __name__)
    
    def process_data(self, input_data):
        """Example processing function"""
        logger.debug("Starting data processing with %d records", len(input_data))
        
        try:
            # Load shared data
            shared_data = data_manager.load_data()
            logger.debug("Loaded shared data with keys: %s", list(shared_data.keys()))
            
            # Process your data
            results = self._do_processing(input_data)
            
            # Update shared data
            shared_data['module_results'] = results
            shared_data['last_processed'] = len(input_data)
            data_manager.save_data(shared_data)
            
            logger.info("Processing completed successfully. %d records processed", len(results))
            return results
            
        except Exception as e:
            logger.exception("Processing failed")
            raise
    
    def _do_processing(self, data):
        # Your actual processing logic here
        logger.debug("Performing specific processing operations")
        return data  # Replace with actual processing
```

---

## 4. Project Structure Recommendation

```
your_project/
├── main.py                 # Main entry point, calls setup_logging()
├── shared_utils.py         # CrossPlatformDataManager class
├── module1.py             # Your 9 modules
├── module2.py
├── ...
├── module9.py
├── logs/                  # Created automatically
│   ├── application.log    # Main log file
│   ├── errors.log         # Error-only log
│   └── application.log.1  # Rotated backups
└── shared_stats.pkl       # Your shared data file
```

---

## 5. Implementation Checklist

### Initial Setup
- [ ] Create `shared_utils.py` with `CrossPlatformDataManager`
- [ ] Add logging setup to main module
- [ ] Test basic pickle save/load functionality
- [ ] Test logging output in console and files

### For Each Module
- [ ] Import logging and create module logger
- [ ] Import shared data manager
- [ ] Add logging statements at key points
- [ ] Test data sharing between modules
- [ ] Verify log files are created and readable

### Testing
- [ ] Run multiple modules simultaneously
- [ ] Check for file locking issues
- [ ] Verify log rotation works
- [ ] Test error handling and logging
- [ ] Check shared data integrity

---

## 6. Key Benefits of This Approach

✅ **Performance**: Pickle is fastest for Python-to-Python data sharing
✅ **Reliability**: File locking prevents data corruption
✅ **Debugging**: Comprehensive logging with automatic rotation
✅ **Maintenance**: Built-in Python libraries, no external dependencies
✅ **Scalability**: Handles multiple modules accessing same data
✅ **Space Efficient**: Compact binary format + log rotation

---

## 7. Quick Reference Commands

```python
# Save data
data_manager.save_data(your_data_dict)

# Load data
current_data = data_manager.load_data()

# Log messages
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.debug("Debug details")
logger.exception("Error with traceback")
```

---

## 8. Troubleshooting Tips

**File Lock Issues**: If modules hang, check for orphaned `.lock` files
**Large Log Files**: Adjust `maxBytes` in RotatingFileHandler
**Missing Data**: Always use `load_data()` default parameter
**Performance**: Use `logger.debug()` for detailed info, `logger.info()` for key events