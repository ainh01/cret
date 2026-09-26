"""Simple test to verify backend server works"""

import asyncio
import aiohttp
import json


async def test_backend():
    print("Testing backend at http://127.0.0.1:5000")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Direct /chat call
        print("\n=== Test 1: Direct /chat call ===")
        payload = {
            "prompt": "Hello",
            "model": "claude-3-5-sonnet-20241022"
        }
        
        try:
            async with session.post(
                "http://127.0.0.1:5000/api/chat",
                json=payload
            ) as resp:
                print(f"Response status: {resp.status}")
                
                chunk_count = 0
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if "text" in data:
                                print(f"Chunk {chunk_count}: text={data['text'][:50]}...")
                            elif "error" in data:
                                print(f"Error: {data['error']}")
                            chunk_count += 1
                        except:
                            pass
                
                print(f"Total chunks: {chunk_count}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_backend())
