const el=id=>document.getElementById(id);
let nextId=3;
let steps=[{id:1,type:'ai',prefix:'',suffix:'',sources:[]},{id:2,type:'final',prefix:'',suffix:'',sources:[{id:1,mode:'all'}]}];
let running=false,controller,output='',loadedAutomation=false,runtimeTimer,runtimeStart=0;
let extraInputs=[],jobs=[];
function inputValues(){return [el('auto-input').value,...extraInputs];}
function renderInputs(){
  el('extra-inputs').replaceChildren();
  extraInputs.forEach((text,index)=>{
    const section=document.createElement('section');section.className='step';
    const label=document.createElement('label');label.htmlFor=`extra-input-${index}`;label.textContent=`Input ${index+2}`;
    const area=document.createElement('textarea');area.id=label.htmlFor;area.value=text;area.disabled=running;
    area.oninput=()=>{extraInputs[index]=area.value;};
    const paste=document.createElement('button');paste.textContent='Paste input';paste.disabled=running;
    paste.onclick=async()=>{try{extraInputs[index]=await navigator.clipboard.readText();area.value=extraInputs[index];}catch{el('auto-error').hidden=false;el('auto-error').textContent='Clipboard unavailable. Paste manually.';}};
    const remove=document.createElement('button');remove.textContent='Remove input';remove.disabled=running;
    remove.onclick=()=>{extraInputs.splice(index,1);renderInputs();};
    section.append(label,area,paste,remove,createFileInput(area,value=>{extraInputs[index]=value;},()=>running));el('extra-inputs').append(section);
  });
}
function viewJob(){
  el('retry-auto').disabled=running||!jobs[Number(el('output-job').value)]?.status?.startsWith('Failed');
  const job=jobs[Number(el('output-job').value)];if(!job)return;
  showOutput(job.output);
  el('auto-error').hidden=!job.error;el('auto-error').textContent=job.error||'';
  steps.forEach((step,index)=>{el(`state-${step.id}`).textContent=job.states[index]||'Waiting';});
}
function updateJob(index){
  const job=jobs[index],option=el('output-job').options[index];
  if(option)option.textContent=`Input ${index+1} · ${job.status}`;
  if(Number(el('output-job').value)===index)viewJob();
}
function formatRuntime(milliseconds){return `Runtime · ${(milliseconds/1000).toFixed(3)} s`;}
function startRuntime(){
  runtimeStart=performance.now();el('auto-runtime').textContent=formatRuntime(0);
  clearInterval(runtimeTimer);runtimeTimer=setInterval(()=>el('auto-runtime').textContent=formatRuntime(performance.now()-runtimeStart),16);
}
function stopRuntime(){
  clearInterval(runtimeTimer);runtimeTimer=null;
  el('auto-runtime').textContent=formatRuntime(Math.max(0,performance.now()-runtimeStart));
}

function validateAutomation(data){
  if(!data||data.version!==1||!Array.isArray(data.steps)||data.steps.length<2)
    throw Error('Invalid automation file: version 1 and at least two steps are required.');
  if(typeof data.model!=='string'||!data.model.trim()||typeof data.input!=='string')
    throw Error('Invalid automation file: model and input must be text.');
  const inputs=data.inputs===undefined?[data.input]:data.inputs;
  if(!Array.isArray(inputs)||!inputs.length||inputs.some(value=>typeof value!=='string'))throw Error('At least one text input is required.');
  const ids=new Set();
  const clean=data.steps.map((step,index)=>{
    if(!step||!Number.isSafeInteger(step.id)||step.id<1||ids.has(step.id)||step.id>=Number.MAX_SAFE_INTEGER)
      throw Error(`Invalid step ${index+1}: IDs must be unique positive integers.`);
    const last=index===data.steps.length-1;
    if(!(last?step.type==='final':index===0?step.type==='ai':['ai','combine'].includes(step.type)))
      throw Error(`Invalid step ${index+1}: incorrect step type.`);
    if(typeof step.prefix!=='string'||typeof step.suffix!=='string'||!Array.isArray(step.sources))
      throw Error(`Invalid step ${index+1}: missing prompts or sources.`);
    if(step.type!=='ai'&&(step.prefix!==''||step.suffix!==''))
      throw Error(`Invalid step ${index+1}: combine and final prompts must be empty.`);
    if(index===0?step.sources.length!==0:step.sources.length<1||(step.type==='ai'&&step.sources.length!==1))
      throw Error(`Invalid step ${index+1}: incorrect number of sources.`);
    const selected=new Set();
    const sources=step.sources.map(source=>{
      if(!source||!ids.has(source.id)||selected.has(source.id)||!['all','txt','material','quiz'].includes(source.mode))
        throw Error(`Invalid step ${index+1}: sources must be distinct earlier steps with a supported format.`);
      selected.add(source.id);return {id:source.id,mode:source.mode};
    });
    ids.add(step.id);
    return {id:step.id,type:step.type,prefix:step.prefix,suffix:step.suffix,sources};
  });
  return {version:1,model:data.model,input:inputs[0],inputs,steps:clean};
}

function selectContent(text,mode){
  if(mode==='txt'){
    const start=text.toLowerCase().lastIndexOf('```txt'),end=text.lastIndexOf('```');
    return start<0||end<start+6?text:text.slice(start+6,end).trim();
  }
  if(mode==='material'){
    if(/endmaterial```[\t \r\n]*$/.test(text))return text;
    if(/endmaterial[\t ]*\r?\n[\t ]*```([\t \r\n]*)$/.test(text))
      return text.replace(/endmaterial[\t ]*\r?\n[\t ]*```([\t \r\n]*)$/, 'endmaterial```$1');
    return text.replace(/(^|\n)([\t ]*)```([\t \r\n]*)$/, '$1$2endmaterial```$3');
  }
  return text;
}

function renderSteps(){
  el('steps').replaceChildren();
  steps.forEach((step,index)=>{
    const last=index===steps.length-1;
    const section=document.createElement('section');section.className='step';
    section.innerHTML=`<div class="step-heading"><h3>Step ${index+1} · ${last?'Final combine':step.type==='combine'?'Combine':'AI prompt'}</h3><button type="button">Remove step</button></div>`;
    const remove=section.querySelector('button');remove.disabled=running||steps.length<=2;
    remove.disabled=remove.disabled||index===0||last;
    remove.onclick=()=>{steps.splice(index,1);for(const node of steps)node.sources=node.sources.filter(source=>source.id!==step.id);renderSteps();};
    const badge=document.createElement('p');badge.id=`state-${step.id}`;badge.className='small-note';badge.textContent=step.status||'Waiting';section.append(badge);
    for(const [key,title] of [['prefix','Prefix prompt'],['suffix','Suffix prompt']]){
      const id=`step-${index}-${key}`,label=document.createElement('label');label.htmlFor=id;label.textContent=title;
      const field=document.createElement('textarea');field.id=id;
      field.value=step[key];field.disabled=running||step.type!=='ai';
      field.addEventListener('input',()=>{step[key]=field.value;});
      section.append(label,field);
    }
    if(index>0){
      const legend=document.createElement('p');legend.className='small-note';legend.textContent=step.type==='ai'?'Choose one source. Steps sharing a source run in parallel.':'Select one or more outputs to combine (top to bottom).';section.append(legend);
      steps.slice(0,index).forEach((prior,priorIndex)=>{
        const row=document.createElement('div');row.className='source-row';
        const label=document.createElement('label'),check=document.createElement('input');
        check.type=step.type==='ai'?'radio':'checkbox';check.name=`sources-${step.id}`;
        const selected=step.sources.find(source=>source.id===prior.id);
        check.checked=Boolean(selected);check.disabled=running;
        label.append(check,document.createTextNode(`Step ${priorIndex+1}`));
        const mode=document.createElement('select');mode.setAttribute('aria-label',`Step ${index+1}: content from step ${priorIndex+1}`);
        for(const value of ['all','txt','material','quiz']){const option=document.createElement('option');option.value=value;option.textContent=value;mode.append(option);}
        mode.value=selected?.mode||'all';mode.disabled=running||!selected;
        check.onchange=()=>{
          if(step.type==='ai')step.sources=[];
          else step.sources=step.sources.filter(source=>source.id!==prior.id);
          if(check.checked)step.sources.push({id:prior.id,mode:mode.value});renderSteps();
        };
        mode.onchange=()=>{step.sources.find(source=>source.id===prior.id).mode=mode.value;};
        row.append(label,mode);section.append(row);
      });
    }
    if(!last){const branch=document.createElement('button');branch.textContent='+ Parallel · 2 branches';branch.disabled=running;branch.onclick=()=>{
      const nodes=[newNode('ai',step.id),newNode('ai',step.id)];steps.splice(index+1,0,...nodes);
      steps[steps.length-1].sources=nodes.map(node=>({id:node.id,mode:'all'}));renderSteps();
    };section.append(branch);}
    const note=document.createElement('p');note.className='small-note';
    note.textContent=step.type!=='ai'?'No AI call. Joins selected outputs with blank lines.':index===0?'Uses all automation input.':'';
    section.append(note);el('steps').append(section);
  });
  if(!running)el('auto-status').textContent=`Ready · ${steps.length} steps`;
}

let hideOutput=false;
fetch('/api/settings',{cache:'no-store'}).then(r=>r.json()).then(data=>{hideOutput=data.hide_output;}).catch(()=>{});

function showOutput(text){
  output=text;
  if(!hideOutput)el('auto-output').textContent=text;
  el('auto-count').textContent=`${text.length.toLocaleString()} characters`;
  el('copy-auto').disabled=!text;
  if(!document.hidden&&document.hasFocus()&&el('auto-follow').checked)el('auto-output').scrollTop=el('auto-output').scrollHeight;
}

async function generate(prompt,model,signal,onText,context={}){
  const response=await fetch('/api/chat',{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,model,...context})});
  if(!response.ok)throw Error(`API returned HTTP ${response.status}`);
  const reader=response.body.getReader(),decoder=new TextDecoder();
  let buffer='',text='',completed=false;
  function consume(line){
    if(!line.trim())return;
    const event=JSON.parse(line);
    if(event.error)throw Error(event.error);
    if(event.text){text+=event.text;onText(text);}
    if(event.done)completed=true;
  }
  while(true){
    const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
    const lines=buffer.split('\n');buffer=lines.pop();lines.forEach(consume);
    if(done){consume(buffer);break;}
  }
  if(!completed||!text.trim())throw Error('No completed response received. Automation stopped.');
  return text;
}

async function executeSteps(plan,input,model,signal,onStep,onText,request=generate){
  const jobs=new Map(),quizzes=new Map(),previews=new Map();
  function preview(index,text){previews.set(index,text);onText([...previews].sort((a,b)=>a[0]-b[0]).map(([i,value])=>`Step ${i+1}\n${value}`).join('\n\n────────\n\n'));}
  for(let index=1;index<plan.length;index++){
    const step=plan[index];
    if(!step.sources.length)throw Error(`Step ${index+1}: select at least one source.`);
    if(step.type==='ai'&&step.sources.length!==1)throw Error(`Step ${index+1}: AI steps require one source. Use Combine for multiple sources.`);
    for(const source of step.sources)if(!plan.slice(0,index).some(node=>node.id===source.id))throw Error(`Step ${index+1}: source must be an earlier step.`);
  }
  async function quiz(source,result){
    if(!quizzes.has(source.id))quizzes.set(source.id,(async()=>{
      try{return processInput(result.text,false);}
      catch(error){
        const message=error.message;
        onStep(plan.findIndex(node=>node.id===source.id),false,'Quiz repair: '+message);
        const corrected=await request(result.prompt||'Return this content as a valid quiz.',model,signal,()=>{},
          {previous:result.text,followup:'The quiz parser displayed this exact error:\n\n'+message+'\n\nCorrect the quiz and return only the complete quiz block starting with ```quiz and ending with endquiz```. Preserve the questions and answers.'});
        try{return processInput(corrected,false);}
        catch(repairError){throw Error('Quiz still invalid after one follow-up:\n'+repairError.message);}
      }
    })());
    return quizzes.get(source.id);
  }
  for(const [index,step] of plan.entries()){
    const sources=plan.slice(0,index).filter(node=>step.sources.some(source=>source.id===node.id));
    jobs.set(step.id,(async()=>{
      try{
        const results=await Promise.all(sources.map(async node=>{
          const result=await jobs.get(node.id),source=step.sources.find(item=>item.id===node.id);
          return source.mode==='quiz'?quiz(source,result):selectContent(result.text,source.mode);
        }));
        if(signal.aborted)throw new DOMException('Stopped','AbortError');
        onStep(index,step.type!=='ai','Running');
        const selected=index===0?input:results.join('\n\n');
        const prompt=step.prefix+selected+step.suffix;
        if(step.type==='ai'&&!prompt.trim())throw Error(`Step ${index+1} has an empty prompt.`);
        const text=step.type==='ai'?await request(prompt,model,signal,text=>preview(index,text)):selected;
        onStep(index,step.type!=='ai','Complete');
        return {text,prompt:step.type==='ai'?prompt:''};
      }catch(error){onStep(index,false,'Failed: '+error.message);throw error;}
    })());
  }
  const results=await Promise.all([...jobs.values()]);
  const final=results[results.length-1].text;onText(final);return final;
}

function newNode(type,sourceId){return {id:nextId++,type,prefix:'',suffix:'',sources:[{id:sourceId,mode:'all'}]};}
function addNode(type){
  const node=newNode(type,steps[steps.length-2].id);
  steps.splice(steps.length-1,0,node);steps[steps.length-1].sources=[{id:node.id,mode:'all'}];renderSteps();
}
el('add-step').onclick=()=>{
  addNode('ai');
};
el('auto-input').after(createFileInput(el('auto-input'),()=>{},()=>running));
el('add-combine').onclick=()=>addNode('combine');
el('add-input').onclick=()=>{extraInputs.push('');renderInputs();};
el('set-input-slots').onclick=()=>{
  if(running||presetLoading||window.fileImportBusy)return;
  const count=Number(el('input-slots').value);
  if(!Number.isInteger(count)||count<1||count>1000){
    el('auto-error').hidden=false;el('auto-error').textContent='Enter a whole number from 1 to 1000.';return;
  }
  applyAutomation({model:el('auto-model').value,input:'',inputs:Array(count).fill(''),
    steps:steps.map(({id,type,prefix,suffix,sources})=>({id,type,prefix,suffix,sources}))});
  el('auto-status').textContent=`Ready · ${count} input slots`;
};
el('output-job').onchange=viewJob;
el('save-auto').onclick=()=>{
  const data={version:1,model:el('auto-model').value,input:el('auto-input').value,inputs:inputValues(),
    steps:steps.map(({id,type,prefix,suffix,sources})=>({id,type,prefix,suffix,sources}))};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='vtask-automation.json';
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
el('load-auto').onclick=()=>el('load-file').click();
let presetLoading=false;
function applyAutomation(data){
  steps=data.steps;nextId=steps.reduce((max,step)=>Math.max(max,step.id),0)+1;
  el('auto-model').value=data.model;el('auto-input').value=data.input;loadedAutomation=true;
  extraInputs=data.inputs.slice(1);jobs=[];controller=null;
  clearInterval(runtimeTimer);runtimeTimer=null;runtimeStart=0;
  el('auto-runtime').textContent=formatRuntime(0);
  el('load-file').value='';el('copy-auto').textContent='Copy output';el('stop-auto').hidden=true;
  renderInputs();el('output-job').replaceChildren(new Option('Input 1 · Ready','0'));
  // Recreate the first file importer to clear its prior conversion message.
  el('auto-input').nextElementSibling.replaceWith(createFileInput(el('auto-input'),()=>{},()=>running));
  showOutput('');el('auto-error').hidden=true;el('auto-error').textContent='';renderSteps();viewJob();
}
el('clean-auto').onclick=()=>{
  if(running||presetLoading||window.fileImportBusy)return;
  applyAutomation(validateAutomation({version:1,model:'inception/mercury-2.5',input:'',steps:[
    {id:1,type:'ai',prefix:'',suffix:'',sources:[]},
    {id:2,type:'final',prefix:'',suffix:'',sources:[{id:1,mode:'all'}]}
  ]}));
};
el('vtask-maker').onclick=async()=>{
  if(running||presetLoading||window.fileImportBusy)return;
  presetLoading=true;el('vtask-maker').disabled=true;
  try{
    const response=await fetch('/api/flows/vtask-maker',{cache:'no-store'});
    if(!response.ok)throw Error(`HTTP ${response.status}`);
    const data=validateAutomation(await response.json());
    if(running||window.fileImportBusy)return;
    applyAutomation(data);el('auto-status').textContent=`Vtask Maker loaded · ${steps.length} steps`;
  }catch(error){el('auto-error').hidden=false;el('auto-error').textContent='Could not load Vtask Maker: '+error.message;}
  finally{presetLoading=false;el('vtask-maker').disabled=running||Boolean(window.fileImportBusy);}
};
el('load-file').onchange=async()=>{
  const file=el('load-file').files[0];el('load-file').value='';
  if(!file||running)return;
  try{
    const data=validateAutomation(JSON.parse(await file.text()));
    if(running)return;
    applyAutomation(data);
    el('auto-status').textContent=`Loaded · ${steps.length} steps`;
  }catch(error){el('auto-error').hidden=false;el('auto-error').textContent='Could not load automation: '+error.message;}
};
el('paste-input').onclick=async()=>{
  try{el('auto-input').value=await navigator.clipboard.readText();}
  catch{el('auto-error').hidden=false;el('auto-error').textContent='Clipboard access unavailable. Paste into the input manually.';}
};
el('copy-auto').onclick=async()=>{
  try{await navigator.clipboard.writeText(output);el('copy-auto').textContent='Copied';setTimeout(()=>{el('copy-auto').textContent='Copy output';},2000);}
  catch{el('auto-error').hidden=false;el('auto-error').textContent='Copy blocked. Allow clipboard access and try again.';}
};
el('stop-auto').onclick=()=>controller?.abort();
el('run-auto').onclick=()=>runJobs();
el('retry-auto').onclick=()=>runJobs(Number(el('output-job').value));
async function runJobs(retryIndex=null){
  if(running)return;
  const retry=retryIndex!==null;
  if(retry&&(!jobs[retryIndex]?.status?.startsWith('Failed')))return;
  el('auto-error').hidden=true;
  const model=retry?jobs[retryIndex].model:el('auto-model').value.trim();
  if(!model){el('auto-error').hidden=false;el('auto-error').textContent='Enter a model ID.';return;}
  const plan=steps.map(step=>({...step,sources:step.sources.map(source=>({...source}))})),inputs=inputValues();
  controller=new AbortController();running=true;startRuntime();steps.forEach(step=>{step.status='Waiting';});renderSteps();
  for(const id of ['input-slots','set-input-slots','clean-auto','vtask-maker','add-step','add-combine','add-input','load-auto','run-auto','paste-input','auto-input','auto-model'])el(id).disabled=true;
  renderInputs();
  el('stop-auto').hidden=false;showOutput('');
  if(!retry){
    jobs=inputs.map(input=>({input,plan,model,output:'',status:'Waiting',states:[],error:''}));
    el('output-job').replaceChildren(...jobs.map((job,index)=>new Option(`Input ${index+1} · Waiting`,String(index))));
  }
  const indices=retry?[retryIndex]:jobs.map((job,index)=>index);
  el('retry-auto').disabled=true;
  let finished=0;
  try{
    await Promise.all(indices.map(async jobIndex=>{
      const job=jobs[jobIndex];
      const abort=()=>job.controller?.abort();controller.signal.addEventListener('abort',abort,{once:true});
      try{
        for(let attempt=1;attempt<=3;attempt++){
          const local=new AbortController();job.controller=local;
          job.output='';job.states=[];job.error='';job.status=attempt===1?'Running':`Retrying · ${attempt}/3`;updateJob(jobIndex);
          try{
            const result=await executeSteps(job.plan,job.input,job.model,local.signal,(index,last,state)=>{
              if(local.signal.aborted)return;
              job.states[index]=state;updateJob(jobIndex);
            },text=>{if(!local.signal.aborted){job.output=text;updateJob(jobIndex);}});
            job.output=result;job.status='Complete';break;
          }catch(error){
            if(error.name==='AbortError')throw error;
            job.error=error.message;
            if(attempt===3){job.status='Failed · 3 attempts';break;}
          }finally{job.controller=null;}
        }
      }catch(error){
        job.status=error.name==='AbortError'?'Stopped':'Failed';
        job.error=error.name==='AbortError'?'Stopped. Available output is preserved.':error.message;
      }finally{
        controller.signal.removeEventListener('abort',abort);finished++;updateJob(jobIndex);
        el('auto-status').textContent=`${finished} / ${indices.length} inputs finished`;
      }
    }));
    el('auto-status').textContent=`Finished · ${jobs.filter(job=>job.status==='Complete').length}/${jobs.length} successful`;
    try{
      const selected=jobs[Number(el('output-job').value)];
      if(!retry&&jobs.length===1&&selected.status==='Complete')await navigator.clipboard.writeText(selected.output);
    }catch{ /* Background tabs may block clipboard access; keep completion silent. */ }
  }catch(error){
    controller.abort();
    el('auto-status').textContent='Automation stopped';
    el('auto-error').hidden=false;el('auto-error').textContent=error.name==='AbortError'?'Stopped. Available output is preserved.':error.message;
  }finally{
    stopRuntime();
    const status=el('auto-status').textContent;
    running=false;renderSteps();el('auto-status').textContent=status;
    for(const id of ['input-slots','set-input-slots','clean-auto','vtask-maker','add-step','add-combine','add-input','load-auto','run-auto','paste-input','auto-input','auto-model'])el(id).disabled=false;
    renderInputs();viewJob();
    el('stop-auto').hidden=true;
  }
}
renderSteps();
fetch('/api/config').then(r=>r.json()).then(config=>{
  if(!running&&!loadedAutomation&&el('auto-model').value==='inception/mercury-2.5')el('auto-model').value=config.model||'inception/mercury-2.5';
  el('config-note').textContent=[config.route,config.warning].filter(Boolean).join(' · ');
  for(const model of config.models||[]){const option=document.createElement('option');option.value=model;el('auto-models').append(option);}
}).catch(()=>{el('config-note').textContent='Model discovery unavailable. Enter a model ID manually.';});