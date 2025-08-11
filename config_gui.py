#!/usr/bin/env python3
"""
Complete Configuration GUI - All Settings with Browse Support
Shows every setting in the config file with appropriate input widgets and browse buttons.
No JSON editing required - pure form-based interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
from datetime import datetime
import shutil
import os

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

class ConfigSection:
    """Represents a section of the configuration with all settings visible"""
    
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
            'preset': 'FFmpeg encoding speed vs compression: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow',
            'custom_temp_path': 'Directory to use for temporary files during processing',
            'backup_directory': 'Directory to store backup files',
            'min_size_multiplier': 'Flag files smaller than this multiple of expected size (0.3 = 30% of normal)',
            'warning_threshold': 'Show warning when files are this multiple of expected size',
            'format_template': 'Template for filename formatting - use {show_name}, {season}, {episode}, etc.'
        }
    
    def create_widgets(self):
        """Create widgets for this entire section"""
        # Create collapsible section
        section_frame = ttk.LabelFrame(self.parent_frame, text=f"📁 {self.name.replace('_', ' ').title()}")
        section_frame.pack(fill='x', padx=5, pady=5)
        
        # Add widgets for each setting in this section
        self._create_section_content(section_frame, self.data, "")
    
    def _create_section_content(self, parent: ttk.Frame, data: dict, path_prefix: str):
        """Recursively create widgets for nested configuration"""
        for key, value in data.items():
            if key.startswith('_'):
                continue  # Skip metadata like _docs
                
            full_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if isinstance(value, dict):
                # Create subsection
                subsection_frame = ttk.LabelFrame(parent, text=key.replace('_', ' ').title())
                subsection_frame.pack(fill='x', padx=10, pady=3)
                self._create_section_content(subsection_frame, value, full_path)
            else:
                # Create input widget for this setting
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
        
        # Add tooltip if we have a description
        description = self.setting_descriptions.get(key, f"Setting: {self.name}.{key}")
        ToolTip(label, description)
        
        # Determine if this setting needs a browse button
        needs_browse, browse_type = self._needs_browse_button(key, full_path, value)
        
        # Create appropriate input widget
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
                # Create frame for entry + browse button for lists
                entry_frame = ttk.Frame(row_frame)
                entry_frame.pack(side='left', padx=5, fill='x', expand=True)
                
                widget = ttk.Entry(entry_frame, textvariable=var, width=40)
                widget.pack(side='left', fill='x', expand=True)
                
                # Add browse button for file lists
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
                # Create frame for entry + browse button
                entry_frame = ttk.Frame(row_frame)
                entry_frame.pack(side='left', padx=5, fill='x', expand=True)
                
                widget = ttk.Entry(entry_frame, textvariable=var, width=35)
                widget.pack(side='left', fill='x', expand=True)
                
                # Add appropriate browse button
                if browse_type == 'file':
                    browse_btn = ttk.Button(entry_frame, text="📁 Browse", width=10,
                                          command=lambda: self._browse_for_file(var, key))
                    tooltip_text = f"Browse for {key} file"
                elif browse_type == 'directory':
                    browse_btn = ttk.Button(entry_frame, text="📂 Browse", width=10,
                                          command=lambda: self._browse_for_directory(var, key))
                    tooltip_text = f"Browse for {key} directory"
                else:
                    browse_btn = ttk.Button(entry_frame, text="📁 Browse", width=10,
                                          command=lambda: self._browse_for_file(var, key))
                    tooltip_text = f"Browse for {key}"
                
                browse_btn.pack(side='right', padx=(2, 0))
                ToolTip(browse_btn, tooltip_text)
                
                # Add path validation
                self._add_path_validation(widget, var, browse_type)
                
            else:
                widget = ttk.Entry(row_frame, textvariable=var, width=40)
                widget.pack(side='left', padx=5)
        
        # Add tooltip to the input widget
        ToolTip(widget, description)
        
        # Store widget reference
        self.widgets[full_path] = var
        
        # Add validation indicator
        status_label = ttk.Label(row_frame, text="✓", foreground="green", width=2)
        status_label.pack(side='right', padx=2)
        self.widgets[f"{full_path}_status"] = status_label
    
    def _needs_browse_button(self, key: str, full_path: str, value) -> tuple:
        """Determine if a setting needs a browse button and what type"""
        key_lower = key.lower()
        path_lower = full_path.lower()
        
        # File path indicators
        if any(indicator in key_lower for indicator in ['executable', 'ffmpeg', 'ffprobe', '_path']) and 'directory' not in key_lower:
            return True, 'file'
        
        if any(indicator in path_lower for indicator in ['executable_paths', 'ffmpeg']):
            return True, 'file_list'
        
        # Directory path indicators  
        if any(indicator in key_lower for indicator in ['directory', 'folder', 'temp_path', 'backup_path']):
            return True, 'directory'
        
        # Check if it's a list of paths
        if isinstance(value, list) and len(value) > 0:
            sample_value = str(value[0]) if value else ""
            if any(ext in sample_value.lower() for ext in ['.exe', '.app', 'ffmpeg', 'ffprobe', '\\', '/']):
                return True, 'file_list'
        
        return False, None
    
    def _browse_for_file(self, var: tk.StringVar, key: str):
        """Open file dialog and update variable"""
        key_lower = key.lower()
        
        if 'ffmpeg' in key_lower or 'executable' in key_lower:
            if os.name == 'nt':  # Windows
                filetypes = [("Executable files", "*.exe"), ("All files", "*.*")]
            else:
                filetypes = [("All files", "*")]
            title = f"Select {key.replace('_', ' ').title()}"
        else:
            filetypes = [("All files", "*.*")]
            title = f"Select {key.replace('_', ' ').title()}"
        
        # Get current value as starting directory
        current_path = var.get().strip()
        initial_dir = None
        if current_path and os.path.exists(current_path):
            initial_dir = os.path.dirname(current_path)
        
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir
        )
        
        if filename:
            var.set(filename)
    
    def _browse_for_directory(self, var: tk.StringVar, key: str):
        """Open directory dialog and update variable"""
        title = f"Select {key.replace('_', ' ').title()}"
        
        current_path = var.get().strip()
        initial_dir = None
        if current_path and os.path.exists(current_path):
            initial_dir = current_path
        
        directory = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir
        )
        
        if directory:
            var.set(directory)
    
    def _browse_for_file_list(self, var: tk.StringVar, key: str):
        """Browse for file and add to comma-separated list"""
        key_lower = key.lower()
        
        if 'ffmpeg' in key_lower or 'executable' in key_lower:
            if os.name == 'nt':
                filetypes = [("Executable files", "*.exe"), ("All files", "*.*")]
            else:
                filetypes = [("All files", "*")]
            title = f"Add {key.replace('_', ' ').title()}"
        else:
            filetypes = [("All files", "*.*")]
            title = f"Add to {key.replace('_', ' ').title()}"
        
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        
        if filename:
            current_list = var.get().strip()
            if current_list:
                new_list = current_list + ", " + filename
            else:
                new_list = filename
            var.set(new_list)
    
    def _add_path_validation(self, entry_widget, var: tk.StringVar, browse_type: str):
        """Add real-time path validation to entry widget"""
        def validate_on_change(*args):
            path = var.get().strip()
            if path:
                is_valid = self._validate_path(path, browse_type)
                if is_valid:
                    entry_widget.config(background='white')
                else:
                    entry_widget.config(background='#ffe6e6')  # Light red
            else:
                entry_widget.config(background='white')
        
        var.trace('w', validate_on_change)
    
    def _validate_path(self, path: str, path_type: str) -> bool:
        """Validate if path exists and is correct type"""
        if not path.strip():
            return True  # Empty is valid
        
        try:
            path_obj = Path(path)
            if path_type == 'file':
                return path_obj.exists() and path_obj.is_file()
            elif path_type == 'directory':
                return path_obj.exists() and path_obj.is_dir()
            else:
                return path_obj.exists()
        except:
            return False
    
    def get_data(self) -> dict:
        """Get the current data from widgets"""
        result = {}
        
        for path, var in self.widgets.items():
            if path.endswith('_status'):
                continue
                
            value = var.get()
            
            # Convert value back to appropriate type
            if ',' in value and not os.path.exists(value):
                # List value (comma-separated)
                value = [item.strip() for item in value.split(',') if item.strip()]
            elif value.lower() in ['true', 'false']:
                # Boolean value
                value = value.lower() == 'true'
            else:
                # Try to convert to number
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # Keep as string
            
            # Set nested value
            self._set_nested_value(result, path.split('.'), value)
        
        return result
    
    def _set_nested_value(self, data: dict, path_parts: list, value):
        """Set a nested value in the data structure"""
        current = data
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = value

class CompleteConfigGUI:
    """Complete configuration GUI showing all settings with browse support"""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Universal Video Cleaner - Complete Configuration Editor")
        self.window.geometry("1000x700")
        
        self.config_file = Path("master_config.json")
        self.config_data = {}
        self.sections = {}
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup the main UI components"""
        # Menu bar
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Config...", command=self.open_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_command(label="Save As...", command=self.save_config_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.quit)
        
        # Toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="💾 Save", command=self.save_config).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔄 Reload", command=self.load_config).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔍 Auto-Detect FFmpeg", command=self.auto_detect_ffmpeg).pack(side='left', padx=2)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')
        
        # Main content area with scrolling
        self.setup_scrollable_content()
    
    def setup_scrollable_content(self):
        """Setup scrollable content area"""
        canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
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
        """Create GUI sections for each configuration section"""
        # Clear existing sections
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.sections.clear()
        
        # Create sections for each top-level config item
        for section_name, section_data in self.config_data.items():
            if section_name.startswith('_'):
                continue  # Skip metadata
                
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
        """Automatically detect FFmpeg installations"""
        self.status_var.set("Searching for FFmpeg installations...")
        
        detected_paths = []
        
        # Common paths to check
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
            # Find the FFmpeg paths widget and update it
            for section_name, section in self.sections.items():
                if 'executable_paths' in section.widgets:
                    # Update the executable paths
                    current_paths = section.widgets['executable_paths'].get()
                    all_paths = current_paths.split(', ') if current_paths else []
                    
                    for path in detected_paths:
                        if path not in all_paths:
                            all_paths.append(path)
                    
                    section.widgets['executable_paths'].set(', '.join(all_paths))
                    break
            
            self.status_var.set(f"Auto-detected {len(detected_paths)} FFmpeg paths")
            messagebox.showinfo("Auto-Detection Complete", 
                              f"Found FFmpeg installations:\n\n" + "\n".join(detected_paths) +
                              f"\n\nAdded to configuration. Click Save to keep changes.")
        else:
            self.status_var.set("No FFmpeg installations found")
            messagebox.showinfo("Auto-Detection Complete", 
                              "No FFmpeg installations found in common locations.")
    
    def open_config(self):
        """Open a different configuration file"""
        filename = filedialog.askopenfilename(
            title="Open Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = Path(filename)
            self.load_config()
    
    def save_config_as(self):
        """Save configuration to a new file"""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            old_file = self.config_file
            self.config_file = Path(filename)
            self.save_config()
            self.config_file = old_file
    
    def run(self):
        """Start the application"""
        self.window.mainloop()

def main():
    """Run the complete config GUI"""
    app = CompleteConfigGUI()
    app.run()

if __name__ == "__main__":
    main()