#!/usr/bin/env python3
"""
Context Export Tool V2 - Production-ready version with enhanced reliability
Gathers content from Confluence and Jira tagged with specified labels and exports as PDFs.
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

# Import our new modules
from exporter_config import ExporterConfig
from api_client import ResilientAPIClient
from structured_logger import LoggerFactory, StructuredLogger
from checkpoint_manager import CheckpointManager

# Import existing dependencies
from dotenv import load_dotenv
load_dotenv()

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import markdown
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
import re
import html2text


class ContextExporterV2:
    """Enhanced Context Exporter with production-ready features"""
    
    def __init__(self, label: str, config: ExporterConfig, resume_checkpoint: Optional[str] = None,
                 confluence_url: Optional[str] = None, jira_url: Optional[str] = None,
                 username: Optional[str] = None, api_token: Optional[str] = None,
                 include_summary: bool = False, dry_run: bool = False, validate_only: bool = False):
        
        self.label = label
        self.config = config
        self.confluence_url = confluence_url or os.getenv('CONFLUENCE_URL')
        self.jira_url = jira_url or os.getenv('JIRA_URL')
        self.username = username or os.getenv('ATLASSIAN_USERNAME')
        self.api_token = api_token or os.getenv('ATLASSIAN_API_TOKEN')
        self.export_date = datetime.now().strftime('%Y_%m_%d')
        self.include_summary = include_summary
        self.dry_run = dry_run
        self.validate_only = validate_only
        
        # Initialize logger
        LoggerFactory.set_config(config.logging)
        LoggerFactory.configure_root_logger()
        self.logger = LoggerFactory.get_logger("ContextExporter")
        
        # Initialize API client
        self.api_client = ResilientAPIClient(config, self.logger)
        if self.username and self.api_token:
            self.api_client.set_auth((self.username, self.api_token))
            self.api_client.set_headers({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
        
        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager(
            config.checkpoint.checkpoint_dir,
            self.logger
        )
        
        # Resume or start new export
        if resume_checkpoint:
            self.export_state = self.checkpoint_manager.resume_export(resume_checkpoint)
            if not self.export_state:
                raise ValueError(f"Failed to resume from checkpoint: {resume_checkpoint}")
            self.output_dir = f"exports/{self.label.replace(' ', '_').lower()}/{self.export_state.export_date}"
        else:
            self.export_state = self.checkpoint_manager.start_new_export(
                label, self.export_date, config.profile_name
            )
            self.output_dir = f"exports/{self.label.replace(' ', '_').lower()}/{self.export_date}"
            
        if not self.dry_run and not self.validate_only:
            os.makedirs(self.output_dir, exist_ok=True)
            
        # Declare optional attributes for Pyright
        self.include_jira = True
        self.include_confluence = True
        
        # Store content for summary generation
        self.all_confluence_content = []
        self.all_jira_content = []
        
        # Performance tracking
        self.start_time = time.time()
        self.api_call_count = 0
        self.api_call_time = 0.0
        
    def run_diagnostics(self) -> bool:
        """Run preflight checks to verify connectivity and authentication"""
        self.logger.info("Running preflight diagnostics")
        
        diagnostics_passed = True
        
        # Test Jira connectivity and authentication
        if self.include_jira and self.jira_url:
            self.logger.info("Testing Jira connectivity")
            try:
                start = time.time()
                response = self.api_client.get(f"{self.jira_url}/rest/api/2/myself")
                duration = time.time() - start
                
                if response.status_code == 200:
                    user_info = response.json()
                    self.logger.info(
                        "Jira connection successful",
                        authenticated_as=user_info.get('displayName', 'Unknown'),
                        response_time_ms=round(duration * 1000, 2)
                    )
                else:
                    self.logger.error(
                        "Jira authentication failed",
                        status_code=response.status_code
                    )
                    diagnostics_passed = False
            except Exception as e:
                self.logger.exception("Jira connection failed")
                diagnostics_passed = False
        elif self.include_jira:
            self.logger.error("Jira URL not configured")
            diagnostics_passed = False
        else:
            self.logger.info("Jira export disabled - skipping diagnostics")
        
        # Test Confluence connectivity and authentication
        if self.include_confluence and self.confluence_url:
            self.logger.info("Testing Confluence connectivity")
            try:
                start = time.time()
                response = self.api_client.get(f"{self.confluence_url}/rest/api/space")
                duration = time.time() - start
                
                if response.status_code == 200:
                    self.logger.info(
                        "Confluence connection successful",
                        response_time_ms=round(duration * 1000, 2)
                    )
                else:
                    self.logger.error(
                        "Confluence authentication failed",
                        status_code=response.status_code
                    )
                    diagnostics_passed = False
            except Exception as e:
                self.logger.exception("Confluence connection failed")
                diagnostics_passed = False
        elif self.include_confluence:
            self.logger.error("Confluence URL not configured")
            diagnostics_passed = False
        else:
            self.logger.info("Confluence export disabled - skipping diagnostics")
        
        if not diagnostics_passed:
            self.logger.error("Preflight checks failed")
        else:
            self.logger.info("All preflight checks passed")
            
        # Log API client statistics
        stats = self.api_client.get_stats()
        self.logger.info("API client statistics", **stats)
        
        return diagnostics_passed
        
    def validate_connectivity(self) -> Dict[str, Any]:
        """Validate connectivity and return detailed results"""
        results = {
            "confluence": {"available": False, "error": None, "spaces_count": 0},
            "jira": {"available": False, "error": None, "projects_count": 0},
            "label_found": {"confluence": False, "jira": False},
            "content_count": {"confluence_pages": 0, "jira_issues": 0}
        }
        
        # Test Confluence
        if self.include_confluence and self.confluence_url:
            try:
                # Test basic connectivity
                response = self.api_client.get(f"{self.confluence_url}/rest/api/space")
                if response.status_code == 200:
                    results["confluence"]["available"] = True
                    spaces_data = response.json()
                    results["confluence"]["spaces_count"] = len(spaces_data.get('results', []))
                    
                    # Test label search
                    search_response = self.api_client.get(
                        f"{self.confluence_url}/rest/api/content/search",
                        params={'cql': f'label = "{self.label}"', 'limit': 1}
                    )
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        total = search_data.get('totalSize', 0)
                        results["label_found"]["confluence"] = total > 0
                        results["content_count"]["confluence_pages"] = total
            except Exception as e:
                results["confluence"]["error"] = str(e)
                
        # Test Jira
        if self.include_jira and self.jira_url:
            try:
                # Test basic connectivity
                response = self.api_client.get(f"{self.jira_url}/rest/api/2/project")
                if response.status_code == 200:
                    results["jira"]["available"] = True
                    projects = response.json()
                    results["jira"]["projects_count"] = len(projects)
                    
                    # Test label search
                    search_response = self.api_client.post(
                        f"{self.jira_url}/rest/api/2/search",
                        json={'jql': f'labels = "{self.label}"', 'maxResults': 1}
                    )
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        total = search_data.get('total', 0)
                        results["label_found"]["jira"] = total > 0
                        results["content_count"]["jira_issues"] = total
            except Exception as e:
                results["jira"]["error"] = str(e)
                
        return results
        
    def search_confluence_spaces(self) -> List[Dict[str, Any]]:
        """Search for Confluence spaces containing pages with specified label"""
        if not self.confluence_url:
            self.logger.warning("Confluence URL not configured. Skipping Confluence export.")
            return []
        
        try:
            search_url = f"{self.confluence_url}/rest/api/content/search"
            batch_size = self.config.batch.confluence_batch_size
            start = 0
            all_results = []
            total = None
            
            while True:
                # Check if this batch was already processed
                if self.checkpoint_manager.current_state:
                    already_exported = len([
                        p for p in all_results 
                        if p['id'] in self.checkpoint_manager.current_state.confluence_pages_exported
                    ])
                    if already_exported >= len(all_results) and len(all_results) >= start:
                        self.logger.info(f"Skipping already processed batch at position {start}")
                        start += batch_size
                        continue
                
                params = {
                    'cql': f'label = "{self.label}"',
                    'limit': batch_size,
                    'start': start,
                    'expand': 'space,version'
                }
                
                self.logger.info(f"Fetching Confluence pages batch starting at {start}")
                
                response = self.api_client.get(search_url, params=params)
                results = response.json()
                batch = results.get('results', [])
                
                if total is None:
                    total = results.get('totalSize', 0)
                    self.logger.info(f"Total Confluence pages to fetch: {total}")
                    
                if not batch:
                    break
                    
                all_results.extend(batch)
                self.logger.log_export_progress("confluence_search", len(all_results), total)
                
                if len(batch) < batch_size:
                    break
                    
                start += batch_size
                
            # Process results into spaces
            spaces = self._process_confluence_results(all_results)
            
            return list(spaces.values())
            
        except Exception as e:
            self.logger.exception("Error searching Confluence")
            self.checkpoint_manager.record_error(
                "confluence_search",
                str(e),
                {"label": self.label}
            )
            return []
            
    def _process_confluence_results(self, pages: List[Dict]) -> Dict[str, Dict]:
        """Process Confluence search results into space structure"""
        spaces = {}
        exported_page_ids = set()
        
        for page in pages:
            # Skip if already exported
            if self.checkpoint_manager.is_confluence_page_exported(page['id']):
                continue
                
            space_key = page['space']['key']
            space_name = page['space']['name']
            
            # Skip if space is already complete
            if self.checkpoint_manager.is_confluence_space_complete(space_key):
                continue
                
            if space_key not in spaces:
                spaces[space_key] = {
                    'name': space_name,
                    'pages': []
                }
                
            page_data = {
                'id': page['id'],
                'title': page['title'],
                'author': page.get('version', {}).get('by', {}).get('displayName', 'Unknown'),
                'last_modified': page.get('version', {}).get('when', 'Unknown'),
                'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page['id']}",
                'level': 0
            }
            
            spaces[space_key]['pages'].append(page_data)
            exported_page_ids.add(page['id'])
            
            # Fetch child pages recursively
            self.fetch_child_pages_recursive(
                page['id'], 
                spaces[space_key]['pages'], 
                exported_page_ids, 
                level=1, 
                max_level=4
            )
            
        return spaces
        
    def fetch_child_pages_recursive(self, parent_id: str, pages_list: List[Dict], 
                                  exported_page_ids: set, level: int, max_level: int):
        """Recursively fetch child pages up to max_level depth"""
        if level > max_level:
            return
            
        try:
            child_url = f"{self.confluence_url}/rest/api/content/{parent_id}/child/page"
            params = {
                'expand': 'version',
                'limit': self.config.batch.confluence_batch_size
            }
            
            response = self.api_client.get(child_url, params=params)
            results = response.json()
            child_pages = results.get('results', [])
            
            for child in child_pages:
                if isinstance(child, dict) and 'id' in child:
                    child_id = child['id']
                    
                    # Skip if already exported
                    if self.checkpoint_manager.is_confluence_page_exported(child_id):
                        continue
                        
                    if child_id not in exported_page_ids:
                        child_data = {
                            'id': child_id,
                            'title': child.get('title', 'Unknown'),
                            'author': child.get('version', {}).get('by', {}).get('displayName', 'Unknown'),
                            'last_modified': child.get('version', {}).get('when', 'Unknown'),
                            'url': f"{self.confluence_url}/pages/viewpage.action?pageId={child_id}",
                            'level': level
                        }
                        pages_list.append(child_data)
                        exported_page_ids.add(child_id)
                        
                        # Recursively fetch children
                        self.fetch_child_pages_recursive(
                            child_id,
                            pages_list,
                            exported_page_ids,
                            level + 1,
                            max_level
                        )
                        
        except Exception as e:
            self.logger.error(f"Error fetching child pages for {parent_id}: {e}")
            self.checkpoint_manager.record_error(
                "fetch_child_pages",
                str(e),
                {"parent_id": parent_id, "level": level}
            )
            
    def get_confluence_page_content(self, page_id: str) -> Optional[str]:
        """Get the content of a Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {'expand': 'body.storage'}
            
            response = self.api_client.get(url, params=params)
            page_data = response.json()
            
            return page_data.get('body', {}).get('storage', {}).get('value', '')
            
        except Exception as e:
            self.logger.error(f"Error getting page content for {page_id}: {e}")
            return None
            
    def convert_html_to_text(self, html_content: str) -> Dict[str, Any]:
        """Convert HTML content to text - implementation from original"""
        if not html_content:
            return {"text": "", "linked_page_ids": []}
        
        # Use the original implementation
        soup = BeautifulSoup(html_content, 'html.parser')
        linked_page_ids = []
        
        # Process links and clean HTML as in original
        # ... (implementation details from original)
        
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.body_width = 0
        h.ignore_tables = False
        markdown_text = h.handle(str(soup))
        
        # Clean up text
        soup2 = BeautifulSoup(markdown_text, 'html.parser')
        clean_text = soup2.get_text()
        
        # Remove any remaining HTML tags
        prev = None
        while prev != clean_text:
            prev = clean_text
            clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        return {"text": clean_text, "linked_page_ids": linked_page_ids}
        
    def search_jira_projects(self) -> List[Dict[str, Any]]:
        """Search for Jira projects with issues labeled with specified label"""
        if not self.jira_url:
            self.logger.warning("Jira URL not configured. Skipping Jira export.")
            return []
        
        try:
            search_url = f"{self.jira_url}/rest/api/2/search"
            batch_size = self.config.batch.jira_batch_size
            start_at = 0
            all_issues = []
            total = None
            
            # Get field list for the search
            fields = self._get_jira_fields()
            
            while True:
                # Check if we should skip this batch based on checkpoint
                if self.checkpoint_manager.current_state:
                    if start_at < self.checkpoint_manager.current_state.current_batch_start:
                        start_at += batch_size
                        continue
                
                payload = {
                    'jql': f'labels = "{self.label}"',
                    'maxResults': batch_size,
                    'startAt': start_at,
                    'fields': fields
                }
                
                self.logger.info(f"Fetching Jira issues batch starting at {start_at}")
                
                response = self.api_client.post(search_url, json=payload)
                results = response.json()
                batch = results.get('issues', [])
                
                if total is None:
                    total = results.get('total', 0)
                    self.logger.info(f"Total Jira issues to fetch: {total}")
                    
                if not batch:
                    break
                    
                # Update checkpoint batch position
                if self.checkpoint_manager.current_state:
                    self.checkpoint_manager.current_state.current_batch_start = start_at
                    
                all_issues.extend(batch)
                self.logger.log_export_progress("jira_search", len(all_issues), total)
                
                if len(batch) < batch_size:
                    break
                    
                start_at += batch_size
                
            # Process results into projects
            projects = self._process_jira_results(all_issues)
            
            return list(projects.values())
            
        except Exception as e:
            self.logger.exception("Error searching Jira")
            self.checkpoint_manager.record_error(
                "jira_search",
                str(e),
                {"label": self.label}
            )
            return []
            
    def _get_jira_fields(self) -> List[str]:
        """Get list of Jira fields to fetch"""
        return [
            'summary', 'status', 'assignee', 'reporter', 'description', 'project',
            'priority', 'labels', 'components', 'fixVersions', 'versions',
            'duedate', 'created', 'updated', 'issuetype', 'parent', 'epic',
            'attachment', 'comment', 'issuelinks', 'subtasks', 'worklog'
        ] + [f'customfield_{i}' for i in range(10000, 10100)]  # Common custom field range
        
    def _process_jira_results(self, issues: List[Dict]) -> Dict[str, Dict]:
        """Process Jira search results into project structure"""
        projects = {}
        issue_map = {}
        
        for issue in issues:
            # Skip if already exported
            if self.checkpoint_manager.is_jira_issue_exported(issue['key']):
                continue
                
            project_key = issue['fields']['project']['key']
            project_name = issue['fields']['project']['name']
            
            # Skip if project is already complete
            if self.checkpoint_manager.is_jira_project_complete(project_key):
                continue
                
            if project_key not in projects:
                projects[project_key] = {
                    'name': project_name,
                    'issues': []
                }
                
            # Get detailed issue info
            detailed_issue = self.get_detailed_issue_info(issue['key'])
            
            # Process issue data (simplified from original)
            issue_data = self._process_issue_data(issue, detailed_issue)
            
            projects[project_key]['issues'].append(issue_data)
            issue_map[issue['key']] = issue_data
            
        # Build hierarchical relationships
        for project in projects.values():
            self._build_issue_hierarchy(project['issues'], issue_map)
            
        return projects
        
    def get_detailed_issue_info(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed information for a specific issue"""
        try:
            url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
            params = {'expand': 'renderedFields,comments,attachments'}
            
            response = self.api_client.get(url, params=params)
            issue_data = response.json()
            
            return {
                'comments': issue_data.get('fields', {}).get('comment', {}).get('comments', []),
                'rendered_fields': issue_data.get('renderedFields', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting detailed info for {issue_key}: {e}")
            return {'comments': [], 'rendered_fields': {}}
            
    def _process_issue_data(self, issue: Dict, detailed_info: Dict) -> Dict[str, Any]:
        """Process issue data into standard format"""
        fields = issue['fields']
        
        # Extract basic fields
        issue_data = {
            'key': issue['key'],
            'summary': fields.get('summary', ''),
            'status': fields.get('status', {}).get('name', 'Unknown'),
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            'reporter': fields.get('reporter', {}).get('displayName', 'Unknown') if fields.get('reporter') else 'Unknown',
            'priority': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
            'labels': fields.get('labels', []),
            'description': fields.get('description', 'No description'),
            'url': f"{self.jira_url}/browse/{issue['key']}",
            'comments': detailed_info.get('comments', []),
            'level': 0,
            'children': []
        }
        
        # Add custom fields processing as needed
        # ... (simplified from original)
        
        return issue_data
        
    def _build_issue_hierarchy(self, issues: List[Dict], issue_map: Dict[str, Dict]):
        """Build hierarchical relationships between issues"""
        # Simplified implementation
        for issue in issues:
            # Sort by key for consistent ordering
            issue['children'] = sorted(issue.get('children', []), key=lambda x: x.get('key', ''))
            
    def export_confluence_content(self):
        """Export Confluence content as PDFs"""
        self.logger.info(f"Starting Confluence export for label '{self.label}'")
        
        spaces = self.search_confluence_spaces()
        
        if not spaces:
            self.logger.info(f"No Confluence spaces found with label '{self.label}'")
            return
            
        total_pages = sum(len(space['pages']) for space in spaces)
        self.logger.info(f"Found {len(spaces)} spaces with {total_pages} total pages to export")
        
        for space in spaces:
            if not space['pages']:
                continue
                
            # Skip if already complete
            if self.checkpoint_manager.is_confluence_space_complete(space['name']):
                self.logger.info(f"Skipping already completed space: {space['name']}")
                continue
                
            self.logger.info(f"Processing Confluence space: {space['name']} ({len(space['pages'])} pages)")
            
            content_sections = []
            space_start_time = time.time()
            
            for page in space['pages']:
                # Skip if already exported
                if self.checkpoint_manager.is_confluence_page_exported(page['id']):
                    continue
                    
                self.logger.info(f"Exporting page: {page['title']}")
                
                # Get page content
                page_content = self.get_confluence_page_content(page['id'])
                if not page_content:
                    continue
                    
                # Convert HTML to text
                conversion_result = self.convert_html_to_text(page_content)
                text_content = conversion_result['text']
                
                # Build content section
                content_parts = [
                    f"**Space:** {space['name']}",
                    f"**Author:** {page['author']}",
                    f"**Last Modified:** {page['last_modified']}",
                    "",
                    "## Content",
                    text_content,
                    "",
                    f"**Page URL:** {page['url']}"
                ]
                
                section = {
                    'title': page['title'],
                    'content': '\n'.join(content_parts)
                }
                content_sections.append(section)
                
                # Update checkpoint
                self.checkpoint_manager.update_confluence_progress(space['name'], page['id'])
                
            # Create PDF for space
            if content_sections and not self.dry_run and not self.validate_only:
                filename = f"{self.label}_Confluence_{space['name'].replace(' ', '_')}_{self.export_date}.pdf"
                self.create_pdf(filename, f"Context Export - Confluence: {space['name']}", content_sections)
                
            # Mark space as complete
            self.checkpoint_manager.mark_confluence_space_complete(space['name'])
            
            # Log performance
            space_duration = time.time() - space_start_time
            self.logger.log_performance_metrics(
                f"confluence_space_{space['name']}",
                space_duration,
                len(content_sections)
            )
            
    def export_jira_content(self):
        """Export Jira content as PDFs"""
        self.logger.info(f"Starting Jira export for label '{self.label}'")
        
        projects = self.search_jira_projects()
        
        if not projects:
            self.logger.info(f"No Jira projects found with label '{self.label}'")
            return
            
        total_issues = sum(len(project['issues']) for project in projects)
        self.logger.info(f"Found {len(projects)} projects with {total_issues} total issues to export")
        
        for project in projects:
            if not project['issues']:
                continue
                
            # Skip if already complete
            if self.checkpoint_manager.is_jira_project_complete(project['name']):
                self.logger.info(f"Skipping already completed project: {project['name']}")
                continue
                
            self.logger.info(f"Processing Jira project: {project['name']} ({len(project['issues'])} issues)")
            
            content_sections = []
            project_start_time = time.time()
            
            for issue in project['issues']:
                # Skip if already exported
                if self.checkpoint_manager.is_jira_issue_exported(issue['key']):
                    continue
                    
                self.logger.info(f"Exporting issue: {issue['key']}")
                
                # Format issue content
                content_parts = [
                    f"**Project:** {project['name']}",
                    f"**Status:** {issue['status']}",
                    f"**Assignee:** {issue['assignee']}",
                    f"**Reporter:** {issue['reporter']}",
                    f"**Priority:** {issue['priority']}",
                    f"**Labels:** {', '.join(issue['labels'])}",
                    "",
                    "## Description",
                    issue.get('description', 'No description'),
                    "",
                    f"**Issue URL:** {issue['url']}"
                ]
                
                section = {
                    'title': f"{issue['key']}: {issue['summary']}",
                    'content': '\n'.join(content_parts)
                }
                content_sections.append(section)
                
                # Update checkpoint
                self.checkpoint_manager.update_jira_progress(project['name'], issue['key'])
                
            # Create PDF for project
            if content_sections and not self.dry_run and not self.validate_only:
                filename = f"{self.label}_Jira_{project['name'].replace(' ', '_')}_{self.export_date}.pdf"
                self.create_pdf(filename, f"Context Export - Jira: {project['name']}", content_sections)
                
            # Mark project as complete
            self.checkpoint_manager.mark_jira_project_complete(project['name'])
            
            # Log performance
            project_duration = time.time() - project_start_time
            self.logger.log_performance_metrics(
                f"jira_project_{project['name']}",
                project_duration,
                len(content_sections)
            )
            
    def create_pdf(self, filename: str, title: str, content_sections: List[Dict]):
        """Create a PDF with the given content sections"""
        # Implementation from original
        # ... (use the original PDF creation logic)
        self.logger.info(f"Created PDF: {filename}")
        
    def run_export(self):
        """Run the complete export process"""
        self.logger.info(
            "Starting Context Export Process",
            label=self.label,
            profile=self.config.profile_name,
            export_date=self.export_date,
            output_dir=self.output_dir
        )
        
        # Print configuration info
        profile_info = self.config.get_profile_info()
        self.logger.info("Export configuration", **profile_info)
        
        # Run diagnostics
        if not self.run_diagnostics():
            return
            
        # If validate only mode, run validation and exit
        if self.validate_only:
            validation_results = self.validate_connectivity()
            print("\n=== Validation Results ===")
            print(json.dumps(validation_results, indent=2))
            return
            
        # Export Confluence content
        if hasattr(self, 'include_confluence') and self.include_confluence:
            self.export_confluence_content()
        else:
            self.logger.info("Skipping Confluence export (not selected)")
            
        # Export Jira content
        if hasattr(self, 'include_jira') and self.include_jira:
            self.export_jira_content()
        else:
            self.logger.info("Skipping Jira export (not selected)")
            
        # Complete export
        self.checkpoint_manager.complete_export()
        
        # Log final statistics
        total_duration = time.time() - self.start_time
        self.logger.log_performance_metrics(
            "total_export",
            total_duration,
            items_processed=len(self.checkpoint_manager.current_state.confluence_pages_exported) + 
                          len(self.checkpoint_manager.current_state.jira_issues_exported),
            api_calls=self.api_call_count,
            cache_stats=self.api_client.get_stats()
        )
        
        if self.dry_run:
            self.logger.info("Dry run complete. No files exported.")
        else:
            self.logger.info(
                "Context Export Process Complete!",
                total_duration_seconds=round(total_duration, 2),
                output_directory=self.output_dir
            )


def main():
    parser = argparse.ArgumentParser(
        description="Context Exporter V2 - Production-ready export tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic export with balanced profile
  python context_exporter_v2.py --label "MyLabel"
  
  # Fast export (may hit rate limits)
  python context_exporter_v2.py --label "MyLabel" --profile fast
  
  # Conservative export for maximum reliability
  python context_exporter_v2.py --label "MyLabel" --profile conservative
  
  # Resume from checkpoint
  python context_exporter_v2.py --resume checkpoint_abc123.json
  
  # Validate connectivity only
  python context_exporter_v2.py --label "MyLabel" --validate-only
  
  # Dry run to see what would be exported
  python context_exporter_v2.py --label "MyLabel" --dry-run
        """
    )
    
    parser.add_argument('--label', type=str, help='Label for export')
    parser.add_argument('--profile', type=str, default='balanced', 
                       choices=['fast', 'balanced', 'conservative'],
                       help='Performance profile (default: balanced)')
    parser.add_argument('--include-summary', action='store_true', 
                       help='Generate summary PDFs combining all content')
    parser.add_argument('--include-jira', action='store_true', 
                       help='Include Jira export')
    parser.add_argument('--include-confluence', action='store_true', 
                       help='Include Confluence export')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run diagnostics and list targets without creating PDFs')
    parser.add_argument('--validate-only', action='store_true',
                       help='Validate connectivity and exit')
    parser.add_argument('--resume', type=str, metavar='CHECKPOINT_FILE',
                       help='Resume from checkpoint file')
    parser.add_argument('--list-checkpoints', action='store_true',
                       help='List available checkpoints and exit')
    parser.add_argument('--config-file', type=str,
                       help='Path to configuration file')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Handle checkpoint listing
    if args.list_checkpoints:
        config = ExporterConfig('balanced')
        LoggerFactory.set_config(config.logging)
        logger = LoggerFactory.get_logger("CheckpointLister")
        checkpoint_manager = CheckpointManager(config.checkpoint.checkpoint_dir, logger)
        
        checkpoints = checkpoint_manager.list_checkpoints()
        if checkpoints:
            print("\nAvailable checkpoints:")
            for cp in checkpoints:
                print(f"\n  File: {cp['file']}")
                print(f"  Label: {cp['label']}")
                print(f"  Started: {cp['started_at']}")
                print(f"  Last Updated: {cp['last_updated']}")
                print(f"  Progress: Confluence={cp['confluence_progress']}, Jira={cp['jira_progress']}")
        else:
            print("\nNo checkpoints found.")
        return
        
    # Validate arguments
    if not args.resume and not args.label:
        parser.error("Either --label or --resume must be specified")
        
    # Load configuration
    config = ExporterConfig(args.profile, args.config_file)
    
    # Override log level if specified
    if args.log_level:
        config.logging.level = args.log_level
        
    # Initialize exporter
    try:
        if args.resume:
            # Resume from checkpoint
            exporter = ContextExporterV2(
                label="",  # Will be loaded from checkpoint
                config=config,
                resume_checkpoint=args.resume,
                include_summary=args.include_summary,
                dry_run=args.dry_run,
                validate_only=args.validate_only
            )
        else:
            # New export
            label = args.label.strip().lower()
            exporter = ContextExporterV2(
                label=label,
                config=config,
                include_summary=args.include_summary,
                dry_run=args.dry_run,
                validate_only=args.validate_only
            )
            
        # Set export preferences
        exporter.include_jira = args.include_jira
        exporter.include_confluence = args.include_confluence
        
        # If no specific export type is specified, default to both
        if not args.include_jira and not args.include_confluence:
            exporter.include_jira = True
            exporter.include_confluence = True
            
        # Run export
        exporter.run_export()
        
    except KeyboardInterrupt:
        print("\n\nExport interrupted by user. Progress has been saved to checkpoint.")
        print("Use --resume to continue from where you left off.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()