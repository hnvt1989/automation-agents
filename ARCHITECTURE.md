# System Architecture

This document outlines the architecture of the automation agents system.

## Overview

The system is designed as a collection of specialized agents that can be orchestrated to perform a variety of tasks. The core of the system is a `PrimaryAgent` that can delegate tasks to other agents, such as a `BraveSearchAgent` for web searches, a `FilesystemAgent` for local file operations, and a `CloudRAGAgent` for retrieving information from a knowledge base.

The system provides two main interfaces:

1.  A **FastAPI-based web server** that exposes a REST API and a WebSocket endpoint for interacting with the agents from a web-based frontend.
2.  A **command-line interface (CLI)** that allows users to interact with the agents from the terminal.

## Core Components

### 1. Agents

The `src/agents` directory contains the implementation of the various agents:

-   **`PrimaryAgent`**: The central orchestrator that receives user queries and delegates them to the appropriate specialized agent.
-   **`BraveSearchAgent`**: An agent that uses the Brave Search API to perform web searches.
-   **`FilesystemAgent`**: An agent that can read, write, and list files on the local filesystem.
-   **`CloudRAGAgent`**: An agent that performs Retrieval-Augmented Generation (RAG) using a cloud-based vector store (Supabase) and a knowledge graph (Neo4j).
-   **`PlannerAgent`**: An agent that can generate daily plans and manage tasks.
-   **`AnalyzerAgent`**: An agent that can analyze data, such as meeting notes, to suggest tasks and provide insights.

### 2. Storage

The `src/storage` directory contains the modules responsible for data persistence:

-   **Supabase**: Used as the primary data store for tasks, documents, notes, and logs. It is also used as a vector store for the `CloudRAGAgent`.
-   **Neo4j**: Used as a graph database to store a knowledge graph, which is also used by the `CloudRAGAgent`.
-   **Local Filesystem**: The system also uses the local filesystem to store some data, such as configuration files and temporary files.

### 3. API Server

The `src/api_server.py` file defines a FastAPI application that provides the following features:

-   **REST API**: A set of endpoints for managing tasks, documents, notes, and logs.
-   **WebSocket Endpoint**: A WebSocket endpoint for real-time, streaming communication with the `PrimaryAgent`.
-   **CORS Middleware**: The server is configured with CORS middleware to allow requests from the frontend.

### 4. Command-Line Interface (CLI)

The `src/main.py` file provides a CLI for interacting with the agents. The CLI supports the following features:

-   **Interactive Prompt**: An interactive prompt for sending queries to the `PrimaryAgent`.
-   **Planning**: A `plan` command for generating daily plans.
-   **Help**: A `help` command for displaying help information.

### 5. Configuration

The `src/core/config.py` file manages the application's configuration using Pydantic's `BaseSettings`. The configuration is loaded from a `local.env` file.

## Frontend

The `frontend` directory contains a React-based web application that provides a user interface for interacting with the system. The frontend communicates with the backend using the REST API and the WebSocket endpoint.

## High-Level Diagram

```
+-----------------+      +------------------+      +-----------------+
|     Frontend    |----->|    API Server    |<---->|   PrimaryAgent  |
+-----------------+      +------------------+      +-----------------+
        |                      ^                            |
        |                      |                            |
        v                      v                            v
+-----------------+      +------------------+      +-----------------+
|       CLI       |      |      Storage     |      |  Specialized   |
|                 |      | (Supabase, Neo4j)|      |     Agents      |
+-----------------+      +------------------+      +-----------------+
```
