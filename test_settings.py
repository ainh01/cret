import os
import json
import httpx
import tempfile
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from fastapi.testclient import TestClient
import app as server

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / '.env').write_text('MODEL=test-model\nPROXY=http://127.0.0.1:3128\n')
    with patch.object(server, 'ROOT', root):
        server.settings = server.GlobalSettings()
        with TestClient(server.app) as client:
            assert client.get('/api/settings').json()['stream'] is True
            response = client.post('/api/settings', json={'endpoint': 'https://example.com/v1', 'api_key': 'test-secret'})
            assert response.status_code == 200
            assert response.json()['endpoint'] == 'https://example.com/v1/chat/completions'
            assert 'test-secret' not in client.get('/api/settings').text
            saved = dotenv_values(root / '.env')
            assert saved['TOKEN'] == 'test-secret' and saved['MODEL'] == 'test-model'
            assert client.post('/api/settings', json={'endpoint': 'https://example.org/v1/chat/completions', 'api_key': ''}).status_code == 200
            assert dotenv_values(root / '.env')['TOKEN'] == 'test-secret'
            for endpoint in ['file:///tmp/test', 'https://user:password@example.org', 'https://example.org/?key=value']:
                assert client.post('/api/settings', json={'endpoint': endpoint}).status_code == 400
            assert server.settings.endpoint == 'https://example.org/v1/chat/completions'
            assert not (root / '.env.settings.tmp').exists()
            requests = []
            for use_proxy in [False, True]:
                response = client.post('/api/settings', json={'endpoint': server.settings.endpoint, 'use_proxy': use_proxy})
                assert response.status_code == 200
                assert response.json()['use_proxy'] is use_proxy
                assert client.get('/api/settings').json()['use_proxy'] is use_proxy
                assert dotenv_values(root / '.env')['USE_PROXY'] == str(use_proxy).lower()
                assert server.api_client() is (server.app.state.client if use_proxy else server.app.state.direct_client)
                client.post('/api/settings', json={'endpoint': server.settings.endpoint})
                assert server.settings.use_proxy is use_proxy
            def provider(request):
                body = json.loads(request.content)
                requests.append(body)
                # Backend must always stream from the provider, regardless of the client setting.
                assert body['stream'] is True
                return httpx.Response(200, headers={'content-type': 'text/event-stream'}, text=(
                    'data: {"choices":[{"delta":{"content":"hello "}}]}\n\n'
                    'data: {"choices":[{"delta":{"content":"world"}}]}\n\n'
                    'data: [DONE]\n\n'))
            real_client = server.app.state.client
            mock_client = httpx.AsyncClient(transport=httpx.MockTransport(provider))
            server.app.state.client = mock_client
            try:
                for enabled in [False, True]:
                    response = client.post('/api/settings', json={'endpoint': server.settings.endpoint, 'stream': enabled})
                    assert response.json()['stream'] is enabled
                    assert client.get('/api/settings').json()['stream'] is enabled
                    assert dotenv_values(root / '.env')['STREAM'] == str(enabled).lower()
                    # Older clients that omit stream must preserve the setting.
                    client.post('/api/settings', json={'endpoint': server.settings.endpoint})
                    assert server.settings.stream is enabled
                    response = client.post('/api/chat', json={'prompt': 'test', 'model': 'test-model'})
                    events = [json.loads(line) for line in response.text.splitlines()]
                    assert ''.join(e.get('text', '') for e in events) == 'hello world'
                    # Streaming forwards each delta; buffered mode sends one complete text event.
                    assert len([e for e in events if 'text' in e]) == (2 if enabled else 1)
                    assert events[-1] == {'done': True}
                    assert requests[-1]['stream'] is True
                for hide in [False, True]:
                    response = client.post('/api/settings', json={'endpoint': server.settings.endpoint, 'hide_output': hide})
                    assert response.json()['hide_output'] is hide
                    loaded = client.get('/api/settings').json()
                    assert loaded['hide_output'] is hide
                    assert dotenv_values(root / '.env')['HIDE_OUTPUT'] == str(hide).lower()
                    client.post('/api/settings', json={'endpoint': server.settings.endpoint})
                    assert server.settings.hide_output is hide
            finally:
                client.portal.call(mock_client.aclose)
                server.app.state.client = real_client
print('Settings persistence, blank-key preservation, secret omission, endpoint validation, stream toggle, and hide output passed')