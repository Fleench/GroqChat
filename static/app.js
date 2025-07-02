let chatData={};
let currentTab='';

function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('show');
}

function toggleCommandBar(){
  const bar=document.getElementById('commandBar');
  const btn=document.getElementById('cmdToggle');
  if(bar.style.display==='block'){
    bar.style.display='none';
    btn.textContent='Commands';
  }else{
    bar.style.display='block';
    btn.textContent='Close';
  }
}

function hideSidebarOnMobile(){
  if(window.innerWidth<=700){
    document.getElementById('sidebar').classList.remove('show');
  }
}

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
  const keys=Object.keys(chatData).filter(k=>k!=='archive').sort();
  if(chatData.archive) keys.push('archive');
  if(!currentTab) currentTab=keys[0]||'';
  renderTabs(keys);
  renderFiles();
}

function renderTabs(order){
  const tabs=document.getElementById('tabButtons');
  tabs.innerHTML='';
  (order||Object.keys(chatData)).forEach(dir=>{
    const b=document.createElement('div');
    b.className='tab'+(dir===currentTab?' active':'');
    b.textContent=dir;
    b.onclick=()=>{currentTab=dir;renderTabs(order);renderFiles();};
    tabs.appendChild(b);
  });
}

function renderFiles(){
  const list=document.getElementById('fileList');
  list.innerHTML='';
  document.getElementById('clearArchiveBtn').style.display=currentTab==='archive'?'':'none';
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
    const btn=document.createElement('button');
    btn.className='chat-btn';
    if(currentTab==='archive'){
      btn.textContent='Restore';
      btn.onclick=e=>{e.stopPropagation();restoreFile(item.file);};
      const del=document.createElement('button');
      del.className='chat-btn';
      del.textContent='Delete';
      del.onclick=e=>{e.stopPropagation();deleteFile(item.file);};
      div.appendChild(btn);
      div.appendChild(del);
    }else{
      btn.textContent='Archive';
      btn.onclick=e=>{e.stopPropagation();archiveFile(item.file);};
      div.appendChild(btn);
    }
    list.appendChild(div);
  });
}

async function loadChat(name){
  const res=await fetch('/api/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  const data=await res.json();
  showMessages(data.chat,data.result);
  hideSidebarOnMobile();
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
  hideSidebarOnMobile();
}

async function archiveFile(name){
  await fetch('/api/archive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function restoreFile(name){
  await fetch('/api/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function deleteFile(name){
  if(!confirm('Delete permanently?')) return;
  await fetch('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function clearArchive(){
  if(!confirm('Delete all archived chats?')) return;
  await fetch('/api/clear-archive',{method:'POST'});
  loadChats();
}

async function updateServer(){
  if(!confirm('Update and restart server?')) return;
  await fetch('/api/update',{method:'POST'});
  setTimeout(()=>location.reload(),2000);
}

async function updateApiKey(){
  const key=document.getElementById('apiKeyInput').value.trim();
  if(!key) return;
  await fetch('/api/api-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
  document.getElementById('apiKeyInput').value='';
  alert('API key updated');
}

async function newChat(){
  const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'/new'})});
  const data=await res.json();
  showMessages(data.chat,data.result);
  hideSidebarOnMobile();
}

function showMessages(chat,res){
  const msgs=chat.messages;
  document.getElementById('chatName').textContent=chat.name||'';
  document.getElementById('chatPath').textContent=chat.file||'';
  const div=document.getElementById('messages');
  div.innerHTML='';
  document.getElementById('summaryText').textContent=chat.summary||'';
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
      document.getElementById('summaryText').textContent=res.summary;
    }
  }
  if(chat.summary){
    document.getElementById('summaryText').textContent=chat.summary;
  }
  loadChats();
}

loadChats();
fetch('/api/chat').then(r=>r.json()).then(d=>showMessages(d));
