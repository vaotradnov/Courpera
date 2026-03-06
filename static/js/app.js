(function(){
  function qs(id){ return document.getElementById(id); }

  function initNotifications(){
    var btn = qs('notifBtn');
    var panel = qs('notifPanel');
    var list = qs('notifList');
    var badge = qs('notifBadge');
    if(!btn || !panel) return;
    function fetchRecent(){
      fetch('/activity/notifications/recent/')
        .then(function(r){ return r.ok ? r.json() : {unread:0,results:[]}; })
        .then(function(d){
          badge.textContent = d.unread ? '(' + d.unread + ')' : '';
          list.innerHTML = '';
          (d.results || []).forEach(function(n){
            var li = document.createElement('li');
            li.textContent = n.message;
            list.appendChild(li);
          });
          if((d.results||[]).length === 0){
            var li = document.createElement('li'); li.textContent = 'No notifications'; list.appendChild(li);
          }
        })
        .catch(function(){});
    }
    btn.addEventListener('click', function(ev){
      try { ev.preventDefault(); ev.stopPropagation(); } catch(e) {}
      var isOpen = panel.classList.contains('open');
      if (isOpen) {
        try { btn.setAttribute('aria-expanded', 'false'); } catch(e) {}
        // Navigate to full notifications page on second click while open
        try { window.location.href = '/activity/notifications/'; } catch(e) {}
        return;
      }
      // Close Explore if open
      try {
        var explorePanel = document.getElementById('explorePanel');
        var exploreBtn = document.getElementById('exploreBtn');
        if (explorePanel && explorePanel.classList.contains('open')) {
          explorePanel.classList.remove('open');
          if (exploreBtn) exploreBtn.setAttribute('aria-expanded','false');
        }
      } catch(e) {}
      panel.classList.add('open');
      try { btn.setAttribute('aria-expanded', 'true'); } catch(e) {}
      fetchRecent();
    });
    // Prevent clicks inside panel from bubbling to document and closing it
    panel.addEventListener('click', function(ev){
      try { ev.stopPropagation(); } catch(e) {}
    });
    document.addEventListener('click', function(e){
      // Close if click is outside both the panel and the button (including its children)
      var clickedInsidePanel = panel.contains(e.target);
      var clickedOnButton = btn.contains ? btn.contains(e.target) : (e.target === btn);
      if(!clickedInsidePanel && !clickedOnButton){
        panel.classList.remove('open');
        try { btn.setAttribute('aria-expanded', 'false'); } catch(e) {}
      }
    });
    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape'){
        panel.classList.remove('open');
        try { btn.setAttribute('aria-expanded', 'false'); } catch(err) {}
      }
    });
  }

  function initExplore(){
    var btn = document.getElementById('exploreBtn');
    var panel = document.getElementById('explorePanel');
    if(!btn || !panel) return;
    function close(){ panel.classList.remove('open'); try{ btn.setAttribute('aria-expanded','false'); }catch(e){} }
    btn.addEventListener('click', function(ev){
      try { ev.preventDefault(); ev.stopPropagation(); } catch(e) {}
      var isOpen = panel.classList.contains('open');
      if(isOpen){ close(); return; }
      // Close Notifications if open
      try {
        var notifPanel = document.getElementById('notifPanel');
        var notifBtn = document.getElementById('notifBtn');
        if (notifPanel && notifPanel.classList.contains('open')) {
          notifPanel.classList.remove('open');
          if (notifBtn) notifBtn.setAttribute('aria-expanded','false');
        }
      } catch(e) {}
      panel.classList.add('open');
      try{ btn.setAttribute('aria-expanded','true'); }catch(e){}
    });
    panel.addEventListener('click', function(ev){ try{ ev.stopPropagation(); }catch(e){} });
    document.addEventListener('click', function(ev){
      var inside = panel.contains(ev.target) || (btn.contains ? btn.contains(ev.target) : ev.target === btn);
      if(!inside) close();
    });
    document.addEventListener('keydown', function(ev){ if(ev.key==='Escape') close(); });
  }

  function initNavToggle(){
    var toggle = document.getElementById('navToggle');
    var links = document.getElementById('headerLinks');
    if(!toggle || !links) return;
    toggle.addEventListener('click', function(){
      var open = links.classList.contains('open');
      links.classList.toggle('open', !open);
      try{ toggle.setAttribute('aria-expanded', String(!open)); }catch(e){}
    });
  }

  function initAccordion(){
    var containers = document.querySelectorAll('.accordion');
    if(!containers || !containers.length) return;
    containers.forEach(function(acc){
      acc.addEventListener('click', function(e){
        var btn = e.target.closest('.accordion-button');
        if(!btn) return;
        try{ e.preventDefault(); }catch(_){ }
        var panelId = btn.getAttribute('aria-controls');
        var panel = panelId && document.getElementById(panelId);
        if(!panel) return;
        var expanded = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', String(!expanded));
        if(expanded){ panel.setAttribute('hidden',''); }
        else { panel.removeAttribute('hidden'); }
      });
      acc.addEventListener('keydown', function(e){
        if(e.key === 'Escape'){
          // collapse any open panels in this accordion
          var btns = acc.querySelectorAll('.accordion-button[aria-expanded="true"]');
          btns.forEach(function(b){ b.setAttribute('aria-expanded','false'); });
          var panels = acc.querySelectorAll('.accordion-panel:not([hidden])');
          panels.forEach(function(p){ p.setAttribute('hidden',''); });
        }
      });
    });
  }

  function initMaterials(){
    var fi = qs('id_file');
    var ti = qs('id_title');
    if(fi && ti){
      fi.addEventListener('change', function(){
        try {
          if (!ti.value && fi.files && fi.files[0] && fi.files[0].name) {
            var n = fi.files[0].name;
            var base = n.replace(/\.[^.]+$/, '');
            ti.value = base;
          }
        } catch (e) {}
      });
    }
  }

  // Moderation moved to chat-drawer.js

  function initChat(){
    var log = qs('chat-log');
    var form = qs('chat-form');
    var input = qs('chat-input');
    var presenceEl = qs('chat-presence');
    var presenceCount = 0; var slowRemain = 0;
    function updatePresenceLabel(){
      if (!presenceEl) return;
      var parts = [];
      if (presenceCount) parts.push(presenceCount + ' online');
      if (slowRemain > 0) parts.push('slow ' + slowRemain + 's');
      presenceEl.textContent = parts.join(' · ');
    }
    var typingEl = qs('chat-typing');
    var fileInput = qs('chat-file');
    var slowSel = qs('chat-slowmode');
    var noticeEl = qs('chat-notice');
    var modBanner = qs('chat-mod');
    var holder = log && log.closest('[data-chat-course-id]');
    if(!log || !form || !input || !holder) return;
    var currentUid = (function(){ try{ return parseInt(holder.getAttribute('data-user-id')||'0',10) || 0; }catch(_){ return 0; } })();
    try{
      // Remove any legacy inline styles to satisfy strict CSP and apply classes instead
      input.classList.add('input','w-80');
      input.removeAttribute('style');
    }catch(e){}
    var courseId = holder.getAttribute('data-chat-course-id');
    function fmtTime(iso){
      try{
        if(!iso) return '';
        var d = new Date(iso);
        return '[' + d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) + '] ';
      }catch(_){ return ''; }
    }
    function addMessage(sender, text, attachments, createdAt){
      var row = document.createElement('div');
      var who = (sender || 'anon');
      var prefix = document.createElement('span');
      prefix.textContent = fmtTime(createdAt) + who + ': ' + (text || '');
      row.appendChild(prefix);
      if (attachments && attachments.length){
        var frag = document.createDocumentFragment();
        attachments.forEach(function(a){
          try{
            var wrap = document.createElement('div');
            wrap.className = 'mt-2';
            if (a.mime && a.mime.indexOf('image/') === 0){
              var img = document.createElement('img');
              img.src = a.url; img.alt='attachment'; img.style.maxWidth='160px'; img.style.maxHeight='120px';
              wrap.appendChild(img);
            } else {
              var link = document.createElement('a');
              link.href = a.url; link.target = '_blank'; link.rel='noopener noreferrer'; link.textContent = 'Attachment';
              wrap.appendChild(link);
            }
            frag.appendChild(wrap);
          }catch(_){ }
        });
        row.appendChild(frag);
      }
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }
    // History + then decide best WS route
    var scheme = (location.protocol === 'https:') ? 'wss' : 'ws';
    var ws;
    var slowTimer = null;
    function stopSlowTimer(){ if (slowTimer) { try{ clearInterval(slowTimer); }catch(_){ } slowTimer = null; } }
    function startSlowTimer(expiresIso){
      try{
        if(!expiresIso) return;
        var expiresAt = new Date(expiresIso).getTime();
        if (isNaN(expiresAt)) return;
        stopSlowTimer();
        var tick = function(){
          var now = Date.now();
          slowRemain = Math.ceil((expiresAt - now)/1000);
          if (slowRemain <= 0){
            stopSlowTimer();
            if (noticeEl) noticeEl.textContent = '';
            try{ if (slowSel) slowSel.value = '0'; }catch(_){ }
            slowRemain = 0; updatePresenceLabel();
            return;
          }
          if (noticeEl) noticeEl.textContent = 'Slow mode: ' + slowRemain + 's remaining';
          updatePresenceLabel();
        };
        tick();
        slowTimer = setInterval(tick, 1000);
      }catch(_){ }
    }
    fetch('/messaging/course/' + courseId + '/history/')
      .then(function(r){return r.ok ? r.json() : {results:[]};})
      .then(function(data){
        (data.results || []).forEach(function(m){
          addMessage(m.sender, m.message, m.attachments || [], m.created_at);
        });
        try {
          var roomId = data.room_id;
          if (!roomId) return; // Do not open legacy course route; rely on room route only
          try { holder._roomIdCache = roomId; } catch(_) {}
          // Initialize slow mode selector to current value if present
          try { if (slowSel && typeof data.slow_mode_seconds === 'number') slowSel.value = String(data.slow_mode_seconds || 0);} catch(_){ }
          try { if (data.slow_mode_expires_at) startSlowTimer(data.slow_mode_expires_at); } catch(_){ }
          var url = scheme + '://' + location.host + '/ws/chat/room/' + roomId + '/';
          ws = new WebSocket(url);
          var typingTimer = null;
          ws.onmessage = function(ev){
            try{ var d = JSON.parse(ev.data) || {}; }catch(_){ return; }
            // Structured events from server
            if (d.type === 'message.new'){
              addMessage(d.sender, d.message, d.attachments || [], d.created_at);
              return;
            }
            if (d.type === 'presence.state'){
              presenceCount = d.count || 0; updatePresenceLabel();
              try { if (presenceEl) presenceEl.title = (d.users && d.users.length) ? ('Online: ' + d.users.join(', ')) : ''; } catch(_){ }
              return;
            }
            if (d.type === 'typing.start'){
              if (typingEl){ typingEl.textContent = (d.user || 'Someone') + ' is typing…'; }
              if (typingTimer) { try{ clearTimeout(typingTimer); }catch(_){ } }
              typingTimer = setTimeout(function(){ if (typingEl) typingEl.textContent=''; }, 1800);
              return;
            }
            if (d.type === 'typing.stop'){
              if (typingEl){ typingEl.textContent=''; }
              return;
            }
            if (d.type === 'system.notice'){
              if (noticeEl){ noticeEl.textContent = d.message || ''; }
              if (d.expires_at) startSlowTimer(d.expires_at);
              else if ((d.message || '').toLowerCase().indexOf('slow mode turned off') >= 0) { stopSlowTimer(); slowRemain = 0; updatePresenceLabel(); }
              return;
            }
            if (d.type === 'moderation.state'){
              var tid = parseInt(String(d.target_id||'0'),10)||0;
              if (tid && currentUid && tid === currentUid && modBanner){
                var act = String(d.action||'');
                if (act === 'mute'){
                  modBanner.textContent = 'You have been muted' + (d.until ? ' until ' + d.until : '');
                } else if (act === 'ban'){
                  modBanner.textContent = 'You have been banned in this room';
                } else if (act === 'unmute' || act === 'unban'){
                  modBanner.textContent = (act === 'unmute') ? 'You have been unmuted' : 'You have been unbanned';
                  try { clearTimeout(modBanner._hideTimer); } catch(_){ }
                  modBanner._hideTimer = setTimeout(function(){ if (modBanner) modBanner.textContent=''; }, 5000);
                }
              }
              return;
            }
            // Back-compat: unstructured payloads (message echo only)
            if (d && d.message){ addMessage(d.sender, d.message, []); }
          };

          // Owner slow mode control
          if (slowSel){
            slowSel.addEventListener('change', function(){
              var secs = parseInt(slowSel.value || '0', 10) || 0;
              try {
                var fd = new FormData();
                fd.append('slow_mode_seconds', String(secs));
                fetch('/messaging/rooms/' + roomId + '/slowmode/', {
                  method: 'POST',
                  headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                  body: fd
                }).then(function(r){
                  if (!r.ok){
                    if (noticeEl) noticeEl.textContent = 'Failed to update slow mode';
                    return;
                  }
                  try { return r.json(); } catch(_){ return null; }
                }).then(function(data){
                  var v = secs; var exp = null;
                  try {
                    if (data && typeof data.slow_mode_seconds === 'number') v = data.slow_mode_seconds;
                    if (data && data.slow_mode_expires_at) exp = data.slow_mode_expires_at;
                  } catch(_){ }
                  if (slowSel) slowSel.value = String(v || 0);
                  if (noticeEl){
                    noticeEl.textContent = v ? ('Slow mode set to ' + v + 's') : 'Slow mode turned off';
                    try { clearTimeout(noticeEl._smTimer); } catch(_){ }
                    noticeEl._smTimer = setTimeout(function(){ if (noticeEl && noticeEl.textContent.indexOf('Slow mode') === 0) noticeEl.textContent = ''; }, 2000);
                  }
                  if (v && exp) { startSlowTimer(exp); } else { stopSlowTimer(); }
                }).catch(function(){ if (noticeEl) noticeEl.textContent = 'Failed to update slow mode'; });
              } catch(_){ }
            });
          }
        } catch(e) {}
      })
      .catch(function(){ /* no-op: keep UI functional without WS */ });
    form.addEventListener('submit', function(e){
      e.preventDefault();
      var txt = (input.value || '').trim();
      // If a file is selected, prefer HTTP POST to persist attachments
      var roomId = (function(){ try { var r = holder.getAttribute('data-chat-room-id'); if(r) return r; } catch(_){ } return null; })();
      // Keep room id in dataset after fetch: store it now if not present
      // We don't have it yet here; but if we posted once, we set it during history load.
      if (fileInput && fileInput.files && fileInput.files.length > 0){
        if (!holder._roomIdCache){ // rely on cached id set in history load
          // History flow sets this; if missing, skip upload and show notice
          if (noticeEl) noticeEl.textContent = 'Please wait for chat to finish loading…';
          return;
        }
        try{
          var fd = new FormData();
          if (txt) fd.append('message', txt);
          fd.append('file', fileInput.files[0]);
          fetch('/messaging/rooms/' + holder._roomIdCache + '/messages/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
            body: fd
          }).then(function(r){
            if(!r.ok && noticeEl){ r.text().then(function(t){ noticeEl.textContent = 'Upload failed'; try{ var j=JSON.parse(t); if(j && j.detail) noticeEl.textContent=j.detail; }catch(_){ } }); }
          }).catch(function(){ if (noticeEl) noticeEl.textContent='Upload failed'; });
        }catch(_){ if (noticeEl) noticeEl.textContent='Upload failed'; }
        input.value='';
        try{ fileInput.value=''; }catch(_){ }
        return;
      }
      if(!txt) return;
      try { if(ws && ws.readyState===1) { ws.send(JSON.stringify({message: txt})); } } catch(e) {}
      input.value='';
    });
    // Typing signal (debounced)
    var lastTyped = 0, typingSent = false, typingDebounce = null;
    function sendTyping(){ try{ if(ws && ws.readyState===1){ ws.send(JSON.stringify({type:'typing', action:'start'})); } }catch(_){ } }
    input.addEventListener('input', function(){
      var now = Date.now();
      if (!typingSent || (now - lastTyped) > 1500){ sendTyping(); typingSent = true; }
      lastTyped = now;
      if (typingDebounce) { try{ clearTimeout(typingDebounce); }catch(_){ } }
      typingDebounce = setTimeout(function(){ typingSent = false; }, 1600);
    });
    input.addEventListener('blur', function(){ typingSent = false; if (typingEl) typingEl.textContent=''; });

    // CSRF cookie helper
    function getCookie(name){
      try {
        var value = '; ' + document.cookie; var parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
      } catch(_){ }
      return '';
    }
  }

  function initConfirms(){
    // Attach a single delegated handler to capture clicks and submit events
    document.addEventListener('click', function(e){
      var el = e.target.closest('[data-confirm]');
      if(!el) return;
      var msg = el.getAttribute('data-confirm');
      if(!msg) return;
      try {
        var ok = window.confirm(msg);
        if(!ok){ e.preventDefault(); e.stopPropagation(); }
      } catch(_){}
    }, true);
    document.addEventListener('submit', function(e){
      var el = e.target.closest('[data-confirm]');
      if(!el) return;
      var msg = el.getAttribute('data-confirm');
      if(!msg) return;
      try {
        var ok = window.confirm(msg);
        if(!ok){ e.preventDefault(); e.stopPropagation(); }
      } catch(_){}
    }, true);
  }

  document.addEventListener('DOMContentLoaded', function(){
    initNotifications();
    initExplore();
    initNavToggle();
    initAccordion();
    initMaterials();
    initChat();
    initConfirms();
  });
})();
