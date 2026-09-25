import json
import os
import tempfile
from urllib.parse import urlsplit
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from markitdown import MarkItDown
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
load_dotenv(ROOT / '.env')

class GlobalSettings:
    def __init__(self):
        self.endpoint = os.getenv('ENDPOINT', '').rstrip('/')
        if self.endpoint and not self.endpoint.endswith('/chat/completions'):
            self.endpoint += '/chat/completions'
        self.token = os.getenv('TOKEN', '')
        self.use_proxy = os.getenv('USE_PROXY', 'true').strip().lower() not in ('false', '0', 'no', 'off')
        self.stream = os.getenv('STREAM', 'true').strip().lower() not in ('false', '0', 'no', 'off')
        self.hide_output = os.getenv('HIDE_OUTPUT', 'false').strip().lower() in ('true', '1', 'yes', 'on')
    
    def update(self, endpoint=None, token=None, stream=None, hide_output=None, use_proxy=None):
        if use_proxy is not None:
            self.use_proxy = use_proxy
        if endpoint is not None:
            self.endpoint = endpoint
        if token is not None:
            self.token = token
        if stream is not None:
            self.stream = stream
        if hide_output is not None:
            self.hide_output = hide_output

settings = GlobalSettings()
PROXY = os.getenv('PROXY', 'http://127.0.0.1:3128').strip() or None


@asynccontextmanager
async def lifespan(app):
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    app.state.client = httpx.AsyncClient(
        proxy=PROXY, trust_env=False,
        timeout=httpx.Timeout(1800, connect=30, pool=10),
        limits=limits,
    )
    app.state.direct_client = httpx.AsyncClient(
        trust_env=False,
        timeout=httpx.Timeout(1800, connect=30, pool=10),
        limits=limits,
    )
    try:
        yield
    finally:
        await app.state.client.aclose()
        await app.state.direct_client.aclose()


def api_client():
    return app.state.client if settings.use_proxy else app.state.direct_client


app = FastAPI(title='VTask Cret', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


def convert_upload(path):
    return MarkItDown(enable_plugins=False).convert(path).text_content


@app.post('/api/convert')
async def convert_file(file: UploadFile):
    # Use a generated temporary path, never a user-supplied path.
    suffix = Path(file.filename or '').suffix.lower()
    if len(suffix) > 20 or any(c not in '.abcdefghijklmnopqrstuvwxyz0123456789' for c in suffix):
        suffix = ''
    try:
        with tempfile.TemporaryDirectory(prefix='vtask-upload-') as directory:
            path = Path(directory) / ('input' + suffix)
            size = 0
            with path.open('wb') as target:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 25 * 1024 * 1024:
                        raise HTTPException(413, 'Files must be 25 MB or smaller.')
                    target.write(chunk)
            if not size:
                raise HTTPException(400, 'The file is empty.')
            try:
                text = await run_in_threadpool(convert_upload, str(path))
            except Exception:
                raise HTTPException(422, 'Could not extract text from this file. It may be unsupported, damaged, or require additional conversion tools.')
            if not text or not text.strip():
                raise HTTPException(422, 'No text was extracted. Try a document containing selectable text.')
            if len(text) > 1000000:
                raise HTTPException(413, 'Extracted text exceeds the 1,000,000 character input limit.')
            return {'text': text}
    finally:
        await file.close()


@app.get('/')
async def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/config')
async def config():
    models = []
    warning = ''
    if settings.endpoint and settings.token:
        try:
            result = await api_client().get(settings.endpoint.removesuffix('/chat/completions') + '/models', headers={'Authorization': f"Bearer {settings.token}"})
            result.raise_for_status()
            models = sorted(item['id'] for item in result.json().get('data', []) if item.get('id'))
        except (httpx.HTTPError, ValueError, KeyError):
            warning = 'Model discovery unavailable. Enter your model ID below.'
    else:
        warning = 'Set TOKEN and ENDPOINT in .env, then restart the server.'
    return {'models': models, 'model': os.getenv('MODEL', 'inception/mercury-2.5'), 'route': 'Proxy' if settings.use_proxy and PROXY else 'Direct', 'warning': warning}


@app.get('/automode')
async def automode():
    return FileResponse(ROOT / 'static' / 'automode.html')


@app.get('/api/flows/vtask-maker')
async def vtask_maker():
    path = ROOT / 'vtask-automation.json'
    if not path.is_file():
        raise HTTPException(404, 'Vtask Maker flow file was not found.')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/setting')
async def setting():
    return FileResponse(ROOT / 'static' / 'setting.html')


@app.get('/api/settings')
async def get_settings():
    return {'endpoint': settings.endpoint, 'has_key': bool(settings.token), 'stream': settings.stream, 'hide_output': settings.hide_output, 'use_proxy': settings.use_proxy}


class SettingsRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)
    api_key: str = Field(default='', max_length=10000)
    stream: bool | None = None
    hide_output: bool | None = None
    use_proxy: bool | None = None


@app.post('/api/settings')
async def save_settings(body: SettingsRequest):
    endpoint = body.endpoint.strip().rstrip('/')
    try:
        parts = urlsplit(endpoint)
        valid = parts.scheme in ('http', 'https') and parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment
        _ = parts.port
    except ValueError:
        valid = False
    if not valid or any(char.isspace() for char in endpoint):
        raise HTTPException(400, 'Enter an HTTP(S) endpoint without credentials, query parameters, or fragments.')
    if not endpoint.endswith('/chat/completions'):
        endpoint += '/chat/completions'
    token = body.api_key.strip() or settings.token
    if not token or any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise HTTPException(400, 'Enter a valid API key without whitespace.')
    stream = settings.stream if body.stream is None else body.stream
    hide_output = settings.hide_output if body.hide_output is None else body.hide_output
    use_proxy = settings.use_proxy if body.use_proxy is None else body.use_proxy
    # Stage updates together, preserving the other environment settings.
    target = ROOT / '.env'
    staged = ROOT / '.env.settings.tmp'
    try:
        staged.write_text(target.read_text(encoding='utf-8') if target.exists() else '', encoding='utf-8')
        set_key(str(staged), 'ENDPOINT', endpoint)
        set_key(str(staged), 'TOKEN', token)
        set_key(str(staged), 'STREAM', str(stream).lower())
        set_key(str(staged), 'HIDE_OUTPUT', str(hide_output).lower())
        set_key(str(staged), 'USE_PROXY', str(use_proxy).lower())
        os.replace(staged, target)
    except OSError:
        raise HTTPException(500, 'Could not save settings. Check environment file permissions.')
    finally:
        staged.unlink(missing_ok=True)
    settings.update(endpoint=endpoint, token=token, stream=stream, hide_output=hide_output, use_proxy=use_proxy)
    return {**await get_settings(), 'message': 'Saved. New requests in both modes use these settings.'}


@app.get('/quiz-parser.js')
async def quiz_parser():
    source = (ROOT / 'quiz.html').read_text(encoding='utf-8')
    functions = source.split('    function processInput(', 1)[1].split('</script>', 1)[0]
    script = ('const START_MARKER="```quiz", END_MARKER="endquiz```", OPTION_VALUES=["A","B","C","D"];\n'
              + 'function processInput(' + functions)
    return Response(script, media_type='application/javascript')


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000000)
    model: str = Field(min_length=1, max_length=300)
    previous: str | None = Field(default=None, max_length=4000000)
    followup: str | None = Field(default=None, max_length=1000000)


@app.post('/api/chat')
async def chat(body: ChatRequest):
    if not settings.endpoint or not settings.token:
        raise HTTPException(503, 'TOKEN and ENDPOINT are required.')
    endpoint, token, to_client = settings.endpoint, settings.token, settings.stream
    client = api_client()
    messages = [{'role': 'user', 'content': body.prompt}]
    if body.followup:
        if not body.previous:
            raise HTTPException(400, 'A completed response is required before following up.')
        messages += [{'role': 'assistant', 'content': body.previous}, {'role': 'user', 'content': body.followup}]

    async def events():
        def event(data):
            return json.dumps(data) + '\n'
        # Always stream from the provider; the setting only gates delivery to the browser.
        full = ''
        try:
            async with client.stream('POST', endpoint, headers={'Authorization': f'Bearer {token}'}, json={
                'model': body.model, 'messages': messages, 'stream': True,
            }) as response:
                if response.is_error:
                    await response.aread()
                    yield event({'error': f'API returned HTTP {response.status_code}. Check the endpoint, model, and token.'})
                    return
                if 'application/json' in response.headers.get('content-type', ''):
                    data = json.loads(await response.aread())
                    text = data['choices'][0]['message'].get('content') or ''
                    yield event({'text': text})
                    yield event({'done': True})
                    return
                finished = False
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if payload == '[DONE]':
                        finished = True
                        break
                    data = json.loads(payload)
                    if data.get('error'):
                        yield event({'error': 'The provider reported a generation error. Please retry.'})
                        return
                    for choice in data.get('choices', []):
                        text = choice.get('delta', {}).get('content')
                        if text:
                            full += text
                            if to_client:
                                yield event({'text': text})
                        if choice.get('finish_reason'):
                            finished = True
                if finished:
                    if not to_client and full:
                        yield event({'text': full})
                    yield event({'done': True})
                else:
                    yield event({'error': 'The stream ended unexpectedly. Partial output is preserved.'})
        except httpx.HTTPError:
            yield event({'error': 'Connection failed or timed out. Check the configured proxy and endpoint. Partial output is preserved.'})
        except (ValueError, KeyError, TypeError):
            yield event({'error': 'The endpoint returned an unexpected response format.'})

    return StreamingResponse(events(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
