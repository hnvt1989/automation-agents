# Brainstorm Feature Improvements

## 1. Enhanced Error Handling & Fallbacks

### Current Issues:
- If RAG fails, it only logs a warning but continues
- If LLM fails, the entire brainstorm fails
- No retry mechanism for API failures

### Suggested Improvements:

```python
# Add retry decorator for API calls
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_llm_with_retry(agent, prompt):
    return await agent.run(prompt)

# Add graceful degradation
async def generate_brainstorm_content(task_info, brainstorm_type='initial'):
    # ... existing code ...
    
    # If RAG fails, continue with task data only
    if not rag_context:
        log_warning("No RAG context available, using task data only")
        rag_context = ["No external context available - brainstorming based on task information only"]
    
    # If LLM fails, provide template-based brainstorm
    try:
        llm_result = await call_llm_with_retry(brainstorm_agent, brainstorm_prompt)
    except Exception as e:
        log_error(f"LLM failed after retries: {e}")
        # Return template-based brainstorm
        return generate_template_brainstorm(task_info, rag_context)
```

## 2. Structured Data Validation

### Add Pydantic Models for Validation:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class BrainstormContent(BaseModel):
    overview: str = Field(..., min_length=10, max_length=1000)
    considerations: List[str] = Field(..., min_items=2, max_items=10)
    approaches: List[str] = Field(..., min_items=1, max_items=8)
    risks: List[str] = Field(..., min_items=1, max_items=8)
    recommendations: List[str] = Field(..., min_items=2, max_items=10)
    
    @validator('considerations', 'approaches', 'risks', 'recommendations', each_item=True)
    def validate_items(cls, item):
        if len(item) < 5:
            raise ValueError("Each item must be at least 5 characters")
        return item

class TaskBrainstormV2(TaskBrainstorm):
    content: BrainstormContent  # Use validated content
```

## 3. Caching & Performance

### Implement Smart Caching:

```python
import hashlib
from datetime import datetime, timedelta

class BrainstormCache:
    def __init__(self, cache_dir="data/.brainstorm_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_key(self, task_info, rag_context):
        # Create hash of task + context for cache key
        content = f"{task_info}{sorted(rag_context)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key, max_age_hours=24):
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(data['cached_at'])
            if datetime.now() - cached_at < timedelta(hours=max_age_hours):
                return data['content']
        return None
    
    def set(self, key, content):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            'content': content,
            'cached_at': datetime.now().isoformat()
        }))
```

## 4. Enhanced RAG Integration

### Improve Context Retrieval:

```python
async def get_enhanced_rag_context(task_info, max_contexts=5):
    """Enhanced RAG context retrieval with relevance scoring."""
    contexts = []
    
    # 1. Search by different query strategies
    search_strategies = [
        lambda t: t['title'],  # Direct title search
        lambda t: f"{t.get('tags', [])} {t['title']}",  # Tags + title
        lambda t: extract_key_terms(t['title']),  # Key terms only
        lambda t: generate_semantic_query(t)  # LLM-generated query
    ]
    
    for strategy in search_strategies:
        query = strategy(task_info['basic_task'])
        results = await rag_agent.search_with_scores(query, n_results=3)
        contexts.extend(results)
    
    # 2. Deduplicate and rank by relevance
    unique_contexts = deduplicate_by_similarity(contexts)
    ranked_contexts = rank_by_relevance(unique_contexts, task_info)
    
    # 3. Return top N most relevant
    return ranked_contexts[:max_contexts]
```

## 5. Template System for Consistency

### Add Brainstorm Templates:

```python
BRAINSTORM_TEMPLATES = {
    'technical': {
        'sections': ['Technical Overview', 'Architecture Considerations', 
                    'Implementation Approaches', 'Technical Risks', 'Best Practices'],
        'prompts': {
            'overview': "Provide a technical overview focusing on system design and architecture",
            'considerations': "List technical constraints, dependencies, and requirements"
        }
    },
    'project': {
        'sections': ['Project Overview', 'Stakeholder Considerations', 
                    'Execution Approaches', 'Project Risks', 'Success Criteria'],
        'prompts': {
            'overview': "Provide a project management perspective",
            'considerations': "Consider stakeholders, timeline, and resources"
        }
    }
}

def detect_brainstorm_type(task_info):
    """Auto-detect the best template based on task content."""
    title = task_info['basic_task']['title'].lower()
    tags = task_info['basic_task'].get('tags', [])
    
    if any(term in title for term in ['api', 'integration', 'sync', 'technical']):
        return 'technical'
    elif any(term in title for term in ['project', 'plan', 'strategy']):
        return 'project'
    return 'general'
```

## 6. Interactive Brainstorming

### Add Follow-up Capabilities:

```python
class InteractiveBrainstorm:
    def __init__(self, task_id):
        self.task_id = task_id
        self.history = []
        
    async def ask_followup(self, question):
        """Ask follow-up questions about the brainstorm."""
        # Load existing brainstorm
        brainstorm = load_existing_individual_brainstorm(self.task_id)
        
        # Add context and ask question
        prompt = f"""
        Based on this brainstorm:
        {brainstorm}
        
        User question: {question}
        
        Provide a detailed answer focusing on the specific aspect asked.
        """
        
        response = await llm_agent.run(prompt)
        self.history.append({'question': question, 'answer': response})
        return response
    
    async def expand_section(self, section_name):
        """Expand a specific section with more details."""
        # ... implementation ...
```

## 7. Version Control for Brainstorms

### Track Brainstorm Evolution:

```python
class BrainstormVersion:
    def __init__(self, task_id):
        self.task_id = task_id
        self.versions_dir = Path(f"data/brainstorm_versions/{task_id}")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
    def save_version(self, brainstorm, version_note=""):
        """Save a new version of the brainstorm."""
        version_num = len(list(self.versions_dir.glob("*.md"))) + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"v{version_num}_{timestamp}.md"
        filepath = self.versions_dir / filename
        
        # Add version metadata
        content = f"<!-- Version: {version_num} -->\n"
        content += f"<!-- Created: {timestamp} -->\n"
        content += f"<!-- Note: {version_note} -->\n\n"
        content += brainstorm.to_markdown()
        
        filepath.write_text(content)
        return filepath
    
    def get_diff(self, v1, v2):
        """Get differences between two versions."""
        # ... implementation ...
```

## 8. Export Formats

### Support Multiple Output Formats:

```python
class BrainstormExporter:
    @staticmethod
    def to_json(brainstorm):
        return json.dumps(brainstorm.to_dict(), indent=2)
    
    @staticmethod
    def to_html(brainstorm):
        """Convert to HTML with styling."""
        template = """
        <html>
        <head>
            <style>
                .brainstorm { font-family: Arial; max-width: 800px; margin: auto; }
                .section { margin: 20px 0; }
                .overview { background: #f0f0f0; padding: 15px; }
                ul { list-style-type: disc; }
            </style>
        </head>
        <body>
            <div class="brainstorm">
                <h1>Brainstorm: {title}</h1>
                <!-- ... rest of template ... -->
            </div>
        </body>
        </html>
        """
        return template.format(**brainstorm.__dict__)
    
    @staticmethod
    def to_pdf(brainstorm):
        """Convert to PDF using markdown-pdf or similar."""
        # ... implementation ...
```

## 9. Metrics & Analytics

### Track Brainstorm Quality:

```python
class BrainstormMetrics:
    def calculate_completeness_score(self, brainstorm):
        """Calculate how complete/comprehensive the brainstorm is."""
        scores = {
            'overview_length': len(brainstorm.content['overview']) / 500,
            'considerations_count': len(brainstorm.content['considerations']) / 5,
            'approaches_count': len(brainstorm.content['approaches']) / 4,
            'has_rag_context': len(brainstorm.rag_context) > 0,
            'sources_count': len(brainstorm.sources) / 3
        }
        return sum(min(1.0, score) for score in scores.values()) / len(scores)
    
    def track_usage(self, task_id, action, duration):
        """Track brainstorm usage for analytics."""
        # Log to analytics database/file
        # ... implementation ...
```

## 10. Configuration & Customization

### Add User Preferences:

```python
# In config.py
class BrainstormConfig(BaseSettings):
    # Model settings
    brainstorm_model: str = Field(default="gpt-4o", env="BRAINSTORM_MODEL")
    brainstorm_temperature: float = Field(default=0.7, env="BRAINSTORM_TEMPERATURE")
    
    # RAG settings
    max_rag_contexts: int = Field(default=5, env="MAX_RAG_CONTEXTS")
    rag_similarity_threshold: float = Field(default=0.7, env="RAG_SIMILARITY_THRESHOLD")
    
    # Output settings
    default_template: str = Field(default="general", env="DEFAULT_BRAINSTORM_TEMPLATE")
    include_rag_context_in_output: bool = Field(default=True, env="INCLUDE_RAG_CONTEXT")
    
    # Performance settings
    enable_caching: bool = Field(default=True, env="ENABLE_BRAINSTORM_CACHE")
    cache_ttl_hours: int = Field(default=24, env="BRAINSTORM_CACHE_TTL_HOURS")
```

## Implementation Priority

1. **High Priority** (Immediate improvements):
   - Error handling with retries
   - Input validation with Pydantic
   - Basic caching mechanism

2. **Medium Priority** (Next iteration):
   - Enhanced RAG integration
   - Template system
   - Version control

3. **Low Priority** (Future enhancements):
   - Interactive brainstorming
   - Export formats
   - Analytics and metrics

## Example Enhanced Usage

```python
# With improvements implemented
brainstorm = await BrainstormManager(
    config=BrainstormConfig(),
    cache=BrainstormCache()
).generate_brainstorm(
    task_id="111025",
    template="technical",
    force_regenerate=False,
    include_followups=True
)

# Get metrics
score = BrainstormMetrics().calculate_completeness_score(brainstorm)
print(f"Brainstorm quality score: {score:.2%}")

# Export in different formats
BrainstormExporter.to_html(brainstorm)
BrainstormExporter.to_pdf(brainstorm)
```