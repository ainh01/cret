"""Test the browser's TXT extraction helper with the optional quickjs package."""
from pathlib import Path
import quickjs

source = (Path(__file__).parent / 'static' / 'app.js').read_text(encoding='utf-8')
helper = source.split('function extractLastTxt(text){', 1)[1].split("$('copy-txt').onclick", 1)[0]
context = quickjs.Context()
context.eval('function extractLastTxt(text){' + helper)
extract = context.get('extractLastTxt')
cases = [
    ('```txt\nhello\n```', 'hello'),
    ('Mention ```txt randomly.\n```txt\ncorrect\n```', 'correct'),
    ('```txt\nfirst\n```\n```txt\nlast\n```', 'last'),
    ('```txt\na\n```\nb\n```', 'a\n```\nb'),
    ('```TXT\r\nhello\r\n```', 'hello'),
    ('```txt\n```', ''),
    ('no block', None),
    ('```txt\nunclosed', None),
    ('```\n```txt\nunclosed', None),
]
for original, expected in cases:
    assert extract(original) == expected, repr(original)
print(f'{len(cases)} JavaScript TXT extraction checks passed')