document.addEventListener('DOMContentLoaded',()=>{
 const form=document.getElementById('chatForm'),list=document.getElementById('messageList');if(!form||!list)return;
 const body=document.getElementById('chatBody'),button=document.getElementById('sendMessage'),status=document.getElementById('chatStatus');
 const strings=JSON.parse(document.getElementById('translations').textContent),tr=k=>strings[k]||k;
 let after=0,polling=false,sending=false;
 async function poll(){
  if(polling||document.hidden)return;polling=true;
  try{
   const r=await fetch(list.dataset.source+'&after='+after,{headers:{'Accept':'application/json'},signal:AbortSignal.timeout(15000)});
   if(!r.ok)throw Error();const data=await r.json();const nearBottom=list.scrollHeight-list.scrollTop-list.clientHeight<90;
   for(const m of data.messages){
    if(m.id<=after)continue;document.getElementById('emptyChat')?.remove();
    const bubble=document.createElement('article');bubble.className='chat-bubble'+(m.mine?' mine':'');
    const text=document.createElement('p');text.textContent=m.body;
    const time=document.createElement('time');time.dateTime=m.created;time.textContent=new Date(m.created).toLocaleString(document.documentElement.lang,{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
    bubble.append(text,time);list.append(bubble);after=m.id;
   }
   if(nearBottom)list.scrollTop=list.scrollHeight;status.textContent=tr('svc.connected');
   if(data.has_more)setTimeout(poll,0);
  }catch(e){status.textContent=tr('svc.chat_error');}finally{polling=false;}
 }
 // Preserve existing query parameters for admin and client URLs.
 list.dataset.source += list.dataset.source.includes('?')?'':'?view=chat';
 form.addEventListener('submit',async e=>{
  e.preventDefault();if(sending||!body.value.trim())return;sending=true;button.disabled=true;
  const draft=body.value;button.textContent=tr('svc.sending');
  try{
   const r=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'Accept':'application/json'},signal:AbortSignal.timeout(20000)});
   if(!r.ok)throw Error();const result=await r.json();form.elements.nonce.value=result.nonce;
   if(body.value===draft)body.value='';await poll();list.scrollTop=list.scrollHeight;
  }catch(e){status.textContent=tr('svc.chat_error');}finally{sending=false;button.disabled=false;button.textContent=tr('svc.send');}
 });
 body.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();form.requestSubmit();}});
 setInterval(poll,4000);document.addEventListener('visibilitychange',poll);poll();
});
