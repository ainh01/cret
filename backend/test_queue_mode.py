"""
Test queue-mode prepare-chat with realistic delays.

Scenario:
- 2 inputs
- Step 1: shared source, 3s delay
- Step 2: uses step 1 output, 6s delay
- Step 3: uses step 1 output, 9s delay
- Step 4: client concat step 2 + step 3

Expected behavior:
- Step 1 starts at t=0, completes at t=3
- Step 2 and 3 prepare-chat calls start immediately after step 1 completes
- Step 2 /chat starts streaming chunks as they arrive (completes at t=9 total)
- Step 3 /chat starts streaming chunks as they arrive (completes at t=12 total)
- Total time ~12s (not 3+6+9=18s sequential)
"""

import asyncio
import aiohttp
import time
from typing import List

MOCK_SERVER = "http://localhost:5001"
BACKEND_SERVER = "http://localhost:5000"


async def call_prepare_chat(step_name: str, prompt: str) -> str:
    """Call /prepare-chat and return cache_id"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "prompt": prompt,
            "model": "claude-3-5-sonnet-20241022"
        }
        
        async with session.post(f"{BACKEND_SERVER}/api/prepare-chat", json=payload) as resp:
            data = await resp.json()
            cache_id = data["cache_id"]
            print(f"[{step_name}] prepare-chat returned cache_id={cache_id}")
            return cache_id


async def call_chat(step_name: str, cache_id: str, start_time: float):
    """Call /chat with cache_id and stream results"""
    print(f"[{step_name}] Starting /chat with cache_id={cache_id} at t={time.time()-start_time:.1f}s")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "cache_id": cache_id
        }
        
        async with session.post(f"{BACKEND_SERVER}/api/chat", json=payload) as resp:
            chunk_count = 0
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                import json
                try:
                    data = json.loads(line)
                    if "text" in data:
                        chunk_count += 1
                        elapsed = time.time() - start_time
                        print(f"[{step_name}] Chunk {chunk_count} at t={elapsed:.1f}s: {data['text'][:20]}...")
                    elif "error" in data:
                        print(f"[{step_name}] Error: {data['error']}")
                        break
                except json.JSONDecodeError:
                    continue
            
            elapsed = time.time() - start_time
            print(f"[{step_name}] Done! chunks={chunk_count} at t={elapsed:.1f}s")


async def call_chat_no_cache(step_name: str, prompt: str, start_time: float):
    """Call /chat directly without cache (for step 1)"""
    print(f"[{step_name}] Starting /chat (no cache) at t={time.time()-start_time:.1f}s")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "prompt": prompt,
            "model": "claude-3-5-sonnet-20241022"
        }
        
        result_text = ""
        async with session.post(f"{BACKEND_SERVER}/api/chat", json=payload) as resp:
            chunk_count = 0
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                import json
                try:
                    data = json.loads(line)
                    if "text" in data:
                        result_text += data["text"]
                        chunk_count += 1
                        elapsed = time.time() - start_time
                        print(f"[{step_name}] Chunk {chunk_count} at t={elapsed:.1f}s")
                    elif "error" in data:
                        print(f"[{step_name}] Error: {data['error']}")
                        break
                except json.JSONDecodeError:
                    continue
            
            elapsed = time.time() - start_time
            print(f"[{step_name}] Done! chunks={chunk_count} at t={elapsed:.1f}s")
        
        return result_text


async def main():
    start_time = time.time()
    
    print("\n=== Testing Queue-Mode Prepare-Chat ===\n")
    
    # Step 1: Shared source (3s delay)
    print("Step 1: Processing shared source (3s)...")
    step1_result = await call_chat_no_cache(
        "Step1",
        "delay:3",
        start_time
    )
    
    print(f"\nStep 1 complete at t={time.time()-start_time:.1f}s")
    print(f"Result: {step1_result[:50]}...\n")
    
    # Step 2 & 3: Prepare concurrently
    print("Step 2 & 3: Starting prepare-chat concurrently...")
    step2_cache_id, step3_cache_id = await asyncio.gather(
        call_prepare_chat("Step2", f"delay:6 based on {step1_result}"),
        call_prepare_chat("Step3", f"delay:9 based on {step1_result}")
    )
    
    print(f"\nBoth prepare-chat calls done at t={time.time()-start_time:.1f}s")
    print("Step 2 & 3: Starting /chat concurrently (queue mode)...\n")
    
    # Step 2 & 3: Chat concurrently (streaming as chunks arrive)
    await asyncio.gather(
        call_chat("Step2", step2_cache_id, start_time),
        call_chat("Step3", step3_cache_id, start_time)
    )
    
    total_time = time.time() - start_time
    print(f"\n=== All steps complete in {total_time:.1f}s ===")
    print(f"Expected: ~12s (3 + max(6,9))")
    print(f"Sequential would be: 18s (3+6+9)")


if __name__ == "__main__":
    asyncio.run(main())
