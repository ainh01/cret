"""
Test script for /prepare-chat and /chat with cache_id
Uses local mock server and backend server
"""
import requests
import time
import json

BACKEND_URL = "http://localhost:5000"
MOCK_URL = "http://localhost:5001"

def test_prepare_chat_flow():
    print("\n" + "="*60)
    print("Testing /prepare-chat -> /chat flow")
    print("="*60)
    
    # Step 1: Check mock server
    try:
        response = requests.get(f"{MOCK_URL}/v1/messages", timeout=2)
        print(f"✓ Mock server is running on {MOCK_URL}")
    except Exception as e:
        print(f"✗ Mock server not reachable: {e}")
        return
    
    # Step 2: Check backend server
    try:
        response = requests.get(f"{BACKEND_URL}/api/settings", timeout=2)
        print(f"✓ Backend server is running on {BACKEND_URL}")
    except Exception as e:
        print(f"✗ Backend server not reachable: {e}")
        return
    
    # Step 3: Update backend to use mock server
    print("\nConfiguring backend to use mock server...")
    config_payload = {
        "endpoint": f"{MOCK_URL}/v1",  # Backend will add /chat/completions
        "api_key": "mock-key",
        "stream": True,
        "use_proxy": False
    }
    response = requests.post(f"{BACKEND_URL}/api/settings", json=config_payload)
    print(f"✓ Backend configured: {response.json()}")
    
    # Step 4: Call /prepare-chat
    print("\n" + "-"*60)
    print("Step 1: Calling /prepare-chat...")
    print("-"*60)
    
    prepare_payload = {
        "prompt": "What is 2+2?",
        "model": "claude-3-5-sonnet-20241022"
    }
    
    response = requests.post(f"{BACKEND_URL}/api/prepare-chat", json=prepare_payload)
    
    if response.status_code != 200:
        print(f"✗ /prepare-chat failed: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    cache_id = result.get("cache_id")
    
    print(f"✓ /prepare-chat returned cache_id: {cache_id}")
    print(f"  Response: {json.dumps(result, indent=2)}")
    
    # Step 5: Wait a bit for background task to start
    print("\nWaiting 2 seconds for background task to process...")
    time.sleep(2)
    
    # Step 6: Call /chat with cache_id
    print("\n" + "-"*60)
    print("Step 2: Calling /chat with cache_id...")
    print("-"*60)
    
    chat_payload = {
        "prompt": "What is 2+2?",
        "model": "claude-3-5-sonnet-20241022",
        "cache_id": cache_id
    }
    
    print(f"Requesting /chat with cache_id={cache_id}...")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=chat_payload,
            stream=True,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"✗ /chat failed: {response.status_code}")
            print(response.text)
            return
        
        print("\nStreaming response:")
        print("-"*60)
        
        line_count = 0
        for line in response.iter_lines():
            if line:
                line_count += 1
                decoded = line.decode('utf-8')
                print(f"[{line_count}] {decoded}")
                
                # Parse the event
                try:
                    data = json.loads(decoded)
                    if 'error' in data:
                        print(f"✗ Error in stream: {data['error']}")
                except json.JSONDecodeError:
                    pass
        
        print("-"*60)
        print(f"✓ Stream completed with {line_count} events")
        
    except requests.exceptions.Timeout:
        print("✗ /chat request timed out after 30 seconds")
    except Exception as e:
        print(f"✗ /chat request failed: {e}")

if __name__ == "__main__":
    test_prepare_chat_flow()
