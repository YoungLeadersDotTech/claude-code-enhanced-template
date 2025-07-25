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
from bs4 import BeautifulSoup
import re

class ContextExporter:
    def __init__(self, label, confluence_url=None, jira_url=None, username=None, api_token=None, include_summary=False):
        self.label = label
        self.confluence_url = confluence_url or os.getenv('CONFLUENCE_URL')
        self.jira_url = jira_url or os.getenv('JIRA_URL')
        self.username = username or os.getenv('USERNAME')
        self.api_token = api_token or os.getenv('API_TOKEN')
        self.include_summary = include_summary
        
        # Create session with authentication
        self.session = requests.Session()
        if self.username and self.api_token:
            self.session.auth = (self.username, self.api_token)
        
        # Create output directory with date
        self.export_date = datetime.now().strftime('%Y_%m_%d')
        self.output_dir = f"exports/{label}/{self.export_date}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Store content for summary PDFs
        self.all_confluence_content = []
        self.all_jira_content = []

    def convert_html_to_text(self, html_content):
        """Convert HTML content to plain text"""
        if not html_content:
            return ""
        
        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text

    def get_confluence_page_info(self, page_id):
        """Get basic information about a Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'space,version,ancestors'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"❌ Error getting page info for {page_id}: {e}")
            return None

    def search_confluence_spaces(self):
        """Search for Confluence spaces with pages labeled with specified label, with pagination"""
        if not self.confluence_url:
            print("⚠️  Confluence URL not configured. Skipping Confluence export.")
            return []
        
        try:
            # First, get all spaces
            spaces_url = f"{self.confluence_url}/rest/api/space"
            spaces_response = self.session.get(spaces_url)
            spaces_response.raise_for_status()
            spaces_data = spaces_response.json()
            
            all_spaces = []
            start = 0
            limit = 25
            
            while True:
                spaces_url = f"{self.confluence_url}/rest/api/space?start={start}&limit={limit}"
                spaces_response = self.session.get(spaces_url)
                spaces_response.raise_for_status()
                spaces_data = spaces_response.json()
                
                batch = spaces_data.get('results', [])
                if not batch:
                    break
                
                all_spaces.extend(batch)
                if len(batch) < limit:
                    break
                start += limit
            
            print(f"Found {len(all_spaces)} Confluence spaces")
            
            # Search for pages with the label in each space
            spaces_with_pages = []
            
            for space in all_spaces:
                space_key = space['key']
                space_name = space['name']
                
                print(f"�� Searching space: {space_name} ({space_key})")
                
                # Search for pages with the label
                search_url = f"{self.confluence_url}/rest/api/content/search"
                batch_size = 100
                start_at = 0
                all_pages = []
                
                while True:
                    payload = {
                        'cql': f'space = "{space_key}" AND label = "{self.label}"',
                        'limit': batch_size,
                        'start': start_at,
                        'expand': 'space,version,ancestors'
                    }
                    
                    response = self.session.post(search_url, json=payload)
                    response.raise_for_status()
                    results = response.json()
                    
                    batch = results.get('results', [])
                    print(f"  Found {len(batch)} pages in batch (starting at {start_at})")
                    
                    if not batch:
                        break
                    
                    all_pages.extend(batch)
                    if len(batch) < batch_size:
                        break
                    start_at += batch_size
                
                if all_pages:
                    print(f"  ✅ Found {len(all_pages)} total pages with label '{self.label}' in space '{space_name}'")
                    
                    # Process each page and get its children
                    processed_pages = []
                    exported_page_ids = set()
                    
                    for page in all_pages:
                        if page['id'] not in exported_page_ids:
                            processed_pages.append(page)
                            exported_page_ids.add(page['id'])
                            
                            # Get child pages recursively (up to 4 levels deep)
                            self.fetch_child_pages_recursive(page['id'], processed_pages, exported_page_ids, 1, 4)
                    
                    # Sort pages by their natural order in the tree
                    processed_pages = self.sort_pages_in_tree_order(processed_pages)
                    
                    spaces_with_pages.append({
                        'key': space_key,
                        'name': space_name,
                        'pages': processed_pages
                    })
                else:
                    print(f"  ℹ️  No pages found with label '{self.label}' in space '{space_name}'")
            
            return spaces_with_pages
            
        except Exception as e:
            print(f"❌ Error searching Confluence: {e}")
            return []

    def sort_pages_in_tree_order(self, pages):
        """Sort pages to maintain their natural tree order"""
        # Create a map of page ID to page object
        page_map = {page['id']: page for page in pages}
        
        # Build parent-child relationships
        for page in pages:
            page['children'] = []
            page['level'] = 0
        
        # Establish parent-child relationships
        for page in pages:
            ancestors = page.get('ancestors', [])
            if ancestors:
                parent_id = ancestors[-1]['id']
                if parent_id in page_map:
                    parent = page_map[parent_id]
                    parent['children'].append(page)
                    page['level'] = parent['level'] + 1
        
        # Sort pages by level and then by position/title
        def sort_pages_recursive(page_list):
            return sorted(page_list, key=lambda x: (x['level'], x.get('position', 0), x['title']))
        
        # Sort all pages and their children
        for page in pages:
            if page['children']:
                page['children'] = sort_pages_recursive(page['children'])
        
        # Return top-level pages (level 0)
        return sort_pages_recursive([page for page in pages if page['level'] == 0])

    def process_smart_links_in_page(self, page_id, pages_list, exported_page_ids, level):
        """Process smart links in a page and add linked pages to the list"""
        if level > 4:  # Limit recursion depth
            return
        
        try:
            # Get page content to look for smart links
            content_url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage'
            }
            
            response = self.session.get(content_url, params=params)
            response.raise_for_status()
            page_data = response.json()
            
            body_content = page_data.get('body', {}).get('storage', {}).get('value', '')
            
            # Look for smart links (Confluence page links)
            # Pattern: [Page Title|Page Title] or [Page Title]
            smart_link_pattern = r'\[([^|\]]+)(?:\|[^\]]+)?\]'
            matches = re.findall(smart_link_pattern, body_content)
            
            for match in matches:
                page_title = match.strip()
                
                # Search for pages with this title in the same space
                space_key = page_data['space']['key']
                search_url = f"{self.confluence_url}/rest/api/content/search"
                
                payload = {
                    'cql': f'space = "{space_key}" AND title = "{page_title}"',
                    'limit': 10
                }
                
                try:
                    search_response = self.session.post(search_url, json=payload)
                    search_response.raise_for_status()
                    search_results = search_response.json()
                    
                    for result in search_results.get('results', []):
                        if result['id'] not in exported_page_ids:
                            pages_list.append(result)
                            exported_page_ids.add(result['id'])
                            
                            # Recursively process smart links in this page
                            self.process_smart_links_in_page(result['id'], pages_list, exported_page_ids, level + 1)
                            
                except Exception as e:
                    print(f"⚠️  Error searching for smart link '{page_title}': {e}")
                    
        except Exception as e:
            print(f"⚠️  Error processing smart links in page {page_id}: {e}")

    def fetch_child_pages_recursive(self, parent_id, pages_list, exported_page_ids, level, max_level):
        """Recursively fetch child pages up to max_level depth with natural tree sorting"""
        if level > max_level:
            return
        
        try:
            # Get child pages
            child_url = f"{self.confluence_url}/rest/api/content/{parent_id}/child/page"
            params = {
                'expand': 'space,version,ancestors',
                'limit': 100
            }
            
            response = self.session.get(child_url, params=params)
            response.raise_for_status()
            child_data = response.json()
            
            child_pages = child_data.get('results', [])
            
            if child_pages:
                print(f"    Found {len(child_pages)} child pages at level {level}")
                
                # Sort child pages by position if available, otherwise by title
                child_pages.sort(key=lambda x: (x.get('position', 0), x['title']))
                
                for child_page in child_pages:
                    if child_page['id'] not in exported_page_ids:
                        pages_list.append(child_page)
                        exported_page_ids.add(child_page['id'])
                        
                        # Recursively fetch children of this child page
                        self.fetch_child_pages_recursive(child_page['id'], pages_list, exported_page_ids, level + 1, max_level)
                        
        except Exception as e:
            print(f"⚠️  Error fetching child pages for {parent_id}: {e}")

    def get_confluence_page_content(self, page_id):
        """Get the content of a Confluence page"""
        try:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage,space,version'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
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
            batch_size = 100
            start_at = 0
            total = None
            all_issues = []
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
                
                issue_data = {
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                    'status': issue['fields']['status']['name'],
                    'assignee': issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else 'Unassigned',
                    'reporter': issue['fields']['reporter']['displayName'] if issue['fields']['reporter'] else 'Unknown',
                    'priority': issue['fields']['priority']['name'] if issue['fields']['priority'] else 'None',
                    'labels': issue['fields']['labels'],
                    'components': [comp['name'] for comp in issue['fields']['components']],
                    'fix_versions': [ver['name'] for ver in issue['fields']['fixVersions']],
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
            
            return list(projects.values())
        except Exception as e:
            print(f"❌ Error searching Jira: {e}")
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