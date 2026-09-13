// Shared file import: conversion finishes before the input can be run or edited.
window.fileImportBusy=false;
window.createFileInput=function(target,onText,isBusy){
  const row=document.createElement('div');
  const picker=document.createElement('input');picker.type='file';picker.hidden=true;
  const button=document.createElement('button');button.type='button';button.textContent='Import file';
  button.disabled=isBusy();
  const status=document.createElement('p');status.className='small-note';status.setAttribute('role','status');
  status.textContent='Import a document as editable text · up to 25 MB. Appends to existing input.';
  button.onclick=()=>{if(!isBusy()&&!window.fileImportBusy)picker.click();};
  picker.onchange=async()=>{
    const file=picker.files[0];picker.value='';
    if(!file||isBusy()||window.fileImportBusy)return;
    if(file.size>25*1024*1024){status.textContent='Files must be 25 MB or smaller.';return;}
    window.fileImportBusy=true;
    const controls=[...document.querySelectorAll('button,input,textarea,select')].map(control=>[control,control.disabled]);
    controls.forEach(([control])=>{control.disabled=true;});
    status.textContent=`Converting ${file.name}…`;
    try{
      const data=new FormData();data.append('file',file);
      const response=await fetch('/api/convert',{method:'POST',body:data});
      const result=await response.json();
      if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'File conversion failed.');
      const text=target.value?target.value+'\n\n'+result.text:result.text;
      if(text.length>1000000)throw Error('Combined input exceeds 1,000,000 characters. Clear or shorten the input first.');
      target.value=text;onText(text);target.dispatchEvent(new Event('input'));
      status.textContent=`Imported ${file.name} · review the text before running.`;
    }catch(error){status.textContent=error.message||'File conversion failed. Try again.';}
    finally{
      window.fileImportBusy=false;
      controls.forEach(([control,disabled])=>{control.disabled=disabled;});
    }
  };
  row.append(button,picker,status);return row;
};