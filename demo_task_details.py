#!/usr/bin/env python3
"""
Demo script showing task details functionality.

This script demonstrates the relationship between tasks and task details,
and how they integrate with the planner system.
"""
import sys
sys.path.append('.')

from src.agents.planner import (
    get_task_details,
    get_task_details_markdown,
    list_all_tasks_with_details
)
from src.agents.planner_task_details import (
    create_task_detail,
    update_task_detail,
    delete_task_detail
)


def main():
    print("=" * 60)
    print("TASK DETAILS INTEGRATION DEMO")
    print("=" * 60)
    print()

    # 1. Show current tasks and their detail status
    print("1. CURRENT TASKS AND DETAIL STATUS")
    print("-" * 40)
    
    result = list_all_tasks_with_details()
    if result.get('success'):
        tasks = result['tasks']
        for task in tasks:
            status = "✓ HAS DETAILS" if task['has_details'] else "✗ No details"
            print(f"{task['id']}: {task['title']}")
            print(f"   Status: {task['status']}, Priority: {task['priority']}")
            print(f"   Details: {status}")
            print()
    
    # 2. Show detailed breakdown for a task with details
    print("2. DETAILED BREAKDOWN - Task 111025")
    print("-" * 40)
    
    result = get_task_details('111025')
    if result.get('success'):
        summary = result['summary']
        print(f"Title: {summary['title']}")
        print(f"Status: {summary['status']}")
        print(f"Priority: {summary['priority']}")
        print()
        
        print("Objective:")
        print(f"  {summary['objective']}")
        print()
        
        print(f"Subtasks ({summary['subtasks_count']}):")
        for i, subtask in enumerate(summary['subtasks'], 1):
            print(f"  {i}. {subtask}")
        print()
        
        print(f"Acceptance Criteria ({summary['acceptance_criteria_count']}):")
        for i, criterion in enumerate(summary['acceptance_criteria'], 1):
            if isinstance(criterion, dict):
                for key, value in criterion.items():
                    print(f"  {i}. {key}:")
                    if isinstance(value, list):
                        for item in value:
                            print(f"     - {item}")
                    else:
                        print(f"     - {value}")
            else:
                print(f"  {i}. {criterion}")
    print()
    
    # 3. Show markdown formatting
    print("3. MARKDOWN FORMATTING")
    print("-" * 40)
    
    result = get_task_details_markdown('111025')
    if result.get('success'):
        markdown = result['markdown']
        lines = markdown.split('\n')
        # Show first 15 lines
        for line in lines[:15]:
            print(line)
        if len(lines) > 15:
            print("... (truncated)")
    print()
    
    # 4. Demonstrate creating task details for a task without them
    print("4. CREATING TASK DETAILS FOR EXISTING TASK")
    print("-" * 40)
    
    print("Creating detailed breakdown for TASK-1 (job search)...")
    
    result = create_task_detail(
        task_id='TASK-1',
        title='Comprehensive Job Search Strategy',
        objective='Execute a systematic and targeted job search to secure a senior-level position in automation/AI engineering within 2-4 weeks.',
        tasks=[
            'Update and optimize resume for automation/AI roles',
            'Research target companies and their technology stacks',
            'Apply to 5-10 positions per week on relevant job boards',
            'Network with professionals in automation and AI field',
            'Prepare for technical interviews with coding practice',
            'Follow up on applications and maintain application tracking'
        ],
        acceptance_criteria=[
            'Resume is updated with latest projects and skills',
            'Target company list of 20+ companies is compiled',
            'Minimum 5 applications submitted per week',
            'At least 2 networking conversations per week',
            'Complete 3+ coding challenges or technical assessments',
            'Interview preparation materials are ready',
            'Application tracking system is set up and maintained'
        ]
    )
    
    if result.get('success'):
        print("✓ Task details created successfully!")
        
        # Show the enhanced task info
        enhanced_result = get_task_details('TASK-1')
        if enhanced_result.get('success'):
            summary = enhanced_result['summary']
            print(f"Now has {summary['subtasks_count']} subtasks and {summary['acceptance_criteria_count']} acceptance criteria")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    print()
    
    # 5. Show final status
    print("5. FINAL TASK STATUS")
    print("-" * 40)
    
    result = list_all_tasks_with_details()
    if result.get('success'):
        tasks = result['tasks']
        tasks_with_details = [t for t in tasks if t['has_details']]
        tasks_without_details = [t for t in tasks if not t['has_details']]
        
        print(f"Tasks with detailed breakdowns: {len(tasks_with_details)}")
        for task in tasks_with_details:
            print(f"  ✓ {task['id']}: {task['title']}")
        
        print(f"\nTasks without detailed breakdowns: {len(tasks_without_details)}")
        for task in tasks_without_details:
            print(f"  ✗ {task['id']}: {task['title']}")
    
    print()
    print("=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    main()