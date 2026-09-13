const field=id=>document.getElementById(id);
function keyState(hasKey){
  field('api-key').required=!hasKey;
  field('key-status').textContent=hasKey?'A key is saved. Leave this field blank to keep it.':'No key saved. Enter an API key.';
}
fetch('/api/settings',{cache:'no-store'}).then(async response=>{
  if(!response.ok)throw Error('Could not load settings. Refresh to retry.');
  const data=await response.json();field('use-proxy').checked=data.use_proxy;field('endpoint').value=data.endpoint;field('stream-mode').checked=data.stream;field('hide-output').checked=data.hide_output;keyState(data.has_key);field('save-settings').disabled=false;
}).catch(error=>{field('save-status').textContent=error.message;});
field('settings-form').onsubmit=async event=>{
  event.preventDefault();field('save-settings').disabled=true;field('save-status').textContent='Saving…';
  try{
    const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endpoint:field('endpoint').value,api_key:field('api-key').value,stream:field('stream-mode').checked,hide_output:field('hide-output').checked,use_proxy:field('use-proxy').checked})});
    const data=await response.json();
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Could not save settings. Check the entered values.');
    field('use-proxy').checked=data.use_proxy;
    field('api-key').value='';field('endpoint').value=data.endpoint;field('stream-mode').checked=data.stream;field('hide-output').checked=data.hide_output;keyState(data.has_key);field('save-status').textContent=data.message;
  }catch(error){field('save-status').textContent=error.message;}
  finally{field('save-settings').disabled=false;}
};