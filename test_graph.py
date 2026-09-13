"""Run automation graph tests against the actual JavaScript using quickjs."""
from pathlib import Path
import quickjs

root = Path(__file__).parent
source = (root / 'static/automode.js').read_text(encoding='utf-8')
quiz = (root / 'quiz.html').read_text(encoding='utf-8')
context = quickjs.Context()
context.eval('const START_MARKER="```quiz",END_MARKER="endquiz```",OPTION_VALUES=["A","B","C","D"];'
             + 'function processInput(' + quiz.split('    function processInput(', 1)[1].split('</script>', 1)[0])
context.eval(source.split("el('add-step').onclick", 1)[0])
context.eval(r'''
var outcome='pending';
function check(value,message){if(!value)throw Error(message);}
function node(id,type,sources,prefix=''){return {id,type,sources,prefix,suffix:''};}
(async()=>{
 const noop=()=>{},signal={aborted:false};
 const saved={version:1,model:'inception/mercury-2.5',input:'saved input',steps:[node(1,'ai',[],'prefix'),node(2,'final',[{id:1,mode:'quiz'}])]};
 const restored=validateAutomation(JSON.parse(JSON.stringify(saved)));
 check(restored.model===saved.model&&restored.input===saved.input&&restored.steps[0].prefix==='prefix'&&restored.steps[1].sources[0].mode==='quiz'&&restored.steps.length===2,'Local file round trip');
 for(const change of [data=>{data.version=2;},data=>{data.steps[1].sources=[];},data=>{data.steps[1].sources[0].id=2;},data=>{data.steps[1].sources[0].mode='invalid';},data=>{data.steps[1].id=1;}]){
   const invalid=JSON.parse(JSON.stringify(saved));change(invalid);let rejected=false;
   try{validateAutomation(invalid);}catch{rejected=true;}check(rejected,'Invalid import accepted');
 }
 const plan=[node(1,'ai',[]),node(2,'ai',[{id:1,mode:'txt'}],'Left:'),node(3,'ai',[{id:1,mode:'all'}],'Right:'),node(4,'combine',[{id:3,mode:'all'},{id:2,mode:'all'}]),node(5,'final',[{id:4,mode:'all'}])];
 let calls=[],release,started=0;
 const request=async prompt=>{
   calls.push(prompt);
   if(calls.length===1)return '```txt\nROOT\n```';
   started++;
   if(started===1)await new Promise(resolve=>{release=resolve;});
   else release();
   return prompt.startsWith('Left:')?'LEFT':'RIGHT';
 };
 const result=await executeSteps(plan,'INPUT','model',signal,noop,noop,request);
 check(started===2,'Branches did not start concurrently');
 check(calls[1]==='Left:ROOT','TXT selection failed');
 check(calls[2]==='Right:```txt\nROOT\n```','All selection failed');
 check(result==='LEFT\n\nRIGHT','Combine must use step order');
 check(calls.length===3,'Combine/final must not call AI');
 const multiSaved={...saved,inputs:['one','two','three']};
 check(validateAutomation(multiSaved).inputs.join('|')==='one|two|three','Multiple inputs saved');
 check(validateAutomation(saved).inputs[0]==='saved input','Legacy input import');
 const independent=[node(1,'ai',[]),node(2,'final',[{id:1,mode:'all'}])];
 let active=0,peak=0;
 const independentRequest=async prompt=>{active++;peak=Math.max(peak,active);await Promise.resolve();active--;if(prompt==='bad')throw Error('Failed input');return prompt+' result';};
 const independentResults=await Promise.allSettled(['one','bad','three'].map(input=>executeSteps(independent,input,'model',signal,noop,noop,independentRequest)));
 check(peak===3,'Independent inputs must overlap');
 check(independentResults[0].value==='one result'&&independentResults[1].status==='rejected'&&independentResults[2].value==='three result','Independent outputs and failures');
 const valid='```quiz\n'+JSON.stringify([{question:'Test',options:['A','B','C','D'].map(value=>({label:value,value})),correct:'A'}])+'\nendquiz```';
 const invalid='```quiz\n[{"options":[]}]\nendquiz```';
 let expected='';try{processInput(invalid,false);}catch(error){expected=error.message;}
 let repairCalls=0;
 const repaired=await executeSteps([node(1,'ai',[]),node(2,'final',[{id:1,mode:'quiz'}])],'INPUT','model',signal,noop,noop,async(prompt,model,signal,onText,context)=>{
   if(!context)return invalid;
   repairCalls++;check(context.previous===invalid,'Repair must include original response');
   check(context.followup.includes(expected),'Repair must contain exact parser error');
   return valid;
 });
 check(repairCalls===1&&repaired.endsWith('endquiz```'),'Quiz repair failed');
 repairCalls=0;
 try{await executeSteps([node(1,'ai',[]),node(2,'final',[{id:1,mode:'quiz'}])],'INPUT','model',signal,noop,noop,async()=>{repairCalls++;return invalid;});throw Error('Expected failure');}
 catch(error){check(error.message.includes('after one follow-up')&&repairCalls===2,'Repair must stop after one follow-up');}
 try{await executeSteps([node(1,'ai',[]),node(2,'combine',[])],'INPUT','model',signal,noop,noop,request);throw Error('Expected missing source error');}
 catch(error){check(error.message.includes('select at least one'),'Missing source validation');}
 try{await executeSteps([node(1,'ai',[]),node(2,'final',[{id:99,mode:'all'}])],'INPUT','model',signal,noop,noop,request);throw Error('Expected invalid source');}
 catch(error){check(error.message.includes('earlier step'),'Invalid dependency validation');}
 const longPlan=[node(1,'ai',[])];for(let i=2;i<=103;i++)longPlan.push(node(i,i===103?'final':'ai',[{id:i-1,mode:'all'}]));
 check(await executeSteps(longPlan,'INPUT','model',signal,noop,noop,async prompt=>prompt)==='INPUT','Long chain');
 let reads=[{value:'{"text":"hel',done:false},{value:'lo"}\n{"done":true}\n',done:false},{done:true}];
 globalThis.TextDecoder=class{decode(value){return value||'';}};
 globalThis.fetch=async()=>({ok:true,body:{getReader:()=>({read:async()=>reads.shift()})}});
 check(await generate('prompt','model',signal,noop)==='hello','Chunked stream buffering');
 outcome='passed';
})().catch(error=>{outcome=error.message;});
''')
while context.execute_pending_job():
    pass
assert context.eval('outcome') == 'passed', context.eval('outcome')
print('Parallel execution, combine order, quiz parser repair, retry limit, graph validation, 103 steps, and streaming passed')