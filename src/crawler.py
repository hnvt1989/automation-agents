import os
import sys
import json
import asyncio
import requests
from xml.etree import ElementTree
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv
import hashlib

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from openai import AsyncOpenAI
import chromadb

load_dotenv("local.env")

# Initialize OpenAI client
openai_api_key = os.getenv("LLM_API_KEY")
if not openai_api_key:
    print("CRITICAL: LLM_API_KEY not found in .env file. The crawler cannot function without it for embeddings and processing.")
    openai_client = None
else:
    openai_client = AsyncOpenAI(api_key=openai_api_key)

async def add_chunk_to_collection(chunk: 'ProcessedChunk', chroma_collection: chromadb.api.models.Collection.Collection):
    """Adds a processed chunk to the provided ChromaDB collection."""
    if not chroma_collection:
        print(f"ChromaDB collection not provided. Cannot add chunk for {chunk.url}.")
        return None
    
    if chunk.embedding is None:
        print(f"Skipping chunk {chunk.chunk_number} from {chunk.url} due to missing embedding.")
        return None

    chroma_metadata = {
        "source_type": "web_page_contextualized",
        "url": chunk.url,
        "title": chunk.title or "N/A",
        "summary": chunk.summary or "N/A",
        "web_chunk_number": chunk.chunk_number, 
        "crawled_at": chunk.metadata.get("crawled_at", datetime.now(timezone.utc).isoformat()),
        "content_length": len(chunk.content),
        "original_content_length": chunk.metadata.get("original_content_length", 0),
        "original_url_path": urlparse(chunk.url).path,
        "source_domain": urlparse(chunk.url).netloc,
        "context_prefix_length": chunk.metadata.get("context_prefix_length", 0)
    }
    for key, value in chunk.metadata.items():
        if key not in chroma_metadata and isinstance(value, (str, int, float, bool)):
            chroma_metadata[key] = value
    
    content_hash_short = hashlib.md5(chunk.content.encode('utf-8')).hexdigest()[:8]
    doc_id = f"web_ctx::{chunk.url}::num_{chunk.chunk_number}::hash_{content_hash_short}"

    try:
        chroma_collection.add(
            ids=[doc_id],
            embeddings=[chunk.embedding],
            documents=[chunk.content],
            metadatas=[chroma_metadata]
        )
        print(f"Added contextualized chunk ID {doc_id} (URL: {chunk.url}, Chunk: {chunk.chunk_number}) to ChromaDB collection '{chroma_collection.name}'.")
        return doc_id
    except chromadb.errors.IDAlreadyExistsError:
        print(f"Contextualized chunk ID {doc_id} already exists in ChromaDB for {chunk.url}. Skipping.")
        return doc_id 
    except Exception as e:
        print(f"Error adding contextualized chunk ID {doc_id} for {chunk.url} to ChromaDB: {e}")
        return None

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float] | None

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        if end >= text_length:
            current_chunk_content = text[start:].strip()
            if current_chunk_content: 
                 chunks.append(current_chunk_content)
            break
        chunk_segment = text[start:end]
        code_block_marker = "```"
        last_code_marker_in_segment = chunk_segment.rfind(code_block_marker)
        if last_code_marker_in_segment != -1:
            num_markers_before_in_text_up_to_segment_end = text[:start + last_code_marker_in_segment].count(code_block_marker)
            if num_markers_before_in_text_up_to_segment_end % 2 == 1:
                potential_end = start + last_code_marker_in_segment + len(code_block_marker)
                if potential_end > start + chunk_size * 0.3 and potential_end <= end :
                     end = potential_end
        last_paragraph_break = chunk_segment.rfind('\n\n')
        if last_paragraph_break > chunk_size * 0.3: 
            end = start + last_paragraph_break + 2 
        elif '. ' in chunk_segment:
            last_sentence_break = chunk_segment.rfind('. ')
            if last_sentence_break > chunk_size * 0.3:
                end = start + last_sentence_break + 1 
        current_chunk_content = text[start:end].strip()
        if current_chunk_content: 
            chunks.append(current_chunk_content)
        start = max(start + 1, end) 
    return chunks

async def _generate_web_chunk_context(whole_document_text: str, original_chunk_content: str, url: str) -> str:
    """Generate situating context for a web chunk using an LLM."""
    if not openai_client:
        print(f"OpenAI client not initialized. Cannot generate context for chunk from {url}.")
        return "" # Return empty string if no context can be generated

    # Limit the size of whole_document_text and original_chunk_content to avoid excessive token usage
    # These limits are heuristics and might need adjustment.
    max_doc_len_for_context = 10000 
    max_chunk_len_for_context = 2000

    truncated_whole_document = whole_document_text
    if len(whole_document_text) > max_doc_len_for_context:
        truncated_whole_document = whole_document_text[:max_doc_len_for_context//2] + "\n... (document truncated for context generation) ...\n" + whole_document_text[-max_doc_len_for_context//2:]
    
    truncated_chunk_content = original_chunk_content
    if len(original_chunk_content) > max_chunk_len_for_context:
        truncated_chunk_content = original_chunk_content[:max_chunk_len_for_context//2] + "... (chunk truncated for context generation) ..." + original_chunk_content[-max_chunk_len_for_context//2:]

    prompt = f"""<document>
{truncated_whole_document}
</document>

Here is a specific chunk from the document above:
<chunk>
{truncated_chunk_content}
</chunk>

Please provide a short, succinct context (1-2 sentences) that situates this chunk within the overall document. This context will be prepended to the chunk to improve search retrieval. Focus on the main topic of the chunk and its relation to the broader document theme. Answer ONLY with the succinct context itself and nothing else."""
    
    llm_model = os.getenv("CONTEXT_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini")) # Allow specific model for this

    try:
        response = await openai_client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2 # Lower temperature for more factual context
        )
        context_prefix = response.choices[0].message.content.strip()
        # Basic filter for common refusal or non-contextual phrases
        if not context_prefix or "cannot provide context" in context_prefix.lower() or "unable to fulfill" in context_prefix.lower():
            print(f"LLM returned non-contextual response for chunk from {url}. Using empty context.")
            return ""
        return context_prefix
    except Exception as e:
        print(f"Error generating web chunk context for {url} with model {llm_model}: {e}")
        return "" # Return empty string on error

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
    if not openai_client:
        print(f"OpenAI client not initialized. Cannot get title/summary for chunk from {url}.")
        return {"title": "OpenAI client error", "summary": "OpenAI client error"}
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title for this specific chunk.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    try:
        content_for_prompt = chunk
        if len(chunk) > 3000: 
            content_for_prompt = chunk[:1500] + "... (content truncated for title/summary) ..." + chunk[-1500:]
        response = await openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL: {url}\n\nContent of the chunk:\n{content_for_prompt}"}
            ],
            response_format={ "type": "json_object" }
        )
        result = json.loads(response.choices[0].message.content)
        return {"title": result.get("title", "N/A"), "summary": result.get("summary", "N/A")}
    except Exception as e:
        print(f"Error getting title and summary for chunk from {url} with model {llm_model}: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float] | None:
    if not openai_client:
        print(f"OpenAI client not initialized. Cannot get embedding for text (first 50 chars: '{text[:50]}...').")
        return None
    try:
        response = await openai_client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for text (first 50 chars: '{text[:50]}...'): {e}")
        return None

async def process_chunk(original_chunk_content: str, chunk_idx: int, url: str, whole_page_text: str) -> ProcessedChunk | None:
    # 1. Generate title and summary from the original chunk content
    # This is done first so it's based on the raw, un-prepended chunk.
    title_summary = await get_title_and_summary(original_chunk_content, url)

    # 2. Generate situating context based on whole page and original chunk
    context_prefix = await _generate_web_chunk_context(whole_page_text, original_chunk_content, url)
    
    # 3. Prepend context to the original chunk content
    if context_prefix: # Only prepend if context was generated
        contextualized_content = f"{context_prefix}\n\n{original_chunk_content}"
    else:
        contextualized_content = original_chunk_content
    
    # 4. Get embedding for the contextualized content
    embedding_vector = await get_embedding(contextualized_content)
    
    # Base metadata for the chunk
    metadata = {
        "source_domain": urlparse(url).netloc,
        "original_content_length": len(original_chunk_content),
        "contextualized_content_length": len(contextualized_content),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path_original": urlparse(url).path,
        "context_prefix_length": len(context_prefix)
    }
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_idx,
        title=title_summary['title'],
        summary=title_summary['summary'],
        content=contextualized_content, # Storing the contextualized content
        metadata=metadata, 
        embedding=embedding_vector
    )

async def crawl_and_process_url(url: str, web_crawler_instance: AsyncWebCrawler, 
                                chroma_collection: chromadb.api.models.Collection.Collection):
    print(f"Starting crawl for: {url}")
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS) 
    result = await web_crawler_instance.arun(url=url, config=crawl_config)

    if result.success and result.markdown:
        # Use the new markdown API which returns a MarkdownGenerationResult
        raw_markdown = result.markdown.raw_markdown
        print(f"Successfully crawled: {url}. Raw content length: {len(raw_markdown)}")
        if not raw_markdown.strip():
            print(f"No actual content found at {url} after crawling. Skipping further processing.")
            return

        text_chunks = chunk_text(raw_markdown) # These are chunks of the original raw_markdown
        print(f"Split content from {url} into {len(text_chunks)} chunks.")
        
        for i, original_chunk_str in enumerate(text_chunks):
            if not original_chunk_str.strip():
                print(f"Skipping empty chunk {i} from {url} after chunking.")
                continue
            
            # Pass the full raw_markdown as whole_page_text for context generation
            processed_chunk_object = await process_chunk(original_chunk_str, i, url, raw_markdown)
            
            if processed_chunk_object:
                if chroma_collection: 
                    await add_chunk_to_collection(processed_chunk_object, chroma_collection)
                else:
                    print(f"ChromaDB collection not provided. Cannot store chunk {i} from {url}.")
            else:
                print(f"Failed to process chunk {i} from {url}. It will not be stored.")
    else:
        print(f"Failed to crawl or get markdown for: {url}. Error: {result.error_message if result else 'Unknown error during crawl'}")

async def run_crawler(urls_to_crawl: List[str], 
                      chroma_collection: chromadb.api.models.Collection.Collection, # Now a required arg
                      max_concurrent_crawls: int = 3, 
                      sitemap_url: str | None = None):
    """Main function to run the crawler, storing results in the provided ChromaDB Collection."""
    if not chroma_collection:
        print("CRITICAL: ChromaDB collection was not provided to run_crawler. Crawled data will NOT be stored.")
        # Decide if to proceed or exit. For now, let it "crawl" but not store if URLs are present.
        # If storing is essential, could raise an error here.

    target_urls = list(urls_to_crawl) 
    if sitemap_url:
        print(f"Fetching URLs from sitemap: {sitemap_url}")
        sitemap_urls = get_urls_from_sitemap(sitemap_url) 
        if sitemap_urls:
            print(f"Found {len(sitemap_urls)} URLs from sitemap.")
            target_urls.extend(sitemap_urls)
        else:
            print(f"No URLs found or error fetching sitemap: {sitemap_url}")
    if not target_urls:
        print("No URLs provided and no URLs found from sitemap. Exiting crawler.")
        return
    unique_target_urls = sorted(list(set(u for u in target_urls if u and u.strip().startswith(('http://', 'https://')))))
    print(f"Total unique and valid URLs to crawl: {len(unique_target_urls)}")
    if not unique_target_urls:
        print("No valid URLs to crawl after filtering. Exiting.")
        return

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    web_crawler_instance = AsyncWebCrawler(config=browser_config) # Renamed for clarity
    await web_crawler_instance.start()
    semaphore = asyncio.Semaphore(max_concurrent_crawls)
    crawl_tasks = []
    async def crawl_with_semaphore(url: str):
        async with semaphore:
            # Pass the provided chroma_collection to each task
            await crawl_and_process_url(url, web_crawler_instance, chroma_collection)
    for url_to_process in unique_target_urls:
        crawl_tasks.append(crawl_with_semaphore(url_to_process))
    if crawl_tasks:
        await asyncio.gather(*crawl_tasks)
    await web_crawler_instance.close()
    print("Crawler run finished.")

def get_urls_from_sitemap(sitemap_url: str) -> List[str]:
    try:
        print(f"Requesting sitemap: {sitemap_url}")
        response = requests.get(sitemap_url, timeout=20) 
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '').lower()
        if 'xml' not in content_type:
            print(f"Warning: Sitemap URL {sitemap_url} returned content type {content_type}, not XML. Trying to parse anyway.")
        namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as e:
            print(f"Failed to parse XML from {sitemap_url}. Error: {e}. Content (first 500 chars): {response.text[:500]}")
            return []
        url_elements = root.findall('.//sitemap:loc', namespaces)
        if not url_elements:
            url_elements = root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
        if not url_elements:
             url_elements = root.findall('.//loc')
        extracted_urls = [elem.text.strip() for elem in url_elements if elem.text and elem.text.strip()]
        print(f"Extracted {len(extracted_urls)} URLs from {sitemap_url}")
        return extracted_urls
    except requests.exceptions.Timeout:
        print(f"Timeout error fetching sitemap {sitemap_url}.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error fetching sitemap {sitemap_url}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while processing sitemap {sitemap_url}: {e}")
        return []

# Removed main_crawl_example and if __name__ == "__main__" block 