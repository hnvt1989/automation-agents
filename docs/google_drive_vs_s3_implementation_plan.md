# Implementation Plan: Google Drive vs S3 Document Management

## Executive Summary

This document provides a comprehensive implementation plan for integrating document storage solutions (Google Drive and AWS S3) with the existing automation-agents RAG system. It includes detailed comparisons, code examples, and a hybrid approach recommendation.

## Table of Contents

1. [Overview](#overview)
2. [Option 1: Google Drive Implementation](#option-1-google-drive-implementation)
3. [Option 2: AWS S3 Implementation](#option-2-aws-s3-implementation)
4. [Option 3: Hybrid Implementation (Recommended)](#option-3-hybrid-implementation-recommended)
5. [Detailed Implementation Comparison](#detailed-implementation-comparison)
6. [Integration with Existing RAG System](#integration-with-existing-rag-system)
7. [Performance Comparison](#performance-comparison)
8. [Migration Strategy](#migration-strategy)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Decision Matrix](#decision-matrix)
11. [Quick Start Guide](#quick-start-guide)

## Overview

This plan addresses the need to fetch notes, documents, interviews, and memos from cloud storage and integrate them with the enhanced RAG system. Both Google Drive and AWS S3 are evaluated as storage solutions.

### Key Requirements
- Fetch documents from cloud storage
- Process various document formats (Google Docs, PDFs, etc.)
- Index documents with contextual chunking
- Maintain metadata and folder structure
- Enable search across all documents
- Support incremental sync

## Option 1: Google Drive Implementation

### 1.1 Setup & Authentication

#### Required Dependencies
```python
# Add to requirements.txt
google-api-python-client>=2.100.0
google-auth>=2.38.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
```

#### Configuration Updates
```python
# src/core/config.py additions
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Google Drive settings
    google_credentials_path: str = Field(
        default="credentials.json",
        env="GOOGLE_CREDENTIALS_PATH",
        description="Path to Google OAuth2 credentials"
    )
    google_token_path: str = Field(
        default="token.json",
        env="GOOGLE_TOKEN_PATH",
        description="Path to store OAuth2 tokens"
    )
    google_drive_folder_ids: List[str] = Field(
        default_factory=list,
        env="GOOGLE_DRIVE_FOLDER_IDS",
        description="List of Google Drive folder IDs to sync"
    )
    google_sync_interval: int = Field(
        default=3600,
        env="GOOGLE_SYNC_INTERVAL",
        description="Sync interval in seconds"
    )
    google_scopes: List[str] = Field(
        default_factory=lambda: [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
    )
```

### 1.2 Google Drive MCP Server

```python
# src/mcp/servers/google_drive/server.py
import asyncio
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import os

class GoogleDriveMCPServer:
    """MCP Server for Google Drive operations."""
    
    def __init__(self, credentials_path: str, token_path: str, scopes: List[str]):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = scopes
        self.service = None
        
    def authenticate(self):
        """Handle OAuth2 authentication flow."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
    
    async def list_files(self, folder_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """List files in a Google Drive folder."""
        try:
            results = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)",
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')
                
                if not page_token:
                    break
                    
            return results
            
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
    
    async def download_file(self, file_id: str, mime_type: str) -> bytes:
        """Download a file from Google Drive."""
        try:
            # Handle Google Workspace files
            if mime_type.startswith('application/vnd.google-apps'):
                export_mime_type = self._get_export_mime_type(mime_type)
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime_type
                )
            else:
                # Regular files
                request = self.service.files().get_media(fileId=file_id)
            
            return request.execute()
            
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
    
    def _get_export_mime_type(self, google_mime_type: str) -> str:
        """Map Google Workspace mime types to export formats."""
        mime_map = {
            'application/vnd.google-apps.document': 'text/plain',
            'application/vnd.google-apps.spreadsheet': 'text/csv',
            'application/vnd.google-apps.presentation': 'text/plain',
            'application/vnd.google-apps.drawing': 'application/pdf'
        }
        return mime_map.get(google_mime_type, 'application/pdf')
```

### 1.3 Google Drive Agent

```python
# src/agents/google_drive.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from datetime import datetime

from src.agents.base import BaseAgent
from src.mcp.servers.google_drive.server import GoogleDriveMCPServer
from src.utils.logging import log_info, log_error

class GoogleDriveAgentDeps(BaseModel):
    """Dependencies for Google Drive agent."""
    drive_server: GoogleDriveMCPServer
    
class GoogleDriveAgent(BaseAgent):
    """Agent for Google Drive operations."""
    
    def __init__(self, model, settings):
        self.drive_server = GoogleDriveMCPServer(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_path,
            scopes=settings.google_scopes
        )
        self.drive_server.authenticate()
        
        deps = GoogleDriveAgentDeps(drive_server=self.drive_server)
        
        super().__init__(
            name="google_drive",
            model=model,
            system_prompt="You are a Google Drive assistant that helps fetch and process documents.",
            deps_type=GoogleDriveAgentDeps
        )
        
        self._register_tools()
    
    def _register_tools(self):
        """Register Google Drive tools."""
        
        @self.agent.tool
        async def fetch_documents(
            ctx: RunContext[GoogleDriveAgentDeps],
            folder_id: str,
            file_types: Optional[List[str]] = None,
            modified_after: Optional[str] = None
        ) -> str:
            """Fetch documents from a Google Drive folder."""
            try:
                files = await ctx.deps.drive_server.list_files(folder_id)
                
                # Filter by file types if specified
                if file_types:
                    files = [f for f in files if any(
                        f['mimeType'].endswith(ft) or ft in f['name'] 
                        for ft in file_types
                    )]
                
                # Filter by modification date
                if modified_after:
                    cutoff_date = datetime.fromisoformat(modified_after)
                    files = [f for f in files if 
                            datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00')) > cutoff_date]
                
                log_info(f"Found {len(files)} files matching criteria")
                
                # Format results
                results = []
                for file in files[:10]:  # Limit to 10 for display
                    results.append(f"- {file['name']} ({file['mimeType']})")
                
                return f"Found {len(files)} files:\n" + "\n".join(results)
                
            except Exception as e:
                log_error(f"Error fetching documents: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def download_and_process(
            ctx: RunContext[GoogleDriveAgentDeps],
            file_id: str,
            file_name: str,
            mime_type: str
        ) -> str:
            """Download and process a single document."""
            try:
                content = await ctx.deps.drive_server.download_file(file_id, mime_type)
                
                # Save to temporary location for processing
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                log_info(f"Downloaded {file_name} to {tmp_path}")
                return f"Downloaded {file_name} ({len(content)} bytes)"
                
            except Exception as e:
                log_error(f"Error downloading file: {str(e)}")
                return f"Error: {str(e)}"
```

## Option 2: AWS S3 Implementation

### 2.1 Setup & Authentication

#### Required Dependencies
```python
# Add to requirements.txt
boto3>=1.26.0
aioboto3>=11.0.0
```

#### Configuration Updates
```python
# src/core/config.py additions
class Settings(BaseSettings):
    # ... existing fields ...
    
    # AWS S3 settings
    aws_access_key_id: str = Field(
        default=None,
        env="AWS_ACCESS_KEY_ID",
        description="AWS access key ID"
    )
    aws_secret_access_key: str = Field(
        default=None,
        env="AWS_SECRET_ACCESS_KEY",
        description="AWS secret access key"
    )
    aws_region: str = Field(
        default="us-east-1",
        env="AWS_REGION",
        description="AWS region"
    )
    s3_bucket_name: str = Field(
        default=None,
        env="S3_BUCKET_NAME",
        description="S3 bucket name for documents"
    )
    s3_prefix: str = Field(
        default="documents/",
        env="S3_PREFIX",
        description="S3 prefix for document organization"
    )
```

### 2.2 S3 MCP Server

```python
# src/mcp/servers/s3/server.py
import asyncio
import aioboto3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class S3MCPServer:
    """MCP Server for AWS S3 operations."""
    
    def __init__(self, access_key_id: str, secret_access_key: str, 
                 region: str, bucket_name: str):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.bucket_name = bucket_name
        self.session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
    
    async def list_objects(self, prefix: str, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List objects in S3 bucket with given prefix."""
        objects = []
        
        async with self.session.client('s3') as s3:
            paginator = s3.get_paginator('list_objects_v2')
            
            async for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_keys}
            ):
                for obj in page.get('Contents', []):
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
        
        return objects
    
    async def download_object(self, key: str) -> bytes:
        """Download an object from S3."""
        async with self.session.client('s3') as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            content = await response['Body'].read()
            return content
    
    async def upload_object(self, key: str, content: bytes, 
                           metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Upload an object to S3 with metadata."""
        async with self.session.client('s3') as s3:
            args = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': content
            }
            
            if metadata:
                args['Metadata'] = metadata
            
            response = await s3.put_object(**args)
            
            return {
                'key': key,
                'etag': response['ETag'].strip('"'),
                'version_id': response.get('VersionId')
            }
    
    async def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for an S3 object."""
        async with self.session.client('s3') as s3:
            response = await s3.head_object(Bucket=self.bucket_name, Key=key)
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'etag': response['ETag'].strip('"')
            }
```

### 2.3 S3 Agent

```python
# src/agents/s3_storage.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
from pathlib import Path

from src.agents.base import BaseAgent
from src.mcp.servers.s3.server import S3MCPServer
from src.utils.logging import log_info, log_error

class S3AgentDeps(BaseModel):
    """Dependencies for S3 agent."""
    s3_server: S3MCPServer
    
class S3StorageAgent(BaseAgent):
    """Agent for S3 storage operations."""
    
    def __init__(self, model, settings):
        self.s3_server = S3MCPServer(
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region,
            bucket_name=settings.s3_bucket_name
        )
        
        deps = S3AgentDeps(s3_server=self.s3_server)
        
        super().__init__(
            name="s3_storage",
            model=model,
            system_prompt="You are an S3 storage assistant that helps manage documents in AWS S3.",
            deps_type=S3AgentDeps
        )
        
        self._register_tools()
    
    def _register_tools(self):
        """Register S3 tools."""
        
        @self.agent.tool
        async def list_documents(
            ctx: RunContext[S3AgentDeps],
            prefix: str,
            file_types: Optional[List[str]] = None
        ) -> str:
            """List documents in S3 with given prefix."""
            try:
                objects = await ctx.deps.s3_server.list_objects(prefix)
                
                # Filter by file types
                if file_types:
                    objects = [obj for obj in objects if any(
                        obj['key'].endswith(ft) for ft in file_types
                    )]
                
                log_info(f"Found {len(objects)} objects in S3")
                
                # Format results
                results = []
                for obj in objects[:10]:  # Limit display
                    size_mb = obj['size'] / (1024 * 1024)
                    results.append(f"- {obj['key']} ({size_mb:.2f} MB)")
                
                return f"Found {len(objects)} objects:\n" + "\n".join(results)
                
            except Exception as e:
                log_error(f"Error listing S3 objects: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def bulk_download(
            ctx: RunContext[S3AgentDeps],
            prefix: str,
            local_dir: str,
            max_files: int = 100
        ) -> str:
            """Bulk download files from S3 to local directory."""
            try:
                objects = await ctx.deps.s3_server.list_objects(prefix, max_keys=max_files)
                
                Path(local_dir).mkdir(parents=True, exist_ok=True)
                downloaded = 0
                
                for obj in objects:
                    content = await ctx.deps.s3_server.download_object(obj['key'])
                    
                    # Preserve S3 path structure locally
                    local_path = Path(local_dir) / obj['key']
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        f.write(content)
                    
                    downloaded += 1
                    log_info(f"Downloaded {obj['key']} to {local_path}")
                
                return f"Downloaded {downloaded} files to {local_dir}"
                
            except Exception as e:
                log_error(f"Error in bulk download: {str(e)}")
                return f"Error: {str(e)}"
```

## Option 3: Hybrid Implementation (Recommended)

### 3.1 Unified Document Manager

```python
# src/storage/document_manager.py
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
import asyncio
from datetime import datetime, timedelta

from src.mcp.servers.google_drive.server import GoogleDriveMCPServer
from src.mcp.servers.s3.server import S3MCPServer
from src.utils.logging import log_info, log_error

class StorageSource(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    S3 = "s3"
    LOCAL = "local"

class DocumentManager:
    """Unified document manager for multiple storage sources."""
    
    def __init__(self, settings, primary_storage: StorageSource = StorageSource.GOOGLE_DRIVE):
        self.settings = settings
        self.primary_storage = primary_storage
        
        # Initialize storage clients
        self.google_drive = GoogleDriveMCPServer(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_path,
            scopes=settings.google_scopes
        ) if settings.google_credentials_path else None
        
        self.s3 = S3MCPServer(
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region,
            bucket_name=settings.s3_bucket_name
        ) if settings.aws_access_key_id else None
        
        # Authenticate Google Drive if available
        if self.google_drive:
            self.google_drive.authenticate()
    
    async def fetch_document(self, doc_id: str, source: Optional[StorageSource] = None) -> bytes:
        """Fetch a document from specified or primary storage."""
        source = source or self.primary_storage
        
        if source == StorageSource.GOOGLE_DRIVE and self.google_drive:
            # For Google Drive, doc_id should be file_id:mime_type
            file_id, mime_type = doc_id.split(':')
            return await self.google_drive.download_file(file_id, mime_type)
            
        elif source == StorageSource.S3 and self.s3:
            return await self.s3.download_object(doc_id)
            
        else:
            raise ValueError(f"Storage source {source} not available")
    
    async def sync_all_sources(self, target_collection: str = "documents") -> Dict[str, Any]:
        """Sync documents from all configured sources."""
        results = {
            'google_drive': {'synced': 0, 'errors': 0},
            's3': {'synced': 0, 'errors': 0}
        }
        
        # Sync from Google Drive
        if self.google_drive and self.settings.google_drive_folder_ids:
            for folder_id in self.settings.google_drive_folder_ids:
                try:
                    files = await self.google_drive.list_files(folder_id)
                    for file in files:
                        await self._process_and_index_file(
                            file, 
                            StorageSource.GOOGLE_DRIVE,
                            target_collection
                        )
                        results['google_drive']['synced'] += 1
                except Exception as e:
                    log_error(f"Error syncing Google Drive folder {folder_id}: {str(e)}")
                    results['google_drive']['errors'] += 1
        
        # Sync from S3
        if self.s3 and self.settings.s3_prefix:
            try:
                objects = await self.s3.list_objects(self.settings.s3_prefix)
                for obj in objects:
                    await self._process_and_index_file(
                        obj,
                        StorageSource.S3,
                        target_collection
                    )
                    results['s3']['synced'] += 1
            except Exception as e:
                log_error(f"Error syncing S3: {str(e)}")
                results['s3']['errors'] += 1
        
        return results
    
    async def archive_to_s3(self, days_old: int = 30) -> int:
        """Archive old documents from Google Drive to S3."""
        if not (self.google_drive and self.s3):
            raise ValueError("Both Google Drive and S3 must be configured for archival")
        
        archived_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for folder_id in self.settings.google_drive_folder_ids:
            files = await self.google_drive.list_files(folder_id)
            
            for file in files:
                modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
                
                if modified_time < cutoff_date:
                    # Download from Google Drive
                    content = await self.google_drive.download_file(file['id'], file['mimeType'])
                    
                    # Upload to S3 with metadata
                    s3_key = f"archive/google_drive/{folder_id}/{file['name']}"
                    metadata = {
                        'google_file_id': file['id'],
                        'google_mime_type': file['mimeType'],
                        'original_modified': file['modifiedTime']
                    }
                    
                    await self.s3.upload_object(s3_key, content, metadata)
                    archived_count += 1
                    
                    log_info(f"Archived {file['name']} to S3")
        
        return archived_count
    
    async def _process_and_index_file(self, file_info: Dict[str, Any], 
                                     source: StorageSource, 
                                     collection: str) -> None:
        """Process and index a file from any source."""
        # Implementation would integrate with your existing indexing pipeline
        log_info(f"Processing file from {source}: {file_info}")
```

### 3.2 Intelligent Routing Strategy

```python
# src/storage/routing.py
from typing import Dict, Any
from datetime import datetime, timedelta

class StorageRouter:
    """Intelligent routing for document storage."""
    
    @staticmethod
    def determine_storage(document: Dict[str, Any]) -> StorageSource:
        """Determine optimal storage location for a document."""
        
        # Active collaboration documents go to Google Drive
        if document.get('requires_collaboration', False):
            return StorageSource.GOOGLE_DRIVE
        
        # Large files go to S3
        if document.get('size', 0) > 100 * 1024 * 1024:  # 100MB
            return StorageSource.S3
        
        # Old documents go to S3
        if document.get('last_modified'):
            last_modified = datetime.fromisoformat(document['last_modified'])
            if datetime.now() - last_modified > timedelta(days=90):
                return StorageSource.S3
        
        # Archived documents go to S3
        if document.get('status') == 'archived':
            return StorageSource.S3
        
        # Default to primary storage
        return StorageSource.GOOGLE_DRIVE
```

## Detailed Implementation Comparison

### Authentication Flow Comparison

#### Google Drive OAuth2
```python
# scripts/setup_google_auth.py
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def setup_google_auth():
    """One-time setup for Google Drive OAuth2."""
    creds = None
    token_path = 'token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    print("Authentication successful!")
    return creds

if __name__ == "__main__":
    setup_google_auth()
```

#### AWS S3 Setup
```python
# scripts/setup_s3_auth.py
import boto3
from botocore.exceptions import ClientError

def verify_s3_access(access_key_id: str, secret_access_key: str, 
                    region: str, bucket_name: str) -> bool:
    """Verify S3 credentials and bucket access."""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        # Test access
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Successfully connected to S3 bucket: {bucket_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"Bucket {bucket_name} not found")
        elif error_code == '403':
            print(f"Access denied to bucket {bucket_name}")
        else:
            print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Read from environment or config
    import os
    verify_s3_access(
        os.getenv('AWS_ACCESS_KEY_ID'),
        os.getenv('AWS_SECRET_ACCESS_KEY'),
        os.getenv('AWS_REGION', 'us-east-1'),
        os.getenv('S3_BUCKET_NAME')
    )
```

### Document Processing Comparison

#### Google Drive Document Processing
```python
# src/processors/google_drive_processor.py
from typing import Dict, Any, Tuple
import io
from googleapiclient.http import MediaIoBaseDownload

class GoogleDriveProcessor:
    """Process documents from Google Drive."""
    
    EXPORT_FORMATS = {
        'application/vnd.google-apps.document': {
            'mime': 'text/plain',
            'extension': '.txt'
        },
        'application/vnd.google-apps.spreadsheet': {
            'mime': 'text/csv',
            'extension': '.csv'
        },
        'application/vnd.google-apps.presentation': {
            'mime': 'application/pdf',
            'extension': '.pdf'
        }
    }
    
    async def process_google_doc(self, file_id: str, 
                                mime_type: str, 
                                service) -> Tuple[str, bytes]:
        """Process a Google Workspace document."""
        
        if mime_type in self.EXPORT_FORMATS:
            # Export Google Workspace files
            export_mime = self.EXPORT_FORMATS[mime_type]['mime']
            request = service.files().export_media(
                fileId=file_id,
                mimeType=export_mime
            )
        else:
            # Download regular files
            request = service.files().get_media(fileId=file_id)
        
        # Download file
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download {int(status.progress() * 100)}%")
        
        content = fh.getvalue()
        
        # Extract text based on format
        if export_mime == 'text/plain':
            text = content.decode('utf-8')
        elif export_mime == 'text/csv':
            text = self._process_csv(content)
        elif export_mime == 'application/pdf':
            text = self._process_pdf(content)
        else:
            text = self._extract_text_fallback(content)
        
        return text, content
    
    def _process_csv(self, content: bytes) -> str:
        """Extract text from CSV content."""
        import csv
        import io
        
        text_stream = io.StringIO(content.decode('utf-8'))
        reader = csv.reader(text_stream)
        
        lines = []
        for row in reader:
            lines.append(' | '.join(row))
        
        return '\n'.join(lines)
    
    def _process_pdf(self, content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            import PyPDF2
            import io
            
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = []
            for page in pdf_reader.pages:
                text.append(page.extract_text())
            
            return '\n'.join(text)
        except Exception as e:
            return f"Error processing PDF: {str(e)}"
```

#### S3 Document Processing
```python
# src/processors/s3_processor.py
from typing import Dict, Any, Optional
import mimetypes
from pathlib import Path

class S3Processor:
    """Process documents from S3."""
    
    async def process_s3_object(self, key: str, content: bytes) -> Tuple[str, Dict[str, Any]]:
        """Process an S3 object."""
        
        # Determine file type
        file_path = Path(key)
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Extract metadata from path
        metadata = {
            'filename': file_path.name,
            'extension': file_path.suffix,
            'path': str(file_path.parent),
            'mime_type': mime_type
        }
        
        # Process based on file type
        if file_path.suffix.lower() in ['.txt', '.md']:
            text = content.decode('utf-8', errors='ignore')
        elif file_path.suffix.lower() == '.pdf':
            text = self._process_pdf(content)
        elif file_path.suffix.lower() in ['.doc', '.docx']:
            text = self._process_word(content)
        elif file_path.suffix.lower() in ['.csv', '.tsv']:
            text = self._process_tabular(content, file_path.suffix)
        else:
            text = f"Unsupported file type: {file_path.suffix}"
        
        return text, metadata
    
    def _process_word(self, content: bytes) -> str:
        """Extract text from Word documents."""
        try:
            import docx
            import io
            
            doc = docx.Document(io.BytesIO(content))
            
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            return '\n'.join(paragraphs)
        except Exception as e:
            return f"Error processing Word document: {str(e)}"
```

## Integration with Existing RAG System

### 1. Enhanced Indexing Script

```python
# scripts/index_from_cloud.py
#!/usr/bin/env python3
"""Enhanced indexing script supporting Google Drive and S3."""

import asyncio
import argparse
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.document_manager import DocumentManager, StorageSource
from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.contextual_chunker import ContextualChunker
from src.utils.logging import setup_logger, log_info, log_error
from src.core.config import get_settings

class CloudDocumentIndexer:
    """Index documents from cloud storage sources."""
    
    def __init__(self, collection_name: str = "documents"):
        self.settings = get_settings()
        self.collection_name = collection_name
        self.vector_client = SupabaseVectorClient(collection_name, enable_contextual=True)
        self.chunker = ContextualChunker()
        self.document_manager = DocumentManager(self.settings)
        
    async def index_from_google_drive(self, folder_ids: List[str]) -> Dict[str, Any]:
        """Index documents from Google Drive folders."""
        stats = {'processed': 0, 'errors': 0}
        
        for folder_id in folder_ids:
            log_info(f"Processing Google Drive folder: {folder_id}")
            
            try:
                files = await self.document_manager.google_drive.list_files(folder_id)
                
                for file in files:
                    try:
                        # Skip folders
                        if file['mimeType'] == 'application/vnd.google-apps.folder':
                            continue
                        
                        # Download and process
                        content = await self.document_manager.google_drive.download_file(
                            file['id'], 
                            file['mimeType']
                        )
                        
                        # Process and index
                        await self._index_document(
                            content=content.decode('utf-8', errors='ignore'),
                            metadata={
                                'source': 'google_drive',
                                'file_id': file['id'],
                                'filename': file['name'],
                                'mime_type': file['mimeType'],
                                'modified_time': file['modifiedTime'],
                                'folder_id': folder_id
                            }
                        )
                        
                        stats['processed'] += 1
                        
                    except Exception as e:
                        log_error(f"Error processing file {file['name']}: {str(e)}")
                        stats['errors'] += 1
                        
            except Exception as e:
                log_error(f"Error accessing folder {folder_id}: {str(e)}")
                stats['errors'] += 1
        
        return stats
    
    async def index_from_s3(self, prefix: str) -> Dict[str, Any]:
        """Index documents from S3."""
        stats = {'processed': 0, 'errors': 0}
        
        log_info(f"Processing S3 prefix: {prefix}")
        
        try:
            objects = await self.document_manager.s3.list_objects(prefix)
            
            for obj in objects:
                try:
                    # Download object
                    content = await self.document_manager.s3.download_object(obj['key'])
                    
                    # Get metadata
                    metadata = await self.document_manager.s3.get_object_metadata(obj['key'])
                    
                    # Process and index
                    await self._index_document(
                        content=content.decode('utf-8', errors='ignore'),
                        metadata={
                            'source': 's3',
                            'key': obj['key'],
                            'size': obj['size'],
                            'last_modified': obj['last_modified'],
                            'etag': obj['etag'],
                            **metadata.get('metadata', {})
                        }
                    )
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    log_error(f"Error processing S3 object {obj['key']}: {str(e)}")
                    stats['errors'] += 1
                    
        except Exception as e:
            log_error(f"Error accessing S3: {str(e)}")
            stats['errors'] += 1
        
        return stats
    
    async def _index_document(self, content: str, metadata: Dict[str, Any]) -> None:
        """Index a document with contextual chunking."""
        
        # Create contextual chunks
        chunks_with_context = self.chunker.create_contextual_chunks(
            content=content,
            context_info={
                'source_type': metadata['source'],
                'filename': metadata.get('filename', metadata.get('key', 'unknown')),
                **metadata
            },
            use_llm_context=False
        )
        
        # Add to vector store
        for chunk in chunks_with_context:
            self.vector_client.add_documents(
                documents=[chunk.contextual_text],
                metadatas=[chunk.metadata]
            )
        
        log_info(f"Indexed {len(chunks_with_context)} chunks from {metadata.get('filename', 'document')}")

async def main():
    parser = argparse.ArgumentParser(description="Index documents from cloud storage")
    parser.add_argument("--source", choices=["google_drive", "s3", "both"], 
                       default="both", help="Storage source to index from")
    parser.add_argument("--collection", default="documents", 
                       help="Target collection name")
    parser.add_argument("--google-folders", nargs="+", 
                       help="Google Drive folder IDs")
    parser.add_argument("--s3-prefix", default="documents/", 
                       help="S3 prefix to index")
    
    args = parser.parse_args()
    
    setup_logger("cloud_indexer")
    
    indexer = CloudDocumentIndexer(args.collection)
    
    if args.source in ["google_drive", "both"] and args.google_folders:
        stats = await indexer.index_from_google_drive(args.google_folders)
        log_info(f"Google Drive: Processed {stats['processed']}, Errors {stats['errors']}")
    
    if args.source in ["s3", "both"]:
        stats = await indexer.index_from_s3(args.s3_prefix)
        log_info(f"S3: Processed {stats['processed']}, Errors {stats['errors']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Update Primary Agent

```python
# src/agents/primary.py additions
from src.agents.google_drive import GoogleDriveAgent
from src.agents.s3_storage import S3StorageAgent

# In __init__ method:
self.google_drive_agent = GoogleDriveAgent(model, settings) if settings.google_credentials_path else None
self.s3_agent = S3StorageAgent(model, settings) if settings.aws_access_key_id else None

# In route_request method:
if "google drive" in request_lower or "drive" in request_lower:
    if self.google_drive_agent:
        return await self.google_drive_agent.run(request, deps=deps)
    else:
        return "Google Drive is not configured. Please set up Google Drive credentials."

if "s3" in request_lower or "aws" in request_lower:
    if self.s3_agent:
        return await self.s3_agent.run(request, deps=deps)
    else:
        return "AWS S3 is not configured. Please set up AWS credentials."
```

### 3. Database Schema Updates

```sql
-- Supabase migration for cloud storage tracking
CREATE TABLE IF NOT EXISTS document_sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_source VARCHAR(50) NOT NULL,
    storage_id VARCHAR(500) NOT NULL,
    storage_path TEXT,
    last_sync TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(storage_source, storage_id)
);

-- Index for efficient lookups
CREATE INDEX idx_sync_status_source ON document_sync_status(storage_source, sync_status);
CREATE INDEX idx_sync_status_updated ON document_sync_status(updated_at);

-- Function to track sync status
CREATE OR REPLACE FUNCTION update_sync_status(
    p_source VARCHAR,
    p_storage_id VARCHAR,
    p_status VARCHAR,
    p_error TEXT DEFAULT NULL
) RETURNS void AS $$
BEGIN
    INSERT INTO document_sync_status (storage_source, storage_id, sync_status, error_message)
    VALUES (p_source, p_storage_id, p_status, p_error)
    ON CONFLICT (storage_source, storage_id)
    DO UPDATE SET 
        sync_status = EXCLUDED.sync_status,
        error_message = EXCLUDED.error_message,
        last_sync = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;
```

## Performance Comparison

### Throughput Analysis

| Operation | Google Drive | AWS S3 |
|-----------|-------------|---------|
| List 1000 files | 20-30 seconds | 2-3 seconds |
| Download 100MB | 10-15 seconds | 3-5 seconds |
| Concurrent downloads | Limited (10) | Unlimited* |
| API rate limit | 1000 req/100s | No limit |
| Max file size | 5TB | 5TB |

*Limited by bandwidth and connection pool

### Cost Analysis (Monthly)

| Storage Amount | Google Drive | AWS S3 Standard | AWS S3 IA |
|---------------|--------------|-----------------|-----------|
| 100 GB | $1.99 | $2.30 | $1.25 |
| 1 TB | $9.99 | $23.00 | $12.50 |
| 10 TB | $99.99 | $230.00 | $125.00 |
| Transfer (1TB) | Free | $90.00 | $90.00 |

### Optimization Strategies

#### Google Drive Optimization
```python
# Batch operations to reduce API calls
def batch_download_gdrive(service, file_ids: List[str]):
    batch = service.new_batch_http_request()
    
    for file_id in file_ids:
        batch.add(service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,modifiedTime'
        ))
    
    return batch.execute()

# Use fields parameter to reduce response size
results = service.files().list(
    q=query,
    fields="files(id,name,mimeType)",  # Only request needed fields
    pageSize=1000  # Max page size
).execute()
```

#### S3 Optimization
```python
# Use multipart download for large files
async def download_large_file_s3(s3_client, bucket: str, key: str, 
                                chunk_size: int = 1024 * 1024):
    """Download large files in chunks."""
    response = await s3_client.head_object(Bucket=bucket, Key=key)
    file_size = response['ContentLength']
    
    chunks = []
    for start in range(0, file_size, chunk_size):
        end = min(start + chunk_size - 1, file_size - 1)
        
        response = await s3_client.get_object(
            Bucket=bucket,
            Key=key,
            Range=f'bytes={start}-{end}'
        )
        
        chunk = await response['Body'].read()
        chunks.append(chunk)
    
    return b''.join(chunks)

# Use S3 Select for filtering
async def query_s3_json(s3_client, bucket: str, key: str, sql_expression: str):
    """Query JSON data directly in S3."""
    response = await s3_client.select_object_content(
        Bucket=bucket,
        Key=key,
        Expression=sql_expression,
        ExpressionType='SQL',
        InputSerialization={'JSON': {'Type': 'LINES'}},
        OutputSerialization={'JSON': {}}
    )
    
    # Process streaming response
    records = []
    async for event in response['Payload']:
        if 'Records' in event:
            records.append(event['Records']['Payload'])
    
    return b''.join(records)
```

## Migration Strategy

### Phase 1: Assessment (Week 1)
1. Inventory existing documents
2. Categorize by type, size, and usage
3. Estimate storage costs
4. Plan access patterns

### Phase 2: Setup (Week 2)
1. Configure authentication for chosen solution
2. Set up development environment
3. Create test collections
4. Implement basic sync scripts

### Phase 3: Pilot Migration (Week 3-4)
1. Start with non-critical documents
2. Test sync and indexing
3. Validate search functionality
4. Monitor performance

### Phase 4: Full Migration (Week 5-6)
1. Migrate remaining documents
2. Update all references
3. Set up automated sync
4. Implement monitoring

### Phase 5: Optimization (Week 7-8)
1. Analyze usage patterns
2. Implement caching
3. Optimize costs
4. Set up archival policies

## Monitoring & Maintenance

### Key Metrics

```python
# src/monitoring/storage_metrics.py
from datetime import datetime
from typing import Dict, Any
import asyncio

class StorageMetricsCollector:
    """Collect metrics for storage operations."""
    
    def __init__(self):
        self.metrics = {
            'sync_operations': [],
            'errors': [],
            'performance': []
        }
    
    async def record_sync(self, source: str, count: int, 
                         duration: float, errors: int = 0):
        """Record sync operation metrics."""
        self.metrics['sync_operations'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'source': source,
            'documents_synced': count,
            'duration_seconds': duration,
            'errors': errors,
            'success_rate': (count - errors) / count if count > 0 else 0
        })
    
    async def record_error(self, source: str, operation: str, 
                          error: str, context: Dict[str, Any] = None):
        """Record error details."""
        self.metrics['errors'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'source': source,
            'operation': operation,
            'error': error,
            'context': context or {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_synced = sum(op['documents_synced'] 
                          for op in self.metrics['sync_operations'])
        total_errors = sum(op['errors'] 
                          for op in self.metrics['sync_operations'])
        
        return {
            'total_documents_synced': total_synced,
            'total_errors': total_errors,
            'success_rate': (total_synced - total_errors) / total_synced 
                           if total_synced > 0 else 0,
            'operations_count': len(self.metrics['sync_operations']),
            'recent_errors': self.metrics['errors'][-10:]  # Last 10 errors
        }
```

### Automated Sync Workflow

```yaml
# .github/workflows/sync-cloud-documents.yml
name: Sync Cloud Documents

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-cloud.txt
    
    - name: Sync from Google Drive
      env:
        GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
        SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
      run: |
        echo "$GOOGLE_CREDENTIALS" > credentials.json
        python scripts/index_from_cloud.py --source google_drive
    
    - name: Sync from S3
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      run: |
        python scripts/index_from_cloud.py --source s3
    
    - name: Generate sync report
      run: |
        python scripts/generate_sync_report.py
    
    - name: Notify on failure
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          github.rest.issues.create({
            owner: context.repo.owner,
            repo: context.repo.repo,
            title: 'Document Sync Failed',
            body: 'The automated document sync workflow failed. Check the logs.'
          })
```

## Decision Matrix

### Feature Comparison

| Feature | Google Drive | AWS S3 | Hybrid Approach |
|---------|-------------|---------|-----------------|
| **Setup Complexity** | Medium (OAuth) | Low (API keys) | High |
| **Cost (1TB/month)** | $9.99 | $23 + transfer | ~$30 |
| **Collaboration** | Excellent | None | Good |
| **Search** | Built-in | Requires setup | Both |
| **API Performance** | Good | Excellent | Excellent |
| **Scalability** | Limited | Unlimited | Unlimited |
| **File Size Limit** | 5TB | 5TB | 5TB |
| **Versioning** | Automatic | Optional | Both |
| **Access Control** | User-based | IAM policies | Both |
| **Developer Experience** | Good | Excellent | Complex |

### Use Case Recommendations

**Choose Google Drive if:**
- Team actively collaborates on documents
- You need built-in search and preview
- Storage needs are under 2TB
- You prefer UI-based management

**Choose S3 if:**
- You have large-scale storage needs (>10TB)
- Cost is a primary concern
- You need programmatic access only
- You're already using AWS services

**Choose Hybrid if:**
- You have diverse document types
- Different teams have different needs
- You want to optimize costs
- You need both collaboration and scale

## Quick Start Guide

### Google Drive Quick Start

```bash
# 1. Install dependencies
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# 2. Download credentials from Google Cloud Console
# Save as credentials.json

# 3. Run authentication setup
python scripts/setup_google_auth.py

# 4. Configure environment
echo "GOOGLE_CREDENTIALS_PATH=credentials.json" >> local.env
echo "GOOGLE_TOKEN_PATH=token.json" >> local.env
echo "GOOGLE_DRIVE_FOLDER_IDS=your_folder_id_here" >> local.env

# 5. Test connection
python scripts/test_google_drive.py

# 6. Start syncing
python scripts/index_from_cloud.py --source google_drive
```

### S3 Quick Start

```bash
# 1. Install dependencies
pip install boto3 aioboto3

# 2. Configure AWS credentials
echo "AWS_ACCESS_KEY_ID=your_key_here" >> local.env
echo "AWS_SECRET_ACCESS_KEY=your_secret_here" >> local.env
echo "AWS_REGION=us-east-1" >> local.env
echo "S3_BUCKET_NAME=your-bucket-name" >> local.env

# 3. Test connection
python scripts/test_s3.py

# 4. Start syncing
python scripts/index_from_cloud.py --source s3 --s3-prefix documents/
```

### Hybrid Setup

```bash
# 1. Complete both Google Drive and S3 setup above

# 2. Configure primary storage
echo "PRIMARY_STORAGE=google_drive" >> local.env

# 3. Set up archival rules
echo "ARCHIVE_DAYS_OLD=90" >> local.env
echo "ARCHIVE_TO_S3=true" >> local.env

# 4. Run full sync
python scripts/index_from_cloud.py --source both

# 5. Set up automated archival
python scripts/archive_old_documents.py
```

## Conclusion

This implementation plan provides comprehensive coverage for integrating both Google Drive and AWS S3 with your existing RAG system. The hybrid approach offers the best of both worlds, allowing you to leverage Google Drive's collaboration features for active documents while using S3's cost-effectiveness for long-term storage.

Key recommendations:
1. Start with Google Drive for ease of use
2. Add S3 for cost-effective archival
3. Implement the hybrid approach as you scale
4. Monitor usage patterns to optimize storage distribution
5. Automate sync and archival processes

The modular design ensures you can start with one solution and easily add the other later without major refactoring.