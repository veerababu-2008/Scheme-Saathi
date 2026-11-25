"""SchemeSaathi AI — Chat API endpoint tests.

Tests the chat session CRUD and message flow.
Gemini API calls are mocked to avoid real API usage in tests.
"""

from unittest.mock import patch

from app.models.chat import ChatMessage

# ── Helper: standard mock answer ─────────────────────────────────

_MOCK_ANSWER = (
    "PM-KISAN provides ₹6,000 per year as income support "
    "[Source: PM-KISAN Portal].\n\n"
    "⚠️ This information is for guidance only. SchemeSaathi is not an "
    "official government portal. Please verify details."
)

_MOCK_FALLBACK = (
    "I don't have enough verified information to answer this. "
    "[Source: N/A]\n\n"
    "⚠️ This information is for guidance only. SchemeSaathi is not an "
    "official government portal. Please verify details."
)

# Patch targets at their source modules
_PATCH_RETRIEVE = "app.services.rag.retriever.retrieve"
_PATCH_GEMINI = "app.services.gemini_client.generate_chat_response"


# ══════════════════════════════════════════════════════════════════
# SESSION CRUD TESTS
# ══════════════════════════════════════════════════════════════════


class TestChatSessions:
    """Tests for chat session creation, listing, and deletion."""

    def test_create_session(self, auth_client):
        resp = auth_client.post(
            "/api/v1/chat/sessions",
            json={"language": "en", "title": "Test Chat"},
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["title"] == "Test Chat"
        assert data["language"] == "en"
        assert data["message_count"] == 0
        assert data["id"] is not None

    def test_create_session_defaults(self, auth_client):
        resp = auth_client.post("/api/v1/chat/sessions", json={})
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["title"] == "New conversation"
        assert data["language"] == "en"

    def test_create_session_telugu(self, auth_client):
        resp = auth_client.post(
            "/api/v1/chat/sessions",
            json={"language": "te"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["language"] == "te"

    def test_create_session_unauthenticated(self, client):
        resp = client.post("/api/v1/chat/sessions", json={})
        assert resp.status_code == 401

    def test_list_sessions_empty(self, auth_client):
        resp = auth_client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_list_sessions(self, auth_client):
        for i in range(3):
            auth_client.post(
                "/api/v1/chat/sessions",
                json={"title": f"Session {i}"},
            )

        resp = auth_client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 3
        assert body["meta"]["total"] == 3

    def test_list_sessions_pagination(self, auth_client):
        for i in range(5):
            auth_client.post(
                "/api/v1/chat/sessions",
                json={"title": f"Session {i}"},
            )

        resp = auth_client.get("/api/v1/chat/sessions?page=1&per_page=2")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5
        assert body["meta"]["pages"] == 3

    def test_get_session(self, auth_client):
        create_resp = auth_client.post(
            "/api/v1/chat/sessions",
            json={"title": "Get Test"},
        )
        session_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.get(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["id"] == session_id
        assert data["title"] == "Get Test"
        assert "messages" in data

    def test_get_session_not_found(self, auth_client):
        resp = auth_client.get("/api/v1/chat/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_session(self, auth_client):
        create_resp = auth_client.post(
            "/api/v1/chat/sessions",
            json={"title": "Delete Me"},
        )
        session_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted"] == session_id

        get_resp = auth_client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_session_not_found(self, auth_client):
        resp = auth_client.delete("/api/v1/chat/sessions/nonexistent")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# MESSAGE TESTS (with mocked Gemini)
# ══════════════════════════════════════════════════════════════════


class TestChatMessages:
    """Tests for sending messages (Gemini API mocked)."""

    def _create_session(self, auth_client):
        resp = auth_client.post(
            "/api/v1/chat/sessions",
            json={"title": "Message Test"},
        )
        return resp.get_json()["data"]["id"]

    @patch(_PATCH_GEMINI, return_value=_MOCK_FALLBACK)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_basic(self, mock_retrieve, mock_gemini, auth_client):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "What is PM-KISAN?"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "What is PM-KISAN?"
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 0

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_updates_session_title(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tell me about PMAY housing scheme"},
        )

        resp = auth_client.get(f"/api/v1/chat/sessions/{session_id}")
        data = resp.get_json()["data"]
        assert data["title"] == "Tell me about PMAY housing scheme"

    def test_send_message_empty(self, auth_client):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": ""},
        )
        assert resp.status_code == 400

    def test_send_message_missing_field(self, auth_client):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={},
        )
        assert resp.status_code == 400

    def test_send_message_session_not_found(self, auth_client):
        resp = auth_client.post(
            "/api/v1/chat/sessions/nonexistent/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[
        {
            "text": "PM-KISAN provides ₹6,000 per year.",
            "metadata": {
                "source_title": "PM-KISAN Portal",
                "source_url": "https://pmkisan.gov.in",
                "scheme_id": 1,
                "verified_date": None,
            },
            "score": 0.92,
        }
    ])
    def test_send_message_with_citations(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "What is PM-KISAN?"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        citations = data["assistant_message"]["citations"]
        assert citations is not None
        assert len(citations) >= 1
        assert citations[0]["source_title"] == "PM-KISAN Portal"

    @patch(_PATCH_GEMINI, side_effect=Exception("API down"))
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_gemini_error_fallback(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "Some question"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "not an official government portal" in data["assistant_message"]["content"].lower()

    @patch(
        _PATCH_GEMINI,
        return_value="Your Aadhaar 1234 5678 9012 is valid.",
    )
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_pii_blocked(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "Check my Aadhaar"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        content = data["assistant_message"]["content"]
        assert "1234 5678 9012" not in content

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_language_detection(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "పీఎం-కిసాన్ అంటే ఏమిటి?"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["language_detected"] == "te"

    def test_send_message_unauthenticated(self, client):
        resp = client.post(
            "/api/v1/chat/sessions/some-id/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 401

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_multiple_messages_in_session(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "First question"},
        )
        auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "Second question"},
        )

        resp = auth_client.get(f"/api/v1/chat/sessions/{session_id}")
        data = resp.get_json()["data"]
        assert data["message_count"] == 4  # 2 user + 2 assistant

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_delete_session_cascades_messages(
        self, mock_retrieve, mock_gemini, auth_client, app
    ):
        session_id = self._create_session(auth_client)

        auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "Some question"},
        )

        auth_client.delete(f"/api/v1/chat/sessions/{session_id}")

        with app.app_context():
            msgs = ChatMessage.query.filter_by(session_id=session_id).all()
            assert len(msgs) == 0

    @patch(_PATCH_GEMINI, return_value=_MOCK_ANSWER)
    @patch(_PATCH_RETRIEVE, return_value=[])
    def test_send_message_explicit_language(
        self, mock_retrieve, mock_gemini, auth_client
    ):
        session_id = self._create_session(auth_client)

        resp = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"message": "What is PM-KISAN?", "language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["language_detected"] == "hi"
