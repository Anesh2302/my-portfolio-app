// ══ ANESHDEV — UI motion + reminder sound engine ══
(function(){
"use strict";
const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];

/* theme */
const sel=$('#themeSel');
function applyTheme(t){
  document.documentElement.dataset.theme=t;
  try{localStorage.setItem('theme',t);}catch(e){}
  const m=document.querySelector('meta[name="theme-color"]');
  const c=getComputedStyle(document.documentElement).getPropertyValue('--acc').trim();
  if(m&&c)m.setAttribute('content',c);
  if(sel)sel.value=t;
}
if(sel)sel.addEventListener('change',()=>applyTheme(sel.value));

/* navbar */
const nav=$('#navbar');
addEventListener('scroll',()=>nav&&nav.classList.toggle('scrolled',scrollY>24),{passive:true});
const tg=$('#navToggle'), links=$('#navLinks');
if(tg&&links)tg.addEventListener('click',()=>links.classList.toggle('open'));
$$('#navLinks a').forEach(a=>a.addEventListener('click',()=>links&&links.classList.remove('open')));

/* reveal on scroll */
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}}),{threshold:.12});
$$('.rv').forEach(el=>io.observe(el));

/* animated counters */
const cio=new IntersectionObserver(es=>es.forEach(e=>{
  if(!e.isIntersecting)return; cio.unobserve(e.target);
  const el=e.target, end=parseFloat(el.dataset.count||0), suf=el.dataset.suffix||'';
  const t0=performance.now(), dur=1400;
  (function tick(t){const p=Math.min((t-t0)/dur,1), v=Math.floor(end*(1-Math.pow(1-p,3)));
    el.textContent=v+suf; if(p<1)requestAnimationFrame(tick);})(t0);
}),{threshold:.4});
$$('[data-count]').forEach(el=>cio.observe(el));

/* 3D tilt on cards (desktop pointers only) */
if(matchMedia('(pointer:fine)').matches){
  $$('[data-tilt]').forEach(card=>{
    card.addEventListener('pointermove',e=>{
      const r=card.getBoundingClientRect();
      const x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
      card.style.setProperty('--ry',(x*7)+'deg');
      card.style.setProperty('--rx',(-y*7)+'deg');
    });
    card.addEventListener('pointerleave',()=>{card.style.setProperty('--rx','0');card.style.setProperty('--ry','0');});
  });
}

/* toast queue */
window.showToast=function(msg){
  const box=$('#toasts'); if(!box)return;
  const t=document.createElement('div'); t.className='toast'; t.textContent=msg;
  box.appendChild(t);
  setTimeout(()=>{t.classList.add('out'); setTimeout(()=>t.remove(),320);},5200);
  while(box.children.length>4)box.firstChild.remove();
};

/* confirm destructive posts */
$$('[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{
  if(!confirm(f.dataset.confirm))e.preventDefault();
}));

/* client-side project search */
const q=$('#projSearch');
if(q)q.addEventListener('input',()=>{
  const s=q.value.toLowerCase();
  $$('#projGrid .card').forEach(c=>{c.style.display=c.textContent.toLowerCase().includes(s)?'':'none';});
});

/* footer year */
const yr=$('#yr'); if(yr)yr.textContent=new Date().getFullYear();

/* ── reminder sound engine (Web Audio, no file) ── */
window.playReminderSound=function(){
  try{
    const C=window.AudioContext||window.webkitAudioContext;
    const ctx=new C();
    if(ctx.state==='suspended')ctx.resume();
    [880,660,990,1174].forEach((f,i)=>{
      const o=ctx.createOscillator(),g=ctx.createGain();
      o.connect(g);g.connect(ctx.destination);
      o.frequency.value=f;o.type='sine';
      const t=ctx.currentTime+i*.32;
      g.gain.setValueAtTime(.001,t);
      g.gain.exponentialRampToValueAtTime(.9,t+.05);
      g.gain.exponentialRampToValueAtTime(.001,t+.3);
      o.start(t);o.stop(t+.32);
    });
  }catch(e){}
};
window.enableNotifications=function(){
  if(!('Notification'in window)){showToast('Notifications not supported here');return;}
  Notification.requestPermission().then(p=>showToast('Notifications: '+p));
};
function csrfToken(){const el=$('input[name="csrf_token"]');return el?el.value:'';}
async function pollDue(){
  try{
    const r=await fetch('/api/reminders/due'); if(!r.ok)return;
    const due=await r.json();
    for(const d of due){
      playReminderSound(); showToast('Reminder: '+d.title);
      if('Notification'in window&&Notification.permission==='granted')
        new Notification('Reminder',{body:d.title+(d.notes?'\n'+d.notes:'')});
      else if('Notification'in window&&Notification.permission!=='denied')
        Notification.requestPermission();
      await fetch('/api/reminders/'+d.id+'/ack',{method:'POST',headers:{'X-CSRFToken':csrfToken()}});
      setTimeout(playReminderSound,1400);
    }
  }catch(e){}
}
let _p=null;
window.startReminderPoller=function(){if(_p)return;_p=setInterval(pollDue,10000);pollDue();};
})();
