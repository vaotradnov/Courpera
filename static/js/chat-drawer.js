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

  function openDrawer(){
    var drawer = document.getElementById('chatDrawer');
    if(!drawer){
      drawer = el('div','chat-drawer'); drawer.id='chatDrawer';
      drawer.innerHTML = '<div class="chat-drawer__panel"><div class="chat-drawer__convos" id="chatConvos"><h4>Messages</h4><div class="muted">Coming soon</div></div><div class="chat-drawer__messages" id="chatMsgs"><h4>Conversation</h4><div class="muted">Select a conversation</div><div id="chatModeration"></div></div></div>';
      document.body.appendChild(drawer);
      // Build moderation UI if available
      try{ var modPanel = document.getElementById('chatModeration'); if(modPanel) _buildModeration(modPanel); }catch(_){ }
    }
    drawer.classList.add('open');
  }
  ready(function(){
    // Add a Messages link to the header actions if not present
    try {
      var header = document.querySelector('header .header-actions')
                || document.getElementById('headerLinks')
                || document.querySelector('header nav .nav-row.bottom');
      if(header && !document.getElementById('messagesBtn')){
        var a = el('a'); a.href = '#'; a.textContent = 'Messages'; a.id='messagesBtn'; a.className='btn-link';
        a.addEventListener('click', function(ev){ try{ ev.preventDefault(); }catch(_){} openDrawer(); });
        if (header.querySelector('.notif-wrap')){
          header.insertBefore(a, header.querySelector('.notif-wrap'));
        } else {
          header.appendChild(a);
        }
      }
    } catch(_){}
  });
})();
