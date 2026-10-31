"use strict";
const productType = document.getElementById('productType');
function showPrice(){const price=productType?.selectedOptions[0]?.dataset.price;const label=document.getElementById('productPrice');if(label)label.textContent=price?`${price} ₴`:'—';}
productType?.addEventListener('change',showPrice);showPrice();
const savedAddress=document.getElementById('savedAddress');
function chooseAddress(){const fields=document.getElementById('newAddressFields');if(!fields)return;const saved=Boolean(savedAddress?.value);fields.hidden=saved;fields.querySelectorAll('input').forEach(input=>{input.disabled=saved;if(input.type!=='checkbox')input.required=!saved;});}
savedAddress?.addEventListener('change',chooseAddress);chooseAddress();
document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{const source=document.getElementById(button.dataset.copy);if(!source)return;try{await navigator.clipboard.writeText(source.textContent.trim());button.textContent=tr('address.copied');}catch{const range=document.createRange();range.selectNodeContents(source);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);button.textContent=tr('address.copy_failed');}}));
const onboarding=document.getElementById('onboarding');
if(onboarding){
 const card=onboarding.querySelector('.onboarding-card'),ring=document.getElementById('spotlightRing'),next=document.getElementById('onboardingNext'),prev=document.getElementById('onboardingPrev');
 const page=onboarding.dataset.page;
 const sequences={profile:[['#profileName','tutorial.name'],['#profilePhone','tutorial.phone'],['#ua-addresses','tutorial.address'],['#ukAddresses','tutorial.uk'],['#profileTelegram','tutorial.telegram'],['#profileSave','tutorial.save']],new_order:[['#productType','tutorial.product'],['#orderAddress','tutorial.address'],['#orderProof','tutorial.proof'],['#submitParcel','tutorial.new']],dashboard:[['[data-new-parcel]','tutorial.new'],['.invoice-stack, .order-grid, .empty-state','tutorial.payment']]};
 let steps=[],current=0,previousFocus=null,frame=0;
 function position(){if(onboarding.hidden)return;const node=document.querySelector(steps[current][0]);if(!node)return;const r=node.getBoundingClientRect();Object.assign(ring.style,{top:`${Math.max(4,r.top-6)}px`,left:`${Math.max(4,r.left-6)}px`,width:`${Math.min(innerWidth-8,r.width+12)}px`,height:`${Math.min(innerHeight-card.offsetHeight-60,r.height+12)}px`});}
 function paint(){document.getElementById('onboardingCount').textContent=`${current+1} / ${steps.length}`;document.getElementById('onboardingText').textContent=tr(steps[current][1]);prev.disabled=current===0;next.textContent=tr(current===steps.length-1?'tutorial.done':'Далее ↗');const node=document.querySelector(steps[current][0]);if(node){const y=scrollY+node.getBoundingClientRect().top-90;window.scrollTo({top:Math.max(0,y),behavior:'instant'});}position();}
 function open(){steps=(sequences[page]||sequences.dashboard).filter(step=>document.querySelector(step[0]));if(!steps.length)return;previousFocus=document.activeElement;current=0;onboarding.hidden=false;document.body.classList.add('tutorial-active');paint();document.getElementById('onboardingClose').focus();}
 async function close(){onboarding.hidden=true;document.body.classList.remove('tutorial-active');previousFocus?.focus({preventScroll:true});try{await fetch('/onboarding/complete',{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},credentials:'same-origin'});}catch{/* The tour can be replayed; no form data is lost. */}}
 next.addEventListener('click',()=>{if(current===steps.length-1)close();else{current++;paint();}});prev.addEventListener('click',()=>{current=Math.max(0,current-1);paint();});
 ['onboardingClose','onboardingSkip'].forEach(id=>document.getElementById(id).addEventListener('click',close));document.querySelectorAll('[data-onboarding]').forEach(button=>button.addEventListener('click',open));
 onboarding.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();close();}if(event.key==='Tab'){const buttons=[...card.querySelectorAll('button:not([disabled])')];const first=buttons[0],last=buttons[buttons.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}});
 for(const type of ['resize','scroll'])window.addEventListener(type,()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(position);},{passive:true});
 if(onboarding.dataset.auto==='1')requestAnimationFrame(open);
}
