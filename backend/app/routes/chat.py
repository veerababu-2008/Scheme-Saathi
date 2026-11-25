"""SchemeSaathi AI — Chat / Saathi AI routes.

Endpoints:
  POST   /sessions            Create a new chat session
  GET    /sessions             List user's sessions
  GET    /sessions/<id>        Get session with messages
  POST   /sessions/<id>/messages  Send a message, get AI reply
  DELETE /sessions/<id>        Delete a session
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    CreateSessionSchema,
    SendMessageSchema,
    SessionListSchema,
)
from app.utils import error_response, paginate_query, success_response
from extensions import db

chat_bp = Blueprint("chat", __name__)


# ── POST /sessions ───────────────────────────────────────────────


@chat_bp.route("/sessions", methods=["POST"])
@jwt_required()
def create_session():
    """Create a new chat session."""
    schema = CreateSessionSchema()
    data = schema.load(request.get_json(silent=True) or {})

    user_id = int(get_jwt_identity())
    session = ChatSession(
        user_id=user_id,
        title=data.get("title") or "New conversation",
        language=data.get("language", "en"),
    )
    db.session.add(session)
    db.session.commit()

    return success_response(session.to_dict(), status=201)


# ── GET /sessions ────────────────────────────────────────────────


@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    """List the authenticated user's chat sessions."""
    user_id = int(get_jwt_identity())
    schema = SessionListSchema()
    params = schema.load(request.args)

    query = (
        ChatSession.query
        .filter_by(user_id=user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    items, meta = paginate_query(query, params["page"], params["per_page"])

    return success_response([s.to_dict() for s in items], meta)


# ── GET /sessions/<id> ───────────────────────────────────────────


@chat_bp.route("/sessions/<session_id>", methods=["GET"])
@jwt_required()
def get_session(session_id):
    """Return a single session with its messages."""
    user_id = int(get_jwt_identity())
    session = ChatSession.query.filter_by(
        id=session_id, user_id=user_id
    ).first()

    if not session:
        return error_response("NOT_FOUND", "Chat session not found.", status=404)

    return success_response(session.to_dict(include_messages=True))


# ── POST /sessions/<id>/messages ─────────────────────────────────


@chat_bp.route("/sessions/<session_id>/messages", methods=["POST"])
@jwt_required()
def send_message(session_id):
    """Send a user message and receive the AI response.

    Flow: validate → retrieve context → build prompt → call Gemini → validate
    response → persist both messages → return.
    """
    user_id = int(get_jwt_identity())
    session = ChatSession.query.filter_by(
        id=session_id, user_id=user_id
    ).first()

    if not session:
        return error_response("NOT_FOUND", "Chat session not found.", status=404)

    schema = SendMessageSchema()
    payload = request.get_json(silent=True) or {}
    errors = schema.validate(payload)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(payload)
    user_message_text = data.get("message") or data.get("content")
    if not user_message_text or not str(user_message_text).strip():
        return error_response(
            "VALIDATION_ERROR",
            "Message text cannot be empty.",
            {"message": ["Field is required."]},
            400,
        )

    # Detect / override language
    from app.services.rag.prompt import detect_language

    language = data.get("language") or detect_language(user_message_text) or session.language

    # 1. Retrieve context from RAG
    from app.services.rag.prompt import (
        DISCLAIMER_TEXT,
        SYSTEM_PROMPT,
        build_messages,
        extract_citations,
    )
    from app.services.rag.retriever import retrieve
    from app.services.rag.validator import (
        build_fallback_response,
        validate_response,
    )

    context_chunks = retrieve(
        user_message_text,
        language=language if language != "en" else None,
    )

    # 2. Build chat history from existing persisted messages BEFORE adding current turn
    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages
        if m.id is not None
    ]

    # 3. Persist user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=user_message_text,
    )
    db.session.add(user_msg)

    # 4. Build prompt and call Gemini
    messages = build_messages(user_message_text, context_chunks, history)

    try:
        from app.services.gemini_client import generate_chat_response

        answer = generate_chat_response(messages, SYSTEM_PROMPT)
    except Exception:  # noqa: BLE001
        answer = build_fallback_response(language)

    # 5. Validate response
    validation = validate_response(answer, had_context=bool(context_chunks))

    if not validation["valid"]:
        answer = build_fallback_response(language)
    elif validation["needs_disclaimer"]:
        answer += DISCLAIMER_TEXT

    # 6. Extract citations and persist assistant message
    citations = extract_citations(context_chunks)
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=citations if citations else None,
    )
    db.session.add(assistant_msg)

    # 7. Update session title if it's the first message
    if len(history) == 0:
        session.title = user_message_text[:100]

    db.session.commit()

    return success_response({
        "user_message": user_msg.to_dict(),
        "assistant_message": assistant_msg.to_dict(),
        "content": assistant_msg.content,
        "citations": citations,
        "language_detected": language,
    })


# ── DELETE /sessions/<id> ────────────────────────────────────────


@chat_bp.route("/sessions/<session_id>", methods=["DELETE"])
@jwt_required()
def delete_session(session_id):
    """Delete a chat session and all its messages."""
    user_id = int(get_jwt_identity())
    session = ChatSession.query.filter_by(
        id=session_id, user_id=user_id
    ).first()

    if not session:
        return error_response("NOT_FOUND", "Chat session not found.", status=404)

    db.session.delete(session)
    db.session.commit()

    return success_response({"deleted": session_id})
