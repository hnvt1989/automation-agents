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
from chromadb import Settings as ChromaSettings

load_dotenv()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("CRITICAL: OPENAI_API_KEY not found in .env file. The crawler cannot function without it for embeddings and processing.")
    openai_client = None
else:
    openai_client = AsyncOpenAI(api_key=openai_api_key)

class ChromaDBManager:
    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "knowledge_base"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None

        if not os.path.exists(self.persist_dir):
            try:
                os.makedirs(self.persist_dir, exist_ok=True)
                print(f"ChromaDB persist directory '{self.persist_dir}' did not exist, created it.")
            except OSError as e:
                print(f"Error creating ChromaDB persist directory '{self.persist_dir}': {e}. ChromaDB will likely fail to initialize.")

        try:
            self.client = chromadb.Client(ChromaSettings(
                persist_directory=self.persist_dir,
                is_persistent=True
            ))
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"} 
            )
            print(f"ChromaDBManager initialized. Collection '{self.collection_name}' loaded/created from '{self.persist_dir}'.")
        except Exception as e:
            print(f"CRITICAL: Error initializing ChromaDBManager for collection '{self.collection_name}' at '{self.persist_dir}': {e}")
            print("Web crawler data will not be saved to ChromaDB.")

    def add_chunk_to_collection(self, chunk: 'ProcessedChunk'):
        if not self.collection:
            print(f"ChromaDB collection '{self.collection_name}' not available. Cannot add chunk for {chunk.url}.")
            return None
        
        if chunk.embedding is None:
            print(f"Skipping chunk {chunk.chunk_number} from {chunk.url} due to missing embedding.")
            return None

        chroma_metadata = {
            "source_type": "web_page", 
            "url": chunk.url,
            "title": chunk.title or "N/A",
            "summary": chunk.summary or "N/A",
            "web_chunk_number": chunk.chunk_number, 
            "crawled_at": chunk.metadata.get("crawled_at", datetime.now(timezone.utc).isoformat()),
            "content_length": len(chunk.content),
            "original_url_path": urlparse(chunk.url).path,
            "source_domain": urlparse(chunk.url).netloc
        }
        for key, value in chunk.metadata.items():
            if key not in chroma_metadata and isinstance(value, (str, int, float, bool)):
                chroma_metadata[key] = value
        
        content_hash_short = hashlib.md5(chunk.content.encode('utf-8')).hexdigest()[:8]
        doc_id = f"web::{chunk.url}::num_{chunk.chunk_number}::hash_{content_hash_short}"

        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[chunk.embedding],
                documents=[chunk.content],
                metadatas=[chroma_metadata]
            )
            print(f"Added chunk ID {doc_id} (URL: {chunk.url}, Chunk: {chunk.chunk_number}) to ChromaDB collection '{self.collection_name}'.")
            return doc_id
        except chromadb.errors.IDAlreadyExistsError:
            print(f"Chunk ID {doc_id} already exists in ChromaDB for {chunk.url}. Skipping.")
            return doc_id 
        except Exception as e:
            print(f"Error adding chunk ID {doc_id} for {chunk.url} to ChromaDB: {e}")
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

async def process_chunk(chunk_content: str, chunk_idx: int, url: str) -> ProcessedChunk | None:
    extracted_info = await get_title_and_summary(chunk_content, url)
    embedding_vector = await get_embedding(chunk_content)
    metadata = {
        "source_domain": urlparse(url).netloc,
        "chunk_size_original": len(chunk_content), 
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path_original": urlparse(url).path 
    }
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_idx,
        title=extracted_info['title'],
        summary=extracted_info['summary'],
        content=chunk_content,
        metadata=metadata, 
        embedding=embedding_vector
    )

async def crawl_and_process_url(url: str, web_crawler_instance: AsyncWebCrawler, chroma_manager: ChromaDBManager):
    print(f"Starting crawl for: {url}")
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS) 
    result = await web_crawler_instance.arun(url=url, config=crawl_config)
    if result.success and result.markdown_v2:
        raw_markdown = result.markdown_v2.raw_markdown
        print(f"Successfully crawled: {url}. Raw content length: {len(raw_markdown)}")
        if not raw_markdown.strip():
            print(f"No actual content found at {url} after crawling. Skipping further processing.")
            return
        text_chunks = chunk_text(raw_markdown)
        print(f"Split content from {url} into {len(text_chunks)} chunks.")
        for i, chunk_str in enumerate(text_chunks):
            if not chunk_str.strip():
                print(f"Skipping empty chunk {i} from {url} after chunking.")
                continue
            processed_chunk_object = await process_chunk(chunk_str, i, url)
            if processed_chunk_object:
                if chroma_manager.collection: 
                    chroma_manager.add_chunk_to_collection(processed_chunk_object)
                else:
                    print(f"ChromaDB collection not available. Cannot store chunk {i} from {url}.")
            else:
                print(f"Failed to process chunk {i} from {url}. It will not be stored.")
    else:
        print(f"Failed to crawl or get markdown_v2 for: {url}. Error: {result.error_message if result else 'Unknown error during crawl'}")

async def run_crawler(urls_to_crawl: List[str], 
                      max_concurrent_crawls: int = 3, 
                      sitemap_url: str | None = None, 
                      chroma_persist_dir: str = "./chroma_db", 
                      chroma_collection_name: str = "knowledge_base"):
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
    chroma_db_manager = ChromaDBManager(persist_dir=chroma_persist_dir, collection_name=chroma_collection_name)
    if not chroma_db_manager.client or not chroma_db_manager.collection:
        print("CRITICAL: ChromaDB could not be initialized. Crawled data will NOT be stored.")
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    web_crawler = AsyncWebCrawler(config=browser_config)
    await web_crawler.start()
    semaphore = asyncio.Semaphore(max_concurrent_crawls)
    crawl_tasks = []
    async def crawl_with_semaphore(url: str):
        async with semaphore:
            await crawl_and_process_url(url, web_crawler, chroma_db_manager)
    for url_to_process in unique_target_urls:
        crawl_tasks.append(crawl_with_semaphore(url_to_process))
    if crawl_tasks:
        await asyncio.gather(*crawl_tasks)
    await web_crawler.close()
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

async def main_crawl_example():
    # print("Example 1: Crawling specific URLs...")
    # await run_crawler(
    #     urls_to_crawl=["https://docs.pydantic.dev/latest/concepts/models/", "https://docs.pydantic.dev/latest/concepts/validation/"],
    #     chroma_persist_dir="./chroma_db", 
    #     chroma_collection_name="knowledge_base" 
    # )
    # print("-" * 50)
    print("Example 2: Crawling Pydantic AI docs sitemap into default 'knowledge_base'...")
    pydantic_ai_sitemap = "https://ai.pydantic.dev/sitemap.xml"
    await run_crawler(
        urls_to_crawl=[], 
        sitemap_url=pydantic_ai_sitemap
    )
    print("-" * 50)
    # print("Example 3: Crawling Python Dev Guide into a custom ChromaDB setup...")
    # python_dev_sitemap = "https://devguide.python.org/sitemap.xml"
    # await run_crawler(
    #     urls_to_crawl=[], 
    #     sitemap_url=python_dev_sitemap,
    #     chroma_persist_dir="./custom_web_store",      
    #     chroma_collection_name="python_dev_guide_kb" 
    # )

if __name__ == "__main__":
    print("Starting web crawler script (configured for ChromaDB)...")
    # asyncio.run(main_crawl_example())
    print("Web crawler script finished. Uncomment `asyncio.run(main_crawl_example())` in __main__ to run.") 