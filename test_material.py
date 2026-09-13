"""Run with the optional quickjs development package installed."""
from pathlib import Path
import quickjs

source = (Path(__file__).parent / 'static' / 'app.js').read_text(encoding='utf-8')
helper = source.split('function fixMaterialEnding(text){', 1)[1].split("$('copy-fixed').onclick", 1)[0]
context = quickjs.Context()
context.eval('function fixMaterialEnding(text){' + helper)
fix = context.get('fixMaterialEnding')
cases = [
    ('```material\nbody\nendmaterial```', '```material\nbody\nendmaterial```'),
    ('```material\nbody\nendmaterial\n```', '```material\nbody\nendmaterial```'),
    ('```material\nbody\n```', '```material\nbody\nendmaterial```'),
    ('```material\r\nbody\r\nendmaterial\r\n```\r\n', '```material\r\nbody\r\nendmaterial```\r\n'),
    ('```material\nbody\n```\n', '```material\nbody\nendmaterial```\n'),
    ('plain output', 'plain output'),
    ('```material\nbody\nendmaterial```\n', '```material\nbody\nendmaterial```\n'),
    ('```material\nbody\n```\nmore text', '```material\nbody\n```\nmore text'),
    ('```material\nbody```', '```material\nbody```'),
]
for original, expected in cases:
    assert fix(original) == expected, repr(original)
print(f'{len(cases)} JavaScript material-ending checks passed')