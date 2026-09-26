"""
Mock LLM server that simulates realistic delays.

Supports special delay syntax in user messages:
- "delay:3" -> 3 second total delay
- "delay:6" -> 6 second total delay
- "delay:9" -> 9 second total delay

Streams chunks gradually over the delay period.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import json
import re

app = FastAPI()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: str
    stream: bool = True
    max_tokens: int = 1024


async def generate_delayed_stream(delay_seconds: int, content_prefix: str):
    """Generate SSE stream with realistic delay"""
    
    # Number of chunks to send
    num_chunks = 20
    delay_per_chunk = delay_seconds / num_chunks
    
    # Stream chunks gradually
    for i in range(num_chunks):
        await asyncio.sleep(delay_per_chunk)
        
        chunk = {
            "id": f"chatcmpl-{i}",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": "claude-3-5-sonnet-20241022",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": f"{content_prefix} chunk {i+1}/{num_chunks}. "
                },
                "finish_reason": None
            }]
        }
        
        yield f"data: {json.dumps(chunk)}\n\n"
    
    # Send finish chunk
    finish_chunk = {
        "id": "chatcmpl-finish",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": "claude-3-5-sonnet-20241022",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    
    yield f"data: {json.dumps(finish_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """Mock chat completions endpoint with delay support"""
    
    # Extract delay from user message
    delay_seconds = 3  # default
    content_prefix = "Response"
    
    if request.messages:
        last_message = request.messages[-1].content
        
        # Check for delay:N pattern
        match = re.search(r'delay:(\d+)', last_message)
        if match:
            delay_seconds = int(match.group(1))
            content_prefix = f"Delayed {delay_seconds}s response"
        else:
            content_prefix = f"Response to: {last_message[:30]}"
    
    print(f"[mock_server] Generating response with {delay_seconds}s delay")
    
    return StreamingResponse(
        generate_delayed_stream(delay_seconds, content_prefix),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
