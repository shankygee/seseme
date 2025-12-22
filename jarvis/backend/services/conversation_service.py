"""
Conversation Service - Manages chat history and context

Handles conversation state, history persistence, and context management
for multi-turn conversations with Jarvis.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation session."""
    id: str
    user_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


class ConversationService:
    """
    Manages conversations and chat history.

    Features:
    - In-memory storage (with optional Redis backend)
    - Conversation context windowing
    - Message history for Claude API
    - Automatic cleanup of old conversations
    """

    def __init__(self, settings):
        self.settings = settings
        self._conversations: dict[str, Conversation] = {}
        self._user_conversations: dict[str, list[str]] = {}
        self._redis = None

        # Configuration
        self.max_history_messages = 50  # Keep last N messages
        self.context_window_messages = 20  # Send last N to Claude
        self.conversation_ttl_hours = 24  # Auto-expire after N hours

        self._initialize()

    def _initialize(self):
        """Initialize storage backend."""
        try:
            # Try to connect to Redis if configured
            if self.settings.redis_url:
                self._initialize_redis()
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory storage: {e}")

        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())

    def _initialize_redis(self):
        """Initialize Redis connection for persistent storage."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.settings.redis_url)
            logger.info("Connected to Redis for conversation storage")
        except ImportError:
            logger.warning("Redis package not installed")

    async def create_conversation(self, user_id: str) -> str:
        """
        Create a new conversation for a user.

        Args:
            user_id: The user identifier

        Returns:
            New conversation ID
        """
        conv_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conv_id,
            user_id=user_id,
        )

        self._conversations[conv_id] = conversation

        # Track user's conversations
        if user_id not in self._user_conversations:
            self._user_conversations[user_id] = []
        self._user_conversations[user_id].append(conv_id)

        logger.info(f"Created conversation {conv_id} for user {user_id}")
        return conv_id

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    async def get_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Get conversation history in Claude API format.

        Args:
            conversation_id: The conversation ID
            limit: Optional limit on messages (defaults to context_window_messages)

        Returns:
            List of message dicts for Claude API
        """
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return []

        # Apply limit
        limit = limit or self.context_window_messages
        messages = conversation.messages[-limit:]

        # Format for Claude API
        return [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ):
        """
        Add a message to a conversation.

        Args:
            conversation_id: The conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (tools used, etc.)
        """
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()

        # Trim old messages if needed
        if len(conversation.messages) > self.max_history_messages:
            conversation.messages = conversation.messages[-self.max_history_messages:]

        # Persist to Redis if available
        if self._redis:
            await self._persist_conversation(conversation)

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent conversations for a user."""
        conv_ids = self._user_conversations.get(user_id, [])
        conversations = []

        for conv_id in conv_ids[-limit:]:
            conv = self._conversations.get(conv_id)
            if conv:
                conversations.append({
                    "id": conv.id,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "message_count": len(conv.messages),
                    "preview": conv.messages[-1].content[:100] if conv.messages else "",
                })

        return conversations

    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation."""
        conversation = self._conversations.pop(conversation_id, None)
        if conversation:
            user_convs = self._user_conversations.get(conversation.user_id, [])
            if conversation_id in user_convs:
                user_convs.remove(conversation_id)
            logger.info(f"Deleted conversation {conversation_id}")

    async def clear_user_history(self, user_id: str):
        """Clear all conversations for a user."""
        conv_ids = self._user_conversations.pop(user_id, [])
        for conv_id in conv_ids:
            self._conversations.pop(conv_id, None)
        logger.info(f"Cleared all conversations for user {user_id}")

    async def _persist_conversation(self, conversation: Conversation):
        """Persist conversation to Redis."""
        if not self._redis:
            return

        try:
            import json
            key = f"conversation:{conversation.id}"
            data = {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                        "metadata": m.metadata,
                    }
                    for m in conversation.messages
                ],
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            }
            await self._redis.setex(
                key,
                timedelta(hours=self.conversation_ttl_hours),
                json.dumps(data),
            )
        except Exception as e:
            logger.error(f"Failed to persist conversation: {e}")

    async def _cleanup_loop(self):
        """Periodically clean up expired conversations."""
        while True:
            await asyncio.sleep(3600)  # Run every hour

            try:
                now = datetime.utcnow()
                expired = []

                for conv_id, conv in self._conversations.items():
                    age = now - conv.updated_at
                    if age > timedelta(hours=self.conversation_ttl_hours):
                        expired.append(conv_id)

                for conv_id in expired:
                    await self.delete_conversation(conv_id)

                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired conversations")

            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "total_conversations": len(self._conversations),
            "total_users": len(self._user_conversations),
            "total_messages": sum(
                len(c.messages) for c in self._conversations.values()
            ),
        }
