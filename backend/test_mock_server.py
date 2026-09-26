"""Simple test to verify mock server works"""

import asyncio
import aiohttp
import json


async def test_mock_server():
    print("Testing mock server at http://127.0.0.1:5001/chat/completions")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "mock-model",
            "messages": [{"role": "user", "content": "delay:2"}],
            "stream": True
        }
        
        print(f"Sending request: {json.dumps(payload, indent=2)}")
        
        try:
            async with session.post(
                "http://127.0.0.1:5001/chat/completions",
                json=payload
            ) as resp:
                print(f"Response status: {resp.status}")
                print(f"Response headers: {dict(resp.headers)}")
                
                chunk_count = 0
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        print(f"Chunk {chunk_count}: {line[:100]}...")
                        chunk_count += 1
                
                print(f"\nTotal chunks received: {chunk_count}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_mock_server())
