import os
import sqlite3
import uuid
from typing import Any, Dict, List

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None  # type: ignore

from backend.database.init_db import DB_PATH
from backend.schemas.models import ChatRequest

NOT_FOUND_MESSAGE = "I could not find evidence in the uploaded documents."


class RAGService:
    def __init__(self) -> None:
        self.db_path = DB_PATH
        self.client = None
        if Groq is not None:
            try:
                self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
            except Exception:
                self.client = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def answer(self, request: ChatRequest) -> Dict[str, Any]:
        prompt = getattr(request, "prompt", None) or getattr(request, "query", "") or ""
        conversation_id = getattr(request, "conversation_id", None) or str(uuid.uuid4())

        conn = self._connect()
        try:
            # --- retrieval ---
            if prompt.strip():
                terms = [t for t in prompt.strip().split() if len(t) > 2][:6] or [prompt.strip()]
                clauses = " OR ".join(["c.content LIKE ?"] * len(terms))
                params = [f"%{t}%" for t in terms]
                rows = conn.execute(
                    f"""
                    SELECT d.id AS document_id, d.title, c.content, c.section, c.page_number, c.metadata
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE {clauses}
                    ORDER BY d.id, c.id
                    LIMIT 8
                    """,
                    params,
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT d.id AS document_id, d.title, c.content, c.section, c.page_number, c.metadata
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    ORDER BY d.id, c.id
                    LIMIT 8
                    """
                ).fetchall()

            # --- conversation memory: last 6 turns for this session ---
            history_rows = conn.execute(
                "SELECT prompt, response FROM chat_history WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 6",
                (conversation_id,),
            ).fetchall()
        finally:
            pass

        context_parts: List[str] = []
        citations: List[Dict[str, Any]] = []
        for row in rows:
            content = row["content"] or ""
            context_parts.append(f"[{row['document_id']}] {content}")
            citations.append(
                {
                    "document_id": row["document_id"],
                    "document_name": row["title"],
                    "page_number": row["page_number"],
                    "section": row["section"],
                    "snippet": (content[:200] + "...") if len(content) > 200 else content,
                    "confidence": 0.9 if prompt.strip() else 0.5,
                }
            )

        if not context_parts:
            answer = NOT_FOUND_MESSAGE
            self._log_turn(conn, conversation_id, prompt, answer)
            conn.close()
            return {"answer": answer, "citations": [], "conversation_id": conversation_id}

        history_messages = []
        for row in reversed(history_rows):  # oldest first
            if row["prompt"]:
                history_messages.append({"role": "user", "content": row["prompt"]})
            if row["response"]:
                history_messages.append({"role": "assistant", "content": row["response"]})

        if self.client is not None:
            try:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant for EPC data centre project documents. "
                            "Answer ONLY using the provided context chunks. Cite the document "
                            f"ID in brackets like [3] when referencing a fact. If the context "
                            f"does not contain the answer, reply exactly: '{NOT_FOUND_MESSAGE}'"
                        ),
                    },
                    *history_messages,
                    {
                        "role": "user",
                        "content": f"Context:\n{chr(10).join(context_parts)}\n\nQuestion: {prompt}",
                    },
                ]
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=600,
                )
                answer = response.choices[0].message.content or NOT_FOUND_MESSAGE
            except Exception:
                answer = "I encountered an error while generating a response. Please try again later."
        else:
            if not prompt.strip():
                answer = "Please provide a question so I can search the ingested documents."
            else:
                answer = "I found relevant context in the uploaded documents. " + " ".join(context_parts[:2])[:400]

        self._log_turn(conn, conversation_id, prompt, answer)
        conn.close()

        return {
            "answer": answer,
            "citations": citations,
            "conversation_id": conversation_id,
        }

    def _log_turn(self, conn: sqlite3.Connection, conversation_id: str, prompt: str, response: str) -> None:
        """Persist this turn so future messages in the same conversation_id have memory."""
        try:
            conn.execute(
                "INSERT INTO chat_history (prompt, response, created_at, conversation_id) VALUES (?, ?, datetime('now'), ?)",
                (prompt, response, conversation_id),
            )
            conn.commit()
        except sqlite3.OperationalError:
            # conversation_id column may not exist yet on an old DB file; degrade gracefully
            conn.execute(
                "INSERT INTO chat_history (prompt, response, created_at) VALUES (?, ?, datetime('now'))",
                (prompt, response),
            )
            conn.commit()
