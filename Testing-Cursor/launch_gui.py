import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import sys
import os
import requests
import json
import webbrowser
from datetime import datetime
import concurrent.futures
import threading

class ContextExporterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Context Exporter GUI")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # Center the window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"900x700+{x}+{y}")

        # Bring window to front and focus
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.root.after(500, lambda: self.root.attributes('-topmost', False))

        # Load environment variables
        self.load_environment()
        
        # Progress tracking variables
        self.progress_total = 0
        self.progress_done = 0
        self.progress_lock = threading.Lock()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create tabs
        self.create_export_tab()
        self.create_search_tab()

    def load_environment(self):
        """Load environment variables for API access"""
        from dotenv import load_dotenv
        load_dotenv()
        
        self.confluence_url = os.getenv('CONFLUENCE_URL')
        self.jira_url = os.getenv('JIRA_URL')
        self.username = os.getenv('ATLASSIAN_USERNAME')
        self.api_token = os.getenv('ATLASSIAN_API_TOKEN')
        
        # Create session for API calls
        self.session = requests.Session()
        if self.username and self.api_token:
            self.session.auth = (self.username, self.api_token)
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })

    def create_export_tab(self):
        """Create the Export tab"""
        export_frame = ttk.Frame(self.notebook)
        self.notebook.add(export_frame, text="Export")

        # Create a frame to center widgets
        frame = tk.Frame(export_frame, bg="#f0f0f0")
        frame.pack(expand=True)

        label_widget = tk.Label(frame, text="Enter label to export:", font=("Arial", 12), bg="#f0f0f0")
        label_widget.pack(pady=(10, 5))

        self.entry = tk.Entry(frame, width=35, font=("Arial", 11), bg="white")
        self.entry.pack(pady=5)

        # Add checkboxes for export options
        checkbox_frame = tk.Frame(frame, bg="#f0f0f0")
        checkbox_frame.pack(pady=10)

        # Include Jira checkbox
        self.include_jira_var = tk.BooleanVar(value=True)  # Default to checked
        jira_checkbox = tk.Checkbutton(
            checkbox_frame, 
            text="Include Jira", 
            variable=self.include_jira_var,
            font=("Arial", 11),
            bg="#f0f0f0",
            selectcolor="white"
        )
        jira_checkbox.pack(anchor='w', pady=2)

        # Include Confluence checkbox
        self.include_confluence_var = tk.BooleanVar(value=True)  # Default to checked
        confluence_checkbox = tk.Checkbutton(
            checkbox_frame, 
            text="Include Confluence", 
            variable=self.include_confluence_var,
            font=("Arial", 11),
            bg="#f0f0f0",
            selectcolor="white"
        )
        confluence_checkbox.pack(anchor='w', pady=2)

        # Add checkbox for summary exports
        self.summary_var = tk.BooleanVar()
        summary_checkbox = tk.Checkbutton(
            frame, 
            text="Include summary exports", 
            variable=self.summary_var,
            font=("Arial", 11),
            bg="#f0f0f0",
            selectcolor="white"
        )
        summary_checkbox.pack(pady=10)

        # Button frame for Run Export and Run Tests
        button_frame = tk.Frame(frame, bg="#f0f0f0")
        button_frame.pack(pady=15)

        export_button = tk.Button(button_frame, text="Run Export", command=self.run_export, font=("Arial", 11))
        export_button.pack(pady=5)

        test_button = tk.Button(button_frame, text="Run Tests", command=self.run_tests, font=("Arial", 11))
        test_button.pack(pady=5)

        # Add confirmation label
        self.confirmation_label = tk.Label(frame, text="", font=("Arial", 10), bg="#f0f0f0", wraplength=350)
        self.confirmation_label.pack(pady=5)

    def create_search_tab(self):
        """Create the Search tab"""
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Search")

        # Main container
        main_container = tk.Frame(search_frame, bg="#f0f0f0")
        main_container.pack(expand=True, fill='both', padx=10, pady=10)

        # Search input section
        search_input_frame = tk.Frame(main_container, bg="#f0f0f0")
        search_input_frame.pack(fill='x', pady=(0, 10))

        # Search phrase row
        search_row = tk.Frame(search_input_frame, bg="#f0f0f0")
        search_row.pack(fill='x', pady=5)

        # Left side - Search phrase
        search_label = tk.Label(search_row, text="Enter search phrase:", font=("Arial", 12), bg="#f0f0f0")
        search_label.pack(side='left')

        self.search_entry = tk.Entry(search_row, width=40, font=("Arial", 11), bg="white")
        self.search_entry.pack(side='left', padx=(10, 20), fill='x', expand=True)

        # Right side - Exclude labels
        exclude_label = tk.Label(search_row, text="Exclude labels:", font=("Arial", 12), bg="#f0f0f0")
        exclude_label.pack(side='right')

        self.exclude_entry = tk.Entry(search_row, width=25, font=("Arial", 11), bg="white")
        self.exclude_entry.pack(side='right', padx=(10, 0))

        # Exclude Jira projects row
        exclude_projects_row = tk.Frame(search_input_frame, bg="#f0f0f0")
        exclude_projects_row.pack(fill='x', pady=5)

        exclude_projects_label = tk.Label(exclude_projects_row, text="Exclude Jira projects (comma-separated):", font=("Arial", 12), bg="#f0f0f0")
        exclude_projects_label.pack(side='left')

        self.exclude_projects_entry = tk.Entry(exclude_projects_row, width=40, font=("Arial", 11), bg="white")
        self.exclude_projects_entry.pack(side='left', padx=(10, 0), fill='x', expand=True)

        search_button = tk.Button(search_input_frame, text="Search Jira & Confluence", command=self.run_search, font=("Arial", 11))
        search_button.pack(pady=5)

        # Status label for search progress
        self.status_label = tk.Label(search_input_frame, text="", font=("Arial", 10), bg="#f0f0f0", fg="blue")
        self.status_label.pack(pady=5)

        # Results section with scrollable frame
        results_frame = tk.Frame(main_container, bg="#f0f0f0")
        results_frame.pack(expand=True, fill='both')

        results_label = tk.Label(results_frame, text="Search Results:", font=("Arial", 12), bg="#f0f0f0")
        results_label.pack(anchor='w')

        # Create canvas and scrollbar for results
        self.canvas = tk.Canvas(results_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Label application section
        label_frame = tk.Frame(main_container, bg="#f0f0f0")
        label_frame.pack(fill='x', pady=(10, 0))

        label_input_label = tk.Label(label_frame, text="Apply label to all results:", font=("Arial", 12), bg="#f0f0f0")
        label_input_label.pack(anchor='w')

        label_input_container = tk.Frame(label_frame, bg="#f0f0f0")
        label_input_container.pack(fill='x', pady=5)

        self.label_entry = tk.Entry(label_input_container, width=30, font=("Arial", 11), bg="white")
        self.label_entry.pack(side='left', padx=(0, 10))

        apply_label_button = tk.Button(label_input_container, text="Apply label to all results", command=self.apply_label_to_results, font=("Arial", 11))
        apply_label_button.pack(side='left')

        # Progress bar for labeling
        progress_frame = tk.Frame(label_frame, bg="#f0f0f0")
        progress_frame.pack(fill='x', pady=(10, 0))
        
        self.progress_label = tk.Label(progress_frame, text="", font=("Arial", 10), bg="#f0f0f0", fg="blue")
        self.progress_label.pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill='x', pady=(5, 0))

        # Store search results
        self.search_results = {'jira': [], 'confluence': []}
        
        # Store section states
        self.jira_expanded = False
        self.confluence_expanded = False

    def log_message(self, message, color="black"):
        """Log a message to the results area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Add to the scrollable frame
        log_label = tk.Label(self.scrollable_frame, text=log_entry, 
                           font=("Arial", 9), bg="white", fg=color, anchor='w', justify='left')
        log_label.pack(fill='x', padx=5, pady=2)
        
        # Scroll to bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
        
        # Update GUI
        self.root.update_idletasks()

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_mousewheel(self, event):
        """Bind mouse wheel when entering canvas"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """Unbind mouse wheel when leaving canvas"""
        self.canvas.unbind_all("<MouseWheel>")

    def run_export(self):
        """Run the export process"""
        label = self.entry.get().strip()
        if not label:
            return  # Do nothing if input is blank
        
        # Clear any previous confirmation message
        self.confirmation_label.config(text="")
        
        # Check if at least one export type is selected
        include_jira = self.include_jira_var.get()
        include_confluence = self.include_confluence_var.get()
        
        if not include_jira and not include_confluence:
            self.confirmation_label.config(text="Please select at least one export type (Jira or Confluence).", fg="red")
            return
        
        # Build command with options
        cmd = [sys.executable, "context_exporter.py", "--label", label]
        
        # Add export type flags
        if include_jira:
            cmd.append("--include-jira")
        if include_confluence:
            cmd.append("--include-confluence")
        if self.summary_var.get():
            cmd.append("--include-summary")
        
        try:
            # Update confirmation label to show what's being exported
            export_types = []
            if include_jira:
                export_types.append("Jira")
            if include_confluence:
                export_types.append("Confluence")
            
            self.confirmation_label.config(text=f"Starting export for label '{label}' ({', '.join(export_types)})...", fg="blue")
            self.root.update_idletasks()
            
            # Run the export command and capture output
            result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)), 
                                  capture_output=True, text=True)
            
            # Display the output in the confirmation label
            if result.returncode == 0:
                # Show last few lines of output
                output_lines = result.stdout.strip().split('\n')
                if len(output_lines) > 10:
                    # Show last 10 lines
                    display_output = '\n'.join(output_lines[-10:])
                else:
                    display_output = result.stdout.strip()
                
                self.confirmation_label.config(text=f"Export completed successfully!\n\n{display_output}", fg="green")
            else:
                self.confirmation_label.config(text=f"Export failed:\n{result.stderr}", fg="red")
                
        except Exception as e:
            self.confirmation_label.config(text=f"Export failed: {e}", fg="red")

    def run_tests(self):
        """Run tests to check connectivity and count available content"""
        label = self.entry.get().strip()
        if not label:
            self.confirmation_label.config(text="Please enter a label to test.", fg="red")
            return
        
        # Clear any previous confirmation message
        self.confirmation_label.config(text="")
        
        # Check if at least one export type is selected
        include_jira = self.include_jira_var.get()
        include_confluence = self.include_confluence_var.get()
        
        if not include_jira and not include_confluence:
            self.confirmation_label.config(text="Please select at least one export type (Jira or Confluence) to test.", fg="red")
            return
        
        # Build command with options
        cmd = [sys.executable, "context_exporter.py", "--label", label, "--dry-run"]
        
        # Add export type flags
        if include_jira:
            cmd.append("--include-jira")
        if include_confluence:
            cmd.append("--include-confluence")
        if self.summary_var.get():
            cmd.append("--include-summary")
        
        try:
            # Update confirmation label to show what's being tested
            test_types = []
            if include_jira:
                test_types.append("Jira")
            if include_confluence:
                test_types.append("Confluence")
            
            self.confirmation_label.config(text=f"Running tests for label '{label}' ({', '.join(test_types)})...", fg="blue")
            self.root.update_idletasks()
            
            # Run the test command and capture output
            result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)), 
                                  capture_output=True, text=True)
            
            # Display the output in the confirmation label
            if result.returncode == 0:
                # Show last few lines of output
                output_lines = result.stdout.strip().split('\n')
                if len(output_lines) > 10:
                    # Show last 10 lines
                    display_output = '\n'.join(output_lines[-10:])
                else:
                    display_output = result.stdout.strip()
                
                self.confirmation_label.config(text=f"Tests completed successfully!\n\n{display_output}", fg="green")
            else:
                self.confirmation_label.config(text=f"Tests failed:\n{result.stderr}", fg="red")
                
        except Exception as e:
            self.confirmation_label.config(text=f"Tests failed: {e}", fg="red")

    def run_search(self):
        """Run search across Jira and Confluence"""
        phrase = self.search_entry.get().strip()
        if not phrase:
            self.status_label.config(text="Please enter a search phrase.", fg="red")
            return

        # Get exclude labels
        exclude_labels_text = self.exclude_entry.get().strip()
        exclude_labels = []
        if exclude_labels_text:
            exclude_labels = [label.strip().lower() for label in exclude_labels_text.split(",") if label.strip()]

        # Get exclude projects
        exclude_projects_text = self.exclude_projects_entry.get().strip()
        exclude_projects = []
        if exclude_projects_text:
            exclude_projects = [project.strip().upper() for project in exclude_projects_text.split(",") if project.strip()]

        # Clear previous results
        self.clear_results_display()
        self.search_results = {'jira': [], 'confluence': []}

        self.status_label.config(text=f"🔍 Searching for: '{phrase}'", fg="blue")
        if exclude_labels:
            self.status_label.config(text=f"🔍 Searching for: '{phrase}' (excluding labels: {', '.join(exclude_labels)})", fg="blue")
        if exclude_projects:
            self.status_label.config(text=f"🔍 Searching for: '{phrase}' (excluding projects: {', '.join(exclude_projects)})", fg="blue")

        # Search Jira
        self.search_jira(phrase, exclude_labels, exclude_projects)

        # Search Confluence
        self.search_confluence(phrase, exclude_labels)

        # Display results
        self.display_search_results()

    def search_jira(self, phrase, exclude_labels, exclude_projects):
        """Search Jira using JQL with full pagination and filtering"""
        if not self.jira_url:
            self.status_label.config(text="⚠️  Jira URL not configured. Skipping Jira search.", fg="orange")
            return

        try:
            self.status_label.config(text="🔍 Searching Jira...", fg="blue")
            search_url = f"{self.jira_url}/rest/api/2/search"
            
            # Use exact phrase search with JQL
            jql = f'text ~ "\\"{phrase}\\""'
            
            # Pagination parameters
            batch_size = 100  # Jira API max per request
            start_at = 0
            total_issues = 0
            filtered_issues = 0
            excluded_by_project = 0
            excluded_by_label = 0
            all_issues = []
            
            while True:
                payload = {
                    'jql': jql,
                    'maxResults': batch_size,
                    'startAt': start_at,
                    'fields': ['summary', 'project', 'status', 'assignee', 'description', 'labels']
                }
                
                response = self.session.post(search_url, json=payload)
                response.raise_for_status()
                
                results = response.json()
                batch = results.get('issues', [])
                
                if not batch:
                    break
                
                all_issues.extend(batch)
                total_issues += len(batch)
                
                # Update status
                self.status_label.config(text=f"🔍 Searching Jira... Found {total_issues} issues so far", fg="blue")
                
                # Check if we've got all results
                if len(batch) < batch_size:
                    break
                
                start_at += batch_size
                
                # Update the GUI to show progress
                self.root.update_idletasks()
            
            # Filter out issues with excluded labels or projects
            for issue in all_issues:
                issue_project_key = issue['fields']['project']['key']
                issue_labels = [label.lower() for label in issue['fields'].get('labels', [])]
                
                # Check if issue is from excluded project
                if issue_project_key in exclude_projects:
                    excluded_by_project += 1
                    continue
                
                # Check if issue has any excluded labels
                has_excluded_label = any(excluded in issue_labels for excluded in exclude_labels)
                if has_excluded_label:
                    excluded_by_label += 1
                    continue
                
                # Issue passed all filters
                issue_data = {
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                    'project': issue['fields']['project']['name'],
                    'project_key': issue_project_key,
                    'url': f"{self.jira_url}/browse/{issue['key']}",
                    'status': issue['fields']['status']['name'],
                    'labels': issue['fields'].get('labels', [])
                }
                self.search_results['jira'].append(issue_data)
                filtered_issues += 1
            
            # Log exclusion summary
            exclusion_summary = []
            if excluded_by_project > 0:
                exclusion_summary.append(f"{excluded_by_project} by project")
            if excluded_by_label > 0:
                exclusion_summary.append(f"{excluded_by_label} by label")
            
            if exclusion_summary:
                self.status_label.config(text=f"✅ Found {filtered_issues} Jira issues (excluded: {', '.join(exclusion_summary)})", fg="green")
            else:
                self.status_label.config(text=f"✅ Found {filtered_issues} Jira issues", fg="green")
                
        except Exception as e:
            self.status_label.config(text=f"❌ Error searching Jira: {e}", fg="red")

    def search_confluence(self, phrase, exclude_labels):
        """Search Confluence using CQL with full pagination and label filtering"""
        if not self.confluence_url:
            self.status_label.config(text="⚠️  Confluence URL not configured. Skipping Confluence search.", fg="orange")
            return

        try:
            self.status_label.config(text="🔍 Searching Confluence...", fg="blue")
            search_url = f"{self.confluence_url}/rest/api/content/search"
            
            # Use exact phrase search with CQL
            cql = f'text ~ "\\"{phrase}\\""'
            
            # Pagination parameters
            batch_size = 1000  # Confluence API max per request
            start = 0
            total_pages = 0
            filtered_pages = 0
            excluded_by_label = 0
            all_pages = []
            
            while True:
                params = {
                    'cql': cql,
                    'limit': batch_size,
                    'start': start,
                    'expand': 'space,version'
                }
                
                response = self.session.get(search_url, params=params)
                response.raise_for_status()
                
                results = response.json()
                batch = results.get('results', [])
                
                if not batch:
                    break
                
                all_pages.extend(batch)
                total_pages += len(batch)
                
                # Update status
                self.status_label.config(text=f"🔍 Searching Confluence... Found {total_pages} pages so far", fg="blue")
                
                # Check if we've got all results
                if len(batch) < batch_size:
                    break
                
                start += batch_size
                
                # Update the GUI to show progress
                self.root.update_idletasks()
            
            # Filter out pages with excluded labels
            for page in all_pages:
                # Get page labels
                page_labels = self.get_confluence_page_labels(page['id'])
                page_labels_lower = [label.lower() for label in page_labels]
                
                # Check if page has any excluded labels
                has_excluded_label = any(excluded in page_labels_lower for excluded in exclude_labels)
                if has_excluded_label:
                    excluded_by_label += 1
                    continue
                
                # Page passed all filters
                page_data = {
                    'id': page['id'],
                    'title': page['title'],
                    'space': page['space']['name'],
                    'space_key': page['space']['key'],
                    'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page['id']}",
                    'author': page.get('version', {}).get('by', {}).get('displayName', 'Unknown'),
                    'labels': page_labels
                }
                self.search_results['confluence'].append(page_data)
                filtered_pages += 1
            
            if excluded_by_label > 0:
                self.status_label.config(text=f"✅ Found {filtered_pages} Confluence pages (excluded {excluded_by_label} by label)", fg="green")
            else:
                self.status_label.config(text=f"✅ Found {filtered_pages} Confluence pages", fg="green")
                
        except Exception as e:
            self.status_label.config(text=f"❌ Error searching Confluence: {e}", fg="red")

    def get_confluence_page_labels(self, page_id):
        """Get labels for a Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}/label"
            response = self.session.get(url)
            response.raise_for_status()
            
            labels_data = response.json()
            return [label.get('name', '') for label in labels_data.get('results', [])]
            
        except Exception as e:
            # If we can't get labels, assume no labels (don't exclude)
            return []

    def clear_results_display(self):
        """Clear the results display"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def display_search_results(self):
        """Display search results in collapsible sections"""
        self.clear_results_display()
        
        total_results = len(self.search_results['jira']) + len(self.search_results['confluence'])
        self.status_label.config(text=f"📋 Displaying {total_results} results", fg="green")

        # Display Jira results section
        self.create_jira_section()

        # Display Confluence results section
        self.create_confluence_section()

        if not self.search_results['jira'] and not self.search_results['confluence']:
            no_results_label = tk.Label(self.scrollable_frame, text="❌ No results found for the search phrase.", 
                                      font=("Arial", 11), bg="white", fg="red")
            no_results_label.pack(pady=20)

    def create_jira_section(self):
        """Create collapsible Jira section"""
        if not self.search_results['jira']:
            return

        # Section header (clickable)
        jira_header = tk.Frame(self.scrollable_frame, bg="#e6f3ff", relief="solid", bd=1)
        jira_header.pack(fill='x', pady=(10, 0), padx=5)
        
        # Toggle button
        toggle_text = "▶️ Show Jira Issues" if not self.jira_expanded else "🔽 Hide Jira Issues"
        jira_toggle = tk.Button(jira_header, text=toggle_text, command=self.toggle_jira_section,
                               font=("Arial", 11, "bold"), bg="#e6f3ff", bd=0, cursor="hand2")
        jira_toggle.pack(side='left', padx=10, pady=5)
        
        # Count label
        count_label = tk.Label(jira_header, text=f"({len(self.search_results['jira'])} found)", 
                              font=("Arial", 11), bg="#e6f3ff", fg="gray")
        count_label.pack(side='left', padx=5, pady=5)

        # Content frame (initially hidden)
        self.jira_content_frame = tk.Frame(self.scrollable_frame, bg="white")
        if self.jira_expanded:
            self.jira_content_frame.pack(fill='x', padx=5)
            self.display_jira_results()

    def create_confluence_section(self):
        """Create collapsible Confluence section"""
        if not self.search_results['confluence']:
            return

        # Section header (clickable)
        confluence_header = tk.Frame(self.scrollable_frame, bg="#fff2e6", relief="solid", bd=1)
        confluence_header.pack(fill='x', pady=(10, 0), padx=5)
        
        # Toggle button
        toggle_text = "▶️ Show Confluence Pages" if not self.confluence_expanded else "🔽 Hide Confluence Pages"
        confluence_toggle = tk.Button(confluence_header, text=toggle_text, command=self.toggle_confluence_section,
                                     font=("Arial", 11, "bold"), bg="#fff2e6", bd=0, cursor="hand2")
        confluence_toggle.pack(side='left', padx=10, pady=5)
        
        # Count label
        count_label = tk.Label(confluence_header, text=f"({len(self.search_results['confluence'])} found)", 
                              font=("Arial", 11), bg="#fff2e6", fg="gray")
        count_label.pack(side='left', padx=5, pady=5)

        # Content frame (initially hidden)
        self.confluence_content_frame = tk.Frame(self.scrollable_frame, bg="white")
        if self.confluence_expanded:
            self.confluence_content_frame.pack(fill='x', padx=5)
            self.display_confluence_results()

    def toggle_jira_section(self):
        """Toggle Jira section visibility"""
        self.jira_expanded = not self.jira_expanded
        if self.jira_expanded:
            self.jira_content_frame.pack(fill='x', padx=5)
            self.display_jira_results()
        else:
            self.jira_content_frame.pack_forget()
        self.update_scroll_region()

    def toggle_confluence_section(self):
        """Toggle Confluence section visibility"""
        self.confluence_expanded = not self.confluence_expanded
        if self.confluence_expanded:
            self.confluence_content_frame.pack(fill='x', padx=5)
            self.display_confluence_results()
        else:
            self.confluence_content_frame.pack_forget()
        self.update_scroll_region()

    def display_jira_results(self):
        """Display Jira results in the content frame"""
        for widget in self.jira_content_frame.winfo_children():
            widget.destroy()
            
        for i, issue in enumerate(self.search_results['jira']):
            self.create_jira_result_row(issue, i, self.jira_content_frame)

    def display_confluence_results(self):
        """Display Confluence results in the content frame"""
        for widget in self.confluence_content_frame.winfo_children():
            widget.destroy()
            
        for i, page in enumerate(self.search_results['confluence']):
            self.create_confluence_result_row(page, i, self.confluence_content_frame)

    def update_scroll_region(self):
        """Update the scroll region after toggling sections"""
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_clickable_link(self, parent, url, text, font_size=9):
        """Create a clickable link label"""
        link_label = tk.Label(parent, text=text, font=("Arial", font_size), 
                             bg="white", fg="blue", cursor="hand2", underline=True)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(url))
        link_label.bind("<Enter>", lambda e: link_label.config(fg="darkblue"))
        link_label.bind("<Leave>", lambda e: link_label.config(fg="blue"))
        return link_label

    def create_jira_result_row(self, issue, index, parent_frame):
        """Create an interactive row for a Jira issue"""
        row_frame = tk.Frame(parent_frame, bg="white", relief="solid", bd=1)
        row_frame.pack(fill='x', pady=3, padx=2)

        # Remove button
        remove_btn = tk.Button(row_frame, text="❌", command=lambda: self.remove_jira_issue(issue['key']), 
                              font=("Arial", 10), bg="red", fg="white", width=3)
        remove_btn.pack(side='left', padx=8, pady=8)

        # Issue details
        details_frame = tk.Frame(row_frame, bg="white")
        details_frame.pack(side='left', fill='x', expand=True, padx=8, pady=8)

        # Issue key and summary
        title_label = tk.Label(details_frame, text=f"📋 {issue['key']}: {issue['summary']}", 
                              font=("Arial", 11, "bold"), bg="white", anchor='w')
        title_label.pack(anchor='w', pady=(0, 4))

        # Project and status
        info_label = tk.Label(details_frame, text=f"   Project: {issue['project']} ({issue['project_key']}) | Status: {issue['status']}", 
                             font=("Arial", 10), bg="white", fg="gray", anchor='w')
        info_label.pack(anchor='w', pady=(0, 4))

        # Labels (if any)
        if issue.get('labels'):
            labels_text = f"   Labels: {', '.join(issue['labels'])}"
            labels_label = tk.Label(details_frame, text=labels_text, 
                                  font=("Arial", 9), bg="white", fg="purple", anchor='w')
            labels_label.pack(anchor='w', pady=(0, 4))

        # Clickable URL
        url_text = f"   🔗 Open in Jira"
        url_label = self.create_clickable_link(details_frame, issue['url'], url_text, 9)
        url_label.pack(anchor='w')

    def create_confluence_result_row(self, page, index, parent_frame):
        """Create an interactive row for a Confluence page"""
        row_frame = tk.Frame(parent_frame, bg="white", relief="solid", bd=1)
        row_frame.pack(fill='x', pady=3, padx=2)

        # Remove button
        remove_btn = tk.Button(row_frame, text="❌", command=lambda: self.remove_confluence_page(page['id']), 
                              font=("Arial", 10), bg="red", fg="white", width=3)
        remove_btn.pack(side='left', padx=8, pady=8)

        # Page details
        details_frame = tk.Frame(row_frame, bg="white")
        details_frame.pack(side='left', fill='x', expand=True, padx=8, pady=8)

        # Page title
        title_label = tk.Label(details_frame, text=f"📄 {page['title']}", 
                              font=("Arial", 11, "bold"), bg="white", anchor='w')
        title_label.pack(anchor='w', pady=(0, 4))

        # Space and author
        info_label = tk.Label(details_frame, text=f"   Space: {page['space']} | Author: {page['author']}", 
                             font=("Arial", 10), bg="white", fg="gray", anchor='w')
        info_label.pack(anchor='w', pady=(0, 4))

        # Labels (if any)
        if page.get('labels'):
            labels_text = f"   Labels: {', '.join(page['labels'])}"
            labels_label = tk.Label(details_frame, text=labels_text, 
                                  font=("Arial", 9), bg="white", fg="purple", anchor='w')
            labels_label.pack(anchor='w', pady=(0, 4))

        # Clickable URL
        url_text = f"   🔗 Open in Confluence"
        url_label = self.create_clickable_link(details_frame, page['url'], url_text, 9)
        url_label.pack(anchor='w')

    def remove_jira_issue(self, issue_key):
        """Remove a Jira issue from the labeling list"""
        self.search_results['jira'] = [issue for issue in self.search_results['jira'] if issue['key'] != issue_key]
        self.status_label.config(text=f"🗑️  Removed {issue_key} from labeling list", fg="orange")
        self.refresh_results_display()

    def remove_confluence_page(self, page_id):
        """Remove a Confluence page from the labeling list"""
        # Find the page title for logging
        page_title = "Unknown"
        for page in self.search_results['confluence']:
            if page['id'] == page_id:
                page_title = page['title']
                break
        
        self.search_results['confluence'] = [page for page in self.search_results['confluence'] if page['id'] != page_id]
        self.status_label.config(text=f"🗑️  Removed page '{page_title}' from labeling list", fg="orange")
        self.refresh_results_display()

    def refresh_results_display(self):
        """Refresh the results display after removals"""
        self.display_search_results()

    def apply_label_to_results(self):
        """Apply label to all search results with parallel processing"""
        label = self.label_entry.get().strip()
        if not label:
            self.status_label.config(text="Please enter a label to apply.", fg="red")
            return

        if not self.search_results['jira'] and not self.search_results['confluence']:
            self.status_label.config(text="No search results to label. Please run a search first.", fg="red")
            return

        # Count total items to label
        total_jira = len(self.search_results['jira'])
        total_confluence = len(self.search_results['confluence'])
        self.progress_total = total_jira + total_confluence
        self.progress_done = 0

        self.status_label.config(text=f"🏷️  Applying label '{label}' to {self.progress_total} items...", fg="blue")
        self.log_message(f"🚀 Starting parallel label application for '{label}' to {self.progress_total} items", "blue")

        # Initialize progress bar
        self.progress_bar['maximum'] = self.progress_total
        self.progress_bar['value'] = 0
        self.progress_label.config(text=f"Progress: 0/{self.progress_total}")

        # Start parallel labeling in a separate thread to avoid blocking GUI
        threading.Thread(target=self._apply_labels_parallel, args=(label,), daemon=True).start()

    def _apply_labels_parallel(self, label):
        """Apply labels in parallel using ThreadPoolExecutor"""
        max_workers = min(10, self.progress_total)  # Limit to 10 workers max
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit Jira labeling tasks
            jira_futures = []
            for issue in self.search_results['jira']:
                future = executor.submit(self._label_jira_issue, issue, label)
                jira_futures.append(future)

            # Submit Confluence labeling tasks
            confluence_futures = []
            for page in self.search_results['confluence']:
                future = executor.submit(self._label_confluence_page, page, label)
                confluence_futures.append(future)

            # Process completed tasks in real-time
            all_futures = jira_futures + confluence_futures
            
            for future in concurrent.futures.as_completed(all_futures):
                try:
                    result = future.result()
                    if result:
                        self.log_message(f"✅ {result}", "green")
                    else:
                        self.log_message(f"⏭️  {result}", "orange")
                except Exception as e:
                    self.log_message(f"❌ {e}", "red")

        # Final status update
        self.root.after(0, lambda: self.status_label.config(text="✅ Parallel label application complete!", fg="green"))
        self.log_message("🎉 Parallel label application completed!", "green")

    def _label_jira_issue(self, issue, label):
        """Worker function to label a single Jira issue"""
        try:
            # Add notifyUsers=false parameter to suppress notifications
            url = f"{self.jira_url}/rest/api/2/issue/{issue['key']}?notifyUsers=false"
            
            # Get current labels
            response = self.session.get(url)
            response.raise_for_status()
            current_data = response.json()
            current_labels = current_data['fields'].get('labels', [])
            
            # Add new label if not already present
            if label.lower() not in [l.lower() for l in current_labels]:
                current_labels.append(label)
                
                # Update issue with new labels
                update_data = {
                    'fields': {
                        'labels': current_labels
                    }
                }
                
                response = self.session.put(url, json=update_data)
                response.raise_for_status()
                
                # Update progress
                with self.progress_lock:
                    self.progress_done += 1
                    progress_msg = f"Added label to {issue['key']} ({self.progress_done}/{self.progress_total})"
                    # Update progress bar in GUI thread
                    self.root.after(0, self._update_progress_bar)
                
                return progress_msg
            else:
                # Update progress
                with self.progress_lock:
                    self.progress_done += 1
                    progress_msg = f"Label already exists on {issue['key']} ({self.progress_done}/{self.progress_total})"
                    # Update progress bar in GUI thread
                    self.root.after(0, self._update_progress_bar)
                
                return progress_msg
                
        except Exception as e:
            # Update progress even on error
            with self.progress_lock:
                self.progress_done += 1
                # Update progress bar in GUI thread
                self.root.after(0, self._update_progress_bar)
            
            raise Exception(f"Error applying label to {issue['key']}: {e}")

    def _label_confluence_page(self, page, label):
        """Worker function to label a single Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page['id']}/label"
            
            # Check if label already exists
            response = self.session.get(url)
            response.raise_for_status()
            current_labels = response.json().get('results', [])
            
            # Check if label already exists (case-insensitive)
            label_exists = any(l.get('name', '').lower() == label.lower() for l in current_labels)
            
            if not label_exists:
                # Add new label
                label_data = {
                    'name': label
                }
                
                response = self.session.post(url, json=label_data)
                response.raise_for_status()
                
                # Update progress
                with self.progress_lock:
                    self.progress_done += 1
                    progress_msg = f"Added label to page: {page['title']} ({self.progress_done}/{self.progress_total})"
                    # Update progress bar in GUI thread
                    self.root.after(0, self._update_progress_bar)
                
                return progress_msg
            else:
                # Update progress
                with self.progress_lock:
                    self.progress_done += 1
                    progress_msg = f"Label already exists on page: {page['title']} ({self.progress_done}/{self.progress_total})"
                    # Update progress bar in GUI thread
                    self.root.after(0, self._update_progress_bar)
                
                return progress_msg
                
        except Exception as e:
            # Update progress even on error
            with self.progress_lock:
                self.progress_done += 1
                # Update progress bar in GUI thread
                self.root.after(0, self._update_progress_bar)
            
            raise Exception(f"Error applying label to page {page['title']}: {e}")

    def _update_progress_bar(self):
        """Update the progress bar and label"""
        self.progress_bar['value'] = self.progress_done
        self.progress_label.config(text=f"Progress: {self.progress_done}/{self.progress_total}")

    def run(self):
        """Start the GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ContextExporterGUI()
    app.run() 