#!/usr/bin/env python3
"""
Checkpoint manager for saving and resuming export progress
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
import hashlib
import shutil

from structured_logger import StructuredLogger


@dataclass
class ExportState:
    """Represents the current state of an export operation"""
    export_id: str
    label: str
    export_date: str
    started_at: str
    last_updated: str
    profile: str
    
    # Progress tracking
    confluence_spaces_completed: List[str]
    confluence_pages_exported: Set[str]
    jira_projects_completed: List[str]
    jira_issues_exported: Set[str]
    
    # Current position
    current_operation: Optional[str] = None  # 'confluence', 'jira', or None
    current_space_key: Optional[str] = None
    current_project_key: Optional[str] = None
    current_batch_start: int = 0
    
    # Statistics
    total_confluence_pages: int = 0
    total_jira_issues: int = 0
    errors_encountered: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Convert lists to sets for efficient lookups
        if isinstance(self.confluence_pages_exported, list):
            self.confluence_pages_exported = set(self.confluence_pages_exported)
        if isinstance(self.jira_issues_exported, list):
            self.jira_issues_exported = set(self.jira_issues_exported)
        if self.errors_encountered is None:
            self.errors_encountered = []
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert sets to lists for JSON serialization
        data['confluence_pages_exported'] = list(self.confluence_pages_exported)
        data['jira_issues_exported'] = list(self.jira_issues_exported)
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportState':
        """Create from dictionary"""
        return cls(**data)


class CheckpointManager:
    """Manages checkpoints for resumable exports"""
    
    def __init__(self, checkpoint_dir: str, logger: StructuredLogger):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.current_state: Optional[ExportState] = None
        self.checkpoint_file: Optional[Path] = None
        self.save_counter = 0
        self.checkpoint_interval = 10
        
    def create_export_id(self, label: str, export_date: str) -> str:
        """Create a unique export ID"""
        timestamp = datetime.now().isoformat()
        data = f"{label}:{export_date}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
        
    def start_new_export(self, label: str, export_date: str, profile: str) -> ExportState:
        """Start a new export session"""
        export_id = self.create_export_id(label, export_date)
        
        self.current_state = ExportState(
            export_id=export_id,
            label=label,
            export_date=export_date,
            started_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            profile=profile,
            confluence_spaces_completed=[],
            confluence_pages_exported=set(),
            jira_projects_completed=[],
            jira_issues_exported=set()
        )
        
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint_{export_id}.json"
        self.save_checkpoint()
        
        self.logger.info(
            "Started new export session",
            export_id=export_id,
            label=label,
            profile=profile
        )
        
        return self.current_state
        
    def resume_export(self, checkpoint_file: str) -> Optional[ExportState]:
        """Resume an export from a checkpoint file"""
        try:
            checkpoint_path = Path(checkpoint_file)
            if not checkpoint_path.exists():
                checkpoint_path = self.checkpoint_dir / checkpoint_file
                
            if not checkpoint_path.exists():
                self.logger.error(f"Checkpoint file not found: {checkpoint_file}")
                return None
                
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
                
            self.current_state = ExportState.from_dict(data)
            self.checkpoint_file = checkpoint_path
            
            self.logger.info(
                "Resumed export session",
                export_id=self.current_state.export_id,
                confluence_pages_completed=len(self.current_state.confluence_pages_exported),
                jira_issues_completed=len(self.current_state.jira_issues_exported)
            )
            
            return self.current_state
            
        except Exception as e:
            self.logger.exception(f"Failed to resume from checkpoint: {e}")
            return None
            
    def find_latest_checkpoint(self, label: str) -> Optional[Path]:
        """Find the most recent checkpoint for a given label"""
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    
                if data.get('label') == label:
                    checkpoints.append({
                        'file': checkpoint_file,
                        'last_updated': data.get('last_updated', ''),
                        'started_at': data.get('started_at', '')
                    })
            except:
                continue
                
        if not checkpoints:
            return None
            
        # Sort by last_updated timestamp
        checkpoints.sort(key=lambda x: x['last_updated'], reverse=True)
        return checkpoints[0]['file']
        
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints"""
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    
                checkpoints.append({
                    'file': checkpoint_file.name,
                    'export_id': data.get('export_id'),
                    'label': data.get('label'),
                    'started_at': data.get('started_at'),
                    'last_updated': data.get('last_updated'),
                    'profile': data.get('profile'),
                    'confluence_progress': len(data.get('confluence_pages_exported', [])),
                    'jira_progress': len(data.get('jira_issues_exported', []))
                })
            except Exception as e:
                self.logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
                
        return checkpoints
        
    def save_checkpoint(self, force: bool = False):
        """Save current state to checkpoint file"""
        if not self.current_state or not self.checkpoint_file:
            return
            
        self.save_counter += 1
        
        # Only save at intervals unless forced
        if not force and self.save_counter % self.checkpoint_interval != 0:
            return
            
        try:
            self.current_state.last_updated = datetime.now().isoformat()
            
            # Write to temporary file first
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.current_state.to_dict(), f, indent=2)
                
            # Atomically replace the checkpoint file
            temp_file.replace(self.checkpoint_file)
            
            self.logger.debug(
                "Saved checkpoint",
                export_id=self.current_state.export_id,
                confluence_progress=len(self.current_state.confluence_pages_exported),
                jira_progress=len(self.current_state.jira_issues_exported)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            
    def update_confluence_progress(self, space_key: str, page_id: str):
        """Update Confluence export progress"""
        if not self.current_state:
            return
            
        self.current_state.current_operation = 'confluence'
        self.current_state.current_space_key = space_key
        self.current_state.confluence_pages_exported.add(page_id)
        
        # Save checkpoint periodically
        self.save_checkpoint()
        
    def mark_confluence_space_complete(self, space_key: str):
        """Mark a Confluence space as completely exported"""
        if not self.current_state:
            return
            
        if space_key not in self.current_state.confluence_spaces_completed:
            self.current_state.confluence_spaces_completed.append(space_key)
            
        self.save_checkpoint(force=True)
        
    def update_jira_progress(self, project_key: str, issue_key: str):
        """Update Jira export progress"""
        if not self.current_state:
            return
            
        self.current_state.current_operation = 'jira'
        self.current_state.current_project_key = project_key
        self.current_state.jira_issues_exported.add(issue_key)
        
        # Save checkpoint periodically
        self.save_checkpoint()
        
    def mark_jira_project_complete(self, project_key: str):
        """Mark a Jira project as completely exported"""
        if not self.current_state:
            return
            
        if project_key not in self.current_state.jira_projects_completed:
            self.current_state.jira_projects_completed.append(project_key)
            
        self.save_checkpoint(force=True)
        
    def record_error(self, error_type: str, error_message: str, context: Dict[str, Any]):
        """Record an error in the checkpoint"""
        if not self.current_state:
            return
            
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context
        }
        
        self.current_state.errors_encountered.append(error_entry)
        self.save_checkpoint(force=True)
        
    def is_confluence_page_exported(self, page_id: str) -> bool:
        """Check if a Confluence page has already been exported"""
        return self.current_state and page_id in self.current_state.confluence_pages_exported
        
    def is_jira_issue_exported(self, issue_key: str) -> bool:
        """Check if a Jira issue has already been exported"""
        return self.current_state and issue_key in self.current_state.jira_issues_exported
        
    def is_confluence_space_complete(self, space_key: str) -> bool:
        """Check if a Confluence space has been completely exported"""
        return self.current_state and space_key in self.current_state.confluence_spaces_completed
        
    def is_jira_project_complete(self, project_key: str) -> bool:
        """Check if a Jira project has been completely exported"""
        return self.current_state and project_key in self.current_state.jira_projects_completed
        
    def get_resume_position(self) -> Dict[str, Any]:
        """Get the position to resume from"""
        if not self.current_state:
            return {}
            
        return {
            'operation': self.current_state.current_operation,
            'confluence_space': self.current_state.current_space_key,
            'jira_project': self.current_state.current_project_key,
            'batch_start': self.current_state.current_batch_start,
            'confluence_completed': self.current_state.confluence_spaces_completed,
            'jira_completed': self.current_state.jira_projects_completed
        }
        
    def complete_export(self):
        """Mark the export as complete and clean up"""
        if not self.current_state:
            return
            
        self.current_state.current_operation = None
        self.save_checkpoint(force=True)
        
        # Create a completion marker file
        completion_file = self.checkpoint_file.with_suffix('.complete')
        completion_data = {
            'export_id': self.current_state.export_id,
            'completed_at': datetime.now().isoformat(),
            'total_confluence_pages': len(self.current_state.confluence_pages_exported),
            'total_jira_issues': len(self.current_state.jira_issues_exported),
            'errors_count': len(self.current_state.errors_encountered)
        }
        
        with open(completion_file, 'w') as f:
            json.dump(completion_data, f, indent=2)
            
        self.logger.info(
            "Export completed",
            export_id=self.current_state.export_id,
            total_confluence_pages=len(self.current_state.confluence_pages_exported),
            total_jira_issues=len(self.current_state.jira_issues_exported),
            errors_count=len(self.current_state.errors_encountered)
        )
        
    def cleanup_old_checkpoints(self, days_to_keep: int = 7):
        """Clean up old checkpoint files"""
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 86400)
        
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    # Check if it has a completion marker
                    completion_file = checkpoint_file.with_suffix('.complete')
                    if completion_file.exists():
                        checkpoint_file.unlink()
                        completion_file.unlink()
                        self.logger.info(f"Cleaned up old checkpoint: {checkpoint_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up checkpoint {checkpoint_file}: {e}")