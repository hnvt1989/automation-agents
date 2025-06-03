#!/usr/bin/env python3
"""
Demo script for task brainstorming functionality.

This script demonstrates the brainstorming feature that integrates RAG and LLM
capabilities to generate comprehensive brainstorming sessions for tasks.
"""
import sys
import asyncio
sys.path.append('.')

from src.agents.planner import brainstorm_task, get_task_brainstorm
from src.agents.task_brainstorm import BrainstormManager, parse_brainstorm_query, find_task_by_query


async def demo_brainstorming():
    print("=" * 70)
    print("TASK BRAINSTORMING DEMO")
    print("=" * 70)
    print()

    # 1. Show query parsing capabilities
    print("1. QUERY PARSING DEMONSTRATION")
    print("-" * 50)
    
    test_queries = [
        'brainstorm task id 111025',
        'brainstorm task title TestRail',
        'brainstorm task with title job search',
        'replace brainstorm for task 111025',
        'improve brainstorm for task TASK-1'
    ]
    
    for query in test_queries:
        result = parse_brainstorm_query(query)
        print(f"Query: \"{query}\"")
        print(f"Parsed: {result}")
        print()

    # 2. Show task finding capabilities
    print("2. TASK FINDING DEMONSTRATION")
    print("-" * 50)
    
    # Find by ID
    task_info = find_task_by_query('id', '111025')
    if task_info:
        print("✓ Found task by ID 111025:")
        print(f"  Title: {task_info['basic_task']['title']}")
        print(f"  Status: {task_info['basic_task']['status']}")
        if task_info.get('task_detail'):
            print(f"  Has detailed breakdown: Yes")
            print(f"  Objective: {task_info['task_detail']['objective'][:100]}...")
        else:
            print(f"  Has detailed breakdown: No")
    else:
        print("❌ Task 111025 not found")
    print()
    
    # Find by title
    task_info = find_task_by_query('title', 'TestRail')
    if task_info:
        print("✓ Found task by title containing 'TestRail':")
        print(f"  ID: {task_info['basic_task']['id']}")
        print(f"  Full Title: {task_info['basic_task']['title']}")
    else:
        print("❌ No task found with title containing 'TestRail'")
    print()

    # 3. Demonstrate brainstorm manager
    print("3. BRAINSTORM MANAGER DEMONSTRATION")
    print("-" * 50)
    
    manager = BrainstormManager(
        brainstorm_file='demo_brainstorms.md',
        tasks_file='data/tasks.yaml',
        task_details_file='data/task_details.yaml'
    )
    
    print("✓ BrainstormManager created successfully")
    print("   - Brainstorm file: demo_brainstorms.md")
    print("   - Tasks file: data/tasks.yaml")
    print("   - Task details file: data/task_details.yaml")
    print()

    # Note: We'll skip the actual LLM/RAG generation in the demo
    # since it requires API keys and external dependencies
    print("4. BRAINSTORM WORKFLOW (STRUCTURE DEMO)")
    print("-" * 50)
    
    print("Note: This demo shows the structure without calling actual LLM/RAG APIs")
    print("In a real scenario, the system would:")
    print("1. Parse the brainstorm query")
    print("2. Find the target task and its details")
    print("3. Search the RAG knowledge base for relevant context")
    print("4. Generate brainstorm content using LLM")
    print("5. Save the brainstorm to markdown file")
    print("6. Return the formatted brainstorm content")
    print()
    
    # Show what a brainstorm structure would look like
    from src.agents.task_brainstorm import TaskBrainstorm
    from datetime import datetime
    
    sample_brainstorm = TaskBrainstorm(
        task_id='111025',
        task_title='Explore weekly Automated Test coverage Sync to TestRail',
        brainstorm_type='initial',
        generated_at=datetime.now(),
        content={
            'overview': 'This task involves integrating automated test coverage reporting with TestRail to improve visibility into testing gaps and provide better context for manual testing needs.',
            'considerations': [
                'TestRail API rate limits and authentication requirements',
                'Different coverage report formats from frontend vs backend tools',
                'Data consistency and accuracy of coverage metrics',
                'Integration frequency and performance impact'
            ],
            'approaches': [
                'Direct API integration using TestRail REST API',
                'Scheduled batch processing of coverage reports',
                'Real-time webhook-based integration',
                'Custom dashboard with TestRail data export'
            ],
            'risks': [
                'API authentication and access control issues',
                'Coverage data accuracy and interpretation challenges',
                'Performance impact on CI/CD pipeline',
                'Maintenance overhead for multiple tool integrations'
            ],
            'recommendations': [
                'Start with a pilot integration using one coverage tool',
                'Implement proper error handling and retry mechanisms',
                'Create comprehensive documentation for the integration process',
                'Set up monitoring and alerting for the integration pipeline'
            ]
        },
        rag_context=[
            'TestRail provides REST API endpoints for test management operations',
            'Coverage tools like Jest, Istanbul, and SonarQube generate detailed reports',
            'CI/CD pipeline integration requires careful consideration of performance impact'
        ],
        sources=[
            'TestRail API documentation',
            'Coverage tool integration guides',
            'CI/CD best practices documentation'
        ]
    )
    
    print("5. SAMPLE BRAINSTORM OUTPUT")
    print("-" * 50)
    
    markdown = sample_brainstorm.to_markdown()
    print(markdown)

    print("6. INTEGRATION WITH PLANNER SYSTEM")
    print("-" * 50)
    
    print("The brainstorming functionality integrates with the planner through:")
    print("• brainstorm_task(query) - Process natural language brainstorm requests")
    print("• get_task_brainstorm(task_id) - Retrieve existing brainstorms")
    print("• Support for force regeneration and improvement of existing brainstorms")
    print("• Automatic saving to task_brainstorms.md file")
    print()
    
    print("Example usage:")
    print("  result = await brainstorm_task('brainstorm task id 111025')")
    print("  existing = await get_task_brainstorm('111025')")
    print("  improved = await brainstorm_task('improve brainstorm for task 111025')")
    print()

    print("=" * 70)
    print("BRAINSTORMING DEMO COMPLETED")
    print("=" * 70)
    print()
    print("To use with real LLM/RAG capabilities:")
    print("1. Ensure OpenAI API key is configured")
    print("2. Ensure ChromaDB has indexed relevant documentation")
    print("3. Use: await brainstorm_task('brainstorm task id 111025')")


if __name__ == '__main__':
    asyncio.run(demo_brainstorming())