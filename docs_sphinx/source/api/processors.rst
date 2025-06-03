Processors
==========

The processors module contains specialized data processing components for handling different types of content including images, calendars, and web content.

Image Processor (:mod:`src.processors.image`)
----------------------------------------------

The image processor handles image analysis using OpenAI's Vision API, particularly for calendar screenshots and conversation images.

.. automodule:: src.processors.image
   :members:
   :undoc-members:
   :show-inheritance:

**Key Features:**

- Calendar screenshot analysis and event extraction
- Conversation screenshot parsing and indexing
- Base64 image encoding for API calls
- Integration with OpenAI Vision API

**Usage Example:**

.. code-block:: python

   from src.processors.image import ImageProcessor

   # Initialize processor
   processor = ImageProcessor()

   # Analyze calendar image
   calendar_events = await processor.analyze_calendar_image("path/to/calendar.png")

   # Process conversation screenshot
   conversation_data = await processor.analyze_conversation_image("path/to/chat.png")

Calendar Processor (:mod:`src.processors.calendar`)
----------------------------------------------------

The calendar processor handles parsing and processing of calendar events from various sources.

.. automodule:: src.processors.calendar
   :members:
   :undoc-members:
   :show-inheritance:

**Features:**

- Calendar event parsing from different formats
- Meeting schedule management
- Integration with planning system
- Event validation and formatting

**Usage Example:**

.. code-block:: python

   from src.processors.calendar import CalendarProcessor

   # Initialize processor
   processor = CalendarProcessor()

   # Parse calendar events
   events = processor.parse_events(calendar_data)

   # Format for storage
   formatted_events = processor.format_for_yaml(events)

Crawler Processor (:mod:`src.processors.crawler`)
--------------------------------------------------

The crawler processor handles web content extraction and processing.

.. automodule:: src.processors.crawler
   :members:
   :undoc-members:
   :show-inheritance:

**Features:**

- Web page content extraction
- HTML parsing and cleaning
- Text normalization and formatting
- Integration with search agents

**Usage Example:**

.. code-block:: python

   from src.processors.crawler import CrawlerProcessor

   # Initialize processor
   processor = CrawlerProcessor()

   # Extract content from URL
   content = await processor.extract_content("https://example.com")

   # Clean and format text
   cleaned_text = processor.clean_text(content)

Processor Design Patterns
--------------------------

**Factory Pattern**
   Processors can be instantiated through factory methods that handle configuration and dependency injection.

**Pipeline Pattern**
   Content processing often involves multiple steps that can be chained together in a pipeline.

**Strategy Pattern**
   Different processing strategies can be applied based on content type or user preferences.

**Example Processor Implementation:**

.. code-block:: python

   from abc import ABC, abstractmethod
   from typing import Any, Dict

   class BaseProcessor(ABC):
       """Base class for all processors."""
       
       def __init__(self, config: Dict[str, Any] = None):
           self.config = config or {}
       
       @abstractmethod
       async def process(self, input_data: Any) -> Any:
           """Process the input data and return result."""
           pass
       
       def validate_input(self, input_data: Any) -> bool:
           """Validate input data format."""
           return True
       
       def format_output(self, result: Any) -> Any:
           """Format the processing result."""
           return result

   class CustomProcessor(BaseProcessor):
       """Example custom processor implementation."""
       
       async def process(self, input_data: str) -> Dict[str, Any]:
           if not self.validate_input(input_data):
               raise ValueError("Invalid input data")
           
           # Processing logic here
           result = {"processed": input_data.upper()}
           
           return self.format_output(result)

Common Processing Workflows
---------------------------

**Image Analysis Workflow:**

.. code-block:: python

   async def analyze_image_workflow(image_path: str):
       """Complete image analysis workflow."""
       
       # 1. Load and validate image
       processor = ImageProcessor()
       if not processor.validate_image(image_path):
           raise ValueError("Invalid image format")
       
       # 2. Analyze based on content type
       if processor.is_calendar_image(image_path):
           events = await processor.analyze_calendar_image(image_path)
           return {"type": "calendar", "events": events}
       elif processor.is_conversation_image(image_path):
           messages = await processor.analyze_conversation_image(image_path)
           return {"type": "conversation", "messages": messages}
       else:
           # General image analysis
           description = await processor.describe_image(image_path)
           return {"type": "general", "description": description}

**Document Processing Pipeline:**

.. code-block:: python

   async def document_processing_pipeline(url: str):
       """Process web document through complete pipeline."""
       
       # 1. Extract content
       crawler = CrawlerProcessor()
       raw_content = await crawler.extract_content(url)
       
       # 2. Clean and normalize
       cleaned_content = crawler.clean_text(raw_content)
       
       # 3. Extract metadata
       metadata = crawler.extract_metadata(raw_content)
       
       # 4. Chunk for indexing
       chunks = crawler.chunk_text(cleaned_content)
       
       return {
           "content": cleaned_content,
           "metadata": metadata,
           "chunks": chunks
       }

Error Handling in Processors
-----------------------------

Processors implement robust error handling:

.. code-block:: python

   from src.core.exceptions import DocumentProcessingError
   from src.utils.logging import log_error, log_warning

   class RobustProcessor:
       async def safe_process(self, input_data: Any) -> Any:
           try:
               # Validate input
               if not self.validate_input(input_data):
                   raise DocumentProcessingError("Invalid input format")
               
               # Process data
               result = await self.process(input_data)
               
               # Validate output
               if not self.validate_output(result):
                   log_warning("Output validation failed, using fallback")
                   result = self.get_fallback_result()
               
               return result
               
           except DocumentProcessingError:
               # Re-raise processing errors
               raise
           except Exception as e:
               log_error(f"Unexpected error in processor: {e}")
               raise DocumentProcessingError(f"Processing failed: {e}")

Performance Considerations
--------------------------

**Async Processing**
   All processors use async/await for non-blocking operations, especially when dealing with external APIs or file I/O.

**Caching**
   Frequently accessed results can be cached to improve performance:

.. code-block:: python

   from functools import lru_cache
   import hashlib

   class CachedProcessor:
       def __init__(self):
           self._cache = {}
       
       def _get_cache_key(self, input_data: str) -> str:
           return hashlib.md5(input_data.encode()).hexdigest()
       
       async def process_with_cache(self, input_data: str) -> Any:
           cache_key = self._get_cache_key(input_data)
           
           if cache_key in self._cache:
               return self._cache[cache_key]
           
           result = await self.process(input_data)
           self._cache[cache_key] = result
           
           return result

**Batch Processing**
   For processing multiple items, use batch operations when possible:

.. code-block:: python

   async def batch_process(self, items: List[Any]) -> List[Any]:
       """Process multiple items efficiently."""
       import asyncio
       
       # Process items concurrently
       tasks = [self.process(item) for item in items]
       results = await asyncio.gather(*tasks, return_exceptions=True)
       
       # Handle any exceptions
       processed_results = []
       for i, result in enumerate(results):
           if isinstance(result, Exception):
               log_error(f"Failed to process item {i}: {result}")
               processed_results.append(None)
           else:
               processed_results.append(result)
       
       return processed_results