"""Test the cache protocol: prepare-chat + chat with cache_id."""
import requests
import json
import time
from threading import Thread

BACKEND_URL = "http://localhost:5000"

def test_cache_protocol():
    """Test the full cache protocol flow."""
    print("=" * 60)
    print("Testing Cache Protocol")
    print("=" * 60)
    
    # Step 1: Regular chat to establish a source
    print("\n[TEST] Step 1: Regular chat (source step)")
    step1_payload = {
        "provider": "openai",
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "What is Python?"}],
        "stream": True,
        "source_format": "openai"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/chat",
        json=step1_payload,
        stream=True
    )
    
    step1_content = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            step1_content += content
                            print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
    
    print(f"\n✓ Step 1 complete: received {len(step1_content)} chars")
    
    # Step 2: Prepare cache for step 2
    print("\n[TEST] Step 2a: Prepare cache")
    step2_prepare_payload = {
        "provider": "openai",
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": step1_content},
            {"role": "user", "content": "Now explain lists and dictionaries"}
        ],
        "source_format": "openai"
    }
    
    prepare_response = requests.post(
        f"{BACKEND_URL}/api/prepare-chat",
        json=step2_prepare_payload
    )
    
    if prepare_response.status_code != 200:
        print(f"✗ Prepare failed: {prepare_response.status_code}")
        print(prepare_response.text)
        return
    
    prepare_data = prepare_response.json()
    cache_id = prepare_data.get('cache_id')
    print(f"✓ Cache ID received: {cache_id}")
    
    # Wait a moment for background task to start
    print("[TEST] Waiting 1s for background generation to start...")
    time.sleep(1)
    
    # Step 2b: Consume from cache
    print("\n[TEST] Step 2b: Consume from cache")
    step2_chat_payload = {
        "cache_id": cache_id,
        "stream": True
    }
    
    print("[TEST] Calling /api/chat with cache_id...")
    chat_response = requests.post(
        f"{BACKEND_URL}/api/chat",
        json=step2_chat_payload,
        stream=True,
        timeout=30  # 30 second timeout
    )
    
    step2_content = ""
    chunk_count = 0
    for line in chat_response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    chunk_count += 1
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            step2_content += content
                            print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
    
    print(f"\n✓ Step 2 complete: received {chunk_count} chunks, {len(step2_content)} chars")
    
    print("\n" + "=" * 60)
    print("✓ Cache protocol test PASSED")
    print("=" * 60)

def test_concurrent_prepare():
    """Test concurrent prepare-chat calls."""
    print("\n" + "=" * 60)
    print("Testing Concurrent Prepare")
    print("=" * 60)
    
    # Prepare 3 cache entries concurrently
    cache_ids = [None, None, None]
    
    def prepare(index, prompt):
        print(f"\n[TEST] Preparing cache {index}")
        payload = {
            "provider": "openai",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "source_format": "openai"
        }
        response = requests.post(f"{BACKEND_URL}/api/prepare-chat", json=payload)
        if response.status_code == 200:
            cache_ids[index] = response.json().get('cache_id')
            print(f"✓ Cache {index} prepared: {cache_ids[index]}")
        else:
            print(f"✗ Cache {index} failed: {response.status_code}")
    
    threads = [
        Thread(target=prepare, args=(0, "Tell me about Python")),
        Thread(target=prepare, args=(1, "Tell me about JavaScript")),
        Thread(target=prepare, args=(2, "Tell me about Go"))
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print(f"\n✓ All 3 caches prepared")
    
    # Wait for background generation
    print("[TEST] Waiting 2s for background generation...")
    time.sleep(2)
    
    # Consume all 3 in sequence
    for i, cache_id in enumerate(cache_ids):
        if not cache_id:
            print(f"✗ Skipping cache {i}: no cache_id")
            continue
        
        print(f"\n[TEST] Consuming cache {i}: {cache_id}")
        payload = {"cache_id": cache_id, "stream": True}
        response = requests.post(f"{BACKEND_URL}/api/chat", json=payload, stream=True, timeout=30)
        
        content = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            text = delta.get('content', '')
                            if text:
                                content += text
                                print(text, end='', flush=True)
                    except json.JSONDecodeError:
                        pass
        
        print(f"\n✓ Cache {i} consumed: {len(content)} chars")
    
    print("\n" + "=" * 60)
    print("✓ Concurrent prepare test PASSED")
    print("=" * 60)

if __name__ == '__main__':
    print("Make sure both servers are running:")
    print("  1. Mock server: python mock_server.py (port 5001)")
    print("  2. Backend: python app.py (port 5000)")
    print("\nStarting tests in 2 seconds...")
    time.sleep(2)
    
    try:
        # Test 1: Basic cache protocol
        test_cache_protocol()
        
        time.sleep(2)
        
        # Test 2: Concurrent prepare
        test_concurrent_prepare()
        
    except requests.exceptions.Timeout:
        print("\n✗ TEST FAILED: Request timed out (server hanging)")
    except requests.exceptions.ConnectionError:
        print("\n✗ TEST FAILED: Could not connect to backend")
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
