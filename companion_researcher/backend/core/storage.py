"""
Storage Module - Session persistence and vector database
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models import Session, Message, Source
from ..config import settings

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    Persistent storage for conversation sessions.

    Stores sessions as JSON files for simplicity.
    In production, this would use a proper database.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.sessions_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session"""
        return self.storage_dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        """Save a session to disk"""
        path = self._get_session_path(session.id)

        data = {
            "id": session.id,
            "personality_id": session.personality_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in session.messages
            ],
            "tags": session.tags,
            "project": session.project,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved session: {session.id}")

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from disk"""
        path = self._get_session_path(session_id)

        if not path.exists():
            return None

        with open(path, 'r') as f:
            data = json.load(f)

        from ..models import MessageRole

        messages = [
            Message(
                id=m["id"],
                role=MessageRole(m["role"]),
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {}),
            )
            for m in data.get("messages", [])
        ]

        return Session(
            id=data["id"],
            personality_id=data["personality_id"],
            messages=messages,
            tags=data.get("tags", []),
            project=data.get("project"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )

    def delete(self, session_id: str) -> bool:
        """Delete a session"""
        path = self._get_session_path(session_id)

        if not path.exists():
            return False

        path.unlink()
        logger.info(f"Deleted session: {session_id}")
        return True

    def list_sessions(self) -> List[Session]:
        """List all sessions"""
        sessions = []

        for path in self.storage_dir.glob("*.json"):
            session = self.load(path.stem)
            if session:
                sessions.append(session)

        # Sort by updated_at, most recent first
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        personality_id: Optional[str] = None,
    ) -> List[Session]:
        """Search sessions by content, tags, or personality"""
        sessions = self.list_sessions()
        results = []

        for session in sessions:
            # Filter by personality
            if personality_id and session.personality_id != personality_id:
                continue

            # Filter by tags
            if tags and not any(t in session.tags for t in tags):
                continue

            # Search in message content
            if query:
                query_lower = query.lower()
                found = any(
                    query_lower in m.content.lower()
                    for m in session.messages
                )
                if not found:
                    continue

            results.append(session)

        return results


class VectorStore:
    """
    Vector database for semantic search and knowledge storage.

    Uses ChromaDB for local vector storage.
    Can be extended to use other vector DBs like Pinecone.
    """

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.vector_db_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def _ensure_initialized(self):
        """Initialize ChromaDB client lazily"""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.persist_dir),
            ))

            self._collection = self._client.get_or_create_collection(
                name="research_knowledge",
                metadata={"hnsw:space": "cosine"},
            )

            logger.info("ChromaDB initialized")

        except ImportError:
            logger.warning("ChromaDB not available. Install with: pip install chromadb")
            raise RuntimeError("ChromaDB not installed")

    def add_source(self, source: Source) -> str:
        """Add a source to the vector store"""
        self._ensure_initialized()

        doc_id = source.id or str(uuid.uuid4())

        self._collection.add(
            documents=[source.content],
            metadatas=[{
                "url": source.url,
                "title": source.title,
                "source_type": source.source_type.value,
                "reliability_score": source.reliability_score,
                "timestamp": source.timestamp.isoformat(),
            }],
            ids=[doc_id],
        )

        return doc_id

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add multiple documents to the vector store"""
        self._ensure_initialized()

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        self._collection.add(
            documents=documents,
            metadatas=metadatas or [{} for _ in documents],
            ids=ids,
        )

        return ids

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        self._ensure_initialized()

        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata,
        )

        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "id": results["ids"][0][i] if results["ids"] else None,
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })

        return formatted

    def delete(self, ids: List[str]) -> None:
        """Delete documents by ID"""
        self._ensure_initialized()
        self._collection.delete(ids=ids)

    def clear(self) -> None:
        """Clear all documents"""
        self._ensure_initialized()
        # Recreate collection to clear all data
        self._client.delete_collection("research_knowledge")
        self._collection = self._client.create_collection(
            name="research_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        """Get total document count"""
        self._ensure_initialized()
        return self._collection.count()


class KnowledgeBase:
    """
    High-level interface for the knowledge base.

    Combines vector search with session storage for a unified
    knowledge management system.
    """

    def __init__(
        self,
        session_storage: Optional[SessionStorage] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.sessions = session_storage or SessionStorage()
        self.vectors = vector_store or VectorStore()

    def index_session(self, session: Session) -> None:
        """Index a session's messages for search"""
        for message in session.messages:
            if message.role.value == "assistant" and len(message.content) > 100:
                self.vectors.add_documents(
                    documents=[message.content],
                    metadatas=[{
                        "session_id": session.id,
                        "message_id": message.id,
                        "timestamp": message.timestamp.isoformat(),
                    }],
                )

    def search_knowledge(
        self,
        query: str,
        include_sessions: bool = True,
        include_research: bool = True,
        n_results: int = 10,
    ) -> Dict[str, List]:
        """Search across all knowledge sources"""
        results = {
            "sessions": [],
            "research": [],
        }

        if include_sessions:
            results["sessions"] = self.sessions.search(query)[:n_results]

        if include_research:
            vector_results = self.vectors.search(query, n_results=n_results)
            results["research"] = vector_results

        return results

    def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """Get relevant context for a query from the knowledge base"""
        results = self.search_knowledge(query, n_results=5)

        context_parts = []

        # Add relevant research
        for r in results.get("research", [])[:3]:
            content = r.get("content", "")[:500]
            context_parts.append(f"Previous research: {content}")

        # Add recent session context
        for s in results.get("sessions", [])[:2]:
            if s.messages:
                recent_messages = s.messages[-3:]
                for m in recent_messages:
                    context_parts.append(f"Previous conversation ({m.role.value}): {m.content[:200]}")

        # Truncate to max tokens (rough estimate: 4 chars per token)
        context = "\n\n".join(context_parts)
        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "..."

        return context
