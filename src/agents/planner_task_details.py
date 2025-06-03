"""Task details management for the planner system."""
from __future__ import annotations

import os
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TaskDetail:
    """Represents a detailed task with objectives, tasks, and acceptance criteria."""
    id: str
    title: str
    objective: str
    tasks: List[str]
    acceptance_criteria: List[str]
    issue_description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskDetail':
        """Create TaskDetail from dictionary."""
        return cls(
            id=data['id'],
            title=data['title'],
            objective=data.get('objective', data.get('issue_description', '')),  # Use issue_description as fallback
            tasks=data.get('tasks', []),
            acceptance_criteria=data.get('acceptance_criteria', []),
            issue_description=data.get('issue_description')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskDetail to dictionary."""
        result = {
            'id': self.id,
            'title': self.title,
            'objective': self.objective,
            'tasks': self.tasks,
            'acceptance_criteria': self.acceptance_criteria
        }
        if self.issue_description:
            result['issue_description'] = self.issue_description
        return result


def _load_yaml(path: str) -> Any:
    """Load YAML file with error handling."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _save_yaml(path: str, data: Any) -> None:
    """Save data to a YAML file."""
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_task_details(paths: Optional[Dict[str, str]] = None) -> List[TaskDetail]:
    """Load all task details from YAML file."""
    if paths is None:
        paths = {'task_details': 'data/task_details.yaml'}
    
    try:
        task_details_data = _load_yaml(paths["task_details"])
        if task_details_data is None:
            return []
        
        if not isinstance(task_details_data, list):
            raise ValueError("Task details file must contain a list")
        
        return [TaskDetail.from_dict(item) for item in task_details_data]
    
    except Exception as e:
        raise ValueError(f"Error loading task details: {str(e)}")


def save_task_details(task_details: List[TaskDetail], paths: Optional[Dict[str, str]] = None) -> None:
    """Save task details to YAML file."""
    if paths is None:
        paths = {'task_details': 'data/task_details.yaml'}
    
    try:
        data = [detail.to_dict() for detail in task_details]
        _save_yaml(paths["task_details"], data)
    except Exception as e:
        raise ValueError(f"Error saving task details: {str(e)}")


def get_task_detail_by_id(task_id: str, paths: Optional[Dict[str, str]] = None) -> Optional[TaskDetail]:
    """Get task detail by ID."""
    try:
        task_details = load_task_details(paths)
        for detail in task_details:
            if detail.id == task_id:
                return detail
        return None
    except Exception:
        return None


def get_enhanced_task_info(task_id: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Get enhanced task information combining basic task and detailed information."""
    if paths is None:
        paths = {
            'tasks': 'data/tasks.yaml',
            'task_details': 'data/task_details.yaml'
        }
    
    result = {
        'basic_task': None,
        'task_detail': None,
        'has_details': False,
        'error': None
    }
    
    try:
        # Load basic task info
        tasks = _load_yaml(paths["tasks"]) or []
        basic_task = None
        for task in tasks:
            if task.get('id') == task_id:
                basic_task = task
                break
        
        result['basic_task'] = basic_task
        
        # Load detailed task info
        task_detail = get_task_detail_by_id(task_id, paths)
        result['task_detail'] = task_detail
        result['has_details'] = task_detail is not None
        
        return result
    
    except Exception as e:
        result['error'] = str(e)
        return result


def create_task_detail(
    task_id: str,
    title: str,
    objective: str,
    tasks: List[str],
    acceptance_criteria: List[str],
    paths: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a new task detail entry."""
    if paths is None:
        paths = {'task_details': 'data/task_details.yaml'}
    
    try:
        # Load existing task details
        task_details = load_task_details(paths)
        
        # Check if task detail with this ID already exists
        for detail in task_details:
            if detail.id == task_id:
                return {"error": f"Task detail with ID '{task_id}' already exists"}
        
        # Create new task detail
        new_detail = TaskDetail(
            id=task_id,
            title=title,
            objective=objective,
            tasks=tasks,
            acceptance_criteria=acceptance_criteria
        )
        
        # Add to list and save
        task_details.append(new_detail)
        save_task_details(task_details, paths)
        
        return {"success": True, "task_detail": new_detail.to_dict()}
    
    except Exception as e:
        return {"error": str(e)}


def update_task_detail(
    task_id: str,
    updates: Dict[str, Any],
    paths: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Update an existing task detail."""
    if paths is None:
        paths = {'task_details': 'data/task_details.yaml'}
    
    try:
        # Load existing task details
        task_details = load_task_details(paths)
        
        # Find the task detail to update
        detail_to_update = None
        for i, detail in enumerate(task_details):
            if detail.id == task_id:
                detail_to_update = detail
                detail_index = i
                break
        
        if not detail_to_update:
            return {"error": f"Task detail with ID '{task_id}' not found"}
        
        # Update fields
        updated_fields = []
        if 'title' in updates:
            detail_to_update.title = updates['title']
            updated_fields.append('title')
        
        if 'objective' in updates:
            detail_to_update.objective = updates['objective']
            updated_fields.append('objective')
        
        if 'tasks' in updates:
            detail_to_update.tasks = updates['tasks']
            updated_fields.append('tasks')
        
        if 'acceptance_criteria' in updates:
            detail_to_update.acceptance_criteria = updates['acceptance_criteria']
            updated_fields.append('acceptance_criteria')
        
        # Save updated task details
        save_task_details(task_details, paths)
        
        return {
            "success": True,
            "task_detail": detail_to_update.to_dict(),
            "updated_fields": updated_fields
        }
    
    except Exception as e:
        return {"error": str(e)}


def delete_task_detail(task_id: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Delete a task detail by ID."""
    if paths is None:
        paths = {'task_details': 'data/task_details.yaml'}
    
    try:
        # Load existing task details
        task_details = load_task_details(paths)
        
        # Find and remove the task detail
        original_count = len(task_details)
        task_details = [detail for detail in task_details if detail.id != task_id]
        
        if len(task_details) == original_count:
            return {"error": f"Task detail with ID '{task_id}' not found"}
        
        # Save updated task details
        save_task_details(task_details, paths)
        
        return {"success": True, "message": f"Task detail '{task_id}' deleted successfully"}
    
    except Exception as e:
        return {"error": str(e)}


def list_tasks_with_details(paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """List all tasks with their detail status."""
    if paths is None:
        paths = {
            'tasks': 'data/tasks.yaml',
            'task_details': 'data/task_details.yaml'
        }
    
    try:
        # Load basic tasks
        tasks = _load_yaml(paths["tasks"]) or []
        
        # Load task details
        task_details = load_task_details(paths)
        detail_ids = {detail.id for detail in task_details}
        
        # Combine information
        result = []
        for task in tasks:
            task_id = task.get('id', '')
            has_details = task_id in detail_ids
            
            result.append({
                'id': task_id,
                'title': task.get('title', ''),
                'priority': task.get('priority', ''),
                'status': task.get('status', ''),
                'due_date': task.get('due_date', ''),
                'has_details': has_details
            })
        
        return {"success": True, "tasks": result}
    
    except Exception as e:
        return {"error": str(e)}


def get_task_progress_summary(task_id: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Get a comprehensive progress summary for a task with details."""
    enhanced_info = get_enhanced_task_info(task_id, paths)
    
    if enhanced_info['error']:
        return {"error": enhanced_info['error']}
    
    if not enhanced_info['basic_task']:
        return {"error": f"Task '{task_id}' not found"}
    
    basic_task = enhanced_info['basic_task']
    task_detail = enhanced_info['task_detail']
    
    summary = {
        'task_id': task_id,
        'title': basic_task.get('title', ''),
        'status': basic_task.get('status', ''),
        'priority': basic_task.get('priority', ''),
        'due_date': basic_task.get('due_date', ''),
        'has_detailed_breakdown': enhanced_info['has_details']
    }
    
    if task_detail:
        summary.update({
            'objective': task_detail.objective,
            'subtasks_count': len(task_detail.tasks),
            'subtasks': task_detail.tasks,
            'acceptance_criteria_count': len(task_detail.acceptance_criteria),
            'acceptance_criteria': task_detail.acceptance_criteria
        })
    
    return {"success": True, "summary": summary}


def format_task_detail_markdown(task_id: str, paths: Optional[Dict[str, str]] = None) -> str:
    """Format task detail as markdown for display."""
    enhanced_info = get_enhanced_task_info(task_id, paths)
    
    if enhanced_info['error']:
        return f"Error: {enhanced_info['error']}"
    
    if not enhanced_info['basic_task']:
        return f"Task '{task_id}' not found"
    
    basic_task = enhanced_info['basic_task']
    task_detail = enhanced_info['task_detail']
    
    markdown = f"# Task {task_id}: {basic_task.get('title', '')}\n\n"
    markdown += f"**Status:** {basic_task.get('status', 'N/A')}\n"
    markdown += f"**Priority:** {basic_task.get('priority', 'N/A')}\n"
    markdown += f"**Due Date:** {basic_task.get('due_date', 'N/A')}\n\n"
    
    if task_detail:
        markdown += f"## Objective\n{task_detail.objective}\n\n"
        
        if task_detail.tasks:
            markdown += "## Tasks\n"
            for i, task in enumerate(task_detail.tasks, 1):
                markdown += f"{i}. {task}\n"
            markdown += "\n"
        
        if task_detail.acceptance_criteria:
            markdown += "## Acceptance Criteria\n"
            for criterion in task_detail.acceptance_criteria:
                if isinstance(criterion, dict):
                    # Handle nested structure
                    for key, value in criterion.items():
                        markdown += f"**{key}:**\n"
                        if isinstance(value, list):
                            for item in value:
                                markdown += f"- {item}\n"
                        else:
                            markdown += f"- {value}\n"
                        markdown += "\n"
                else:
                    markdown += f"- {criterion}\n"
            markdown += "\n"
    else:
        markdown += "*No detailed breakdown available for this task.*\n"
    
    return markdown