import json
from pathlib import Path
import quickjs
from fastapi.testclient import TestClient
import app

root = Path(__file__).parent
source = (root / 'static/automode.js').read_text(encoding='utf-8')
response = TestClient(app.app).get('/api/flows/vtask-maker')
assert response.status_code == 200
assert response.json() == json.loads((root / 'vtask-automation.json').read_text(encoding='utf-8'))
ctx = quickjs.Context()
ctx.eval(source.split("el('add-step').onclick", 1)[0])
ctx.eval('''
const items={};
const document={getElementById(id){return items[id] ||= {value:'',nextElementSibling:{replaceWith(){}},replaceChildren(){}};}};
const window={fileImportBusy:false};
function Option(){}
function clearInterval(){}
function createFileInput(){}
renderInputs=renderSteps=()=>{};
showOutput=text=>{output=text;};
''')
ctx.eval(source[source.index('let presetLoading=false;'):source.index("el('vtask-maker').onclick")])
ctx.eval('applyAutomation(validateAutomation('+json.dumps(response.json())+'));')
assert ctx.eval('steps.length') == 5
assert ctx.eval('steps[4].sources[1].mode') == 'quiz'
ctx.eval("jobs=[{status:'Failed'}];extraInputs=['old'];output='old';el('clean-auto').onclick();")
assert ctx.eval("steps.length===2&&nextId===3&&jobs.length===0&&extraInputs.length===0&&output===''&&el('auto-input').value===''&&el('retry-auto').disabled")
print('Saved preset API, flow validation, and clean/reset state passed.')