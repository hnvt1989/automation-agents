"""Task brainstorming functionality using RAG and LLM capabilities."""
from __future__ import annotations

import os
import re
import yaml
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agents.rag import RAGAgent
from src.storage.chromadb_client import get_chromadb_client
from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings
from src.agents.enhanced_rag import (
    extract_key_terms,
    generate_search_queries,
    deduplicate_contexts,
    calculate_relevance_score,
    rank_contexts_by_relevance,
    get_enhanced_rag_context
)


@dataclass
class TaskBrainstorm:
    """Represents a brainstorming session for a task."""
    task_id: str
    task_title: str
    brainstorm_type: str  # 'initial', 'improved', 'updated', etc.
    generated_at: datetime
    content: Dict[str, Any]  # Structured brainstorm content
    rag_context: List[str]   # Context retrieved from RAG
    sources: List[str]       # Sources used for brainstorming
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'brainstorm_type': self.brainstorm_type,
            'generated_at': self.generated_at.isoformat(),
            'content': self.content,
            'rag_context': self.rag_context,
            'sources': self.sources
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskBrainstorm':
        """Create from dictionary."""
        return cls(
            task_id=data['task_id'],
            task_title=data['task_title'],
            brainstorm_type=data['brainstorm_type'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            content=data['content'],
            rag_context=data['rag_context'],
            sources=data['sources']
        )
    
    def to_markdown(self) -> str:
        """Convert brainstorm to markdown format."""
        md_lines = []
        
        # Header
        md_lines.append(f"## Brainstorm: {self.task_title} ({self.task_id})")
        md_lines.append("")
        md_lines.append(f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"**Type:** {self.brainstorm_type}")
        md_lines.append("")
        
        # Overview
        if 'overview' in self.content:
            md_lines.append("### Overview")
            md_lines.append(self.content['overview'])
            md_lines.append("")
        
        # Key Considerations
        if 'considerations' in self.content and self.content['considerations']:
            md_lines.append("### Key Considerations")
            for consideration in self.content['considerations']:
                md_lines.append(f"- {consideration}")
            md_lines.append("")
        
        # Potential Approaches
        if 'approaches' in self.content and self.content['approaches']:
            md_lines.append("### Potential Approaches")
            for approach in self.content['approaches']:
                md_lines.append(f"- {approach}")
            md_lines.append("")
        
        # Risks and Challenges
        if 'risks' in self.content and self.content['risks']:
            md_lines.append("### Risks and Challenges")
            for risk in self.content['risks']:
                md_lines.append(f"- {risk}")
            md_lines.append("")
        
        # Recommendations
        if 'recommendations' in self.content and self.content['recommendations']:
            md_lines.append("### Recommendations")
            for recommendation in self.content['recommendations']:
                md_lines.append(f"- {recommendation}")
            md_lines.append("")
        
        # RAG Context
        if self.rag_context:
            md_lines.append("### RAG Context Used")
            for context in self.rag_context:
                md_lines.append(f"- {context}")
            md_lines.append("")
        
        # Sources
        if self.sources:
            md_lines.append("### Sources")
            for source in self.sources:
                md_lines.append(f"- {source}")
            md_lines.append("")
        
        md_lines.append("---")
        md_lines.append("")
        
        return "\n".join(md_lines)


def _load_yaml(path: str) -> Any:
    """Load YAML file with error handling."""
    if not os.path.exists(path):
        log_warning(f"YAML file not found: {path}")
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or []
    except Exception as e:
        log_error(f"Error loading YAML file {path}: {str(e)}")
        return []


def parse_brainstorm_query(query: str) -> Optional[Dict[str, str]]:
    """Parse brainstorm query to extract task identifier and action."""
    query_lower = query.lower().strip()
    
    # Check for brainstorm-related keywords
    if 'brainstorm' not in query_lower:
        return None
    
    # Determine action type
    action = 'brainstorm'  # default
    if any(word in query_lower for word in ['replace', 'improve', 'update', 'redo']):
        for word in ['replace', 'improve', 'update', 'redo']:
            if word in query_lower:
                action = word
                break
    
    # Extract title patterns first (more specific)
    title_patterns = [
        r'title\s+["\']([^"\']+)["\']',
        r'with\s+title\s+([^,\n]+?)(?:\s*$)',
        r'title\s+([^,\n]+?)(?:\s*$)'
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            if title and not re.match(r'^[A-Z0-9-]+$', title):  # Not just an ID
                return {
                    'type': 'title',
                    'value': title,
                    'action': action
                }
    
    # Extract task ID patterns (less specific, check after title)
    id_patterns = [
        r'\bid\s+([A-Z0-9-]+)',
        r'\btask\s+([A-Z0-9-]+)',
        r'\bfor\s+task\s+([A-Z0-9-]+)',
        r'\b([A-Z0-9-]+)\s*$',  # ID at the end
        r'\b(\d{6})\b'  # 6-digit numbers
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return {
                'type': 'id',
                'value': match.group(1),
                'action': action
            }
    
    return None


def find_task_by_query(query_type: str, query_value: str, 
                      paths: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Find task by ID or title."""
    if paths is None:
        paths = {
            'tasks': 'data/tasks.yaml',
            'task_details': 'data/task_details.yaml'
        }
    
    # Load tasks and task details
    tasks = _load_yaml(paths['tasks'])
    task_details = _load_yaml(paths['task_details'])
    
    # Create lookup dictionary for task details
    details_lookup = {detail.get('id'): detail for detail in task_details}
    
    if query_type == 'id':
        # Find by exact ID match
        for task in tasks:
            if task.get('id') == query_value:
                return {
                    'basic_task': task,
                    'task_detail': details_lookup.get(task.get('id'))
                }
    
    elif query_type == 'title':
        query_lower = query_value.lower()
        
        # Try exact title match first
        for task in tasks:
            if task.get('title', '').lower() == query_lower:
                return {
                    'basic_task': task,
                    'task_detail': details_lookup.get(task.get('id'))
                }
        
        # Try partial title match
        for task in tasks:
            if query_lower in task.get('title', '').lower():
                return {
                    'basic_task': task,
                    'task_detail': details_lookup.get(task.get('id'))
                }
    
    return None


async def generate_brainstorm_content(task_info: Dict[str, Any], 
                                     brainstorm_type: str = 'initial') -> Optional[TaskBrainstorm]:
    """Generate brainstorm content using RAG and LLM."""
    try:
        basic_task = task_info['basic_task']
        task_detail = task_info.get('task_detail')
        
        task_id = basic_task['id']
        task_title = basic_task['title']
        
        log_info(f"Generating brainstorm for task {task_id}: {task_title}")
        
        # Step 1: Gather enhanced context from RAG
        rag_context = []
        sources = []
        
        try:
            # Use enhanced RAG context retrieval
            enhanced_contexts = await get_enhanced_rag_context(task_info, max_contexts=5)
            
            # Extract content and sources from enhanced contexts
            for ctx in enhanced_contexts:
                content = ctx.get('content', '')
                if content:
                    rag_context.append(content)
                    
                    # Add source information
                    metadata = ctx.get('metadata', {})
                    source = metadata.get('source', 'RAG search')
                    relevance = ctx.get('relevance_score', 0)
                    sources.append(f"{source} (relevance: {relevance:.2f})")
            
            log_info(f"Retrieved {len(rag_context)} enhanced RAG contexts")
        
        except Exception as e:
            log_warning(f"Enhanced RAG retrieval failed: {str(e)}")
            # Fall back to basic search if enhanced fails
            try:
                # Initialize RAG agent with configured API key
                settings = get_settings()
                provider = OpenAIProvider(
                    base_url=settings.base_url,
                    api_key=settings.llm_api_key
                )
                model = OpenAIModel('gpt-4o-mini', provider=provider)
                rag_agent = RAGAgent(model)
                
                # Basic search with just the title
                rag_result = await rag_agent.run(
                    f"Find relevant information about: {task_title}",
                    deps=None
                )
                
                if hasattr(rag_result, 'data') and rag_result.data:
                    rag_context.append(str(rag_result.data))
                    sources.append(f"RAG search: {task_title}")
            except Exception as e2:
                log_error(f"Fallback RAG search also failed: {str(e2)}")
        
        # Step 2: Generate brainstorm using LLM
        try:
            # Prepare context for LLM
            context_parts = []
            
            # Basic task info
            context_parts.append(f"Task ID: {task_id}")
            context_parts.append(f"Task Title: {task_title}")
            context_parts.append(f"Task Status: {basic_task.get('status', 'N/A')}")
            context_parts.append(f"Task Priority: {basic_task.get('priority', 'N/A')}")
            
            # Detailed task info if available
            if task_detail:
                if task_detail.get('objective'):
                    context_parts.append(f"Objective: {task_detail['objective']}")
                
                if task_detail.get('tasks'):
                    context_parts.append("Subtasks:")
                    for i, subtask in enumerate(task_detail['tasks'], 1):
                        context_parts.append(f"  {i}. {subtask}")
                
                if task_detail.get('acceptance_criteria'):
                    context_parts.append("Acceptance Criteria:")
                    for i, criteria in enumerate(task_detail['acceptance_criteria'], 1):
                        if isinstance(criteria, dict):
                            for key, value in criteria.items():
                                context_parts.append(f"  {i}. {key}")
                                if isinstance(value, list):
                                    for item in value:
                                        context_parts.append(f"     - {item}")
                                else:
                                    context_parts.append(f"     - {value}")
                        else:
                            context_parts.append(f"  {i}. {criteria}")
            
            # Enhanced RAG context with relevance info
            if rag_context:
                context_parts.append("Relevant Context from Knowledge Base (ranked by relevance):")
                for i, context in enumerate(rag_context, 1):
                    # Truncate long contexts for prompt
                    truncated = context[:500] + "..." if len(context) > 500 else context
                    context_parts.append(f"  {i}. {truncated}")
            
            task_context = "\n".join(context_parts)
            
            # Create brainstorming prompt
            brainstorm_prompt = f"""
You are an expert project analyst and brainstorming facilitator. Analyze the following task and provide a comprehensive brainstorming session.

TASK INFORMATION:
{task_context}

Please provide a structured brainstorm in JSON format with the following sections:

1. "overview": A comprehensive overview of the task and its implications (2-3 sentences)
2. "considerations": Key considerations, challenges, and factors to think about (list of 3-5 items)
3. "approaches": Different potential approaches or methods to accomplish this task (list of 3-4 items)
4. "risks": Potential risks, challenges, or blockers (list of 2-4 items)
5. "recommendations": Specific recommendations and next steps (list of 3-5 items)

Focus on practical, actionable insights. Consider technical aspects, resource requirements, timeline implications, and potential dependencies.

Response format: Return only a valid JSON object with the five sections above.
"""
            
            # Generate brainstorm using LLM with configured API key
            settings = get_settings()
            provider = OpenAIProvider(
                base_url=settings.base_url,
                api_key=settings.llm_api_key
            )
            brainstorm_model = OpenAIModel('gpt-4o', provider=provider)
            brainstorm_agent = Agent(
                model=brainstorm_model,
                system_prompt="You are an expert project analyst specializing in task breakdown and strategic brainstorming. Provide structured, actionable insights for complex technical tasks."
            )
            
            llm_result = await brainstorm_agent.run(brainstorm_prompt)
            
            if hasattr(llm_result, 'data') and llm_result.data:
                # Parse the JSON response from LLM
                try:
                    # If llm_result.data is a string, parse it as JSON
                    if isinstance(llm_result.data, str):
                        brainstorm_content = json.loads(llm_result.data)
                    else:
                        brainstorm_content = llm_result.data
                    
                    # Validate that we have a dictionary
                    if not isinstance(brainstorm_content, dict):
                        log_error(f"Brainstorm content is not a dictionary: {type(brainstorm_content)}")
                        return None
                    
                    # Create TaskBrainstorm object
                    return TaskBrainstorm(
                        task_id=task_id,
                        task_title=task_title,
                        brainstorm_type=brainstorm_type,
                        generated_at=datetime.now(),
                        content=brainstorm_content,
                        rag_context=rag_context,
                        sources=sources
                    )
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse JSON from LLM response: {str(e)}")
                    log_error(f"Raw response: {llm_result.data}")
                    return None
                except Exception as e:
                    log_error(f"Error processing LLM response: {str(e)}")
                    return None
            else:
                log_error("LLM did not return valid brainstorm content")
                return None
        
        except Exception as e:
            log_error(f"Error generating brainstorm with LLM: {str(e)}")
            return None
    
    except Exception as e:
        log_error(f"Error in generate_brainstorm_content: {str(e)}")
        return None


def save_brainstorm_to_file(brainstorm: TaskBrainstorm, file_path: str) -> Dict[str, Any]:
    """Save brainstorm to markdown file."""
    try:
        markdown_content = brainstorm.to_markdown()
        
        # Check if file exists
        if os.path.exists(file_path):
            # Append to existing file
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(markdown_content)
        else:
            # Create new file with header
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Task Brainstorms\n\n")
                f.write("This file contains brainstorming sessions for various tasks.\n\n")
                f.write(markdown_content)
        
        log_info(f"Brainstorm for task {brainstorm.task_id} saved to {file_path}")
        return {'success': True}
    
    except Exception as e:
        log_error(f"Error saving brainstorm to file: {str(e)}")
        return {'success': False, 'error': str(e)}


def save_brainstorm_to_individual_file(brainstorm: TaskBrainstorm, data_dir: str = "data") -> Dict[str, Any]:
    """Save brainstorm to individual markdown file named with task ID."""
    try:
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Create file path with task ID
        file_path = os.path.join(data_dir, f"{brainstorm.task_id}_brainstorm.md")
        
        # Generate markdown content
        markdown_content = brainstorm.to_markdown()
        
        # Write to individual file (overwrite if exists)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Brainstorm for Task {brainstorm.task_id}\n\n")
            f.write(markdown_content)
        
        log_info(f"Brainstorm for task {brainstorm.task_id} saved to individual file: {file_path}")
        return {'success': True, 'file_path': file_path}
    
    except Exception as e:
        log_error(f"Error saving brainstorm to individual file: {str(e)}")
        return {'success': False, 'error': str(e)}


def load_existing_brainstorm(task_id: str, file_path: str) -> Optional[str]:
    """Load existing brainstorm for a task from file."""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for brainstorm section for this task
        pattern = rf"## Brainstorm: [^(]*\({re.escape(task_id)}\).*?(?=## Brainstorm:|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(0).strip()
        
        return None
    
    except Exception as e:
        log_error(f"Error loading existing brainstorm: {str(e)}")
        return None


def load_existing_individual_brainstorm(task_id: str, data_dir: str = "data") -> Optional[str]:
    """Load existing brainstorm from individual task file."""
    file_path = os.path.join(data_dir, f"{task_id}_brainstorm.md")
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content.strip()
    
    except Exception as e:
        log_error(f"Error loading individual brainstorm file: {str(e)}")
        return None


class BrainstormManager:
    """Manager for task brainstorming operations."""
    
    def __init__(self, brainstorm_file: str = "task_brainstorms.md",
                 tasks_file: str = "data/tasks.yaml",
                 task_details_file: str = "data/task_details.yaml"):
        """Initialize brainstorm manager."""
        self.brainstorm_file = brainstorm_file
        self.tasks_file = tasks_file
        self.task_details_file = task_details_file
    
    async def get_brainstorm(self, query_type: str, query_value: str, 
                            force_regenerate: bool = False) -> Dict[str, Any]:
        """Get or generate brainstorm for a task."""
        # Find the task
        task_info = find_task_by_query(
            query_type, 
            query_value, 
            {'tasks': self.tasks_file, 'task_details': self.task_details_file}
        )
        
        if not task_info:
            return {
                'success': False,
                'error': f"Task with {query_type} '{query_value}' not found"
            }
        
        task_id = task_info['basic_task']['id']
        
        # Check for existing brainstorm unless forced to regenerate
        if not force_regenerate:
            # First check individual file
            existing = load_existing_individual_brainstorm(task_id)
            if existing:
                return {
                    'success': True,
                    'content': existing,
                    'source': 'existing_individual',
                    'newly_generated': False
                }
            
            # Then check collective file
            existing = load_existing_brainstorm(task_id, self.brainstorm_file)
            if existing:
                return {
                    'success': True,
                    'content': existing,
                    'source': 'existing_collective',
                    'newly_generated': False
                }
        
        # Generate new brainstorm
        brainstorm_type = 'improved' if force_regenerate else 'initial'
        brainstorm = await generate_brainstorm_content(task_info, brainstorm_type)
        
        if not brainstorm:
            return {
                'success': False,
                'error': 'Failed to generate brainstorm content'
            }
        
        # Save to collective file
        save_result = save_brainstorm_to_file(brainstorm, self.brainstorm_file)
        if not save_result['success']:
            return {
                'success': False,
                'error': f"Failed to save brainstorm: {save_result.get('error')}"
            }
        
        # Save to individual file
        individual_save_result = save_brainstorm_to_individual_file(brainstorm)
        if not individual_save_result['success']:
            log_warning(f"Failed to save individual brainstorm file: {individual_save_result.get('error')}")
        else:
            log_info(f"Brainstorm saved to individual file: {individual_save_result.get('file_path')}")
        
        return {
            'success': True,
            'content': brainstorm.to_markdown(),
            'source': 'generated',
            'newly_generated': True,
            'brainstorm': brainstorm,
            'individual_file': individual_save_result.get('file_path')
        }
    
    async def process_brainstorm_query(self, query: str) -> Dict[str, Any]:
        """Process a brainstorm query and return appropriate response."""
        parsed = parse_brainstorm_query(query)
        
        if not parsed:
            return {
                'success': False,
                'error': 'Could not parse brainstorm query. Use format like "brainstorm task id 111025" or "brainstorm task title TestRail"'
            }
        
        query_type = parsed['type']
        query_value = parsed['value']
        action = parsed['action']
        
        # Determine if we should force regeneration
        force_regenerate = action in ['replace', 'improve', 'update', 'redo']
        
        return await self.get_brainstorm(query_type, query_value, force_regenerate)