// Test auto mode: 2 inputs → step 1 (3s) → step 2 depends on step 1 (6s) → step 3 depends on step 1 (9s) → step 4 combines step 2 & 3

const BACKEND = 'http://127.0.0.1:8000';

async function streamSSE(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const data = trimmed.startsWith('data: ') ? trimmed.slice(6).trim() : trimmed;
            if (data === '[DONE]' || data === '') continue;
            
            try {
                const parsed = JSON.parse(data);
                if (parsed.text) {
                    process.stdout.write(parsed.text);
                    fullText += parsed.text;
                }
            } catch (e) {
                // Ignore parse errors
            }
        }
    }

    console.log(); // newline
    return fullText;
}

async function main() {
    console.log('=== Auto Mode Test ===\n');
    console.log('Flow: 2 inputs → step 1 (3s) → step 2 depends on step 1 (6s) → step 3 depends on step 1 (9s) → step 4 combines step 2 & 3\n');

    const startTime = Date.now();

    // Step 1: Process first input (3s delay)
    console.log('Step 1: Processing "Add numbers from 1 to 3" (expect 3s)...');
    const step1Start = Date.now();
    const step1Result = await streamSSE(`${BACKEND}/api/chat`, {
        prompt: 'Add numbers from 1 to 3',
        model: 'gpt-4o-mini',
        previous: '',
        followup: ''
    });
    console.log(`✓ Step 1 complete in ${((Date.now() - step1Start) / 1000).toFixed(1)}s\n`);

    // Step 2: Prepare cache for "Add numbers from 4 to 6" (depends on step 1)
    console.log('Step 2: Preparing cache for "Add numbers from 4 to 6" (depends on step 1)...');
    const prepareResponse2 = await fetch(`${BACKEND}/api/prepare-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            prompt: 'Add numbers from 4 to 6',
            model: 'gpt-4o-mini',
            previous: step1Result,
            followup: ''
        })
    });
    const { cache_id: cacheId2 } = await prepareResponse2.json();
    console.log(`✓ Cache prepared: ${cacheId2}\n`);

    // Step 3: Prepare cache for "Add numbers from 7 to 9" (depends on step 1)
    console.log('Step 3: Preparing cache for "Add numbers from 7 to 9" (depends on step 1)...');
    const prepareResponse3 = await fetch(`${BACKEND}/api/prepare-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            prompt: 'Add numbers from 7 to 9',
            model: 'gpt-4o-mini',
            previous: step1Result,
            followup: ''
        })
    });
    const { cache_id: cacheId3 } = await prepareResponse3.json();
    console.log(`✓ Cache prepared: ${cacheId3}\n`);

    // Step 2 execution: Call /chat with cache_id (6s delay)
    console.log('Step 2 execution: Calling /chat with cache_id (expect 6s)...');
    const step2Start = Date.now();
    const step2Result = await streamSSE(`${BACKEND}/api/chat`, {
        prompt: 'Add numbers from 4 to 6',
        model: 'gpt-4o-mini',
        previous: step1Result,
        followup: '',
        cache_id: cacheId2
    });
    console.log(`✓ Step 2 complete in ${((Date.now() - step2Start) / 1000).toFixed(1)}s\n`);

    // Step 3 execution: Call /chat with cache_id (9s delay)
    console.log('Step 3 execution: Calling /chat with cache_id (expect 9s)...');
    const step3Start = Date.now();
    const step3Result = await streamSSE(`${BACKEND}/api/chat`, {
        prompt: 'Add numbers from 7 to 9',
        model: 'gpt-4o-mini',
        previous: step1Result,
        followup: '',
        cache_id: cacheId3
    });
    console.log(`✓ Step 3 complete in ${((Date.now() - step3Start) / 1000).toFixed(1)}s\n`);

    // Step 4: Combine results (client-side, expect 3s default)
    console.log('Step 4: Combining step 2 and step 3 results (expect 3s)...');
    const step4Start = Date.now();
    const step4Result = await streamSSE(`${BACKEND}/api/chat`, {
        prompt: 'Combine these results',
        model: 'gpt-4o-mini',
        previous: `Step 2: ${step2Result}\nStep 3: ${step3Result}`,
        followup: ''
    });
    console.log(`✓ Step 4 complete in ${((Date.now() - step4Start) / 1000).toFixed(1)}s\n`);

    const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log('=== Test Complete ===');
    console.log(`Total time: ${totalTime}s`);
    console.log(`\nStep 1 result: ${step1Result.substring(0, 60)}...`);
    console.log(`Step 2 result: ${step2Result.substring(0, 60)}...`);
    console.log(`Step 3 result: ${step3Result.substring(0, 60)}...`);
    console.log(`Step 4 result: ${step4Result.substring(0, 60)}...`);
}

main().catch(console.error);
