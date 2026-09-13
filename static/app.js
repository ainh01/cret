const $=id=>document.getElementById(id);let out='',busy=false,followUsed=false,matchIndex=-1,matchPositions=[];const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(t){$('toast').textContent=t;$('toast').hidden=false;setTimeout(()=>{$('toast').hidden=true},2200)}function render(){if(hideOutput){$('output-count').textContent=`${out.trim()?out.trim().split(/\s+/).length:0} words · ${out.length} characters`;return}let q=$('search').value;let html=$('raw').classList.contains('selected')?`<pre>${esc(out)}</pre>`:window.marked?DOMPurify.sanitize(marked.parse(out||'')):esc(out);if(q&&out){let re=new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');html=html.replace(re,(m)=>`<mark>${m}</mark>`)}$('output').innerHTML=html;$('output').classList.toggle('raw',$('raw').classList.contains('selected'));$('output-count').textContent=`${out.trim()?out.trim().split(/\s+/).length:0} words · ${out.length} characters`;let marks=[...$('output').querySelectorAll('mark')];$('matches').textContent=`${marks.length} match${marks.length===1?'':'es'}`}
let originalPrompt='', originalResponse='', originalModel='', controller;
let hideOutput=false;
fetch('/api/settings',{cache:'no-store'}).then(r=>r.json()).then(data=>{hideOutput=Boolean(data.hide_output);}).catch(()=>{});
function resetFollowup(){
	followUsed=false; originalPrompt=''; originalResponse=''; originalModel='';
	$('followup').value=''; $('followup').disabled=true; $('follow').disabled=true;
	$('follow-badge').textContent='1 FOLLOW-UP';
}
function setBusy(v){
	busy=v; $('generate').disabled=v; $('clear').disabled=v; $('stop').hidden=!v;
	$('prc').disabled=v;
	$('prompt').disabled=v; $('model').disabled=v; $('paste').disabled=v;
	$('followup').disabled=$('follow').disabled=v||followUsed||!originalResponse;
	$('status').textContent=v?'Writing response…':'Ready when you are';
}
const promptFileInput=createFileInput($('prompt'),()=>{},()=>busy);
$('prompt').after(promptFileInput);
async function run(follow=false){
	if(window.fileImportBusy)return;
	if(busy|| (follow&&followUsed))return;
	const prompt=(follow?$('followup'):$('prompt')).value.trim();
	if(!prompt)return toast('Add a prompt first.');
	if(!follow&&!$('model').value.trim())return toast('Choose a model.');
	if(follow&&!originalResponse)return toast('Complete the first prompt before following up.');
	if(!follow){resetFollowup();originalPrompt=prompt;originalModel=$('model').value.trim();}
	const previousOutput=out;
	out=''; render(); $('empty').hidden=true; $('output').hidden=false; $('error').hidden=true;
	controller=new AbortController(); setBusy(true);
	let completed=false;
	try{
		const r=await fetch('/api/chat',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},
			body:JSON.stringify({prompt:originalPrompt,model:originalModel,previous:follow?originalResponse:null,followup:follow?prompt:null})});
		if(!r.ok)throw Error('HTTP '+r.status);
		const reader=r.body.getReader(),dec=new TextDecoder(); let buffer='';
		function consume(line){
			if(!line.trim())return;
			const e=JSON.parse(line);
			if(e.error)throw Error(e.error);
			if(e.done)completed=true;
			if(e.text){out+=e.text;render();if(!document.hidden&&document.hasFocus()&&$('auto-scroll').checked)$('output-scroll').scrollTop=$('output-scroll').scrollHeight;}
		}
		while(true){
			const {value,done}=await reader.read();
			buffer+=dec.decode(value,{stream:!done});
			const lines=buffer.split('\n');buffer=lines.pop();lines.forEach(consume);
			if(done){consume(buffer);break;}
		}
		if(!completed||!out.trim())throw Error('No completed response received. Please retry.');
		if(follow){followUsed=true;$('followup').value='';$('follow-badge').textContent='USED';}
		else{originalResponse=out;}
		$('txt-status').textContent='Output ready';
		return out;
	}catch(e){
		if(follow&&!out)out=previousOutput;
		$('error').textContent=e.name==='AbortError'?'Stopped. Partial output is preserved.':e.message;
		$('error').hidden=false;
	}finally{
		render();$('copy-fixed').disabled=$('copy').disabled=$('copy-txt').disabled=!out;setBusy(false);
	}
}
$('generate').onclick=()=>run();$('follow').onclick=()=>run(true);$('clear').onclick=()=>{out='';$('prompt').value='';$('followup').value='';$('output').hidden=true;$('empty').hidden=false;$('copy').disabled=$('copy-txt').disabled=true;$('status').textContent='Ready when you are';render()};$('prompt').oninput=()=> $('prompt-count').textContent=`${$('prompt').value.length} characters`;$('prompt').onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')run()};$('paste').onclick=async()=>{try{$('prompt').value=await navigator.clipboard.readText();$('prompt').dispatchEvent(new Event('input'))}catch{toast('Clipboard access unavailable.')}};$('copy').onclick=()=>navigator.clipboard.writeText(out).then(()=>toast('Output copied'));$('copy-txt').onclick=()=>{let m=out.match(/```txt\s*\n?([\s\S]*?)```/i);navigator.clipboard.writeText(m?m[1].trim():out).then(()=>toast(m?'TXT content copied':'No txt block found; output copied'))};$('top').onclick=()=> $('output-scroll').scrollTo({top:0,behavior:'smooth'});$('bottom').onclick=()=> $('output-scroll').scrollTo({top:$('output-scroll').scrollHeight,behavior:'smooth'});$('search').oninput=render;$('raw').onclick=()=>{ $('raw').classList.add('selected');$('rendered').classList.remove('selected');render()};$('rendered').onclick=()=>{$('rendered').classList.add('selected');$('raw').classList.remove('selected');render()};$('collapse').onclick=()=>{let c=$('composer');c.classList.toggle('collapsed');let v=!c.classList.contains('collapsed');$('collapse').textContent=v?'Hide prompt −':'Show prompt +';$('collapse').setAttribute('aria-expanded',v)};
$('clear').addEventListener('click',()=>{resetFollowup();$('prompt').dispatchEvent(new Event('input'));$('error').hidden=true;$('txt-status').textContent='Waiting for output';});
$('stop').onclick=()=>controller?.abort();
function extractLastTxt(text){
	const start=text.toLowerCase().lastIndexOf('```txt');
	const end=text.lastIndexOf('```');
	if(start<0||end<start+6)return null;
	return text.slice(start+6,end).trim();
}
$('copy-txt').onclick=async()=>{
	const content=extractLastTxt(out);
	try{
		await navigator.clipboard.writeText(content===null?out:content);
		toast(content===null?'No complete txt block found; output copied':'TXT content copied');
	}catch{toast('Clipboard access unavailable. Allow clipboard access and try again.');}
};
function fixMaterialEnding(text){
	// Keep an already-correct ending (including trailing whitespace) unchanged.
	if(/endmaterial```[\t \r\n]*$/.test(text))return text;
	// Case 1: join the marker and the final fence across a line break.
	if(/endmaterial[\t ]*\r?\n[\t ]*```([\t \r\n]*)$/.test(text)){
		return text.replace(/endmaterial[\t ]*\r?\n[\t ]*```([\t \r\n]*)$/, 'endmaterial```$1');
	}
	// Case 2: insert the missing marker before a standalone final fence.
	return text.replace(/(^|\n)([\t ]*)```([\t \r\n]*)$/, '$1$2endmaterial```$3');
}
$('copy-fixed').onclick=async()=>{
	try{await navigator.clipboard.writeText(fixMaterialEnding(out));toast('Fixed material copied');}
	catch{toast('Clipboard access unavailable. Allow clipboard access and try again.');}
};
$('clear').addEventListener('click',()=>{$('copy-fixed').disabled=true;});
let prcPending=false;
$('prc').onclick=async()=>{
	if(busy||prcPending)return;
	prcPending=true;setBusy(true);$('stop').hidden=true;
	try{
		let prompt;
		try{prompt=await navigator.clipboard.readText();}
		catch{toast('Clipboard access unavailable. Allow clipboard access, or paste manually.');return;}
		if(!prompt.trim()){toast('Clipboard is empty. Copy a prompt first.');return;}
		$('prompt').value=prompt;$('prompt').dispatchEvent(new Event('input'));
		setBusy(false);
		const result=await run();
		if(typeof result!=='string')return;
		try{await navigator.clipboard.writeText(result);toast('PRC complete · Output copied');}
		catch{
			$('status').textContent='Output ready · Click Copy output to copy';
			toast('Automatic copy blocked. Click Copy output.');
		}
	}finally{prcPending=false;if(busy)setBusy(false);}
};
fetch('/api/config').then(r=>r.json()).then(c=>{ $('route').textContent=c.route;$('config-note').textContent=c.warning||'';$('model').value=c.model||'inception/mercury-2.5';(c.models||[]).forEach(m=>{let o=document.createElement('option');o.value=m;$('models').append(o)})}).catch(()=>$('route').textContent='Offline');
