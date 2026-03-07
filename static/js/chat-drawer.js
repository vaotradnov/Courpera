/* Chat Drawer UI scaffold (CSP-safe). Progressive enhancement only. */
(function(){
  function ready(fn){ if(document.readyState!=='loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  function el(tag, cls){ var e=document.createElement(tag); if(cls) e.className=cls; return e; }
  function _getCookie(name){
    try{ var v='; ' + document.cookie; var parts=v.split('; ' + name + '='); if(parts.length===2) return parts.pop().split(';').shift(); }catch(_){ }
    return '';
  }
  function _findRoomContext(){
    var holder = document.querySelector('[data-chat-course-id]');
    if(!holder) return {courseId:null, roomId:null, holder:null};
    var courseId = holder.getAttribute('data-chat-course-id');
    var roomId = holder._roomIdCache || null;
    return {courseId:courseId, roomId:roomId, holder:holder};
  }
  function _ensureRoomId(ctx, cb){
    if(ctx.roomId){ cb(ctx.roomId); return; }
    if(!ctx.courseId){ cb(null); return; }
    fetch('/messaging/course/' + ctx.courseId + '/history/')
      .then(function(r){ return r.ok ? r.json() : {}; })
      .then(function(d){ try{ if(ctx.holder) ctx.holder._roomIdCache = d.room_id; }catch(_){ } cb(d.room_id || null); })
      .catch(function(){ cb(null); });
  }
  function _buildModeration(panel){
    try{
      var rosterSel = document.getElementById('modRoster');
      if(!rosterSel) return; // only for owners
      var wrap = el('div','panel mt-2');
      wrap.innerHTML = '<h4>Moderation</h4>';
      var row = el('div');
      var userSel = el('select','input'); userSel.id='drawerModUser';
      for(var i=0;i<rosterSel.options.length;i++){ var opt=rosterSel.options[i]; var o=document.createElement('option'); o.value=opt.value; o.textContent=opt.textContent; userSel.appendChild(o); }
      var muteBtn = el('button','btn-secondary'); muteBtn.textContent='Mute 5m'; muteBtn.id='drawerMute5';
      var unmuteBtn = el('button','btn-secondary'); unmuteBtn.textContent='Unmute'; unmuteBtn.id='drawerUnmute';
      var banBtn = el('button','btn-secondary'); banBtn.textContent='Ban'; banBtn.id='drawerBan';
      var unbanBtn = el('button','btn-secondary'); unbanBtn.textContent='Unban'; unbanBtn.id='drawerUnban';
      var delaySel = el('select','input'); delaySel.id='drawerDelay'; delaySel.innerHTML='<option value="0">Delay: Off</option><option value="5">5s</option><option value="10">10s</option><option value="30">30s</option>';
      row.appendChild(userSel); row.appendChild(muteBtn); row.appendChild(unmuteBtn); row.appendChild(banBtn); row.appendChild(unbanBtn); row.appendChild(delaySel);
      wrap.appendChild(row); panel.appendChild(wrap);

      function postMod(roomId, userId, action, params){
        var url = '/messaging/rooms/' + roomId + '/moderate/' + userId + '/' + action + '/';
        if (params){ var qs = new URLSearchParams(params).toString(); if(qs) url += (url.indexOf('?')===-1?'?':'&') + qs; }
        return fetch(url, { method:'POST', headers:{ 'X-CSRFToken': _getCookie('csrftoken') } });
      }
      function getCtxAndDo(doit){ var ctx=_findRoomContext(); _ensureRoomId(ctx, function(rid){ if(!rid) return; doit(rid, userSel.value); }); }

      muteBtn.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){ } getCtxAndDo(function(rid,uid){ postMod(rid, uid, 'mute', {minutes:'5'}); }); });
      unmuteBtn.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){ } getCtxAndDo(function(rid,uid){ postMod(rid, uid, 'unmute'); }); });
      banBtn.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){ } getCtxAndDo(function(rid,uid){ postMod(rid, uid, 'ban'); }); });
      unbanBtn.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){ } getCtxAndDo(function(rid,uid){ postMod(rid, uid, 'unban'); }); });
      delaySel.addEventListener('change', function(){ var secs=parseInt(delaySel.value||'0',10)||0; getCtxAndDo(function(rid,uid){ postMod(rid, uid, 'delay', {seconds:String(secs)}); }); });
    }catch(_){ }
  }

  var _activeRow = null;
  function _qs(id){ return document.getElementById(id); }
  function _getCookie(name){
    try{ var v='; ' + document.cookie; var parts=v.split('; ' + name + '='); if(parts.length===2) return parts.pop().split(';').shift(); }catch(_){ }
    return '';
  }
  function _buildList(container, items, onOpen){
    container.innerHTML = '';
    var controls = el('div','chat-convos__controls');
    controls.innerHTML = '<label for="dmUser" class="sr-only">Search or start chat</label>'+
                         '<input id="dmUser" class="input" placeholder="Seach or start chat"/>'+
                         '<button id="grpToggle" class="btn-secondary" type="button">New group</button>';
    container.appendChild(controls);
    // DM via Enter or Start
    function submitDM(){ var q=_qs('dmUser').value.trim(); if(!q) return; var key='username'; if(/^\d+$/.test(q)) key='user_id'; else if(q.indexOf('@')>=0) key='email'; var body=key+'='+encodeURIComponent(q); fetch('/messaging/rooms/dm/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':_getCookie('csrftoken')}, body:body}).then(function(r){return r.ok?r.json():null;}).then(function(d){ if(d && d.room_id){ refreshConvos(d.room_id); } }); }
    try{ _qs('dmUser').addEventListener('keydown', function(ev){ if(ev.key==='Enter'){ ev.preventDefault(); submitDM(); } }); }catch(_){ }
    // Group panel (collapsed)
    var grp = el('div','chat-convos__group'); grp.id='grpPanel'; grp.innerHTML = '<form><input id="grpTitle" class="input" placeholder="New group title"/>'+
                '<input id="grpMembers" class="input mt-1" placeholder="Members (IDs, emails, usernames)"/>'+
                '<div class="mt-1"><button class="btn-secondary" type="submit">Create</button></div></form>';
    container.appendChild(grp);
    try{ _qs('grpToggle').addEventListener('click', function(){ grp.classList.toggle('open'); }); }catch(_){ }
    grp.querySelector('form').addEventListener('submit', function(ev){ ev.preventDefault(); var t=_qs('grpTitle').value.trim(); if(!t) return; var mem=_qs('grpMembers').value.trim(); var body='title='+encodeURIComponent(t); if(mem) body+='&members='+encodeURIComponent(mem); fetch('/messaging/rooms/group/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':_getCookie('csrftoken')}, body:body}).then(function(r){return r.ok?r.json():null;}).then(function(d){ if(d && d.room_id){ refreshConvos(d.room_id); grp.classList.remove('open'); } }); });
    // List with small section headers
    var list = el('div','chat-convos__list'); list.id='chatConvoList'; container.appendChild(list);
    var dms=[], groups=[], courses=[];
    (items||[]).forEach(function(it){
      if(it.kind === 'dm') dms.push(it); else if(it.kind === 'group') groups.push(it); else courses.push(it);
    });
    function renderSection(label, arr){
      if(!arr || !arr.length) return;
      var hdr = el('div','chat-list-section'); hdr.textContent = label; list.appendChild(hdr);
      arr.forEach(function(it){
        var row = el('div','convo-row');
        var title = el('div'); title.textContent = it.title || '(untitled)';
        var sub = el('div','muted');
        try{ var txt = (it.last_message && it.last_message.text) ? it.last_message.text : ''; sub.textContent = txt.length>42 ? txt.slice(0,42)+'…' : txt; }catch(_){ }
        row.appendChild(title); row.appendChild(sub);
        var chip = null; if (it.unread && it.unread > 0){ chip = el('span'); chip.className='chip'; chip.textContent = String(it.unread); row.appendChild(chip); }
        row.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){ } onOpen(it.id, row, chip); });
        list.appendChild(row);
      });
    }
    renderSection('Direct (' + dms.length + ')', dms);
    renderSection('Groups (' + groups.length + ')', groups);
    renderSection('Courses (' + courses.length + ')', courses);
  }
  var _activeRow = null;
  function _openConversation(root, roomId, row){
    try{ if(_activeRow) _activeRow.classList.remove('active'); if(row){ row.classList.add('active'); _activeRow=row; } }catch(_){ }
    root.innerHTML='';
    var heading = el('div'); heading.className='chat-convo-header'; heading.innerHTML='<div><h4 class="inline" id="roomTitleHd">Conversation</h4> <span class="presence" id="roomPresence"></span></div><div><button id="roomToolsBtn" class="btn-secondary" type="button">Room tools</button></div>'; root.appendChild(heading);
    var log = el('div'); log.className='chat-log'; root.appendChild(log);
    var form = el('form'); form.className='chat-composer'; form.innerHTML='<input id="drawerMsg" class="input" placeholder="Type a message"/><button class="btn-primary" type="submit">Send</button>'; root.appendChild(form);
    var typingLine = document.createElement('div'); typingLine.className='typing-line'; typingLine.id='typingLine'; root.appendChild(typingLine);
    var toolsWrap = el('div'); toolsWrap.id='chatToolsWrap'; toolsWrap.style.display='none'; root.appendChild(toolsWrap);
    var tools = el('div'); tools.id = 'chatModeration'; toolsWrap.appendChild(tools);
    var prevSender = null; var roomKind = 'group'; var lastReadISO = null; // set after members fetch
    function makeAvatar(name){
      try{
        var s=(name||'').toString(); var ch=s.trim().charAt(0).toUpperCase() || '?';
        var h=0; for(var i=0;i<s.length;i++){ h=(h*31 + s.charCodeAt(i))>>>0; }
        var hue=h%360; var a=document.createElement('span'); a.className='avatar'; a.textContent=ch; a.style.backgroundColor='hsl('+hue+', 65%, 55%)'; a.style.color='#fff'; return a;
      }catch(_){ var a=document.createElement('span'); a.className='avatar'; a.textContent='?'; return a; }
    }
    function addMessage(sender, text, created, prepend){
      var row=el('div'); row.className='msg-row'; row.setAttribute('data-sender', sender||'');
      var myname=null; try{ var me=document.getElementById('currentUserData'); myname = me ? me.getAttribute('data-username') : null; }catch(_){ }
      if (myname && sender === myname) row.classList.add('self');
      // Username label above first message in a sequence (not for self, not for DMs)
      if (roomKind !== 'dm' && (!myname || sender !== myname)){
        var needLabel = false;
        if (prepend){
          // when prepending, compare with current first message's sender
          var next = log.firstElementChild;
          var nextSender = (next && next.getAttribute) ? (next.getAttribute('data-sender') || '') : '';
          needLabel = (!next || nextSender !== sender);
        } else {
          needLabel = (prevSender !== sender);
        }
        if (needLabel){ var lab=document.createElement('div'); lab.className='msg-label'; var av=makeAvatar(sender||''); lab.appendChild(av); var nm=document.createElement('span'); nm.textContent=sender||''; lab.appendChild(nm); if (prepend){ log.insertBefore(lab, log.firstChild); } else { log.appendChild(lab); } }
      }
      var b=el('div'); b.className='msg-bubble'; b.textContent=(text||'');
      var meta=el('span'); meta.className='msg-meta'; try{ var d=new Date(created); meta.textContent=d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); }catch(_){ }
      row.appendChild(b); row.appendChild(meta);
      if(prepend){ log.insertBefore(row, log.firstChild); } else { log.appendChild(row); log.scrollTop=log.scrollHeight; }
      prevSender = sender;
    }
    // Load history then connect WS
    var nextBefore = null; var loadBtn = document.createElement('button'); loadBtn.className='btn-secondary'; loadBtn.textContent='Load older'; loadBtn.style.display='none'; loadBtn.addEventListener('click', function(){ if(!nextBefore) return; fetch('/messaging/rooms/' + roomId + '/messages/?limit=50&before=' + encodeURIComponent(nextBefore)).then(function(r){ return r.ok ? r.json() : {results:[], next_before:null}; }).then(function(d){ var curTop = log.scrollTop; (d.results||[]).forEach(function(m){ // prepend older, no divider logic needed here
            addMessage(m.sender, m.message, m.created_at, true);
          }); nextBefore = d.next_before || null; loadBtn.style.display = nextBefore ? 'inline-block' : 'none'; if(d.results && d.results.length){ log.scrollTop = curTop + 1; } checkMarkRead(); }); });
    root.insertBefore(loadBtn, log);
    // Scroll-to-bottom button
    var sbtn=document.createElement('button'); sbtn.className='scroll-down'; sbtn.setAttribute('title','Scroll to bottom'); sbtn.addEventListener('click', function(){ try{ log.scrollTop = log.scrollHeight; sbtn.style.display='none'; }catch(_){ } });
    root.appendChild(sbtn);
    function positionScrollButton(){
      try{
        var rr=root.getBoundingClientRect(); var lr=log.getBoundingClientRect();
        var size=40, margin=12; // 40px button, 12px gap
        sbtn.style.right='auto'; sbtn.style.bottom='auto';
        sbtn.style.left = (lr.left - rr.left + lr.width - (size + margin)) + 'px';
        sbtn.style.top  = (lr.top  - rr.top  + lr.height - (size + margin)) + 'px';
      }catch(_){ }
    }
    positionScrollButton();
    try{ window.addEventListener('resize', positionScrollButton); }catch(_){ }
    function atBottom(){ try{ return (log.scrollHeight - log.scrollTop - log.clientHeight) < 48; }catch(_){ return true; } }
    log.addEventListener('scroll', function(){ try{ sbtn.style.display = atBottom() ? 'none' : 'inline-block'; }catch(_){ } });
    // First, fetch members to get room kind and last_read
    fetch('/messaging/rooms/' + roomId + '/members/')
      .then(function(r){ return r.ok ? r.json() : {kind:'group', self_last_read_at:null, title:''}; })
      .then(function(info){ try{ roomKind = info.kind || 'group'; lastReadISO = info.self_last_read_at || null; var ti=document.getElementById('roomTitleHd'); if(ti && info.title){ ti.textContent = info.title; } }catch(_){ }
        return fetch('/messaging/rooms/' + roomId + '/messages/?limit=50');
      })
      .then(function(r){ return r.ok ? r.json() : {results:[], next_before:null}; })
      .then(function(d){
        var inserted = false; var lr = null; try{ lr = lastReadISO ? new Date(lastReadISO) : null; }catch(_){ lr = null; }
        (d.results||[]).forEach(function(m){
          // Insert unread divider when we cross last_read_at -> first newer message
          try{ if(!inserted && lr){ var mc=new Date(m.created_at); if(mc > lr){ var div=document.createElement('div'); div.className='msg-divider'; div.id='unreadDivider'; var span=document.createElement('span'); span.textContent='New'; var btn=document.createElement('button'); btn.className='btn-outline'; btn.textContent='Mark as read'; btn.style.marginLeft='.5rem'; btn.addEventListener('click', function(){ markRead(); }); div.appendChild(span); div.appendChild(btn); log.appendChild(div); inserted=true; } } }catch(_){ }
          addMessage(m.sender, m.message, m.created_at);
        });
        nextBefore = d.next_before || null; loadBtn.style.display = nextBefore ? 'inline-block' : 'none';
        sbtn.style.display = atBottom() ? 'none' : 'inline-block';
        checkMarkRead();
      });
    // defer mark-read: done after user scrolls past divider or explicitly reaches bottom
    // WS
    try{ var scheme=(location.protocol==='https:')?'wss':'ws'; var ws=new WebSocket(scheme+'://'+location.host+'/ws/chat/room/'+roomId+'/'); ws.onmessage=function(ev){ try{ var d=JSON.parse(ev.data||'{}'); if(d.type==='message.new'){ var near=atBottom(); addMessage(d.sender, d.message, d.created_at); if(near) { try{ log.scrollTop=log.scrollHeight; }catch(_){ } } else { sbtn.style.display='inline-block'; } refreshConvos(roomId); checkMarkRead(); }
      if(d.type==='presence.state'){ var p=document.getElementById('roomPresence'); if(p){ p.textContent = (d.count? d.count:0) + ' online'; } }
      if(d.type && d.type.indexOf('typing.')===0){ var tl=document.getElementById('typingLine'); if(tl){ if(d.type==='typing.start'){ tl.textContent='typing…'; } else { tl.textContent=''; } } }
    }catch(_){ } } }catch(_){ }
    // Mark-read logic: when unread divider is scrolled past
    var hasMarked=false; function markRead(){ if(hasMarked) return; hasMarked=true; fetch('/messaging/rooms/' + roomId + '/read/', { method:'POST', headers:{ 'X-CSRFToken': _getCookie('csrftoken') } }).then(function(){ try{ var d=document.getElementById('unreadDivider'); if(d) d.remove(); }catch(_){ } }); }
    function checkMarkRead(){ try{ var div=document.getElementById('unreadDivider'); if(!div || hasMarked) return; var top = log.getBoundingClientRect().top; var divTop = div.getBoundingClientRect().top; if (divTop <= top + 4){ markRead(); } }catch(_){ } }
    log.addEventListener('scroll', checkMarkRead);
    form.addEventListener('submit', function(ev){ try{ ev.preventDefault(); }catch(_){ } var input=_qs('drawerMsg'); var txt=(input && input.value||'').trim(); if(!txt) return; try{ if(ws && ws.readyState===1){ ws.send(JSON.stringify({message:txt})); } }catch(_){ } try{ input.value=''; }catch(_){ } });
    try{ var mp=document.getElementById('chatModeration'); if(mp) _buildModeration(mp); }catch(_){ }
    // Build simple Room Tools (rename, add/remove)
    try{
      var btn = document.getElementById('roomToolsBtn');
      if(btn){
        btn.addEventListener('click', function(){ toolsWrap.style.display = toolsWrap.style.display==='none' ? 'block' : 'none'; });
      }
      // Fetch members and render tools
      fetch('/messaging/rooms/' + roomId + '/members/')
        .then(function(r){ return r.ok ? r.json() : {results:[], kind:'group', title:''}; })
        .then(function(info){
          var canEdit = (info.kind !== 'course');
          try{ var ti=document.getElementById('roomTitleHd'); if(ti){ ti.textContent = info.title ? info.title : (info.kind==='dm'?'Direct message':'Conversation'); } }catch(_){ }
          var panel = document.createElement('div');
          panel.className = 'panel mt-2';
          var html = '';
          if (canEdit) {
            html += '<div><label class="sr-only" for="roomTitle">Title</label><input id="roomTitle" class="input" placeholder="Room title" value="'+ (info.title||'') +'"/> <button id="saveTitle" class="btn-secondary" type="button">Save</button></div>';
            html += '<div class="mt-1"><label class="sr-only" for="addMember">Add member</label><input id="addMember" class="input" placeholder="Add member (username/email/ID)"/> <button id="btnAdd" class="btn-secondary" type="button">Add</button></div>';
            html += '<div class="mb-1"><button id="btnLeave" class="btn-danger" type="button">Leave chat</button></div>';
          } else {
            html += '<div class="muted">Editing is teacher‑only for course chats.</div>';
          }
          html += '<div class="mt-2" id="memberList"></div>';
          panel.innerHTML = html; toolsWrap.insertBefore(panel, toolsWrap.firstChild);

          function refreshMembers(){
            fetch('/messaging/rooms/' + roomId + '/members/')
              .then(function(r){ return r.ok ? r.json() : {results:[]}; })
              .then(function(d){ var box=document.getElementById('memberList'); if(!box) return; box.innerHTML=''; var me=document.getElementById('currentUserData'); var myid = 0; try{ myid = parseInt(me && me.getAttribute('data-uid') || '0',10)||0; }catch(_){ }
                (d.results||[]).forEach(function(m){ var row=document.createElement('div'); row.style.display='flex'; row.style.justifyContent='space-between'; row.style.alignItems='center'; var name=document.createElement('span'); name.textContent=m.username; row.appendChild(name); if(canEdit && m.id !== myid){ var rm=document.createElement('button'); rm.className='btn-secondary'; rm.textContent='Remove'; rm.addEventListener('click', function(){ fetch('/messaging/rooms/'+roomId+'/members/remove/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':_getCookie('csrftoken')}, body:'user_id='+encodeURIComponent(m.id)}).then(function(){ refreshMembers(); }); }); row.appendChild(rm);} box.appendChild(row); }); });
          }
          refreshMembers();

          if (canEdit){
            var saveBtn = document.getElementById('saveTitle'); if(saveBtn){ saveBtn.addEventListener('click', function(){ var v=document.getElementById('roomTitle').value.trim(); if(!v) return; fetch('/messaging/rooms/'+roomId+'/rename/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':_getCookie('csrftoken')}, body:'title='+encodeURIComponent(v)}).then(function(){ var hd=document.getElementById('roomTitleHd'); if(hd) hd.textContent=v; refreshConvos(roomId); }); }); }
            var addBtn = document.getElementById('btnAdd'); if(addBtn){ addBtn.addEventListener('click', function(){ var q=document.getElementById('addMember').value.trim(); if(!q) return; fetch('/messaging/rooms/'+roomId+'/members/add/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':_getCookie('csrftoken')}, body:'q='+encodeURIComponent(q)}).then(function(){ document.getElementById('addMember').value=''; refreshMembers(); }); }); }
            var leaveBtn = document.getElementById('btnLeave'); if(leaveBtn){ leaveBtn.addEventListener('click', function(){
              try{
                var ov=document.getElementById('chatConfirmOverlay');
                if(!ov) return;
                document.getElementById('confirmText').textContent='Are you sure you want to leave this chat?';
                ov.classList.add('open');
                var cancel=document.getElementById('confirmCancel'); var ok=document.getElementById('confirmOk');
                var close=function(){ try{ ov.classList.remove('open'); }catch(_){ } };
                cancel.onclick=function(){ close(); };
                ok.onclick=function(){ fetch('/messaging/rooms/'+roomId+'/leave/', {method:'POST', headers:{'X-CSRFToken':_getCookie('csrftoken')}}).then(function(){ close(); refreshConvos(); toolsWrap.style.display='none'; }); };
              }catch(_){ }
            }); }
          }
        });
    } catch(_){ }
  }
  function refreshConvos(openRoomId){
    var listPanel=_qs('chatConvos'); var msgPanel=_qs('chatMsgs'); if(!listPanel) return;
    fetch('/messaging/rooms/mine/')
      .then(function(r){ return r.ok ? r.json() : {results:[]}; })
      .then(function(d){ var res=d.results||[]; _buildList(listPanel, res, function(roomId, row, chip){ _openConversation(msgPanel, roomId, row); try{ chip.textContent=''; }catch(_){ } }); var defId=openRoomId || (res.length ? res[0].id : null); if(defId){ _openConversation(msgPanel, defId); } });
  }
  function closeDrawer(){ var d=document.getElementById('chatDrawer'); var b=document.getElementById('chatBackdrop'); if(d){ d.classList.remove('open'); } if(b){ b.classList.remove('open'); } }
  function openDrawer(){
    var drawer = document.getElementById('chatDrawer');
    if(!drawer){
      drawer = el('div','chat-drawer'); drawer.id='chatDrawer';
      drawer.innerHTML = '<div class="chat-drawer__header" role="toolbar" aria-label="Messages"><strong>Messages</strong><button id="chatCloseBtn" aria-label="Close messages" type="button">&times;</button></div>'+
                         '<div class="chat-drawer__panel"><div class="chat-drawer__convos" id="chatConvos"><div class="muted">Loading…</div></div><div class="chat-drawer__messages" id="chatMsgs"><div class="muted">Select a conversation</div></div></div>';
      document.body.appendChild(drawer);
      var backdrop = el('div','chat-backdrop'); backdrop.id='chatBackdrop'; backdrop.addEventListener('click', function(){ closeDrawer(); }); document.body.appendChild(backdrop);
      // Ensure a global confirm overlay exists for destructive actions
      try{
        if(!document.getElementById('chatConfirmOverlay')){
          var cbo=document.createElement('div'); cbo.className='confirm-overlay'; cbo.id='chatConfirmOverlay'; cbo.innerHTML='<div class="confirm-panel"><div id="confirmText">Are you sure?</div><div class="confirm-actions"><button id="confirmCancel" class="btn-outline" type="button">Cancel</button><button id="confirmOk" class="btn-danger" type="button">Confirm</button></div></div>'; document.body.appendChild(cbo);
        }
      }catch(_){ }
      // Build moderation UI if available
      try{ var modPanel = document.getElementById('chatModeration'); if(modPanel) _buildModeration(modPanel); }catch(_){ }
      try{ var x=document.getElementById('chatCloseBtn'); if(x){ x.addEventListener('click', function(){ closeDrawer(); }); } }catch(_){ }
      // Open a notify WS to refresh list on new bumps
      try{
        if(!window._drawerNotifyWs){
          var scheme=(location.protocol==='https:')?'wss':'ws';
          var nws=new WebSocket(scheme+'://'+location.host+'/ws/notify/');
          nws.onmessage=function(ev){ try{ var d=JSON.parse(ev.data||'{}'); if(d.type==='notif.bump'){ refreshConvos(); } }catch(_){ } };
          window._drawerNotifyWs = nws;
        }
      }catch(_){ }
    }
    var bElm=document.getElementById('chatBackdrop'); if(bElm){ bElm.classList.add('open'); }
    drawer.classList.add('open');
    refreshConvos();
  }
  ready(function(){
    // Add a Messages link to the header actions if not present
    try {
      var header = document.querySelector('header .header-actions')
                || document.getElementById('headerLinks')
                || document.querySelector('header nav .nav-row.bottom');
      if(header && !document.getElementById('messagesBtn')){
        var a = el('a'); a.href = '#'; a.textContent = 'Messages'; a.id='messagesBtn'; a.className='btn-link';
        a.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){} var d=document.getElementById('chatDrawer'); if(d && d.classList.contains('open')){ closeDrawer(); } else { openDrawer(); } });
        if (header.querySelector('.notif-wrap')){
          header.insertBefore(a, header.querySelector('.notif-wrap'));
        } else {
          header.appendChild(a);
        }
      }
    } catch(_){}
  });
  document.addEventListener('keydown', function(ev){ if(ev.key==='Escape'){ try{ closeDrawer(); }catch(_){ } } });
})();
