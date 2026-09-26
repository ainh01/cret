"""Configuration for testing with mock server."""

# Mock server configuration
MOCK_SERVER_URL = "http://localhost:5001"

# Update app.py settings to point to mock server
TEST_CONFIG = {
    "openai": {
        "endpoint": f"{MOCK_SERVER_URL}/v1/chat/completions",
        "token": "mock-token-not-needed"
    },
    "anthropic": {
        "endpoint": f"{MOCK_SERVER_URL}/v1/messages",
        "token": "mock-token-not-needed"
    }
}

# Instructions:
# 1. Start mock server: python mock_server.py
# 2. Start backend with test config: 
#    - Set ENDPOINT=http://localhost:5001/v1/chat/completions
#    - Set TOKEN=mock-token
#    - Or update .env file
# 3. Run tests: python test_cache_protocol.py

print("""
To test locally:

Terminal 1 - Mock LLM Server:
  python mock_server.py

Terminal 2 - Backend (update .env first):
  ENDPOINT=http://localhost:5001/v1/chat/completions
  TOKEN=mock-token
  
  python app.py

Terminal 3 - Run tests:
  python test_cache_protocol.py
""")
