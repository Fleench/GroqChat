  let chatData={};
  let currentTab='';
  function md(t){
    let h=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    h=h.replace(/\*(.+?)\*/g,'<em>$1</em>');
    h=h.replace(/`([^`]+)`/g,'<code>$1</code>');
    return h.replace(/\n/g,'<br>');
  }
  function setSystem(text){
    document.getElementById('sysPrompt').value=text||'';
  }
  async function loadChats(){
    const res=await fetch('/api/chats');
    chatData=await res.json();
    const keys=Object.keys(chatData);
    if(!currentTab) currentTab=keys[0]||'';
    renderTabs();
    renderFiles();
  }
  function renderTabs(){
    const tabs=document.getElementById('tabButtons');
    tabs.innerHTML='';
    for(const dir in chatData){
      const b=document.createElement('div');
      b.className='tab'+(dir===currentTab?' active':'');
      b.textContent=dir;
      b.onclick=()=>{currentTab=dir;renderTabs();renderFiles();};
      tabs.appendChild(b);
    }
  }
  function renderFiles(){
    const list=document.getElementById('fileList');
    list.innerHTML='';
    if(!currentTab) return;
    chatData[currentTab].forEach(item=>{
      const div=document.createElement('div');
      div.className='chat-entry';
      div.onclick=()=>loadChat(item.file);
      const n=document.createElement('div');
      n.className='chat-name';
      n.textContent=item.name;
      const f=document.createElement('div');
      f.className='chat-file';
      f.textContent=item.file;
      div.appendChild(n);
      div.appendChild(f);
      list.appendChild(div);
    });
  }
  async function loadChat(name){
    const res=await fetch('/api/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
    const data=await res.json();
    showMessages(data.chat,data.result);
  }
  async function updateSystem(){
    const text=document.getElementById('sysPrompt').value;
    const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'/system '+text})});
    const data=await res.json();
    showMessages(data.chat,data.result);
  }
  async function sendMsg(){
    const t=document.getElementById('msg');
    const text=t.value;t.value='';
    const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
    const data=await res.json();
    showMessages(data.chat,data.result);
  }
  function showMessages(chat,res){
    const msgs=chat.messages;
    document.getElementById('chatName').textContent=chat.name||'';
    document.getElementById('chatPath').textContent=chat.file||'';
    const div=document.getElementById('messages');
    div.innerHTML='';
    if(msgs[0]&&msgs[0].role==='system') setSystem(msgs[0].content);
    msgs.slice(1).forEach(m=>{
      const p=document.createElement('div');
      p.className='message '+(m.role==='user'?'user':'assistant');
      p.innerHTML=md(m.content);
      div.appendChild(p);
    });
    if(res){
      if(res.system){
        const p=document.createElement('div');
        p.className='message system';
        p.innerHTML=md(res.system);
        div.appendChild(p);
      }
      if(res.error){
        const p=document.createElement('div');
        p.className='message error';
        p.textContent=res.error;
        div.appendChild(p);
      }
      if(res.assistant){
        const p=document.createElement('div');
        p.className='message assistant';
        p.innerHTML=md(res.assistant);
        div.appendChild(p);
      }
      if(res.prompts){
        const p=document.createElement('div');
        p.className='message system';
        p.textContent='Prompts: '+res.prompts.join(', ');
        div.appendChild(p);
      }
      if(res.results){
        const p=document.createElement('div');
        p.className='message system';
        p.innerHTML=md(res.results.join('\n'));
        div.appendChild(p);
      }
      if(res.models){
        const p=document.createElement('div');
        p.className='message system';
        p.textContent='Models: '+res.models.join(', ');
        div.appendChild(p);
      }
      if(res.file){
        const p=document.createElement('div');
        p.className='message system';
        p.textContent=`File: ${res.file} | Model: ${res.model} | Messages: ${res.messages}`;
        div.appendChild(p);
      }
      if(res.summary){
        document.getElementById('summaryBox').textContent=res.summary;
      }
    }
    loadChats();
  }
  loadChats();
  fetch('/api/chat').then(r=>r.json()).then(d=>showMessages(d));

