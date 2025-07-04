let chatData={};
// Front-end logic for the GroqChat web UI

let currentTab='';

// Show or hide the sidebar on small screens
function toggleSidebar(){
  const sb=document.getElementById('sidebar');
  const btn=document.getElementById('menuButton');
  sb.classList.toggle('show');
  btn.classList.toggle('open',sb.classList.contains('show'));
}


// Ensure the sidebar is hidden after selecting an item on mobile
function hideSidebarOnMobile(){
  if(window.innerWidth<=700){
    document.getElementById('sidebar').classList.remove('show');
  }
}

// Keep the newest messages visible when updating the chat
function scrollMessagesToEnd(){
  const msgDiv=document.getElementById('messages');
  msgDiv.scrollTop=msgDiv.scrollHeight;
}

// Very small Markdown renderer for messages
function md(t){
  let h=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  h=h.replace(/\*(.+?)\*/g,'<em>$1</em>');
  h=h.replace(/`([^`]+)`/g,'<code>$1</code>');
  return h.replace(/\n/g,'<br>');
}

// Update the system prompt textarea
function setSystem(text){
  document.getElementById('sysPrompt').value=text||'';
}

// Load the list of chats from the server
async function loadChats(){
  const res=await fetch('/api/chats');
  chatData=await res.json();
  const keys=Object.keys(chatData).filter(k=>k!=='archive').sort();
  if(chatData.archive) keys.push('archive');
  if(!currentTab) currentTab=keys[0]||'';
  renderTabs(keys);
  renderFiles();
}

// Render the directory tabs
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

// Display chat entries for the current tab
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

// Load an individual chat file
async function loadChat(name){
  const res=await fetch('/api/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  const data=await res.json();
  showMessages(data.chat,data.result);
  hideSidebarOnMobile();
}

// Send the updated system prompt to the server
async function updateSystem(){
  const text=document.getElementById('sysPrompt').value;
  const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'/system '+text})});
  const data=await res.json();
  showMessages(data.chat,data.result);
}

// Send the message typed by the user
async function sendMsg(){
  const t=document.getElementById('msg');
  const text=t.value;t.value='';
  if(!text.trim()) return;
  // Show the message immediately while waiting for the server
  const div=document.getElementById('messages');
  const p=document.createElement('div');
  p.className='message user';
  p.innerHTML=md(text);
  div.appendChild(p);
  scrollMessagesToEnd();

  const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
  const data=await res.json();
  showMessages(data.chat,data.result);
  hideSidebarOnMobile();
}

// Move a chat into the archive
async function archiveFile(name){
  await fetch('/api/archive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function restoreFile(name){
  // Move a chat out of the archive
  await fetch('/api/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function deleteFile(name){
  // Permanently delete an archived chat
  if(!confirm('Delete permanently?')) return;
  await fetch('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:name})});
  loadChats();
}

async function clearArchive(){
  // Remove all chats from the archive directory
  if(!confirm('Delete all archived chats?')) return;
  await fetch('/api/clear-archive',{method:'POST'});
  loadChats();
}

async function updateServer(){
  // Fetch the latest code and restart the server
  if(!confirm('Update and restart server?')) return;
  await fetch('/api/update',{method:'POST'});
  setTimeout(()=>location.reload(),2000);
}

async function updateApiKey(){
  // Send a new API key to the server
  const key=document.getElementById('apiKeyInput').value.trim();
  if(!key) return;
  await fetch('/api/api-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
  document.getElementById('apiKeyInput').value='';
  alert('API key updated');
}

async function newChat(){
  // Start a new chat session
  const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'/new'})});
  const data=await res.json();
  showMessages(data.chat,data.result);
  hideSidebarOnMobile();
}

function showMessages(chat,res){
  // Render the message history and any system responses
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
  // ensure the scroll position follows new messages
  scrollMessagesToEnd();
  loadChats();
}

loadChats();
// Load the most recent chat when the page first opens
fetch('/api/chat').then(r=>r.json()).then(d=>showMessages(d));
