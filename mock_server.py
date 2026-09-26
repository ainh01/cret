"""Mock OpenAI/Anthropic server for testing cache protocol."""
import json
import time
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def stream_response(content: str, delay_ms: int = 50):
    """Stream a response chunk by chunk."""
    words = content.split()
    for i, word in enumerate(words):
        chunk = {
            "choices": [{
                "delta": {"content": word + " "},
                "index": 0,
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        time.sleep(delay_ms / 1000.0)
    
    # Final chunk
    final = {
        "choices": [{
            "delta": {},
            "index": 0,
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final)}\n\n"
    yield "data: [DONE]\n\n"

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Mock OpenAI chat completions endpoint."""
    data = request.json
    messages = data.get('messages', [])
    
    # Extract the last user message
    user_msg = "Hello"
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            user_msg = msg.get('content', '')[:50]
            break
    
    # Generate a response based on the message
    response_text = f"Mock response to: {user_msg}. This is a streaming test with multiple words to simulate real generation."
    
    print(f"[mock] Received request with {len(messages)} messages, responding with stream")
    
    return Response(
        stream_response(response_text, delay_ms=30),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/v1/messages', methods=['POST'])
def anthropic_messages():
    """Mock Anthropic messages endpoint."""
    data = request.json
    messages = data.get('messages', [])
    
    # Extract the last user message
    user_msg = "Hello"
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'text':
                        user_msg = block.get('text', '')[:50]
                        break
            else:
                user_msg = content[:50]
            break
    
    response_text = f"Mock Anthropic response to: {user_msg}. This simulates Claude streaming with proper event formatting."
    
    print(f"[mock] Received Anthropic request with {len(messages)} messages, responding with stream")
    
    def anthropic_stream():
        words = response_text.split()
        for word in words:
            event = {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": word + " "}
            }
            yield f"data: {json.dumps(event)}\n\n"
            time.sleep(0.03)
        
        yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}})}\n\n"
    
    return Response(
        anthropic_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    print("Starting mock LLM server on http://localhost:5001")
    print("OpenAI endpoint: POST http://localhost:5001/v1/chat/completions")
    print("Anthropic endpoint: POST http://localhost:5001/v1/messages")
    app.run(port=5001, debug=True, threaded=True)
