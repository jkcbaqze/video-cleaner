#!/usr/bin/env python3
"""
Video Cleaner GUI - Complete Mission Control System
Based on the A+ config GUI, now with execution and monitoring capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
from datetime import datetime
import shutil
import os
import subprocess
import threading
import queue
import time

class ToolTip:
    """Simple tooltip that shows helpful text when you hover over widgets"""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        # Bind hover events
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        """Show the tooltip when mouse enters widget"""
        if self.tooltip_window or not self.text:
            return
        
        # Get widget position safely
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
        except:
            return
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("Arial", 9))
        label.pack()
    
    def hide_tooltip(self, event=None):
        """Hide the tooltip when mouse leaves widget"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ProcessorBridge:
    """Transfer station between GUI and video_cleaner.py"""
    
    def __init__(self, gui_callback):
        self.gui_callback = gui_callback
        self.process = None
        self.monitor_thread = None
        self.output_queue = queue.Queue()
        self.is_running = False
        
    def start_processing(self, directory, mode, dry_run=False, config_file="master_config.json"):
        """Start video processing with specified parameters"""
        if self.is_running:
            return False, "Processing already running"
        
        try:
            # Build command
            cmd = [
                'python', 'video_cleaner.py',
                '--auto',
                '--directory', str(directory),
                '--mode', mode,
                '--config', config_file
            ]
            
            if dry_run:
                cmd.append('--dry-run')
            
            # Start subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            self.is_running = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.monitor_thread.start()
            
            return True, "Processing started successfully"
            
        except Exception as e:
            return False, f"Failed to start processing: {e}"
    
    def stop_processing(self):
        """Stop the current processing"""
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.is_running = False
            return True, "Processing stopped"
        return False, "No processing running"
    
    def _monitor_output(self):
        """Monitor subprocess output and send updates to GUI"""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_queue.put(('output', line.strip()))
                    self._parse_progress_line(line.strip())
            
            # Process finished
            return_code = self.process.wait()
            self.is_running = False
            
            if return_code == 0:
                self.output_queue.put(('status', 'completed'))
            else:
                self.output_queue.put(('status', 'failed'))
                
        except Exception as e:
            self.output_queue.put(('error', f"Monitor error: {e}"))
            self.is_running = False
    
    def _parse_progress_line(self, line):
        """Parse output lines for progress information"""
        # Look for progress patterns
        if "Processing:" in line:
            # Extract current file
            parts = line.split("Processing:")
            if len(parts) > 1:
                filename = parts[1].strip()
                self.output_queue.put(('current_file', filename))
        
        elif "Progress:" in line:
            # Extract progress numbers
            # Expected format: "Progress: 45/100 files completed"
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if '/' in part and part.replace('/', '').isdigit():
                        current, total = map(int, part.split('/'))
                        self.output_queue.put(('progress', {'current': current, 'total': total}))
                        break
            except Exception:
                pass
        
        elif "Status:" in line:
            # Extract status message
            parts = line.split("Status:")
            if len(parts) > 1:
                status = parts[1].strip()
                self.output_queue.put(('status_message', status))
    
    def get_updates(self):
        """Get all queued updates"""
        updates = []
        try:
            while True:
                update = self.output_queue.get_nowait()
                updates.append(update)
        except queue.Empty:
            pass
        return updates

class ConfigSection:
    """Configuration section with browse support (from your A+ GUI)"""
    
    def __init__(self, name: str, data: dict, parent_frame: ttk.Frame, gui_parent):
        self.name = name
        self.data = data
        self.parent_frame = parent_frame
        self.gui_parent = gui_parent
        self.widgets = {}
        
        # Setting descriptions for tooltips
        self.setting_descriptions = {
            'processing_timeout_seconds': 'How long to wait for video conversion before giving up (in seconds)',
            'crf_quality': 'Video quality setting: 18=excellent/large, 23=good/medium, 28=okay/small',
            'max_size_multiplier': 'Flag files larger than this multiple of expected size (2.5 = 250% of normal)',
            'enable_size_checking': 'Turn on/off automatic detection of unusually large or small files',
            'use_rich_ui': 'Use colorful enhanced interface (true) or simple text interface (false)',
            'max_iterations': 'Maximum number of processing runs allowed in one session',
            'panel_width': 'Width of display panels in characters (40-120)',
            'log_level': 'How much detail to log: DEBUG=everything, INFO=normal, ERROR=problems only',
            'executable_paths': 'List of paths where FFmpeg/FFprobe might be installed',
            'preset': 'FFmpeg encoding speed vs compression: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow'
        }
    
    def create_widgets(self):
        """Create widgets for this entire section"""
        section_frame = ttk.LabelFrame(self.parent_frame, text=f"📁 {self.name.replace('_', ' ').title()}")
        section_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_section_content(section_frame, self.data, "")
    
    def _create_section_content(self, parent: ttk.Frame, data: dict, path_prefix: str):
        """Recursively create widgets for nested configuration"""
        for key, value in data.items():
            if key.startswith('_'):
                continue
                
            full_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if isinstance(value, dict):
                subsection_frame = ttk.LabelFrame(parent, text=key.replace('_', ' ').title())
                subsection_frame.pack(fill='x', padx=10, pady=3)
                self._create_section_content(subsection_frame, value, full_path)
            else:
                self._create_setting_widget(parent, key, value, full_path)
    
    def _create_setting_widget(self, parent: ttk.Frame, key: str, value, full_path: str):
        """Create appropriate widget for a configuration setting"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill='x', padx=5, pady=2)
        
        # Label
        label_text = key.replace('_', ' ').title()
        if len(label_text) > 30:
            label_text = label_text[:27] + "..."
        label = ttk.Label(row_frame, text=label_text, width=30)
        label.pack(side='left')
        
        # Add tooltip
        description = self.setting_descriptions.get(key, f"Setting: {self.name}.{key}")
        ToolTip(label, description)
        
        # Determine if this setting needs a browse button
        needs_browse, browse_type = self._needs_browse_button(key, full_path, value)
        
        # Create input widget
        if isinstance(value, bool):
            var = tk.StringVar(value=str(value).lower())
            widget = ttk.Combobox(row_frame, textvariable=var, values=['true', 'false'], 
                                state='readonly', width=10)
            widget.pack(side='left', padx=5)
            
        elif isinstance(value, (int, float)):
            var = tk.StringVar(value=str(value))
            widget = ttk.Entry(row_frame, textvariable=var, width=15)
            widget.pack(side='left', padx=5)
            
        elif isinstance(value, list):
            var = tk.StringVar(value=', '.join(map(str, value)))
            
            if needs_browse:
                entry_frame = ttk.Frame(row_frame)
                entry_frame.pack(side='left', padx=5, fill='x', expand=True)
                
                widget = ttk.Entry(entry_frame, textvariable=var, width=40)
                widget.pack(side='left', fill='x', expand=True)
                
                browse_btn = ttk.Button(entry_frame, text="➕ Add", width=8,
                                      command=lambda: self._browse_for_file_list(var, key))
                browse_btn.pack(side='right', padx=(2, 0))
                ToolTip(browse_btn, f"Browse to add files to {key}")
            else:
                widget = ttk.Entry(row_frame, textvariable=var, width=40)
                widget.pack(side='left', padx=5)
                
        else:
            # String value
            var = tk.StringVar(value=str(value))
            
            if needs_browse:
                entry_frame = ttk.Frame(row_frame)
                entry_frame.pack(side='left', padx=5, fill='x', expand=True)
                
                widget = ttk.Entry(entry_frame, textvariable=var, width=35)
                widget.pack(side='left', fill='x', expand=True)
                
                if browse_type == 'file':
                    browse_btn = ttk.Button(entry_frame, text="📁 Browse", width=10,
                                          command=lambda: self._browse_for_file(var, key))
                elif browse_type == 'directory':
                    browse_btn = ttk.Button(entry_frame, text="📂 Browse", width=10,
                                          command=lambda: self._browse_for_directory(var, key))
                else:
                    browse_btn = ttk.Button(entry_frame, text="📁 Browse", width=10,
                                          command=lambda: self._browse_for_file(var, key))
                
                browse_btn.pack(side='right', padx=(2, 0))
                ToolTip(browse_btn, f"Browse for {key}")
            else:
                widget = ttk.Entry(row_frame, textvariable=var, width=40)
                widget.pack(side='left', padx=5)
        
        ToolTip(widget, description)
        self.widgets[full_path] = var
        
        # Add validation indicator
        status_label = ttk.Label(row_frame, text="✓", foreground="green", width=2)
        status_label.pack(side='right', padx=2)
        self.widgets[f"{full_path}_status"] = status_label
    
    def _needs_browse_button(self, key: str, full_path: str, value) -> tuple:
        """Determine if a setting needs a browse button"""
        key_lower = key.lower()
        path_lower = full_path.lower()
        
        if any(indicator in key_lower for indicator in ['executable', 'ffmpeg', 'ffprobe', '_path']) and 'directory' not in key_lower:
            return True, 'file'
        
        if any(indicator in path_lower for indicator in ['executable_paths', 'ffmpeg']):
            return True, 'file_list'
        
        if any(indicator in key_lower for indicator in ['directory', 'folder', 'temp_path', 'backup_path']):
            return True, 'directory'
        
        if isinstance(value, list) and len(value) > 0:
            sample_value = str(value[0]) if value else ""
            if any(ext in sample_value.lower() for ext in ['.exe', '.app', 'ffmpeg', 'ffprobe', '\\', '/']):
                return True, 'file_list'
        
        return False, None
    
    def _browse_for_file(self, var: tk.StringVar, key: str):
        """Open file dialog"""
        key_lower = key.lower()
        
        if 'ffmpeg' in key_lower or 'executable' in key_lower:
            if os.name == 'nt':
                filetypes = [("Executable files", "*.exe"), ("All files", "*.*")]
            else:
                filetypes = [("All files", "*")]
        else:
            filetypes = [("All files", "*.*")]
        
        filename = filedialog.askopenfilename(
            title=f"Select {key.replace('_', ' ').title()}",
            filetypes=filetypes
        )
        
        if filename:
            var.set(filename)
    
    def _browse_for_directory(self, var: tk.StringVar, key: str):
        """Open directory dialog"""
        directory = filedialog.askdirectory(
            title=f"Select {key.replace('_', ' ').title()}"
        )
        
        if directory:
            var.set(directory)
    
    def _browse_for_file_list(self, var: tk.StringVar, key: str):
        """Browse for file and add to list"""
        key_lower = key.lower()
        
        if 'ffmpeg' in key_lower or 'executable' in key_lower:
            if os.name == 'nt':
                filetypes = [("Executable files", "*.exe"), ("All files", "*.*")]
            else:
                filetypes = [("All files", "*")]
        else:
            filetypes = [("All files", "*.*")]
        
        filename = filedialog.askopenfilename(
            title=f"Add to {key.replace('_', ' ').title()}",
            filetypes=filetypes
        )
        
        if filename:
            current_list = var.get().strip()
            if current_list:
                new_list = current_list + ", " + filename
            else:
                new_list = filename
            var.set(new_list)
    
    def get_data(self) -> dict:
        """Get current data from widgets"""
        result = {}
        
        for path, var in self.widgets.items():
            if path.endswith('_status'):
                continue
                
            value = var.get()
            
            # Convert value back to appropriate type
            if ',' in value and not os.path.exists(value):
                value = [item.strip() for item in value.split(',') if item.strip()]
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            else:
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
            
            # Set nested value
            self._set_nested_value(result, path.split('.'), value)
        
        return result
    
    def _set_nested_value(self, data: dict, path_parts: list, value):
        """Set nested value in data structure"""
        current = data
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = value

class VideoCleanerGUI:
    """Complete Video Cleaner GUI - Configuration + Execution + Monitoring"""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Universal Video Cleaner - Mission Control")
        self.window.geometry("1000x700")
        
        self.config_file = Path("master_config.json")
        self.config_data = {}
        self.sections = {}
        
        # Processing control
        self.processor_bridge = ProcessorBridge(self.on_process_update)
        self.selected_directory = tk.StringVar()
        self.processing_mode = tk.StringVar(value="tv")
        self.dry_run_mode = tk.BooleanVar(value=True)
        
        # Monitoring variables
        self.current_file = tk.StringVar(value="Ready")
        self.progress_current = tk.IntVar(value=0)
        self.progress_total = tk.IntVar(value=100)
        self.status_message = tk.StringVar(value="Ready to process")
        
        self.setup_ui()
        self.load_config()
        
        # Start update polling
        self.poll_updates()
    
    def setup_ui(self):
        """Setup the main UI with three tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Tab 1: Configuration (your A+ GUI)
        self.setup_config_tab()
        
        # Tab 2: Execute
        self.setup_execute_tab()
        
        # Tab 3: Monitor (placeholder for future)
        self.setup_monitor_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')
    
    def setup_config_tab(self):
        """Setup configuration tab (your existing A+ code)"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="⚙️ Configuration")
        
        # Toolbar
        toolbar = ttk.Frame(config_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="💾 Save", command=self.save_config).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔄 Reload", command=self.load_config).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔍 Auto-Detect FFmpeg", command=self.auto_detect_ffmpeg).pack(side='left', padx=2)
        
        # Scrollable content
        canvas = tk.Canvas(config_frame)
        scrollbar = ttk.Scrollbar(config_frame, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mousewheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def setup_execute_tab(self):
        """Setup execution control tab"""
        execute_frame = ttk.Frame(self.notebook)
        self.notebook.add(execute_frame, text="🚀 Execute")
        
        # Main control panel
        control_panel = ttk.LabelFrame(execute_frame, text="Processing Control")
        control_panel.pack(fill='x', padx=10, pady=10)
        
        # Directory selection
        dir_frame = ttk.Frame(control_panel)
        dir_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(dir_frame, text="Directory:", width=12).pack(side='left')
        dir_entry = ttk.Entry(dir_frame, textvariable=self.selected_directory, width=50)
        dir_entry.pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(dir_frame, text="📂 Browse", 
                  command=self.browse_directory).pack(side='right', padx=5)
        
        # Mode and options
        options_frame = ttk.Frame(control_panel)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(options_frame, text="Mode:", width=12).pack(side='left')
        mode_combo = ttk.Combobox(options_frame, textvariable=self.processing_mode, 
                                 values=['tv', 'movie'], state='readonly', width=10)
        mode_combo.pack(side='left', padx=5)
        
        dry_run_check = ttk.Checkbutton(options_frame, text="Dry Run (Analysis Only)", 
                                       variable=self.dry_run_mode)
        dry_run_check.pack(side='left', padx=20)
        
        # Control buttons
        button_frame = ttk.Frame(control_panel)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Processing", 
                                      command=self.start_processing)
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="🛑 Stop Processing", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Status display
        status_panel = ttk.LabelFrame(execute_frame, text="Current Status")
        status_panel.pack(fill='x', padx=10, pady=5)
        
        # Current file
        current_frame = ttk.Frame(status_panel)
        current_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(current_frame, text="Current File:").pack(side='left')
        ttk.Label(current_frame, textvariable=self.current_file, 
                 font=('Arial', 9, 'bold')).pack(side='left', padx=10)
        
        # Progress bar
        progress_frame = ttk.Frame(status_panel)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(progress_frame, text="Progress:").pack(side='left')
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(side='left', padx=10, fill='x', expand=True)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0 (0%)")
        self.progress_label.pack(side='right', padx=5)
        
        # Status message
        status_msg_frame = ttk.Frame(status_panel)
        status_msg_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(status_msg_frame, text="Status:").pack(side='left')
        ttk.Label(status_msg_frame, textvariable=self.status_message).pack(side='left', padx=10)
    
    def setup_monitor_tab(self):
        """Setup monitoring tab (placeholder for future enhancement)"""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="📊 Monitor")
        
        # Placeholder content
        placeholder = ttk.Label(monitor_frame, 
                               text="📊 Advanced Monitoring\n\n" +
                                    "Coming Soon:\n" +
                                    "• Live log viewer\n" +
                                    "• Detailed statistics\n" +
                                    "• Multi-session tracking\n" +
                                    "• Performance analytics",
                               font=('Arial', 12),
                               justify='center')
        placeholder.pack(expand=True)
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                self.create_config_sections()
                self.status_var.set(f"Loaded: {self.config_file}")
            else:
                messagebox.showerror("Error", f"Config file not found: {self.config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
    
    def create_config_sections(self):
        """Create configuration sections"""
        # Clear existing sections
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.sections.clear()
        
        # Create sections
        for section_name, section_data in self.config_data.items():
            if section_name.startswith('_'):
                continue
                
            if isinstance(section_data, dict):
                section = ConfigSection(section_name, section_data, self.scrollable_frame, self)
                section.create_widgets()
                self.sections[section_name] = section
    
    def save_config(self):
        """Save configuration"""
        try:
            # Collect data from all sections
            new_config = {}
            for section_name, section in self.sections.items():
                new_config[section_name] = section.get_data()
            
            # Preserve metadata
            if '_metadata' in self.config_data:
                new_config['_metadata'] = self.config_data['_metadata'].copy()
                new_config['_metadata']['last_updated'] = datetime.now().isoformat()
            
            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            
            self.config_data = new_config
            self.status_var.set("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def auto_detect_ffmpeg(self):
        """Auto-detect FFmpeg installations"""
        self.status_var.set("Searching for FFmpeg installations...")
        
        detected_paths = []
        common_paths = [
            "ffmpeg", "ffprobe",
            "C:\\ffmpeg\\bin\\ffmpeg.exe", "C:\\ffmpeg\\bin\\ffprobe.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe", "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe"
        ]
        
        for path in common_paths:
            if shutil.which(path) or (Path(path).exists() and Path(path).is_file()):
                if path not in detected_paths:
                    detected_paths.append(path)
        
        if detected_paths:
            # Update executable paths
            for section_name, section in self.sections.items():
                if 'executable_paths' in section.widgets:
                    current_paths = section.widgets['executable_paths'].get()
                    all_paths = current_paths.split(', ') if current_paths else []
                    
                    for path in detected_paths:
                        if path not in all_paths:
                            all_paths.append(path)
                    
                    section.widgets['executable_paths'].set(', '.join(all_paths))
                    break
            
            self.status_var.set(f"Auto-detected {len(detected_paths)} FFmpeg paths")
            messagebox.showinfo("Auto-Detection Complete", 
                              f"Found:\n" + "\n".join(detected_paths) +
                              f"\n\nClick Save to keep changes.")
        else:
            self.status_var.set("No FFmpeg installations found")
            messagebox.showinfo("Auto-Detection Complete", "No installations found.")
    
    def browse_directory(self):
        """Browse for processing directory"""
        directory = filedialog.askdirectory(title="Select Directory to Process")
        if directory:
            self.selected_directory.set(directory)
    
    def start_processing(self):
        """Start video processing"""
        directory = self.selected_directory.get().strip()
        if not directory:
            messagebox.showerror("Error", "Please select a directory to process")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", f"Directory does not exist: {directory}")
            return
        
        # Save config first
        self.save_config()
        
        # Start processing
        success, message = self.processor_bridge.start_processing(
            directory, 
            self.processing_mode.get(),
            self.dry_run_mode.get(),
            str(self.config_file)
        )
        
        if success:
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.status_var.set("Processing started...")
            self.status_message.set("Initializing...")
        else:
            messagebox.showerror("Error", message)
    
    def stop_processing(self):
        """Stop video processing"""
        success, message = self.processor_bridge.stop_processing()
        
        if success:
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.status_var.set("Processing stopped")
            self.status_message.set("Stopped by user")
        else:
            messagebox.showwarning("Warning", message)
    
    def on_process_update(self, update_type, data):
        """Handle process updates (callback)"""
        # This can be extended for more sophisticated update handling
        pass
    
    def poll_updates(self):
        """Poll for updates from processor bridge"""
        updates = self.processor_bridge.get_updates()
        
        for update_type, data in updates:
            if update_type == 'current_file':
                self.current_file.set(data)
            elif update_type == 'progress':
                current = data['current']
                total = data['total']
                self.progress_current.set(current)
                self.progress_total.set(total)
                
                # Update progress bar
                if total > 0:
                    percentage = (current / total) * 100
                    self.progress_bar['value'] = percentage
                    self.progress_label.config(text=f"{current}/{total} ({percentage:.1f}%)")
                
            elif update_type == 'status_message':
                self.status_message.set(data)
            elif update_type == 'status':
                if data == 'completed':
                    self.start_button.config(state='normal')
                    self.stop_button.config(state='disabled')
                    self.status_var.set("Processing completed!")
                    messagebox.showinfo("Complete", "Processing finished successfully!")
                elif data == 'failed':
                    self.start_button.config(state='normal')
                    self.stop_button.config(state='disabled')
                    self.status_var.set("Processing failed")
                    messagebox.showerror("Failed", "Processing failed. Check the logs.")
            elif update_type == 'output':
                # For future: could add to log viewer
                pass
        
        # Schedule next poll
        self.window.after(500, self.poll_updates)  # Poll every 500ms
    
    def run(self):
        """Start the application"""
        self.window.mainloop()

def main():
    """Run the video cleaner GUI"""
    app = VideoCleanerGUI()
    app.run()

if __name__ == "__main__":
    main()