# C4 Model - Level 1: System Context Diagram

```mermaid
C4Context
    title System Context Diagram - Multi-Agent Automation System
    
    Person(user, "User", "Software engineer, project manager, or knowledge worker")
    
    System(automation_agents, "Automation Agents System", "Multi-agent system with RAG for automation, QA, and intelligent document processing")
    
    System_Ext(openai, "OpenAI API", "GPT models for language processing and vision analysis")
    System_Ext(brave_search, "Brave Search API", "Web search and research capabilities")
    System_Ext(github, "GitHub API", "Repository management and development workflows")
    System_Ext(slack, "Slack API", "Team communication and notifications")
    System_Ext(filesystem, "File System", "Local files, documents, and knowledge base")
    
    Rel(user, automation_agents, "Interacts with", "CLI commands, queries, planning requests")
    Rel(automation_agents, openai, "Uses", "GPT-4o for text generation, GPT-4o for image analysis")
    Rel(automation_agents, brave_search, "Searches", "Web content, research queries")
    Rel(automation_agents, github, "Manages", "Repositories, issues, workflows")
    Rel(automation_agents, slack, "Sends", "Messages, notifications")
    Rel(automation_agents, filesystem, "Reads/Writes", "Documents, images, data files")
    
    UpdateRelStyle(user, automation_agents, $textColor="blue", $lineColor="blue")
    UpdateRelStyle(automation_agents, openai, $textColor="green", $lineColor="green")
    UpdateRelStyle(automation_agents, brave_search, $textColor="orange", $lineColor="orange")
    UpdateRelStyle(automation_agents, github, $textColor="purple", $lineColor="purple")
    UpdateRelStyle(automation_agents, slack, $textColor="red", $lineColor="red")
    UpdateRelStyle(automation_agents, filesystem, $textColor="brown", $lineColor="brown")
```

## System Overview

The **Multi-Agent Automation System** is a sophisticated AI-powered automation platform that orchestrates specialized agents to handle various tasks including:

- **Web Search & Research** via Brave Search API
- **File Management & Analysis** through filesystem operations
- **Code Analysis & Development** using GitHub integration
- **Team Communication** via Slack notifications
- **Document Processing & RAG** with ChromaDB vector storage
- **Calendar & Conversation Analysis** using OpenAI Vision API

## Key Actors

- **User**: Primary actor who interacts with the system through CLI commands for automation tasks, planning, and information retrieval

## External Systems

- **OpenAI API**: Provides language models (GPT-4o-mini, GPT-4o) for text generation and vision analysis
- **Brave Search API**: Enables web search and research capabilities
- **GitHub API**: Facilitates repository management and development workflows
- **Slack API**: Handles team communication and notification delivery
- **File System**: Stores and manages local documents, images, and knowledge base files

## Core Capabilities

1. **Multi-Agent Orchestration**: Intelligent routing of requests to specialized agents
2. **RAG-Enhanced Knowledge Retrieval**: Vector-based search through indexed documents
3. **Image Analysis**: Calendar and conversation extraction from screenshots
4. **Planning & Task Management**: YAML-based task and meeting management
5. **Model Context Protocol (MCP)**: Extensible server architecture for tool integration