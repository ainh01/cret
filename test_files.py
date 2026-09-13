"""File import API checks with real MarkItDown conversions."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from zipfile import ZipFile
from fastapi.testclient import TestClient
import app

client = TestClient(app.app)
for name, content in [('notes.txt', b'Hello from a file'),
                      ('page.html', b'<html><body><h1>Hello from a file</h1></body></html>')]:
    result = client.post('/api/convert', files={'file': (name, content)})
    assert result.status_code == 200, result.text
    assert 'Hello from a file' in result.json()['text']

buffer = BytesIO()
with ZipFile(buffer, 'w') as archive:
    archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Word document import</w:t></w:r></w:p></w:body></w:document>')
result = client.post('/api/convert', files={'file': ('document.docx', buffer.getvalue())})
assert result.status_code == 200, result.text
assert 'Word document import' in result.json()['text']
assert client.post('/api/convert', files={'file': ('empty.txt', b'')}).status_code == 400
assert client.post('/api/convert', files={'file': ('large.txt', b'x' * (25 * 1024 * 1024 + 1))}).status_code == 413
paths = []

def fail(path):
    paths.append(Path(path))
    raise ValueError('Internal conversion error')

with patch.object(app, 'convert_upload', fail):
    result = client.post('/api/convert', files={'file': ('../../document.txt', b'content')})
    assert result.status_code == 422
    assert 'Internal conversion error' not in result.text
assert paths and all(not path.parent.exists() for path in paths)
with patch.object(app, 'convert_upload', return_value=' '):
    assert client.post('/api/convert', files={'file': ('blank.txt', b' ')}).status_code == 422
with patch.object(app, 'convert_upload', return_value='x' * 1000001):
    assert client.post('/api/convert', files={'file': ('long.txt', b'x')}).status_code == 413
print('Text, HTML, Word import, limits, empty files, conversion errors and cleanup passed.')