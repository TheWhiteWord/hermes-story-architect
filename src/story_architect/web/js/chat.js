(function(){
  const H = {'X-Story-Architect':'1'};
  let slug = null, convId = null, streaming = false;
  function currentSlug(){ const m=(location.hash||'').match(/^#\/p\/(.+)$/); return m?decodeURIComponent(m[1]):null; }
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function ensureUI(){
    if(document.getElementById('sa-chat-panel')) return;
    const p=document.createElement('div'); p.id='sa-chat-panel';
    p.innerHTML='<div id="sa-chat-header"><strong>Chat</strong><button id="sa-chat-close">✕</button></div>'+
      '<div id="sa-chat-messages"></div>'+
      '<div id="sa-chat-input"><textarea id="sa-chat-text" rows="3"></textarea><div><button id="sa-chat-send">Send</button><button id="sa-chat-stop" style="display:none">Stop</button><button id="sa-chat-new">New</button></div></div>';
    document.body.appendChild(p);
    const t=document.createElement('button'); t.id='sa-chat-toggle'; t.textContent='Chat'; document.body.appendChild(t);
    t.onclick=toggle;
    document.getElementById('sa-chat-close').onclick=toggle;
    document.getElementById('sa-chat-send').onclick=send;
    document.getElementById('sa-chat-stop').onclick=stop;
    document.getElementById('sa-chat-new').onclick=newConv;
  }
  function toggle(){ ensureUI(); const p=document.getElementById('sa-chat-panel'); p.classList.toggle('open'); if(p.classList.contains('open')) init(); }
  async function init(){
    slug=currentSlug(); if(!slug) return;
    const r=await fetch('/api/projects/'+encodeURIComponent(slug)+'/conversations',{headers:H});
    const d=await r.json(); const convs=d.conversations||[];
    if(convs.length){ convId=convs[0].id; await loadConv(); } else { await createConv(); }
  }
  async function createConv(){
    const r=await fetch('/api/projects/'+encodeURIComponent(slug)+'/conversations',{method:'POST',headers:H});
    const d=await r.json(); convId=d.id; renderMsgs([]);
  }
  async function newConv(){ await createConv(); }
  async function loadConv(){
    const r=await fetch('/api/projects/'+encodeURIComponent(slug)+'/conversations/'+encodeURIComponent(convId),{headers:H});
    const d=await r.json(); renderMsgs(d.messages||[]);
  }
  function renderMsgs(msgs){
    const el=document.getElementById('sa-chat-messages'); el.innerHTML='';
    msgs.forEach(m=>{ const div=document.createElement('div'); div.id='sa-chat-msg'; div.className=m.role; div.innerHTML='<div>'+esc(m.text||'')+'</div>'; el.appendChild(div); });
    el.scrollTop=el.scrollHeight;
  }
  function appendText(text){ const el=document.getElementById('sa-chat-messages'); let last=el.lastElementChild; if(!last||!last.classList.contains('assistant')){ last=document.createElement('div'); last.className='assistant'; last.innerHTML='<div></div>'; el.appendChild(last);} last.querySelector('div').textContent += text; el.scrollTop=el.scrollHeight; }
  function appendTool(name){ const el=document.getElementById('sa-chat-messages'); const d=document.createElement('div'); d.className='sa-tool'; d.textContent='… '+name; el.appendChild(d); el.scrollTop=el.scrollHeight; }
  async function send(){
    const ta=document.getElementById('sa-chat-text'); const text=ta.value.trim(); if(!text||streaming) return;
    ta.value=''; streaming=true; document.getElementById('sa-chat-stop').style.display='inline';
    const el=document.getElementById('sa-chat-messages');
    const u=document.createElement('div'); u.className='user'; u.textContent=text; el.appendChild(u);
    if(!convId) await createConv();
    const res=await fetch('/api/projects/'+encodeURIComponent(slug)+'/conversations/'+encodeURIComponent(convId)+'/messages',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({text:text,context:{project:slug}})});
    const reader=res.body.getReader(); const dec=new TextDecoder(); let buf='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\n\n'); buf=parts.pop();
      for(const part of parts){
        const m=part.match(/^event: (\w+)\ndata: (.*)$/s); if(!m) continue;
        let payload={}; try{payload=JSON.parse(m[2]);}catch(e){}
        if(m[1]==='TextDelta') appendText(payload.text||'');
        else if(m[1]==='ToolStarted') appendTool(payload.name||'tool');
        else if(m[1]==='Error'){ const d=document.createElement('div'); d.textContent='Error: '+(payload.message||''); el.appendChild(d);}
      }
    }
    streaming=false; document.getElementById('sa-chat-stop').style.display='none';
  }
  async function stop(){ if(!convId) return; await fetch('/api/projects/'+encodeURIComponent(slug)+'/conversations/'+encodeURIComponent(convId)+'/cancel',{method:'POST',headers:H}); }
  window.DASH = window.DASH || {};
  const orig = window.DASH.askAgent;
  window.DASH.askAgent = function(text){
    ensureUI();
    if(!document.getElementById('sa-chat-panel').classList.contains('open')) toggle();
    if(text){ setTimeout(()=>{ document.getElementById('sa-chat-text').value=text; send(); }, 50); }
  };
  ensureUI();
})();
