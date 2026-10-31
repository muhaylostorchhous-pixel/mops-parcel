"use strict";
window.addEventListener('DOMContentLoaded',()=>{
 const grid=document.getElementById('feedGrid'),button=document.getElementById('feedRefresh'),status=document.getElementById('feedStatus');
 if(!grid)return;
 const make=(tag,cls,value)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(value)el.textContent=value;return el;};
 const link=(url,label,cls)=>{const a=make('a',cls,label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;};
 function card(row){const item=make('article','feed-card'),media=make('div','feed-image'),body=make('div','feed-body');
  if(row.image){const img=make('img');img.src=row.image;img.alt=row.title||tr('feed.listing');img.loading='lazy';img.referrerPolicy='no-referrer';img.addEventListener('error',()=>media.replaceChildren(make('span','',tr('feed.no_photo'))),{once:true});media.append(img);}else media.append(make('span','',tr('feed.no_photo')));
  body.append(make('small','','MOPS FINDS'),make('h2','',row.title||tr('feed.listing')),make('strong','feed-price',row.price||tr('feed.price_unknown')),make('p','',row.description));const links=make('div','feed-links');
  if(row.url)links.append(link(row.url,tr('feed.open')+' ↗','button primary small-btn'));if(row.source)links.append(link(row.source,tr('feed.source')+' ↗','text-button'));body.append(links);item.append(media,body);return item;
 }
 let busy=false;
 async function refresh(){if(busy||document.hidden)return;busy=true;button.disabled=true;const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),35000);
  try{const response=await fetch('/parser/data'+location.search,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(!response.ok||response.redirected)throw new Error('unavailable');const data=await response.json();if(!Array.isArray(data.cards))throw new Error('invalid');grid.replaceChildren(...data.cards.map(card));document.getElementById('feedEmpty').hidden=data.cards.length>0;document.getElementById('feedNext').hidden=!data.has_more;status.textContent=data.status||tr('feed.updated');const admin=document.getElementById('feedAdminError');if(admin)admin.textContent=data.admin_error||'';
  }catch{status.textContent=tr('feed.unavailable');}finally{clearTimeout(timer);busy=false;button.disabled=false;}}
 button.addEventListener('click',refresh);setInterval(refresh,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
 document.querySelectorAll('.feed-image img').forEach(img=>img.addEventListener('error',()=>img.parentElement.replaceChildren(make('span','',tr('feed.no_photo'))),{once:true}));
});
