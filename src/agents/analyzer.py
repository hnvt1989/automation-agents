"""Meeting analyzer agent for analyzing meetings and suggesting tasks."""
from __future__ import annotations

import json
import os
import yaml
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agents.rag import RAGAgent
from src.agents.enhanced_rag import get_enhanced_rag_context
from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings


@dataclass
class SuggestedTask:
    """Represents a suggested task from meeting analysis."""
    title: str
    description: str
    priority: str  # 'high', 'medium', 'low'
    deadline: Optional[str]
    assignee: Optional[str]
    category: str  # 'action_item', 'follow_up', 'research', etc.
    confidence: float  # 0.0 to 1.0 confidence score
    context: str  # Meeting context that led to this task
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'deadline': self.deadline,
            'assignee': self.assignee,
            'category': self.category,
            'confidence': self.confidence,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuggestedTask':
        """Create from dictionary."""
        return cls(
            title=data['title'],
            description=data['description'],
            priority=data.get('priority', 'medium'),
            deadline=data.get('deadline'),
            assignee=data.get('assignee'),
            category=data.get('category', 'action_item'),
            confidence=data.get('confidence', 0.8),
            context=data.get('context', '')
        )


@dataclass
class MeetingAnalysis:
    """Represents the analysis of a meeting with suggested tasks."""
    meeting_date: str
    meeting_title: str
    analysis_timestamp: datetime
    summary: str
    key_decisions: List[str]
    action_items: List[str]
    suggested_tasks: List[SuggestedTask]
    next_steps: List[str]
    participants: List[str]
    rag_context: List[str]
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'meeting_date': self.meeting_date,
            'meeting_title': self.meeting_title,
            'analysis_timestamp': self.analysis_timestamp.isoformat(),
            'summary': self.summary,
            'key_decisions': self.key_decisions,
            'action_items': self.action_items,
            'suggested_tasks': [task.to_dict() for task in self.suggested_tasks],
            'next_steps': self.next_steps,
            'participants': self.participants,
            'rag_context': self.rag_context,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeetingAnalysis':
        """Create from dictionary."""
        return cls(
            meeting_date=data['meeting_date'],
            meeting_title=data['meeting_title'],
            analysis_timestamp=datetime.fromisoformat(data['analysis_timestamp']),
            summary=data['summary'],
            key_decisions=data['key_decisions'],
            action_items=data['action_items'],
            suggested_tasks=[SuggestedTask.from_dict(task) for task in data['suggested_tasks']],
            next_steps=data['next_steps'],
            participants=data['participants'],
            rag_context=data['rag_context'],
            confidence_score=data['confidence_score']
        )


class AnalyzerAgent:
    """Agent for analyzing meetings and suggesting tasks."""
    
    def __init__(self):
        """Initialize the analyzer agent."""
        try:
            settings = get_settings()
            provider = OpenAIProvider(
                base_url=settings.base_url,
                api_key=settings.llm_api_key
            )
            self.model = OpenAIModel('gpt-4o', provider=provider)
            
            self.agent = Agent(
                model=self.model,
                system_prompt="""
                You are an expert meeting analyzer and project management assistant. 
                Your role is to analyze meeting notes, extract key information, and suggest actionable tasks.
                
                When analyzing meetings, focus on:
                1. Identifying concrete action items and deliverables
                2. Extracting key decisions and their implications
                3. Recognizing follow-up tasks and research needs
                4. Determining appropriate priorities and deadlines
                5. Suggesting clear, actionable task descriptions
                
                Always provide structured, practical recommendations that can be easily converted to trackable tasks.
                """
            )
            
            log_info("AnalyzerAgent initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize AnalyzerAgent: {str(e)}")
            raise
    
    async def analyze_meeting(self, meeting_content: str, meeting_date: str, 
                            meeting_title: str) -> Optional[MeetingAnalysis]:
        """Analyze a meeting and suggest tasks."""
        try:
            log_info(f"Analyzing meeting: {meeting_title} ({meeting_date})")
            
            # Step 1: Get enhanced context from RAG
            rag_context = []
            try:
                # Create a pseudo task info for RAG context retrieval
                task_info = {
                    'basic_task': {
                        'id': f"meeting_{meeting_date}",
                        'title': meeting_title,
                        'status': 'active',
                        'priority': 'medium'
                    },
                    'task_detail': {
                        'objective': f"Analyze meeting: {meeting_title}",
                        'description': meeting_content[:500]  # Truncate for search
                    }
                }
                
                enhanced_contexts = await get_enhanced_rag_context(task_info, max_contexts=3)
                
                for ctx in enhanced_contexts:
                    content = ctx.get('content', '')
                    if content:
                        rag_context.append(content[:300])  # Truncate for prompt
                        
                log_info(f"Retrieved {len(rag_context)} RAG contexts for meeting analysis")
                
            except Exception as e:
                log_warning(f"RAG context retrieval failed: {str(e)}")
            
            # Step 2: Prepare analysis prompt
            analysis_prompt = f"""
            Analyze the following meeting and suggest actionable tasks.
            
            MEETING INFORMATION:
            Date: {meeting_date}
            Title: {meeting_title}
            
            MEETING CONTENT:
            {meeting_content}
            
            RELEVANT CONTEXT FROM KNOWLEDGE BASE:
            {chr(10).join(f"- {ctx}" for ctx in rag_context) if rag_context else "No additional context available"}
            
            Please provide a comprehensive analysis in JSON format with the following structure:
            
            {{
                "summary": "Brief 2-3 sentence summary of the meeting",
                "key_decisions": ["List of key decisions made", "..."],
                "action_items": ["Explicit action items mentioned", "..."],
                "participants": ["List of participants if mentioned", "..."],
                "next_steps": ["Immediate next steps identified", "..."],
                "suggested_tasks": [
                    {{
                        "title": "Clear, actionable task title",
                        "description": "Detailed description of what needs to be done",
                        "priority": "high|medium|low",
                        "deadline": "YYYY-MM-DD or null if not specified",
                        "assignee": "person responsible or null",
                        "category": "action_item|follow_up|research|decision|communication",
                        "confidence": 0.85,
                        "context": "Meeting context that led to this task"
                    }}
                ],
                "confidence_score": 0.90
            }}
            
            Guidelines for task suggestions:
            - Only suggest tasks that are clearly actionable and specific
            - Include both explicit action items and implied follow-up tasks
            - Prioritize based on urgency and impact mentioned in the meeting
            - Set realistic deadlines based on context
            - Ensure each task has a clear owner if mentioned
            - Use confidence scores to indicate how certain you are about each task
            
            IMPORTANT: Return ONLY valid JSON. Do not wrap in markdown code blocks.
            """
            
            # Step 3: Run analysis
            result = await self.agent.run(analysis_prompt)
            
            if not (hasattr(result, 'data') and result.data):
                log_error("Analyzer agent returned no data")
                return None
            
            # Step 4: Parse JSON response
            try:
                if isinstance(result.data, str):
                    # Clean up response text
                    response_text = result.data.strip()
                    if response_text.startswith('```'):
                        first_newline = response_text.find('\n')
                        if first_newline > -1:
                            response_text = response_text[first_newline+1:]
                        if response_text.rstrip().endswith('```'):
                            response_text = response_text.rstrip()[:-3].rstrip()
                    
                    analysis_data = json.loads(response_text)
                else:
                    analysis_data = result.data
                
                if not isinstance(analysis_data, dict):
                    log_error(f"Analysis result is not a dictionary: {type(analysis_data)}")
                    return None
                
                # Convert suggested_tasks to SuggestedTask objects
                suggested_tasks = []
                for task_data in analysis_data.get('suggested_tasks', []):
                    try:
                        suggested_tasks.append(SuggestedTask.from_dict(task_data))
                    except Exception as e:
                        log_warning(f"Failed to parse suggested task: {str(e)}")
                        continue
                
                # Create MeetingAnalysis object
                return MeetingAnalysis(
                    meeting_date=meeting_date,
                    meeting_title=meeting_title,
                    analysis_timestamp=datetime.now(),
                    summary=analysis_data.get('summary', ''),
                    key_decisions=analysis_data.get('key_decisions', []),
                    action_items=analysis_data.get('action_items', []),
                    suggested_tasks=suggested_tasks,
                    next_steps=analysis_data.get('next_steps', []),
                    participants=analysis_data.get('participants', []),
                    rag_context=rag_context,
                    confidence_score=analysis_data.get('confidence_score', 0.8)
                )
                
            except json.JSONDecodeError as e:
                log_error(f"Failed to parse JSON from analyzer response: {str(e)}")
                log_error(f"Raw response: {result.data}")
                return None
            except Exception as e:
                log_error(f"Error processing analyzer response: {str(e)}")
                return None
        
        except Exception as e:
            log_error(f"Error in analyze_meeting: {str(e)}")
            return None
    
    async def enhance_task_with_rag(self, task: SuggestedTask) -> Dict[str, Any]:
        """Enhance a suggested task with additional context from RAG."""
        try:
            log_info(f"Enhancing task with RAG: {task.title}")
            
            # Create RAG agent
            rag_agent = RAGAgent(self.model)
            
            # Search for relevant context
            search_query = f"Find information relevant to: {task.title} {task.description}"
            rag_result = await rag_agent.run(search_query, deps=None)
            
            enhanced_context = ""
            if hasattr(rag_result, 'data') and rag_result.data:
                enhanced_context = str(rag_result.data)
            
            # Generate enhanced task description
            enhancement_prompt = f"""
            Enhance the following task with additional context and details:
            
            ORIGINAL TASK:
            Title: {task.title}
            Description: {task.description}
            Priority: {task.priority}
            Category: {task.category}
            
            ADDITIONAL CONTEXT FROM KNOWLEDGE BASE:
            {enhanced_context[:1000] if enhanced_context else "No additional context found"}
            
            Please provide an enhanced task description that includes:
            1. More specific details and steps
            2. Relevant background information
            3. Potential challenges or considerations
            4. Success criteria
            
            Return only the enhanced description text, not JSON.
            """
            
            enhancement_result = await self.agent.run(enhancement_prompt)
            
            enhanced_todo = ""
            if hasattr(enhancement_result, 'data') and enhancement_result.data:
                enhanced_todo = str(enhancement_result.data)
            
            return {
                'success': True,
                'enhanced_todo': enhanced_todo,
                'rag_context': enhanced_context[:500] if enhanced_context else ""
            }
        
        except Exception as e:
            log_error(f"Error enhancing task with RAG: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'enhanced_todo': task.description,
                'rag_context': ""
            }
    
    def save_analysis(self, analysis: MeetingAnalysis, output_dir: str = "data/meeting_analyses") -> Dict[str, Any]:
        """Save meeting analysis to file."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"{analysis.meeting_date}_{analysis.meeting_title.replace(' ', '_')}_analysis.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
            
            log_info(f"Meeting analysis saved to: {filepath}")
            return {'success': True, 'filepath': filepath}
        
        except Exception as e:
            log_error(f"Error saving meeting analysis: {str(e)}")
            return {'success': False, 'error': str(e)}