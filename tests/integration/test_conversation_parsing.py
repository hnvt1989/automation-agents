"""Integration tests for conversation screenshot parsing functionality."""

import pytest
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

from src.processors.image import (
    extract_text_from_image, 
    parse_conversation_from_text,
    process_conversation_and_index
)


class TestConversationParsingIntegration:
    """Integration tests for conversation screenshot parsing."""

    @pytest.fixture
    def sample_conversation_texts(self):
        """Sample conversation text data from various platforms."""
        return {
            "slack_conversation": """
Alice Johnson  12:34 PM
Hey team, are we still on for the sprint demo tomorrow?

Bob Smith  12:35 PM
Yes! I've got the presentation ready. Should take about 30 minutes.

Charlie Brown  12:36 PM
Perfect. I'll send out the meeting invite with the demo link.

Alice Johnson  12:37 PM
Great! Don't forget to include the QA team.
👍 2

Bob Smith  12:38 PM
Already on it. The demo covers all the new features we implemented this sprint.

David Wilson  12:40 PM
Looking forward to it! Any specific areas you want feedback on?

Alice Johnson  12:41 PM
Mainly the user interface changes and performance improvements.
💯 1 ✅ 3

Charlie Brown  12:42 PM
I'll record the session for anyone who can't attend live.
""",
            "discord_conversation": """
TechLead_Sarah — Today at 2:15 PM
@channel Quick update on the database migration

DevOps_Mike — Today at 2:16 PM
I've been monitoring the performance metrics

Junior_Dev_Emma — Today at 2:17 PM
Should I hold off on deploying my feature branch?

TechLead_Sarah — Today at 2:18 PM
@Junior_Dev_Emma Yes, let's wait until after the migration completes

Senior_Dev_Alex — Today at 2:20 PM
ETA on completion?

DevOps_Mike — Today at 2:21 PM
Should be done by 4 PM today. All systems looking good so far.
⚡ 2 ✅ 4

TechLead_Sarah — Today at 2:22 PM
Thanks for the update! I'll notify the team once it's complete.

Junior_Dev_Emma — Today at 2:23 PM
Sounds good, I'll keep my branch ready for deployment tomorrow.
👍 1
""",
            "teams_conversation": """
Anna Thompson
2:45 PM
Hi everyone, I wanted to discuss the quarterly review agenda

Mark Davis  
2:46 PM
Good timing! I just finished compiling the metrics report

Lisa Chen
2:47 PM
Should we include the customer satisfaction scores?

Anna Thompson
2:48 PM
Absolutely. Mark, can you add those to your report?

Mark Davis
2:49 PM
Already included! Customer satisfaction is up 15% this quarter

James Wilson
2:51 PM
That's fantastic news! Any insights on what drove the improvement?

Lisa Chen
2:52 PM
I think it's the new onboarding process we implemented

Anna Thompson
2:53 PM
Great point. Let's make sure to highlight that in the presentation

Mark Davis
2:55 PM
I'll add a section specifically about the onboarding improvements
""",
            "whatsapp_conversation": """
Mom
Today, 10:30 AM
Don't forget about dinner tonight at 6 PM

You
Today, 10:35 AM
I'll be there! Should I bring anything?

Mom
Today, 10:37 AM
Just yourself 😊 Your dad is making his famous lasagna

Sister
Today, 10:40 AM
Can't wait! I'll bring dessert

You  
Today, 10:42 AM
Perfect! See you all at 6

Mom
Today, 10:45 AM
Love you both ❤️

Sister
Today, 10:46 AM
Love you too! 🥰
""",
            "mixed_platform_conversation": """
Sarah (Slack) - 9:00 AM
Starting the standup now

Mike via Teams - 9:01 AM  
Connected from the mobile app

Emma@Discord - 9:02 AM
Here! Working on the API integration today

Alex (Slack) - 9:03 AM
I'll focus on the frontend components

Sarah (Slack) - 9:04 AM
Great! Any blockers from yesterday?

Mike via Teams - 9:05 AM
Still waiting for the design specs from the UX team

Emma@Discord - 9:06 AM
Same here. Need those wireframes to proceed

Alex (Slack) - 9:07 AM
I can help bridge that gap. Let me reach out to the design team

Sarah (Slack) - 9:08 AM
Perfect! Thanks Alex. Let's sync up again this afternoon
""",
            "code_review_conversation": """
reviewer_john  2 hours ago
@author_sarah This looks good overall, but I have a few suggestions

author_sarah  2 hours ago  
Thanks for the quick review! What changes would you recommend?

reviewer_john  2 hours ago
Line 45: Consider using a more descriptive variable name
Line 78: This function could be broken down into smaller methods

author_sarah  1 hour ago
Good points! I'll refactor those sections and push an update

reviewer_mike  1 hour ago
Also noticed on line 92: potential memory leak with the event listeners

author_sarah  1 hour ago
@reviewer_mike You're absolutely right. I'll add proper cleanup in the useEffect hook

reviewer_john  1 hour ago
Once those changes are made, this should be ready to merge

author_sarah  45 minutes ago
Changes pushed! Please take another look when you have a chance

reviewer_mike  30 minutes ago
✅ Looks great now! LGTM

reviewer_john  25 minutes ago  
Approved! Nice work on the refactoring
"""
        }

    @pytest.fixture
    def sample_conversation_images(self, temp_dir):
        """Create sample conversation screenshot files."""
        conversation_images = {}
        
        # Create mock screenshot files with platform-specific names
        screenshot_files = [
            "slack_conversation_2025_06_02.png",
            "discord_chat_screenshot.jpg",
            "teams_meeting_chat.png", 
            "whatsapp_conversation.jpg",
            "zoom_chat_export.png",
            "code_review_comments.png"
        ]
        
        for filename in screenshot_files:
            image_path = temp_dir / filename
            # Create mock image file
            image_path.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')  # PNG header
            conversation_images[filename] = str(image_path)
        
        return conversation_images

    @pytest.mark.asyncio
    async def test_basic_conversation_parsing(self, sample_conversation_texts):
        """Test basic conversation parsing functionality."""
        slack_text = sample_conversation_texts["slack_conversation"]
        
        # Parse the conversation
        conversation = await parse_conversation_from_text(slack_text, "test_slack.png")
        
        assert conversation is not None
        assert conversation.platform == "slack"
        assert len(conversation.messages) >= 6
        
        # Verify message structure
        first_message = conversation.messages[0]
        assert first_message.speaker == "Alice Johnson"
        assert "12:34 PM" in first_message.timestamp
        assert "sprint demo tomorrow" in first_message.content
        
        # Verify participants are extracted
        assert "Alice Johnson" in conversation.participants
        assert "Bob Smith" in conversation.participants
        assert "Charlie Brown" in conversation.participants

    @pytest.mark.asyncio
    async def test_multiple_platform_parsing(self, sample_conversation_texts):
        """Test parsing conversations from different platforms."""
        platform_tests = [
            ("discord_conversation", "discord"),
            ("teams_conversation", "teams"),  
            ("whatsapp_conversation", "whatsapp")
        ]
        
        for text_key, expected_platform in platform_tests:
            conversation_text = sample_conversation_texts[text_key]
            conversation = await parse_conversation_from_text(conversation_text, f"test_{expected_platform}.png")
            
            assert conversation is not None, f"Failed to parse {expected_platform} conversation"
            assert conversation.platform == expected_platform
            assert len(conversation.messages) > 0
            assert len(conversation.participants) > 0
            
            # Verify timestamp parsing
            for message in conversation.messages:
                assert message.timestamp is not None
                assert len(message.timestamp) > 0

    @pytest.mark.asyncio  
    async def test_conversation_reactions_and_emojis(self, sample_conversation_texts):
        """Test parsing of reactions and emoji in conversations."""
        slack_text = sample_conversation_texts["slack_conversation"]
        conversation = await parse_conversation_from_text(slack_text, "test_reactions.png")
        
        assert conversation is not None
        
        # Find messages with reactions
        messages_with_reactions = [msg for msg in conversation.messages if msg.reactions]
        assert len(messages_with_reactions) > 0
        
        # Verify reaction parsing
        for message in messages_with_reactions:
            for reaction in message.reactions:
                assert "emoji" in reaction
                assert "count" in reaction
                # Should have common reaction emojis
                assert reaction["emoji"] in ["👍", "💯", "✅", "⚡"]

    @pytest.mark.asyncio
    async def test_complex_conversation_parsing(self, sample_conversation_texts):
        """Test parsing of complex conversations with mixed content."""
        code_review_text = sample_conversation_texts["code_review_conversation"]
        conversation = await parse_conversation_from_text(code_review_text, "code_review.png")
        
        assert conversation is not None
        assert len(conversation.messages) >= 8
        
        # Verify technical content is preserved
        technical_content = [msg for msg in conversation.messages if "line" in msg.content.lower() or "function" in msg.content.lower()]
        assert len(technical_content) > 0
        
        # Verify mentions are captured
        mentions = [msg for msg in conversation.messages if "@" in msg.content]
        assert len(mentions) > 0

    @pytest.mark.asyncio
    async def test_conversation_image_extraction(self, sample_conversation_images):
        """Test text extraction from conversation screenshot images."""
        mock_slack_conversation = """
Alice Johnson  12:34 PM
Hey team, are we still on for the sprint demo tomorrow?

Bob Smith  12:35 PM
Yes! I've got the presentation ready.

Charlie Brown  12:36 PM
Perfect. I'll send out the meeting invite.
👍 2
"""
        
        slack_image = sample_conversation_images["slack_conversation_2025_06_02.png"]
        
        # Mock the OCR extraction
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = mock_slack_conversation
            
            # Extract text from conversation image  
            extracted_text = await extract_text_from_image(slack_image, 'file')
            
            assert extracted_text is not None
            assert "Alice Johnson" in extracted_text
            assert "12:34 PM" in extracted_text
            assert "sprint demo" in extracted_text

    @pytest.mark.asyncio
    async def test_end_to_end_conversation_processing(self, sample_conversation_images):
        """Test complete end-to-end conversation processing."""
        mock_conversation_text = """
TechLead_Sarah — Today at 2:15 PM
@channel Quick update on the database migration

DevOps_Mike — Today at 2:16 PM  
I've been monitoring the performance metrics

Junior_Dev_Emma — Today at 2:17 PM
Should I hold off on deploying my feature branch?
"""
        
        discord_image = sample_conversation_images["discord_chat_screenshot.jpg"]
        
        # Mock the full pipeline
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = mock_conversation_text
            
            # Extract text from image
            extracted_text = await extract_text_from_image(discord_image, 'file')
            
            # Parse conversation
            conversation = await parse_conversation_from_text(extracted_text, discord_image)
            
            # Verify end-to-end processing
            assert conversation is not None
            assert conversation.platform == "discord"
            assert len(conversation.messages) >= 3
            assert "TechLead_Sarah" in conversation.participants
            assert "DevOps_Mike" in conversation.participants
            assert "Junior_Dev_Emma" in conversation.participants
            
            # Verify message content
            first_message = conversation.messages[0]
            assert first_message.speaker == "TechLead_Sarah"
            assert "database migration" in first_message.content

    @pytest.mark.asyncio
    async def test_conversation_indexing_integration(self, sample_conversation_texts, temp_dir):
        """Test integration with ChromaDB indexing."""
        slack_text = sample_conversation_texts["slack_conversation"]
        
        # Parse conversation
        conversation = await parse_conversation_from_text(slack_text, "test_indexing.png")
        assert conversation is not None
        
        # Mock ChromaDB collection
        mock_collection = Mock()
        mock_collection.add = Mock()
        
        # Test indexing
        await process_conversation_and_index(conversation, mock_collection)
        
        # Verify indexing was called
        mock_collection.add.assert_called()
        
        # Verify indexed data structure
        call_args = mock_collection.add.call_args
        assert "documents" in call_args.kwargs
        assert "metadatas" in call_args.kwargs
        assert "ids" in call_args.kwargs
        
        # Verify conversation content is in documents
        documents = call_args.kwargs["documents"]
        assert len(documents) > 0
        assert any("sprint demo" in doc for doc in documents)

    @pytest.mark.asyncio
    async def test_conversation_metadata_extraction(self, sample_conversation_texts):
        """Test extraction of conversation metadata."""
        teams_text = sample_conversation_texts["teams_conversation"]
        conversation = await parse_conversation_from_text(teams_text, "teams_test.png")
        
        assert conversation is not None
        
        # Verify metadata
        assert conversation.platform == "teams"
        assert len(conversation.participants) >= 4
        assert conversation.message_count == len(conversation.messages)
        
        # Verify message metadata
        for message in conversation.messages:
            assert hasattr(message, 'speaker')
            assert hasattr(message, 'timestamp')
            assert hasattr(message, 'content')
            assert hasattr(message, 'message_id')

    @pytest.mark.asyncio
    async def test_conversation_search_and_filtering(self, sample_conversation_texts):
        """Test conversation search and filtering capabilities."""
        # Parse multiple conversations
        conversations = []
        for platform, text in sample_conversation_texts.items():
            conv = await parse_conversation_from_text(text, f"{platform}.png")
            if conv:
                conversations.append(conv)
        
        assert len(conversations) > 0
        
        # Test filtering by participant
        alice_conversations = [conv for conv in conversations if "Alice" in conv.participants]
        assert len(alice_conversations) > 0
        
        # Test filtering by platform  
        slack_conversations = [conv for conv in conversations if conv.platform == "slack"]
        assert len(slack_conversations) > 0
        
        # Test content search
        demo_conversations = []
        for conv in conversations:
            for message in conv.messages:
                if "demo" in message.content.lower():
                    demo_conversations.append(conv)
                    break
        
        assert len(demo_conversations) > 0

    @pytest.mark.asyncio
    async def test_conversation_export_formats(self, sample_conversation_texts):
        """Test exporting conversations to various formats."""
        slack_text = sample_conversation_texts["slack_conversation"]
        conversation = await parse_conversation_from_text(slack_text, "export_test.png")
        
        assert conversation is not None
        
        # Test JSON export
        json_export = conversation.to_json()
        parsed_json = json.loads(json_export)
        
        assert "platform" in parsed_json
        assert "participants" in parsed_json  
        assert "messages" in parsed_json
        assert len(parsed_json["messages"]) == len(conversation.messages)
        
        # Test plain text export
        text_export = conversation.to_text()
        assert "Alice Johnson" in text_export
        assert "sprint demo" in text_export
        assert "12:34 PM" in text_export
        
        # Test markdown export
        markdown_export = conversation.to_markdown()
        assert "**Alice Johnson**" in markdown_export or "## Alice Johnson" in markdown_export
        assert "sprint demo" in markdown_export

    @pytest.mark.asyncio
    async def test_conversation_analytics(self, sample_conversation_texts):
        """Test conversation analytics and statistics."""
        # Parse all conversations for analysis
        all_conversations = []
        for platform, text in sample_conversation_texts.items():
            conv = await parse_conversation_from_text(text, f"{platform}.png")
            if conv:
                all_conversations.append(conv)
        
        # Generate analytics
        total_messages = sum(len(conv.messages) for conv in all_conversations)
        total_participants = len(set().union(*[conv.participants for conv in all_conversations]))
        
        assert total_messages > 20  # Should have many messages across conversations
        assert total_participants > 10  # Should have many unique participants
        
        # Test per-conversation analytics
        for conversation in all_conversations:
            stats = conversation.get_statistics()
            
            assert "message_count" in stats
            assert "participant_count" in stats
            assert "time_span" in stats
            assert stats["message_count"] == len(conversation.messages)
            assert stats["participant_count"] == len(conversation.participants)

    @pytest.mark.asyncio
    async def test_conversation_thread_detection(self, sample_conversation_texts):
        """Test detection of conversation threads and topics."""
        code_review_text = sample_conversation_texts["code_review_conversation"]
        conversation = await parse_conversation_from_text(code_review_text, "thread_test.png")
        
        assert conversation is not None
        
        # Test thread detection (implementation dependent)
        threads = conversation.detect_threads()
        
        # Should identify at least one main thread about code review
        assert len(threads) >= 1
        
        # Test topic extraction
        topics = conversation.extract_topics()
        
        # Should find topics related to code review
        technical_topics = [topic for topic in topics if any(word in topic.lower() for word in ["code", "review", "function", "variable"])]
        assert len(technical_topics) > 0

    @pytest.mark.asyncio
    async def test_conversation_privacy_and_sanitization(self, sample_conversation_texts):
        """Test privacy features and content sanitization."""
        whatsapp_text = sample_conversation_texts["whatsapp_conversation"]
        conversation = await parse_conversation_from_text(whatsapp_text, "privacy_test.png")
        
        assert conversation is not None
        
        # Test anonymization
        anonymized_conv = conversation.anonymize()
        
        # Participants should be anonymized
        for participant in anonymized_conv.participants:
            assert participant.startswith("User_") or participant == "Anonymous"
        
        # Test content sanitization
        sanitized_conv = conversation.sanitize_content()
        
        # Personal information should be redacted
        for message in sanitized_conv.messages:
            # Should not contain personal information (implementation dependent)
            assert isinstance(message.content, str)
            assert len(message.content) > 0

    @pytest.mark.asyncio
    async def test_real_time_conversation_processing(self, sample_conversation_images):
        """Test processing of real-time conversation updates."""
        # Simulate a conversation that gets updated over time
        initial_conversation = """
Alice  1:00 PM
Starting the meeting now

Bob  1:01 PM  
Ready when you are
"""
        
        updated_conversation = """
Alice  1:00 PM
Starting the meeting now

Bob  1:01 PM
Ready when you are

Charlie  1:02 PM
Just joined, sorry I'm late

Alice  1:03 PM
No problem, let's get started
"""
        
        image_path = list(sample_conversation_images.values())[0]
        
        # Process initial conversation
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = initial_conversation
            
            conv1 = await parse_conversation_from_text(
                await extract_text_from_image(image_path, 'file'), 
                image_path
            )
        
        # Process updated conversation
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = updated_conversation
            
            conv2 = await parse_conversation_from_text(
                await extract_text_from_image(image_path, 'file'),
                image_path
            )
        
        # Verify incremental processing
        assert len(conv1.messages) == 2
        assert len(conv2.messages) == 4
        assert len(conv2.participants) > len(conv1.participants)
        
        # Test message deduplication
        new_messages = conv2.get_new_messages_since(conv1)
        assert len(new_messages) == 2  # Two new messages added

    @pytest.mark.asyncio
    async def test_error_handling_and_edge_cases(self, sample_conversation_images):
        """Test error handling for various edge cases."""
        image_path = list(sample_conversation_images.values())[0]
        
        # Test with empty text
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = ""
            
            conversation = await parse_conversation_from_text("", image_path)
            # Should handle gracefully
            assert conversation is None or len(conversation.messages) == 0
        
        # Test with malformed conversation text
        malformed_texts = [
            "Random text without conversation structure",
            "Name without timestamp: Some message",
            "12:34 PM: Message without speaker name",
            "Mixed up format with various issues"
        ]
        
        for malformed_text in malformed_texts:
            with patch('src.processors.image.extract_text_from_image') as mock_extract:
                mock_extract.return_value = malformed_text
                
                conversation = await parse_conversation_from_text(malformed_text, image_path)
                # Should not crash, may return None or minimal data
                assert conversation is None or isinstance(conversation.messages, list)

    @pytest.mark.asyncio
    async def test_conversation_compression_and_summarization(self, sample_conversation_texts):
        """Test conversation compression and summarization features."""
        # Use the longest conversation for testing
        long_conversation_text = sample_conversation_texts["code_review_conversation"]
        conversation = await parse_conversation_from_text(long_conversation_text, "summary_test.png")
        
        assert conversation is not None
        
        # Test conversation summarization
        summary = conversation.generate_summary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(long_conversation_text)  # Should be shorter than original
        
        # Test key points extraction
        key_points = conversation.extract_key_points()
        
        assert isinstance(key_points, list)
        assert len(key_points) > 0
        
        # Should contain important topics from the conversation
        code_related_points = [point for point in key_points if any(word in point.lower() for word in ["code", "review", "function", "variable"])]
        assert len(code_related_points) > 0