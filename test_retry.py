"""Exercise automation batch/retry orchestration without API calls."""
from pathlib import Path
import quickjs

source = (Path(__file__).parent / 'static/automode.js').read_text(encoding='utf-8')
context = quickjs.Context()
context.eval('function fetch(){return Promise.resolve({json:async()=>({hide_output:false})});}')
context.eval(source.split("el('add-step').onclick", 1)[0])
context.eval(source[source.index('async function runJobs('):source.index('\nrenderSteps();\nfetch')])
context.eval(r'''
const elements = {};
const document = {getElementById(id){return elements[id] ||= {
  value: id==='auto-model'?'model':id==='output-job'?'0':'original',
  options: [], replaceChildren(...items){this.options=items;this.value='0';}
};}};
function Option(text,value){this.textContent=text;this.value=value;}
function AbortController(){this.signal={aborted:false,addEventListener(){},removeEventListener(){}};this.abort=()=>{this.signal.aborted=true;};}
let copies=[],calls=[],fail=true;
const navigator={clipboard:{async writeText(text){copies.push(text);}}};
renderSteps=renderInputs=startRuntime=stopRuntime=()=>{};
showOutput=text=>{output=text;};
executeSteps=async(plan,input,model,signal,onStep,onText)=>{
  calls.push({input,model,prefix:plan[0].prefix});
  if(input==='bad'&&fail)throw Error('Test failure');
  onText(input+' result');return input+' result';
};
function check(value,message){if(!value)throw Error(message);}
var outcome='pending';
(async()=>{
  extraInputs=['bad'];
  await runJobs();
  check(calls.length===2&&jobs[0].status==='Complete'&&jobs[1].status==='Failed','Initial batch states');
  check(copies.length===0,'Multi-input batch must not copy');
  const first=jobs[0],firstOutput=first.output;
  steps[0].prefix='changed';el('auto-model').value='changed';extraInputs=['changed'];
  fail=false;el('output-job').value='1';
  await runJobs(1);
  check(calls.length===3&&calls[2].input==='bad'&&calls[2].model==='model'&&calls[2].prefix==='','Retry must reuse original snapshot');
  check(jobs[0]===first&&first.output===firstOutput&&jobs[1].status==='Complete','Retry must preserve other jobs');
  check(copies.length===0,'Retry must not auto-copy');
  await runJobs(0);check(calls.length===3,'Successful job cannot retry');
  extraInputs=[];await runJobs();
  check(copies.length===1&&copies[0]==='original result','Single input must auto-copy');
  outcome='passed';
})().catch(error=>{outcome=String(error);});
''')
while context.execute_pending_job():
    pass
assert context.eval('outcome') == 'passed', context.eval('outcome')
print('Failed-job retry isolation, original snapshot, and single-input copying passed.')