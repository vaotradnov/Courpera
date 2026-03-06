/* Chat Drawer UI scaffold (CSP-safe). Progressive enhancement only. */
(function(){
  function ready(fn){ if(document.readyState!=='loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  function el(tag, cls){ var e=document.createElement(tag); if(cls) e.className=cls; return e; }
  function openDrawer(){
    var drawer = document.getElementById('chatDrawer');
    if(!drawer){
      drawer = el('div','chat-drawer'); drawer.id='chatDrawer';
      drawer.innerHTML = '<div class="chat-drawer__panel"><div class="chat-drawer__convos" id="chatConvos"><h4>Messages</h4><div class="muted">Coming soon</div></div><div class="chat-drawer__messages" id="chatMsgs"><h4>Conversation</h4><div class="muted">Select a conversation</div></div></div>';
      document.body.appendChild(drawer);
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
