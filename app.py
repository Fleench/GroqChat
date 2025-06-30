from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json

import cli

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cli.ensure_directories()
client = cli.setup_client()
MODEL = cli.MODEL
chat_data, active_filename = cli.get_new_session_state()
messages = chat_data["messages"]
cli.save_chat_to_file(active_filename, chat_data)


def summarize(messages):
    recent = messages[-cli.SUMMARY_HISTORY_LIMIT:]
    convo = "\n".join(
        f"{m['role']}: {m['content']}" for m in recent if m['role'] != 'system'
    )
    summary_messages = [
        {"role": "system", "content": cli.SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Summarize the following conversation:\n{convo}"},
    ]
    completion = client.chat.completions.create(
        messages=summary_messages,
        model=MODEL,
        temperature=0.7,
        top_p=1,
        max_tokens=cli.SUMMARY_MAX_TOKENS,
    )
    return completion.choices[0].message.content


def search_messages(messages, term):
    term = term.lower()
    results = []
    for i, m in enumerate(messages[1:], start=1):
        if term in m["content"].lower():
            results.append(f"{i}: {m['role']} - {m['content']}")
    return results


def list_chats():
    data = {}
    if not os.path.exists(cli.CHAT_HISTORY_DIR):
        return data
    for d in os.listdir(cli.CHAT_HISTORY_DIR):
        path = os.path.join(cli.CHAT_HISTORY_DIR, d)
        if os.path.isdir(path):
            chats = []
            for fname in os.listdir(path):
                if not fname.endswith('.chat'):
                    continue
                fpath = os.path.join(path, fname)
                try:
                    with open(fpath, 'r') as f:
                        j = json.load(f)
                    name = j.get('name', os.path.splitext(fname)[0]) if isinstance(j, dict) else os.path.splitext(fname)[0]
                except Exception:
                    name = os.path.splitext(fname)[0]
                chats.append({'file': fname, 'name': name})
            data[d] = chats
    return data


def handle_command(user_input):
    global chat_data, messages, active_filename, MODEL
    parts = user_input.split()
    cmd = parts[0]
    if cmd == '/new':
        chat_data, active_filename = cli.get_new_session_state()
        messages = chat_data['messages']
        cli.save_chat_to_file(active_filename, chat_data)
        return {"system": f"New chat started: {chat_data['name']}"}
    elif cmd == '/save':
        if len(parts) < 2:
            return {"error": "Usage: /save <name>"}
        name = parts[1]
        if not name.endswith('.chat'):
            name += '.chat'
        full = os.path.join('userchat', name)
        success, path = cli.save_chat_to_file(full, chat_data)
        if success:
            active_filename = full
            return {"system": f"Chat saved to {path}"}
        return {"error": "Could not save chat"}
    elif cmd == '/load':
        if len(parts) < 2:
            return {"error": "Usage: /load <name>"}
        name = parts[1]
        if not name.endswith('.chat'):
            name += '.chat'
        loaded, loaded_path = cli.load_chat_from_file(name)
        if loaded:
            chat_data = loaded
            messages = chat_data['messages']
            active_filename = loaded_path or name
            return {"system": f"Chat '{chat_data['name']}' loaded"}
        return {"error": f"File {name} not found"}
    elif cmd == '/chats':
        return {"chats": list_chats()}
    elif cmd == '/system':
        if len(parts) < 2:
            return {"error": "Usage: /system <prompt>"}
        new_prompt = " ".join(parts[1:])
        chat_data['messages'][0] = {"role": "system", "content": new_prompt}
        cli.save_chat_to_file(active_filename, chat_data)
        return {"system": "System prompt updated"}
    elif cmd == '/prompt':
        if len(parts) < 2:
            return {"error": "Usage: /prompt <new|use|list|sys>"}
        action = parts[1]
        if action == 'new':
            if len(parts) < 4:
                return {"error": "Usage: /prompt new <name> <text>"}
            name = parts[2]
            text = " ".join(parts[3:])
            success, path = cli.save_prompt(name, text)
            if success:
                return {"system": f"Prompt '{name}' saved to {path}"}
            return {"error": f"Could not save prompt {name}"}
        elif action == 'list':
            names = cli.list_prompts()
            return {"prompts": names}
        elif action == 'use':
            if len(parts) < 3:
                return {"error": "Usage: /prompt use <name>"}
            name = parts[2]
            text = cli.load_prompt(name)
            if text is None:
                return {"error": f"Prompt {name} not found"}
            messages.append({"role": "user", "content": text})
            cli.save_chat_to_file(active_filename, chat_data)
            completion = client.chat.completions.create(
                messages=messages[-cli.HISTORY_LIMIT:],
                model=MODEL,
                temperature=0.7,
                top_p=1,
            )
            assistant_response = completion.choices[0].message.content
            messages.append({"role": "assistant", "content": assistant_response})
            cli.save_chat_to_file(active_filename, chat_data)
            return {"assistant": assistant_response}
        elif action in ('sys', 'system'):
            if len(parts) < 3:
                return {"error": "Usage: /prompt sys <name>"}
            name = parts[2]
            text = cli.load_prompt(name)
            if text is None:
                return {"error": f"Prompt {name} not found"}
            chat_data['messages'][0] = {"role": "system", "content": text}
            cli.save_chat_to_file(active_filename, chat_data)
            return {"system": f"System prompt set from {name}"}
        else:
            return {"error": "Unknown prompt command"}
    elif cmd == '/summary':
        s = summarize(messages)
        return {"summary": s}
    elif cmd == '/search':
        if len(parts) < 2:
            return {"error": "Usage: /search <term>"}
        term = " ".join(parts[1:])
        return {"results": search_messages(messages, term)}
    elif cmd == '/export':
        name = parts[1] if len(parts) > 1 else ''
        path = cli.export_chat(chat_data, name)
        return {"system": f"Exported to {path}"}
    elif cmd == '/model':
        if len(parts) == 1:
            return {"system": f"Current model: {MODEL}"}
        if parts[1] == 'select':
            return {"models": cli.AVAILABLE_MODELS}
        MODEL = parts[1]
        chat_data['model'] = MODEL
        return {"system": f"Model set to {MODEL}"}
    elif cmd == '/info':
        path = os.path.join(cli.CHAT_HISTORY_DIR, active_filename)
        mtime = "unknown"
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            pass
        return {
            "file": active_filename,
            "model": chat_data['model'],
            "messages": len(messages)-1,
            "mtime": mtime,
        }
    else:
        return {"error": f"Unknown command {cmd}"}


def process_message(text):
    global chat_data, messages
    if text.startswith('/'):
        return handle_command(text)
    messages.append({"role": "user", "content": text})
    cli.save_chat_to_file(active_filename, chat_data)
    context = messages[-cli.HISTORY_LIMIT:]
    if context[0]['role'] != 'system':
        context = [messages[0]] + context
    chat_completion = client.chat.completions.create(
        messages=context,
        model=MODEL,
        temperature=0.7,
        top_p=1,
    )
    assistant_response = chat_completion.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})
    cli.save_chat_to_file(active_filename, chat_data)
    if len(messages) == 3 and chat_data['name'].startswith('Chat '):
        new_name = cli.generate_chat_name(client, messages)
        if new_name:
            chat_data['name'] = new_name
            cli.save_chat_to_file(active_filename, chat_data)
    return {"assistant": assistant_response}


@app.get('/api/chat')
async def get_chat():
    return chat_data


@app.get('/api/chats')
async def get_chats():
    return list_chats()


@app.post('/api/load')
async def api_load(data: dict):
    res = handle_command(f"/load {data.get('filename','')}")
    return {"result": res, "chat": chat_data}


@app.post('/api/message')
async def api_message(data: dict):
    res = process_message(data.get('message',''))
    return {"result": res, "chat": chat_data}


INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>GroqChat Web</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:0;display:flex;height:100vh;background:#1e1e1e;color:#eee}
    #sidebar{width:250px;border-right:1px solid #444;overflow-y:auto;padding:10px;background:#2b2b2b;display:flex;flex-direction:column}
    #tabButtons{display:flex;margin-bottom:10px}
    .tab{flex:1;padding:5px;background:#333;border:1px solid #444;color:#eee;cursor:pointer;text-align:center}
    .tab.active{background:#555}
    #fileList{display:flex;flex-direction:column;gap:6px}
    .chat-entry{cursor:pointer;color:#9cf;padding:2px}
    .chat-entry:hover{background:#3a3a3a}
    .chat-name{font-size:14px}
    .chat-file{font-size:12px;color:#aaa;margin-left:4px}
    #chat{flex:1;display:flex;flex-direction:column;height:100%}
    #messages{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
    .message{padding:8px;border-radius:4px;max-width:80%;white-space:pre-wrap}
    .user{background:#2f3b55;align-self:flex-end}
    .assistant{background:#353535}
    .system{background:#444;align-self:center}
    .error{background:#552222;color:#ffbbbb;align-self:center}
    #sysBox{margin-top:10px}
    #sysPrompt{width:100%;background:#333;color:#eee;border:1px solid #555;margin-top:4px}
    #summaryBox{margin-top:10px;font-size:12px;white-space:pre-wrap}
    #input{display:flex;border-top:1px solid #444}
    #input textarea{flex:1;padding:5px;background:#333;color:#eee;border:1px solid #444}
    #input button{background:#444;color:#eee;border:1px solid #555;padding:5px 10px}
  </style>
</head>
<body>
  <div id='sidebar'>
    <h3>Chats</h3>
    <div id='tabButtons'></div>
    <div id='fileList'></div>
    <details id='sysBox'>
      <summary>System Prompt</summary>
      <textarea id='sysPrompt' rows='4'></textarea>
      <button onclick='updateSystem()'>Save</button>
    </details>
    <div id='summaryBox'></div>
  </div>
  <div id='chat'>
    <div id='messages'></div>
    <div id='input'>
      <textarea id='msg' rows='3'></textarea>
      <button onclick='sendMsg()'>Send</button>
    </div>
  </div>
  <script>
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
    showMessages(data.chat.messages,data.result);
  }
  async function updateSystem(){
    const text=document.getElementById('sysPrompt').value;
    const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'/system '+text})});
    const data=await res.json();
    showMessages(data.chat.messages,data.result);
  }
  async function sendMsg(){
    const t=document.getElementById('msg');
    const text=t.value;t.value='';
    const res=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
    const data=await res.json();
    showMessages(data.chat.messages,data.result);
  }
  function showMessages(msgs,res){
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
  fetch('/api/chat').then(r=>r.json()).then(d=>showMessages(d.messages));
  </script>
</body>
</html>
"""


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse(INDEX_HTML)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='0.0.0.0', port=8000)
