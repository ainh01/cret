const express = require('express');
const app = express();
app.use(express.json());

// Track requests to simulate different delays
let requestCount = 0;

app.post('/chat/completions', async (req, res) => {
    requestCount++;
    const requestId = requestCount;
    
    console.log(`[${new Date().toISOString()}] Request ${requestId} received`);
    
    const { messages, model, stream } = req.body;
    
    if (!messages || !Array.isArray(messages)) {
        return res.status(400).json({ error: 'messages array is required' });
    }
    
    // Determine delay based on the content
    let delay = 3000; // Default 3s for step 1
    const lastMessage = messages[messages.length - 1]?.content || '';
    
    if (lastMessage.includes('4 to 6')) {
        delay = 6000; // 6s for step 2
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Step 2 detected, using 6s delay`);
    } else if (lastMessage.includes('7 to 9')) {
        delay = 9000; // 9s for step 3
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Step 3 detected, using 9s delay`);
    } else if (lastMessage.includes('Combine')) {
        delay = 1000; // 1s for step 4 (fast)
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Step 4 detected, using 1s delay`);
    } else {
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Step 1 detected, using 3s delay`);
    }
    
    if (stream) {
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        
        const chunks = [
            { content: 'Chunk 1 ' },
            { content: 'of response ' },
            { content: `after ${delay/1000}s delay. ` },
            { content: 'This is chunk 2. ' },
            { content: 'Final chunk.' }
        ];
        
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Starting stream with ${delay}ms total delay`);
        const startTime = Date.now();
        
        // Send chunks with timing
        for (let i = 0; i < chunks.length; i++) {
            const chunkDelay = (delay / chunks.length) * (i + 1);
            const elapsed = Date.now() - startTime;
            const waitTime = chunkDelay - elapsed;
            
            if (waitTime > 0) {
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }
            
            const chunk = {
                id: `chatcmpl-${requestId}-${i}`,
                object: 'chat.completion.chunk',
                created: Math.floor(Date.now() / 1000),
                model: model || 'gpt-4o-mini',
                choices: [{
                    index: 0,
                    delta: i === chunks.length - 1 ? {} : { content: chunks[i].content },
                    finish_reason: i === chunks.length - 1 ? 'stop' : null
                }]
            };
            
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
            console.log(`[${new Date().toISOString()}] Request ${requestId}: Sent chunk ${i + 1}/${chunks.length}`);
        }
        
        res.write('data: [DONE]\n\n');
        res.end();
        
        const totalTime = Date.now() - startTime;
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Stream complete in ${totalTime}ms`);
    } else {
        // Non-streaming response
        await new Promise(resolve => setTimeout(resolve, delay));
        
        const response = {
            id: `chatcmpl-${requestId}`,
            object: 'chat.completion',
            created: Math.floor(Date.now() / 1000),
            model: model || 'gpt-4o-mini',
            choices: [{
                index: 0,
                message: {
                    role: 'assistant',
                    content: `Response after ${delay/1000}s delay.`
                },
                finish_reason: 'stop'
            }],
            usage: {
                prompt_tokens: 10,
                completion_tokens: 10,
                total_tokens: 20
            }
        };
        
        res.json(response);
        console.log(`[${new Date().toISOString()}] Request ${requestId}: Non-stream response sent after ${delay}ms`);
    }
});

const PORT = 5001;
app.listen(PORT, () => {
    console.log(`Mock OpenAI server running on http://127.0.0.1:${PORT}`);
    console.log('Timing rules:');
    console.log('  - Step 1 (default): 3s');
    console.log('  - Step 2 (4 to 6): 6s');
    console.log('  - Step 3 (7 to 9): 9s');
    console.log('  - Step 4 (Combine): 1s');
});
