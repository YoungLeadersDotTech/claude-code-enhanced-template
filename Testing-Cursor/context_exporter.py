#!/usr/bin/env python3
"""
Context Export Tool
Gathers content from Confluence and Jira tagged with specified labels and exports as PDFs.
"""

import os
import json
import requests
from datetime import datetime
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

class ContextExporter:
    def __init__(self, label, confluence_url=None, jira_url=None, username=None, api_token=None, include_summary=False, dry_run=False):
        self.label = label
        self.confluence_url = confluence_url or os.getenv('CONFLUENCE_URL')
        self.jira_url = jira_url or os.getenv('JIRA_URL')
        self.username = username or os.getenv('ATLASSIAN_USERNAME')
        self.api_token = api_token or os.getenv('ATLASSIAN_API_TOKEN')
        self.export_date = datetime.now().strftime('%Y_%m_%d')
        self.include_summary = include_summary
        self.dry_run = dry_run

        # Declare optional attributes for Pyright
        self.include_jira = True
        self.include_confluence = True

        self.output_dir = f"exports/{self.label.replace(' ', '_').lower()}/{self.export_date}"
        if not self.dry_run:
            os.makedirs(self.output_dir, exist_ok=True)

        self.session = requests.Session()
        if self.username and self.api_token:
            self.session.auth = (self.username, self.api_token)
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
        
        # Store content for summary generation
        self.all_confluence_content = []
        self.all_jira_content = []

    def run_diagnostics(self):
        """Run preflight checks to verify connectivity and authentication"""
        print("🔍 Running preflight diagnostics...")
        print("-" * 50)
        
        diagnostics_passed = True
        
        # Test Jira connectivity and authentication
        if self.include_jira and self.jira_url:
            print("🔍 Testing Jira connectivity...")
            try:
                # Test basic connectivity
                response = self.session.get(f"{self.jira_url}/rest/api/2/myself", timeout=10)
                if response.status_code == 200:
                    user_info = response.json()
                    print(f"✅ Jira connection successful - authenticated as: {user_info.get('displayName', 'Unknown')}")
                else:
                    print(f"❌ Jira authentication failed - status code: {response.status_code}")
                    diagnostics_passed = False
            except requests.exceptions.RequestException as e:
                print(f"❌ Jira connection failed: {e}")
                diagnostics_passed = False
        elif self.include_jira:
            print("❌ Jira URL not configured")
            diagnostics_passed = False
        else:
            print("ℹ️  Jira export disabled - skipping diagnostics")
        
        # Test Confluence connectivity and authentication
        if self.include_confluence and self.confluence_url:
            print("🔍 Testing Confluence connectivity...")
            try:
                # Test basic connectivity
                response = self.session.get(f"{self.confluence_url}/rest/api/space", timeout=10)
                if response.status_code == 200:
                    print("✅ Confluence connection successful")
                else:
                    print(f"❌ Confluence authentication failed - status code: {response.status_code}")
                    diagnostics_passed = False
            except requests.exceptions.RequestException as e:
                print(f"❌ Confluence connection failed: {e}")
                diagnostics_passed = False
        elif self.include_confluence:
            print("❌ Confluence URL not configured")
            diagnostics_passed = False
        else:
            print("ℹ️  Confluence export disabled - skipping diagnostics")
        
        print("-" * 50)
        
        if not diagnostics_passed:
            print("🚫 Preflight checks failed. Aborting export.")
            return False
        
        print("✅ All preflight checks passed!")
        return True

    def convert_html_to_text(self, html_content):
        """Convert HTML content to markdown-style plain text with smart link expansion and heading hierarchy"""
        if not html_content:
            return {"text": "", "linked_page_ids": []}
        
        # Clean HTML: remove problematic attributes
        soup = BeautifulSoup(html_content, 'html.parser')
        
        linked_page_ids = []  # Track page IDs from smart links
        
        # Handle smart links to other Confluence pages
        for link in soup.find_all('a', class_='confluence-userlink'):
            # Type-safe check for Tag elements
            if not isinstance(link, Tag):
                continue
                
            # This is a smart link to another Confluence page
            href = link.get('href', '')
            if isinstance(href, str) and 'pageId=' in href:
                page_id = href.split('pageId=')[-1]
            else:
                page_id = None
                
            if page_id:
                linked_page_ids.append(page_id)  # Track this page ID for export
                try:
                    # Try to get page info
                    page_info = self.get_confluence_page_info(page_id)
                    if page_info:
                        link_text = link.get_text()
                        link.replace_with(NavigableString(f"**[{link_text}]({page_info['url']})** - {page_info['title']}"))
                    else:
                        # Fallback to just the link text
                        link_text = link.get_text()
                        link.replace_with(NavigableString(f"**[{link_text}]({href})**"))
                except:
                    # If we can't get page info, just keep the original link
                    pass
        
        # Handle regular links
        for link in soup.find_all('a'):
            if not isinstance(link, Tag):
                continue
                
            # Safe handling of link classes
            link_classes = link.get('class')
            if not isinstance(link_classes, list) or 'confluence-userlink' not in link_classes:
                href = link.get('href', '')
                link_text = link.get_text()
                if isinstance(href, str) and isinstance(link_text, str) and href and link_text:
                    link.replace_with(NavigableString(f"[{link_text}]({href})"))
        
        # Remove problematic attributes but keep structure
        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue
                
            # Safe handling of tag attributes
            if hasattr(tag, 'attrs') and isinstance(tag.attrs, dict):
                for attr in list(tag.attrs):
                    if attr not in ['href', 'src']:
                        del tag[attr]
        
        # Convert cleaned HTML to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False  # Keep images
        h.ignore_emphasis = False
        h.body_width = 0
        h.ignore_tables = False
        markdown_text = h.handle(str(soup))
        
        # Remove any remaining HTML tags from the markdown output using BeautifulSoup
        soup2 = BeautifulSoup(markdown_text, 'html.parser')
        clean_text = soup2.get_text()
        # Aggressively remove any <...> tags (even if not valid HTML)
        prev = None
        while prev != clean_text:
            prev = clean_text
            clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        return {"text": clean_text, "linked_page_ids": linked_page_ids}

    def get_confluence_page_info(self, page_id):
        """Get basic info about a Confluence page for smart link expansion"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'version'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            page_data = response.json()
            return {
                'title': page_data.get('title', 'Unknown Page'),
                'url': f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            }
            
        except Exception as e:
            print(f"❌ Error getting page info for {page_id}: {e}")
            return None

    def search_confluence_spaces(self):
        """Search for Confluence spaces containing pages with specified label and their children, with pagination"""
        if not self.confluence_url:
            print("⚠️  Confluence URL not configured. Skipping Confluence export.")
            return []
        
        try:
            search_url = f"{self.confluence_url}/rest/api/content/search"
            batch_size = 1000  # Confluence API max is 1000
            start = 0
            all_results = []
            total = None
            while True:
                params = {
                    'cql': f'label = "{self.label}"',
                    'limit': batch_size,
                    'start': start,
                    'expand': 'space,version'
                }
                response = self.session.get(search_url, params=params)
                response.raise_for_status()
                results = response.json()
                batch = results.get('results', [])
                if total is None:
                    total = results.get('total', None)
                print(f"Fetched {len(batch)} Confluence pages (batch starting at {start})")
                if not batch:
                    break
                all_results.extend(batch)
                if len(batch) < batch_size:
                    break
                start += batch_size
            spaces = {}
            exported_page_ids = set()
            for page in all_results:
                space_key = page['space']['key']
                space_name = page['space']['name']
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
                self.fetch_child_pages_recursive(
                    page['id'], 
                    spaces[space_key]['pages'], 
                    exported_page_ids, 
                    level=1, 
                    max_level=4
                )
                self.process_smart_links_in_page(
                    page['id'],
                    spaces[space_key]['pages'],
                    exported_page_ids,
                    level=0
                )
            for space_key in spaces:
                spaces[space_key]['pages'].sort(
                    key=lambda x: (x['level'], x['title'])
                )
            return list(spaces.values())
        except Exception as e:
            print(f"❌ Error searching Confluence: {e}")
            return []

    def process_smart_links_in_page(self, page_id, pages_list, exported_page_ids, level):
        """Process smart links in a page and add linked pages to the export"""
        try:
            # Get page content to find smart links
            page_content = self.get_confluence_page_content(page_id)
            if not page_content:
                return
            
            # Parse HTML to find smart links
            soup = BeautifulSoup(page_content, 'html.parser')
            
            for link in soup.find_all('a', class_='confluence-userlink'):
                if not isinstance(link, Tag):
                    continue
                    
                # Safe handling of href attribute
                href = link.get('href', '')
                if isinstance(href, str) and 'pageId=' in href:
                    linked_page_id = href.split('pageId=')[-1]
                    
                    # Only process if we haven't already exported this page
                    if linked_page_id not in exported_page_ids:
                        try:
                            # Get page info
                            page_info = self.get_confluence_page_info(linked_page_id)
                            if page_info:
                                # Add to pages list
                                page_data = {
                                    'id': linked_page_id,
                                    'title': page_info['title'],
                                    'author': 'Unknown',
                                    'last_modified': 'Unknown',
                                    'url': page_info['url'],
                                    'level': level + 1
                                }
                                pages_list.append(page_data)
                                exported_page_ids.add(linked_page_id)
                                
                                # Recursively process this page's smart links
                                self.process_smart_links_in_page(
                                    linked_page_id,
                                    pages_list,
                                    exported_page_ids,
                                    level + 1
                                )
                        except Exception as e:
                            print(f"❌ Error processing smart link to {linked_page_id}: {e}")
                            
        except Exception as e:
            print(f"❌ Error processing smart links in page {page_id}: {e}")

    def fetch_child_pages_recursive(self, parent_id, pages_list, exported_page_ids, level, max_level):
        """Recursively fetch child pages up to max_level depth with natural tree sorting"""
        if level > max_level:
            return
        
        try:
            # Get child pages
            child_url = f"{self.confluence_url}/rest/api/content/{parent_id}/child/page"
            params = {
                'expand': 'version',
                'limit': 1000  # Get all children
            }
            
            response = self.session.get(child_url, params=params)
            response.raise_for_status()
            
            results = response.json()
            child_pages = results.get('results', [])
            
            # Sort child pages by position if available, otherwise by title
            def sort_key(page):
                # Safe handling of page data
                if isinstance(page, dict):
                    # Try to get position, fall back to title
                    position = page.get('position')
                    title = page.get('title', '')
                    if position is not None:
                        return (position, title)
                    return (0, title)
                return (0, '')
            
            child_pages.sort(key=sort_key)
            
            for child in child_pages:
                if isinstance(child, dict) and 'id' in child:
                    child_id = child['id']
                    if child_id not in exported_page_ids:
                        # Safe handling of nested dictionary access
                        version_info = child.get('version', {})
                        if isinstance(version_info, dict):
                            by_info = version_info.get('by', {})
                            author = by_info.get('displayName', 'Unknown') if isinstance(by_info, dict) else 'Unknown'
                            last_modified = version_info.get('when', 'Unknown')
                        else:
                            author = 'Unknown'
                            last_modified = 'Unknown'
                        
                        child_data = {
                            'id': child_id,
                            'title': child.get('title', 'Unknown'),
                            'author': author,
                            'last_modified': last_modified,
                            'url': f"{self.confluence_url}/pages/viewpage.action?pageId={child_id}",
                            'level': level
                        }
                        pages_list.append(child_data)
                        exported_page_ids.add(child_id)
                        
                        # Recursively fetch children of this child
                        self.fetch_child_pages_recursive(
                            child_id,
                            pages_list,
                            exported_page_ids,
                            level + 1,
                            max_level
                        )
                        
        except Exception as e:
            print(f"❌ Error fetching child pages for {parent_id}: {e}")

    def get_confluence_page_content(self, page_id):
        """Get the content of a Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            page_data = response.json()
            return page_data.get('body', {}).get('storage', {}).get('value', '')
            
        except Exception as e:
            print(f"❌ Error getting page content for {page_id}: {e}")
            return None

    def search_jira_projects(self):
        """Search for Jira projects with issues labeled with specified label, with pagination and hierarchical data"""
        if not self.jira_url:
            print("⚠️  Jira URL not configured. Skipping Jira export.")
            return []
        
        try:
            search_url = f"{self.jira_url}/rest/api/2/search"
            batch_size = 100  # Jira API max is 100
            start_at = 0
            all_issues = []
            total = None
            while True:
                payload = {
                    'jql': f'labels = "{self.label}"',
                    'maxResults': batch_size,
                    'startAt': start_at,
                    'fields': [
                        'summary', 'status', 'assignee', 'reporter', 'description', 'project',
                        'priority', 'labels', 'components', 'fixVersions', 'versions',
                        'duedate', 'created', 'updated', 'issuetype', 'parent', 'epic',
                        'customfield_10014', 'customfield_10016', 'customfield_10034', 'customfield_10035',
                        'customfield_10036', 'customfield_10037', 'customfield_10038', 'customfield_10039',
                        'customfield_10040', 'customfield_10041', 'customfield_10042', 'customfield_10043',
                        'customfield_10044', 'customfield_10045', 'customfield_10046', 'customfield_10047',
                        'customfield_10048', 'customfield_10049', 'customfield_10050', 'customfield_10051',
                        'customfield_10052', 'customfield_10053', 'customfield_10054', 'customfield_10055',
                        'customfield_10056', 'customfield_10057', 'customfield_10058', 'customfield_10059',
                        'customfield_10060', 'customfield_10061', 'customfield_15013', 'customfield_13554',
                        'attachment', 'comment', 'issuelinks', 'subtasks', 'worklog'
                    ]
                }
                response = self.session.post(search_url, json=payload)
                response.raise_for_status()
                results = response.json()
                batch = results.get('issues', [])
                if total is None:
                    total = results.get('total', None)
                print(f"Fetched {len(batch)} Jira issues (batch starting at {start_at})")
                if not batch:
                    break
                all_issues.extend(batch)
                if len(batch) < batch_size:
                    break
                start_at += batch_size
            
            print(f"📊 Total Jira issues found with label '{self.label}': {len(all_issues)}")
            
            if not all_issues:
                print(f"ℹ️  No Jira issues found with label '{self.label}'.")
                return []
            
            # Process issues and build hierarchical structure
            projects = {}
            issue_map = {}  # Map issue keys to issue objects for hierarchy building
            
            for issue in all_issues:
                project_key = issue['fields']['project']['key']
                project_name = issue['fields']['project']['name']
                
                if project_key not in projects:
                    projects[project_key] = {
                        'name': project_name,
                        'issues': []
                    }
                
                detailed_issue = self.get_detailed_issue_info(issue['key'])
                
                # Extract hierarchical information
                issue_type = issue['fields']['issuetype']
                parent_info = issue['fields'].get('parent')
                epic_info = issue['fields'].get('epic')
                
                # Safely extract fix versions and components
                fix_versions = []
                try:
                    fix_versions_field = issue['fields'].get('fixVersions')
                    if fix_versions_field and isinstance(fix_versions_field, list):
                        fix_versions = [ver.get('name', 'Unknown') for ver in fix_versions_field if isinstance(ver, dict) and ver.get('name')]
                except Exception as e:
                    print(f"⚠️  Warning: Error extracting fix versions for {issue['key']}: {e}")
                
                components = []
                try:
                    components_field = issue['fields'].get('components')
                    if components_field and isinstance(components_field, list):
                        components = [comp.get('name', 'Unknown') for comp in components_field if isinstance(comp, dict) and comp.get('name')]
                except Exception as e:
                    print(f"⚠️  Warning: Error extracting components for {issue['key']}: {e}")
                
                issue_data = {
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                    'status': issue['fields']['status']['name'],
                    'assignee': issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else 'Unassigned',
                    'reporter': issue['fields']['reporter']['displayName'] if issue['fields']['reporter'] else 'Unknown',
                    'priority': issue['fields']['priority']['name'] if issue['fields']['priority'] else 'None',
                    'labels': issue['fields']['labels'],
                    'components': components,
                    'fix_versions': fix_versions,
                    'description': issue['fields']['description'] or 'No description',
                    'attachments': issue['fields']['attachment'],
                    'comments': detailed_issue.get('comments', []),
                    'issuelinks': issue['fields']['issuelinks'],
                    'subtasks': issue['fields']['subtasks'],
                    'story_points': issue['fields'].get('customfield_10014'),
                    'sprint': self.extract_sprint_info(issue['fields'].get('customfield_10016')),
                    'duedate': issue['fields'].get('duedate'),
                    'created': issue['fields'].get('created'),
                    'owner': self.extract_custom_field_value(issue['fields'], 'customfield_10034'),
                    'team': self.extract_custom_field_value(issue['fields'], 'customfield_10035'),
                    'six_week_cycle': self.extract_custom_field_value(issue['fields'], 'customfield_10036'),
                    'current_environment': self.extract_custom_field_value(issue['fields'], 'customfield_10037'),
                    'final_environment': self.extract_custom_field_value(issue['fields'], 'customfield_10038'),
                    'copado_current_environment': self.extract_custom_field_value(issue['fields'], 'customfield_10039'),
                    'solution_architect': self.extract_custom_field_value(issue['fields'], 'customfield_10051'),
                    'qa_point_of_contact': self.extract_custom_field_value(issue['fields'], 'customfield_10052'),
                    'approved_by_qa': self.extract_custom_field_value(issue['fields'], 'customfield_10053'),
                    'change_control_review': self.extract_custom_field_value(issue['fields'], 'customfield_10054'),
                    'investment_categories': self.extract_custom_field_value(issue['fields'], 'customfield_10055'),
                    'env_found_in': self.extract_custom_field_value(issue['fields'], 'customfield_10056'),
                    'portfolio_work': self.extract_custom_field_value(issue['fields'], 'customfield_10057'),
                    'development': self.extract_custom_field_value(issue['fields'], 'customfield_10058'),
                    'parent': self.extract_custom_field_value(issue['fields'], 'customfield_10059'),
                    'rca_category': self.extract_custom_field_value(issue['fields'], 'customfield_10060'),
                    'start_date': self.extract_custom_field_value(issue['fields'], 'customfield_10061'),
                    'description_custom': self.extract_custom_field_value(issue['fields'], 'customfield_15013'),
                    'acceptance_criteria': self.extract_custom_field_value(issue['fields'], 'customfield_13554'),
                    'solution_status': self.extract_custom_field_value(issue['fields'], 'customfield_10040'),
                    'solution': self.extract_custom_field_value(issue['fields'], 'customfield_10041'),
                    'test_plan': self.extract_custom_field_value(issue['fields'], 'customfield_10042'),
                    'testing_notes': self.extract_custom_field_value(issue['fields'], 'customfield_10043'),
                    'release_note': self.extract_custom_field_value(issue['fields'], 'customfield_10049'),
                    'justification': self.extract_custom_field_value(issue['fields'], 'customfield_10044'),
                    'backout_plan': self.extract_custom_field_value(issue['fields'], 'customfield_10045'),
                    'risk_analysis': self.extract_custom_field_value(issue['fields'], 'customfield_10046'),
                    'product_owner_signoff': self.extract_custom_field_value(issue['fields'], 'customfield_10047'),
                    'stakeholder_reviewers': self.extract_custom_field_value(issue['fields'], 'customfield_10048'),
                    'url': f"{self.jira_url}/browse/{issue['key']}",
                    # Hierarchical fields
                    'issuetype': issue_type['name'],
                    'is_subtask': issue_type.get('subtask', False),
                    'parent_key': parent_info['key'] if parent_info else None,
                    'parent_summary': parent_info['fields']['summary'] if parent_info else None,
                    'epic_key': epic_info['key'] if epic_info else None,
                    'epic_name': epic_info['fields']['summary'] if epic_info else None,
                    'children': [],  # Will be populated during hierarchy building
                    'level': 0  # Will be set during hierarchy building
                }
                
                projects[project_key]['issues'].append(issue_data)
                issue_map[issue['key']] = issue_data
            
            # Build hierarchical relationships
            for project in projects.values():
                self.build_issue_hierarchy(project['issues'], issue_map)
            
            # Log project summary
            for project_key, project in projects.items():
                print(f"📋 Project '{project['name']}': {len(project['issues'])} issues")
            
            return list(projects.values())
        except Exception as e:
            print(f"❌ Error searching Jira: {e}")
            import traceback
            traceback.print_exc()
            return []

    def build_issue_hierarchy(self, issues, issue_map):
        """Build hierarchical relationships between issues"""
        # First pass: establish parent-child relationships
        for issue in issues:
            if issue['parent_key'] and issue['parent_key'] in issue_map:
                parent = issue_map[issue['parent_key']]
                parent['children'].append(issue)
                issue['level'] = parent['level'] + 1
        
        # Second pass: establish epic relationships
        epic_groups = {}
        for issue in issues:
            if issue['epic_key'] and issue['epic_key'] in issue_map:
                epic = issue_map[issue['epic_key']]
                if epic['key'] not in epic_groups:
                    epic_groups[epic['key']] = {
                        'epic': epic,
                        'children': []
                    }
                epic_groups[epic['key']]['children'].append(issue)
        
        # Sort issues by hierarchy level and then by key
        def sort_issues(issue_list):
            return sorted(issue_list, key=lambda x: (x['level'], x['key']))
        
        # Sort all issues and their children
        for issue in issues:
            if issue['children']:
                issue['children'] = sort_issues(issue['children'])

    def get_detailed_issue_info(self, issue_key):
        """Get detailed information for a specific issue including comments and rendered fields"""
        try:
            url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
            params = {
                'expand': 'renderedFields,comments,attachments'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            issue_data = response.json()
            return {
                'comments': issue_data.get('fields', {}).get('comment', {}).get('comments', []),
                'rendered_fields': issue_data.get('renderedFields', {})
            }
            
        except Exception as e:
            print(f"❌ Error getting detailed info for {issue_key}: {e}")
            return {'comments': [], 'rendered_fields': {}}

    def extract_sprint_info(self, sprint_field):
        """Extract sprint information from the sprint custom field"""
        if not sprint_field:
            return None
        
        try:
            # Sprint field is usually a string containing JSON-like data
            # Example: "com.atlassian.greenhopper.service.sprint.Sprint@12345[id=123,rapidViewId=456,state=active,name=Sprint 1,startDate=2025-01-01T00:00:00.000Z,endDate=2025-01-15T00:00:00.000Z,completeDate=<null>,sequence=123]"
            import re
            match = re.search(r'name=([^,]+)', sprint_field)
            if match:
                return match.group(1)
            return sprint_field
        except:
            return sprint_field

    def extract_epic_info(self, fields):
        """Extract epic information from various epic custom fields"""
        epic_info = {}
        
        # Try different common epic field names
        epic_fields = [
            'customfield_10020', 'customfield_10021', 'customfield_10022',
            'customfield_10023', 'customfield_10024', 'customfield_10025',
            'customfield_10026', 'customfield_10027', 'customfield_10028',
            'customfield_10029', 'customfield_10030', 'customfield_10031',
            'customfield_10032', 'customfield_10033'
        ]
        
        for field in epic_fields:
            if field in fields and fields[field]:
                if isinstance(fields[field], dict):
                    epic_info[field] = fields[field].get('value', str(fields[field]))
                else:
                    epic_info[field] = str(fields[field])
        
        return epic_info if epic_info else None

    def extract_custom_field_value(self, fields, field_name):
        """Extract value from a custom field, handling different field types"""
        if field_name not in fields or not fields[field_name]:
            return None
        
        field_value = fields[field_name]
        
        # Handle different field types
        if isinstance(field_value, dict):
            # Single select, user, etc.
            return field_value.get('displayName') or field_value.get('value') or field_value.get('name')
        elif isinstance(field_value, list):
            # Multi-select, multiple users, etc.
            return [item.get('displayName') or item.get('value') or item.get('name') for item in field_value]
        else:
            # String, number, etc.
            return str(field_value)

    def format_issue_metadata(self, issue):
        """Format issue metadata into the two specified sections with exact field order"""
        context_fields = []
        description_fields = []
        
        # Section 1: Context Fields (in exact order specified)
        context_field_mappings = [
            ('Status', issue['status']),
            ('Labels', ', '.join(issue['labels']) if issue['labels'] else None),
            ('Owner', issue['owner']),
            ('Assignee', issue['assignee']),
            ('Reporter', issue['reporter']),
            ('Solution Architect', issue['solution_architect']),
            ('QA Point of Contact', issue['qa_point_of_contact']),
            ('Stakeholder Reviewers', issue['stakeholder_reviewers']),
            ('Approved by QA', issue['approved_by_qa']),
            ('Product Owner Sign-off to Release', issue['product_owner_signoff']),
            ('Team', issue['team']),
            ('Priority', issue['priority']),
            ('Story Points', issue['story_points']),
            ('Sprint', issue['sprint']),
            ('6 Week Cycle', issue['six_week_cycle']),
            ('Due Date', issue['duedate']),
            ('Start Date', issue['start_date']),
            ('Components', ', '.join(issue['components']) if issue['components'] else None),
            ('Parent', issue['parent']),
            ('RCA Category', issue['rca_category']),
            ('Fix Versions', ', '.join(issue['fix_versions']) if issue['fix_versions'] else None),
            ('Change Control Review', issue['change_control_review']),
            ('Current Environment', issue['current_environment']),
            ('Copado Current Environment', issue['copado_current_environment']),
            ('Final Environment', issue['final_environment']),
            ('Investment Categories', issue['investment_categories']),
            ('Env Found-In', issue['env_found_in']),
            ('Portfolio Work', issue['portfolio_work']),
            ('Development', issue['development'])
        ]
        
        for field_name, field_value in context_field_mappings:
            if field_value:
                context_fields.append(f"**{field_name}:** {field_value}")
            else:
                context_fields.append(f"**{field_name}:** Not Provided")
        
        # Section 2: Description Fields (in exact order specified)
        description_field_mappings = [
            ('Summary', issue['summary']),
            ('Description', issue['description_custom'] or issue['description']),
            ('Acceptance Criteria', issue['acceptance_criteria']),
            ('Solution Status', issue['solution_status']),
            ('Solution', issue['solution']),
            ('Test Plan', issue['test_plan']),
            ('Testing Notes', issue['testing_notes']),
            ('Release Note', issue['release_note']),
            ('Justification', issue['justification']),
            ('Backout Plan', issue['backout_plan']),
            ('Risk and Impact Analysis', issue['risk_analysis'])
        ]
        
        for field_name, field_value in description_field_mappings:
            if field_value:
                description_fields.append(f"**{field_name}:** {field_value}")
            else:
                description_fields.append(f"**{field_name}:** Not Provided")
        
        return {
            'context_fields': context_fields,
            'description_fields': description_fields
        }

    def format_attachments(self, attachments):
        """Format attachments as links"""
        if not attachments:
            return "No attachments"
        
        attachment_links = []
        for attachment in attachments:
            filename = attachment.get('filename', 'Unknown file')
            size = attachment.get('size', 0)
            size_mb = size / (1024 * 1024) if size > 0 else 0
            
            link = f"• {filename} ({size_mb:.1f} MB)"
            if 'content' in attachment:
                link += f" - [Download]({attachment['content']})"
            
            attachment_links.append(link)
        
        return '\n'.join(attachment_links)

    def format_comments(self, comments):
        """Format comments with author and timestamp"""
        if not comments:
            return "No comments"
        
        comment_texts = []
        for comment in comments:
            author = comment.get('author', {}).get('displayName', 'Unknown')
            created = comment.get('created', 'Unknown date')
            body = comment.get('body', '')
            
            # Convert HTML to text if needed
            if '<' in body and '>' in body:
                body = BeautifulSoup(body, 'html.parser').get_text()
            
            comment_text = f"**{author}** ({created}):\n{body}"
            comment_texts.append(comment_text)
        
        return '\n\n'.join(comment_texts)

    def format_issue_links(self, issuelinks):
        """Format issue links"""
        if not issuelinks:
            return "No related issues"
        
        link_texts = []
        for link in issuelinks:
            link_type = link.get('type', {}).get('name', 'Related')
            
            if 'inwardIssue' in link:
                issue = link['inwardIssue']
                key = issue['key']
                summary = issue['fields']['summary']
                link_texts.append(f"• {link_type}: {key} - {summary}")
            
            if 'outwardIssue' in link:
                issue = link['outwardIssue']
                key = issue['key']
                summary = issue['fields']['summary']
                link_texts.append(f"• {link_type}: {key} - {summary}")
        
        return '\n'.join(link_texts)

    def format_subtasks(self, subtasks):
        """Format subtasks"""
        if not subtasks:
            return "No subtasks"
        
        subtask_texts = []
        for subtask in subtasks:
            key = subtask['key']
            summary = subtask['fields']['summary']
            status = subtask['fields']['status']['name']
            subtask_texts.append(f"• {key} - {summary} ({status})")
        
        return '\n'.join(subtask_texts)

    def track_skipped_fields(self, issue):
        """Track which fields were skipped due to missing data"""
        skipped_fields = set()
        
        # Check each field and add to skipped if None/empty
        field_checks = [
            ('owner', issue['owner']),
            ('team', issue['team']),
            ('solution_architect', issue['solution_architect']),
            ('qa_point_of_contact', issue['qa_point_of_contact']),
            ('stakeholder_reviewers', issue['stakeholder_reviewers']),
            ('approved_by_qa', issue['approved_by_qa']),
            ('product_owner_signoff', issue['product_owner_signoff']),
            ('six_week_cycle', issue['six_week_cycle']),
            ('current_environment', issue['current_environment']),
            ('final_environment', issue['final_environment']),
            ('copado_current_environment', issue['copado_current_environment']),
            ('investment_categories', issue['investment_categories']),
            ('env_found_in', issue['env_found_in']),
            ('portfolio_work', issue['portfolio_work']),
            ('development', issue['development']),
            ('parent', issue['parent']),
            ('rca_category', issue['rca_category']),
            ('start_date', issue['start_date']),
            ('description_custom', issue['description_custom']),
            ('acceptance_criteria', issue['acceptance_criteria']),
            ('solution_status', issue['solution_status']),
            ('solution', issue['solution']),
            ('test_plan', issue['test_plan']),
            ('testing_notes', issue['testing_notes']),
            ('release_note', issue['release_note']),
            ('justification', issue['justification']),
            ('backout_plan', issue['backout_plan']),
            ('risk_analysis', issue['risk_analysis']),
            ('change_control_review', issue['change_control_review'])
        ]
        
        for field_name, field_value in field_checks:
            if not field_value or field_value == 'Not Provided':
                skipped_fields.add(field_name)
        
        return skipped_fields

    def _get_unique_filename(self, filename):
        """Generate a unique filename if the file already exists"""
        base_name, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(self.output_dir, new_filename)):
            new_filename = f"{base_name}_{counter}{ext}"
            counter += 1
        
        return new_filename

    def clean_html_for_reportlab(self, html_content):
        """Clean HTML content to be compatible with ReportLab's HTML parser"""
        if not html_content:
            return ""
        
        import re
        
        # Remove CSS classes and unsupported attributes
        # Remove class="..." attributes
        html_content = re.sub(r'class="[^"]*"', '', html_content)
        # Remove style="..." attributes  
        html_content = re.sub(r'style="[^"]*"', '', html_content)
        # Remove other unsupported attributes
        html_content = re.sub(r'data-[^=]*="[^"]*"', '', html_content)
        html_content = re.sub(r'id="[^"]*"', '', html_content)
        
        # Remove unsupported HTML tags that ReportLab doesn't handle
        unsupported_tags = ['label', 'div', 'span', 'section', 'article', 'header', 'footer', 'nav', 'aside']
        for tag in unsupported_tags:
            # Remove opening and closing tags, keeping content
            html_content = re.sub(rf'<{tag}[^>]*>', '', html_content)
            html_content = re.sub(rf'</{tag}>', '', html_content)
        
        # Convert markdown-style formatting to HTML
        # Convert **text** to <b>text</b> (handle paired markers)
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_content)
        # Convert *text* to <i>text</i> (handle paired markers)
        html_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html_content)
        
        # Handle any remaining unpaired markers by removing them
        html_content = html_content.replace('**', '').replace('*', '')
        
        # Clean up extra whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = html_content.strip()
        
        return html_content

    def create_pdf(self, filename, title, content_sections):
        """Create a PDF with the given content sections"""
        if self.dry_run:
            print(f"🧪 [DRY RUN] Would create PDF: {filename}")
            return
            
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.join('exports', self.label, self.export_date)
            os.makedirs(output_dir, exist_ok=True)
            
            # Get unique filename
            unique_filename = self._get_unique_filename(filename)
            filepath = os.path.join(output_dir, unique_filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20,
                alignment=1  # Center alignment
            )
            toc_style = ParagraphStyle(
                'CustomTOC',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=10,
                spaceBefore=10,
                alignment=0  # Left alignment
            )
            section_style = ParagraphStyle(
                'CustomSection',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=10,
                spaceBefore=10
            )
            content_style = ParagraphStyle(
                'CustomContent',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                leading=14
            )
            
            # Build story
            story = []
            
            # Add title
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))
            
            # Add export info
            export_info = f"<b>Export Details:</b><br/>"
            export_info += f"Label: {self.label}<br/>"
            export_info += f"Export Date: {self.export_date}<br/>"
            export_info += f"Total Sections: {len(content_sections)}<br/>"
            story.append(Paragraph(export_info, content_style))
            story.append(Spacer(1, 20))
            
            # Add Table of Contents
            if content_sections:
                story.append(Paragraph("<b>Table of Contents</b>", toc_style))
                story.append(Spacer(1, 10))
                
                # Create numbered TOC entries
                toc_entries = []
                for i, section in enumerate(content_sections, 1):
                    # For Jira issues, show key + summary
                    if 'key' in section.get('title', ''):
                        # Extract key and summary from title like "FOBUAT-188: Revenue Integration and Validation"
                        title_parts = section['title'].split(':', 1)
                        if len(title_parts) > 1:
                            key = title_parts[0].strip()
                            summary = title_parts[1].strip()
                            toc_entry = f"{i}. {key}: {summary}"
                        else:
                            toc_entry = f"{i}. {section['title']}"
                    else:
                        # For Confluence pages, just show the title
                        toc_entry = f"{i}. {section['title']}"
                    
                    toc_entries.append(toc_entry)
                
                # Add TOC as a single paragraph with line breaks
                toc_text = "<br/>".join(toc_entries)
                story.append(Paragraph(toc_text, content_style))
                story.append(Spacer(1, 20))
                
                # Add page break after TOC
                story.append(PageBreak())
            
            # Add content sections
            for i, section in enumerate(content_sections, 1):
                # Add section title
                section_title = f"{i}. {section['title']}"
                story.append(Paragraph(section_title, section_style))
                story.append(Spacer(1, 10))
                
                # Add section content
                content = section['content']
                
                # Clean HTML content for ReportLab compatibility
                content = self.clean_html_for_reportlab(content)
                
                # Split content into paragraphs and add each
                paragraphs = content.split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        # Clean up any remaining HTML issues
                        para = para.strip()
                        
                        # Ensure proper HTML structure for ReportLab
                        if not para.startswith('<'):
                            para = f'<para>{para}</para>'
                        else:
                            # If it already has HTML tags, wrap in para tags
                            para = f'<para>{para}</para>'
                        
                        try:
                            story.append(Paragraph(para, content_style))
                            story.append(Spacer(1, 6))
                        except Exception as para_error:
                            # If paragraph fails, try with plain text
                            print(f"⚠️  Paragraph failed, using plain text: {para_error}")
                            import re
                            plain_text = re.sub(r'<[^>]+>', '', para)  # Remove all HTML tags
                            plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                            story.append(Paragraph(f'<para>{plain_text}</para>', content_style))
                            story.append(Spacer(1, 6))
                
                # Add page break between sections (except for the last one)
                if i < len(content_sections):
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            print(f"✅ Created PDF: {unique_filename}")
            
        except Exception as e:
            print(f"❌ Error creating PDF {filename}: {e}")
            import traceback
            traceback.print_exc()

    def export_confluence_content(self):
        """Export Confluence content as PDFs"""
        print(f"📦 Starting Confluence export for label '{self.label}'...")
        
        spaces = self.search_confluence_spaces()
        
        if not spaces:
            print(f"ℹ️  No Confluence spaces found with label '{self.label}'.")
            return
        
        total_pages = sum(len(space['pages']) for space in spaces)
        print(f"📊 Found {len(spaces)} spaces with {total_pages} total pages to export")
        
        for space in spaces:
            if not space['pages']:
                continue
                
            print(f"📋 Processing Confluence space: {space['name']} ({len(space['pages'])} pages)")
            
            content_sections = []
            
            def process_page_hierarchy(page, level=0):
                print(f"📄 Exporting page: {page['title']} ({space['name']})")
                
                # Get page content
                page_content = self.get_confluence_page_content(page['id'])
                if not page_content:
                    return
                
                # Convert HTML content to text
                html_content = page_content
                conversion_result = self.convert_html_to_text(html_content)
                text_content = conversion_result['text']
                
                # Build page content
                content_parts = []
                
                # Page metadata
                content_parts.append(f"**Space:** {space['name']}")
                content_parts.append(f"**Author:** {page['author']}")
                content_parts.append(f"**Last Modified:** {page['last_modified']}")
                content_parts.append("")
                
                # Page content
                content_parts.append("## Content")
                content_parts.append(text_content)
                content_parts.append("")
                
                # Page URL
                content_parts.append(f"**Page URL:** {page['url']}")
                
                # Create section
                section = {
                    'title': page['title'],
                    'content': '\n'.join(content_parts)
                }
                content_sections.append(section)
                
                # Process child pages recursively
                for child in page.get('children', []):
                    process_page_hierarchy(child, level + 1)
            
            # Process all pages in the space
            for page in space['pages']:
                process_page_hierarchy(page)
            
            # Store for summary if needed
            if self.include_summary:
                self.all_confluence_content.extend(content_sections)
            
            # Create PDF
            filename = f"{self.label}_Confluence_{space['name'].replace(' ', '_')}_{self.export_date}.pdf"
            self.create_pdf(filename, f"Context Export - Confluence: {space['name']}", content_sections)

    def export_jira_content(self):
        """Export Jira content as PDFs with hierarchical structure"""
        print(f"📦 Starting Jira export for label '{self.label}'...")
        
        projects = self.search_jira_projects()
        
        if not projects:
            print(f"ℹ️  No Jira projects found with label '{self.label}'.")
            return
        
        total_issues = sum(len(project['issues']) for project in projects)
        print(f"📊 Found {len(projects)} projects with {total_issues} total issues to export")
        
        all_processed_issues = []
        all_skipped_fields_summary = {}
        
        for project in projects:
            if not project['issues']:
                continue
                
            print(f"📋 Processing Jira project: {project['name']} ({len(project['issues'])} issues)")
            
            content_sections = []
            project_skipped_fields = set()
            
            # Process issues in hierarchical order
            def process_issue_hierarchy(issue, level=0):
                print(f" Exporting {issue['key']} ({project['name']})")
                all_processed_issues.append(issue['key'])
                
                # Track skipped fields for this issue
                skipped_fields = self.track_skipped_fields(issue)
                project_skipped_fields.update(skipped_fields)
                
                # Format the issue with hierarchy
                formatted_issue = self.format_hierarchical_issue(issue, level)
                content_sections.append(formatted_issue)
                
                # Process children recursively
                for child in issue['children']:
                    process_issue_hierarchy(child, level + 1)
            
            # Process top-level issues (those without parents or with parents not in the result set)
            top_level_issues = [issue for issue in project['issues'] if issue['level'] == 0]
            for issue in top_level_issues:
                process_issue_hierarchy(issue)
            
            # Store for summary if needed
            if self.include_summary:
                self.all_jira_content.extend(content_sections)
            
            # Create PDF
            filename = f"{self.label}_Jira_{project['name'].replace(' ', '_')}_{self.export_date}.pdf"
            self.create_pdf(filename, f"Context Export - Jira: {project['name']}", content_sections)
            
            # Store skipped fields for this project
            all_skipped_fields_summary[project['name']] = sorted(project_skipped_fields)
            
            # Report skipped fields for this project
            if project_skipped_fields:
                print(f"  ⚠️  Skipped fields due to missing data: {', '.join(sorted(project_skipped_fields))}")
            else:
                print(f"  ✅ All requested fields were found and included")
        
        # Final comprehensive report
        print("\n" + "="*60)
        print("📊 JIRA EXPORT SUMMARY REPORT")
        print("="*60)
        
        # PDF filenames
        print(f"\n📄 PDF Files Created:")
        for project in projects:
            if project['issues']:
                filename = f"{self.label}_Jira_{project['name'].replace(' ', '_')}_{self.export_date}.pdf"
                print(f"  • {filename}")
        
        # Jira keys processed
        print(f"\n🔑 Jira Issues Processed ({len(all_processed_issues)} total):")
        for issue_key in sorted(all_processed_issues):
            print(f"  • {issue_key}")
        
        # Missing fields summary
        print(f"\n⚠️  Missing Fields Summary:")
        if all_skipped_fields_summary:
            for project_name, skipped_fields in all_skipped_fields_summary.items():
                if skipped_fields:
                    print(f"  📋 {project_name}:")
                    for field in skipped_fields:
                        print(f"    - {field}")
        else:
            print("  ✅ All requested fields were found across all projects")
        
        print("="*60)

    def format_hierarchical_issue(self, issue, level=0):
        """Format an issue with proper hierarchy indentation"""
        indent = "  " * level
        prefix = "#" * (level + 1)
        
        # Build the hierarchical title
        title = f"{prefix}{issue['key']}: {issue['summary']}"
        
        # Get formatted metadata sections
        metadata_sections = self.format_issue_metadata(issue)
        
        # Build comprehensive issue content
        content_parts = []
        
        # Section 1: Context Fields
        content_parts.append("## Context Fields")
        content_parts.extend(metadata_sections['context_fields'])
        content_parts.append("")  # Add spacing
        
        # Section 2: Description Fields
        content_parts.append("## Description Fields")
        content_parts.extend(metadata_sections['description_fields'])
        content_parts.append("")  # Add spacing
        
        # Additional sections
        # Attachments
        if issue['attachments']:
            attachments_text = self.format_attachments(issue['attachments'])
            content_parts.append(f"## Attachments\n{attachments_text}\n")
        
        # Comments
        if issue['comments']:
            comments_text = self.format_comments(issue['comments'])
            content_parts.append(f"## Comments\n{comments_text}\n")
        
        # Related Links
        if issue['issuelinks']:
            links_text = self.format_issue_links(issue['issuelinks'])
            content_parts.append(f"## Related Issues\n{links_text}\n")
        
        # Subtasks (only show direct subtasks, not nested ones)
        if issue['subtasks'] and level == 0:
            subtasks_text = self.format_subtasks(issue['subtasks'])
            content_parts.append(f"## Subtasks\n{subtasks_text}\n")
        
        # Issue URL footer
        content_parts.append(f"## Issue Details\n**Issue Key:** {issue['key']}\n**URL:** {issue['url']}")
        
        return {
            'title': title,
            'content': '\n'.join(content_parts),
            'level': level,
            'children': issue['children']
        }

    def create_summary_pdfs(self):
        """Create summary PDFs combining all Confluence and Jira content"""
        if not self.include_summary:
            return
            
        print("\n" + "="*60)
        print("📋 CREATING SUMMARY PDFS")
        print("="*60)
        
        # Create Confluence summary
        if self.all_confluence_content:
            confluence_filename = f"{self.label}_All_Confluence_Spaces_{self.export_date}.pdf"
            confluence_title = f"All Confluence Pages with label – {self.label}"
            print(f"📄 Creating Confluence summary: {confluence_filename}")
            self.create_pdf(confluence_filename, confluence_title, self.all_confluence_content)
        
        # Create Jira summary
        if self.all_jira_content:
            jira_filename = f"{self.label}_All_Jira_Projects_{self.export_date}.pdf"
            jira_title = f"All Jira Projects and tickets with label – {self.label}"
            print(f"📄 Creating Jira summary: {jira_filename}")
            self.create_pdf(jira_filename, jira_title, self.all_jira_content)
        
        print("✅ Summary PDFs created successfully!")
        print("="*60)

    def run_export(self):
        """Run the complete export process"""
        print("🚀 Starting Context Export Process")
        print(f"📅 Export Date: {self.export_date}")
        print(f"📁 Output Directory: {self.output_dir}")
        
        # High-level configuration logging
        print("\n▶️ Starting export configuration:")
        print(f"Label: {self.label}")
        print(f"Including Jira: {self.include_jira}")
        print(f"Including Confluence: {self.include_confluence}")
        print(f"Including summary exports: {self.include_summary}")
        if self.dry_run:
            print("🧪 DRY RUN MODE - No files will be created")
        print("-" * 50)
        
        # Run preflight diagnostics
        if not self.run_diagnostics():
            return
        
        # Export Confluence content (if enabled)
        if hasattr(self, 'include_confluence') and self.include_confluence:
            self.export_confluence_content()
        else:
            print("⏭️ Skipping Confluence export (not selected)")
        
        print("-" * 50)
        
        # Export Jira content (if enabled)
        if hasattr(self, 'include_jira') and self.include_jira:
            self.export_jira_content()
        else:
            print("⏭️ Skipping Jira export (not selected)")
        
        # Create summary PDFs if requested
        if self.include_summary:
            self.create_summary_pdfs()
        
        print("-" * 50)
        if self.dry_run:
            print("🧪 Dry run complete. No files exported.")
        else:
            print("✅ Context Export Process Complete!")
            print(f"📁 Check the '{self.output_dir}' directory for exported PDFs.")

def run_tests(self):
    """Run tests to check connectivity and count available content"""
    print("🧪 Starting export tests...")
    print(f"📅 Test Date: {self.export_date}")
    
    # High-level configuration logging
    print("\n▶️ Test configuration:")
    print(f"Label: {self.label}")
    print(f"Including Jira: {self.include_jira}")
    print(f"Including Confluence: {self.include_confluence}")
    print(f"Including summary exports: {self.include_summary}")
    print("-" * 50)
    
    # Run preflight diagnostics
    if not self.run_diagnostics():
        print("❌ Tests failed due to connectivity issues")
        return False
    
    confluence_results = None
    jira_results = None
    
    # Test Confluence if enabled
    if self.include_confluence:
        print("🔍 Testing Confluence search...")
        try:
            confluence_results = self.search_confluence_spaces()
            if confluence_results:
                total_pages = sum(len(space['pages']) for space in confluence_results)
                print(f"✅ Confluence test successful: {len(confluence_results)} spaces, {total_pages} pages")
            else:
                print("ℹ️  Confluence test: No spaces found with the specified label")
        except Exception as e:
            print(f"❌ Confluence test failed: {e}")
            confluence_results = None
    else:
        print("⏭️ Skipping Confluence test (not selected)")
    
    # Test Jira if enabled
    if self.include_jira:
        print("🚧 Testing Jira search...")
        try:
            jira_results = self.search_jira_projects()
            if jira_results:
                total_issues = sum(len(project['issues']) for project in jira_results)
                print(f"✅ Jira test successful: {len(jira_results)} projects, {total_issues} issues")
            else:
                print("ℹ️  Jira test: No projects found with the specified label")
        except Exception as e:
            print(f"❌ Jira test failed: {e}")
            jira_results = None
    else:
        print("⏭️ Skipping Jira test (not selected)")
    
    # Print test summary
    print("\n" + "="*50)
    print("✅ TEST COMPLETE")
    print("="*50)
    
    if confluence_results:
        total_confluence_pages = sum(len(space['pages']) for space in confluence_results)
        print(f"Confluence: {total_confluence_pages} pages across {len(confluence_results)} spaces")
    else:
        print("Confluence: No results")
    
    if jira_results:
        total_jira_issues = sum(len(project['issues']) for project in jira_results)
        print(f"Jira: {total_jira_issues} issues across {len(jira_results)} projects")
    else:
        print("Jira: No results")
    
    print("="*50)
    
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Context Exporter")
    parser.add_argument('--label', type=str, default="EasyPayExport", help='Label for export')
    parser.add_argument('--include-summary', action='store_true', help='Generate summary PDFs combining all content')
    parser.add_argument('--include-jira', action='store_true', help='Include Jira export')
    parser.add_argument('--include-confluence', action='store_true', help='Include Confluence export')
    parser.add_argument('--dry-run', action='store_true', help='Run diagnostics and list targets without creating PDFs')
    args = parser.parse_args()

    # Normalize label: strip spaces and lowercase
    label = args.label.strip().lower()

    print(f"🎯 Exporting content with label: {label}")
    exporter = ContextExporter(label, include_summary=args.include_summary, dry_run=args.dry_run)
    
    # Set export preferences
    exporter.include_jira = args.include_jira
    exporter.include_confluence = args.include_confluence
    
    # If no specific export type is specified, default to both
    if not args.include_jira and not args.include_confluence:
        exporter.include_jira = True
        exporter.include_confluence = True
        print("ℹ️  No export type specified, defaulting to both Jira and Confluence")
    
    exporter.run_export()

if __name__ == "__main__":
    main()