import pytest
from chatbot import app as chatbot_app


# ---------------- MOCK RAG ----------------

@pytest.fixture(autouse=True)
def mock_rag(monkeypatch):

    class FakeRAG:
        def __init__(self):
            self.chunks = ["doc1", "doc2"]

        def query(self, question, top_k=5):
            return {
                "question": question,
                "answer": "Test answer",
                "found_in_kb": True,
                "sources": [("sample text", 0.9)]
            }

        def rebuild(self):
            self.chunks = ["doc1", "doc2", "doc3"]

    chatbot_app.rag = FakeRAG()


# ---------------- CHAT ----------------

def test_chat_success(client):
    res = client.post("/chatbot/chat", json={
        "question": "How do I track my shipment?",
        "top_k": 3
    })

    assert res.status_code == 200

    data = res.json()
    assert "question" in data
    assert "answer" in data
    assert "found_in_kb" in data
    assert isinstance(data["sources"], list)


def test_chat_empty_question(client):
    res = client.post("/chatbot/chat", json={
        "question": ""
    })

    assert res.status_code == 422


def test_chat_missing_question(client):
    res = client.post("/chatbot/chat", json={})
    assert res.status_code == 422


def test_chat_invalid_topk(client):
    res = client.post("/chatbot/chat", json={
        "question": "Where is my shipment?",
        "top_k": 50
    })

    assert res.status_code == 422


# ---------------- REBUILD ----------------

def test_rebuild_success(client):
    res = client.post("/chatbot/rebuild")

    assert res.status_code == 200

    data = res.json()
    assert "message" in data
    assert "chunks_loaded" in data


# ---------------- ERROR CASE ----------------

def test_chat_model_failure(client, monkeypatch):
    import pytest
    from chatbot import app as chatbot_app

    def fake_query(*args, **kwargs):
        raise RuntimeError("Model error")

    monkeypatch.setattr(chatbot_app.rag, "query", fake_query)

    with pytest.raises(Exception):
        client.post("/chatbot/chat", json={
            "question": "Test question"
        })