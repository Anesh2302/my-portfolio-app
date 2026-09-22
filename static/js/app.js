// theme + reminder sound engine
const sel = document.getElementById('themeSel');
if (sel) sel.addEventListener('change', () => {
  document.documentElement.dataset.theme = sel.value;
  localStorage.setItem('theme', sel.value);
});
function showToast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  setTimeout(()=>t.style.display='none', 6000);
}
// Loud alarm with Web Audio (no file needed)
function playReminderSound(){
  try{
    const C = window.AudioContext || window.webkitAudioContext;
    const ctx = new C();
    [880, 660, 990, 880].forEach((f,i)=>{
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = f; o.type='sine';
      const t = ctx.currentTime + i*0.35;
      g.gain.setValueAtTime(0.001, t);
      g.gain.exponentialRampToValueAtTime(0.8, t+0.05);
      g.gain.exponentialRampToValueAtTime(0.001, t+0.3);
      o.start(t); o.stop(t+0.32);
    });
  }catch(e){ console.log('audio blocked', e); }
}
function enableNotifications(){
  if(!('Notification' in window)){ showToast('No notification support'); return; }
  Notification.requestPermission().then(p=>showToast('Notifications: '+p));
}
function getCsrf(){
  const m = document.cookie.match(/session=([^;]+)/); return null;
}
async function pollDue(){
  try{
    const r = await fetch('/api/reminders/due');
    if(!r.ok) return;
    const due = await r.json();
    for(const d of due){
      playReminderSound();
      showToast('⏰ REMINDER: '+d.title);
      if('Notification' in window && Notification.permission==='granted')
        new Notification('⏰ Reminder', {body: d.title + (d.notes?'\n'+d.notes:'')});
      else if('Notification' in window && Notification.permission!=='denied')
        Notification.requestPermission();
      await fetch('/api/reminders/'+d.id+'/ack', {method:'POST', headers:{'X-CSRFToken': csrfToken()}});
      setTimeout(playReminderSound, 1200); // double beep
    }
  }catch(e){}
}
function csrfToken(){
  const el = document.querySelector('input[name="csrf_token"]');
  return el ? el.value : '';
}
// attach CSRF to ack posts via header fallback: use form-less fetch with same-origin cookie + token
const _fetch = window.fetch;
window.fetch = function(url, opts={}){
  if(typeof url==='string' && url.includes('/ack') && (opts.method||'').toUpperCase()==='POST'){
    opts.headers = opts.headers||{};
    const t = csrfToken();
    // Flask-WTF also checks form; send as header + try header name it accepts
    if(t){ opts.headers['X-CSRFToken']=t; }
  }
  return _fetch(url, opts);
};
let _poller=null;
function startReminderPoller(on){ if(_poller) return; _poller=setInterval(pollDue, 10000); pollDue(); }
