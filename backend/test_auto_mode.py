"""
Test auto mode with mock server
Scenario:
- 2 inputs
- Step 1: something that takes 3s
- Step 2: uses output from step 1, takes 6s  
- Step 3: uses output from step 1, takes 9s
- Step 4: client concatenates outputs from step 2 and 3
"""

import asyncio
import aiohttp
import json
from datetime import datetime


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")


async def prepare_chat(session, prompt, model="claude-3-5-sonnet-20241022"):
    """Call /prepare-chat to get cache_id"""
    log(f"📝 prepare_chat: {prompt[:50]}...")
    
    payload = {"prompt": prompt, "model": model}
    
    async with session.post(
        "http://127.0.0.1:5000/api/prepare-chat",
        json=payload
    ) as resp:
        data = await resp.json()
        cache_id = data.get("cache_id")
        log(f"✅ prepare_chat done, cache_id={cache_id}")
        return cache_id


async def chat_with_cache(session, cache_id, step_name):
    """Call /chat with cache_id and stream results"""
    log(f"🚀 chat_with_cache started: {step_name}, cache_id={cache_id}")
    
    payload = {"cache_id": cache_id}
    
    result_text = ""
    chunk_count = 0
    
    async with session.post(
        "http://127.0.0.1:5000/api/chat",
        json=payload
    ) as resp:
        log(f"📡 {step_name}: Response status={resp.status}")
        
        async for line in resp.content:
            line = line.decode('utf-8').strip()
            if line:
                try:
                    data = json.loads(line)
                    if "text" in data:
                        result_text += data["text"]
                        chunk_count += 1
                        if chunk_count % 5 == 0:
                            log(f"   {step_name}: received {chunk_count} chunks...")
                    elif "error" in data:
                        log(f"❌ {step_name}: Error - {data['error']}")
                        return None
                    elif data.get("done"):
                        log(f"✅ {step_name}: Stream complete, {chunk_count} chunks")
                except:
                    pass
    
    log(f"✅ {step_name}: Final result length={len(result_text)}")
    return result_text


async def test_auto_mode():
    log("=" * 70)
    log("Starting Auto Mode Test")
    log("=" * 70)
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Initial task that takes 3s
        log("\n📍 STEP 1: Initial processing (3s)")
        cache_id_step1 = await prepare_chat(
            session,
            "delay:3 Generate a report about user activity"
        )
        
        result_step1 = await chat_with_cache(session, cache_id_step1, "Step1")
        
        if not result_step1:
            log("❌ Step 1 failed")
            return
        
        log(f"\n✅ Step 1 complete: {result_step1[:100]}...")
        
        # Step 2 and 3 should happen in parallel
        # Both use output from step 1
        log("\n📍 STEP 2 & 3: Parallel processing using Step 1 output")
        
        # Step 2: prepare-chat (should be instant, just caching)
        log("\n   → Preparing Step 2 (will take 6s when executed)")
        cache_id_step2 = await prepare_chat(
            session,
            f"delay:6 Based on this report: {result_step1}, analyze trends"
        )
        
        # Step 3: prepare-chat (should be instant, just caching)
        log("\n   → Preparing Step 3 (will take 9s when executed)")
        cache_id_step3 = await prepare_chat(
            session,
            f"delay:9 Based on this report: {result_step1}, generate recommendations"
        )
        
        log("\n   → Both prepared, now executing in parallel...")
        
        # Execute step 2 and 3 in parallel
        start_parallel = datetime.now()
        
        results = await asyncio.gather(
            chat_with_cache(session, cache_id_step2, "Step2"),
            chat_with_cache(session, cache_id_step3, "Step3")
        )
        
        end_parallel = datetime.now()
        parallel_duration = (end_parallel - start_parallel).total_seconds()
        
        result_step2, result_step3 = results
        
        if not result_step2 or not result_step3:
            log("❌ Step 2 or 3 failed")
            return
        
        log(f"\n✅ Steps 2 & 3 complete in {parallel_duration:.1f}s (expected ~9s)")
        log(f"   Step 2 result: {result_step2[:100]}...")
        log(f"   Step 3 result: {result_step3[:100]}...")
        
        # Step 4: Client-side concatenation
        log("\n📍 STEP 4: Client concatenates results")
        final_result = f"Trends: {result_step2}\n\nRecommendations: {result_step3}"
        log(f"✅ Final result length: {len(final_result)}")
        
        log("\n" + "=" * 70)
        log("Test Complete!")
        log("=" * 70)
        log(f"\n📊 Summary:")
        log(f"   Step 1: ✅ (3s processing)")
        log(f"   Step 2: ✅ (prepared + 6s processing)")
        log(f"   Step 3: ✅ (prepared + 9s processing)")
        log(f"   Step 4: ✅ (client-side concat)")
        log(f"   Parallel execution: {parallel_duration:.1f}s")


if __name__ == "__main__":
    asyncio.run(test_auto_mode())
