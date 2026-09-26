"""
Mock LLM server that simulates delays based on prompt content.

Supports prompts like "delay:3" to simulate a 3-second response.
Returns streaming JSON responses with chunks.
"""

import asyncio
import json
import re
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    
    # Extract delay from the last user message
    delay_seconds = 1.0
    response_text = "Mock response"
    
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            match = re.search(r'delay:(\d+)', content)
            if match:
                delay_seconds = int(match.group(1))
                response_text = f"Response after {delay_seconds}s delay"
            break
    
    async def generate():
        # Simulate processing delay
        await asyncio.sleep(delay_seconds)
        
        # Send response in chunks (simulate streaming)
        chunks = [
            f"Chunk 1 of response ",
            f"after {delay_seconds}s delay. ",
            f"This is chunk 2. ",
            f"Final chunk."
        ]
        
        for i, chunk_text in enumerate(chunks):
            chunk = {
                "id": f"mock-{i}",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": body.get("model", "mock"),
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk_text},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.1)  # Small delay between chunks
        
        # Send final chunk
        final = {
            "id": "mock-final",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": body.get("model", "mock"),
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5001, log_level="info")
