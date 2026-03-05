// Live password strength checklist (mirrors server rules; UX only)
(function(){
  function bySel(sel){ return document.querySelector(sel); }
  function qsAll(sel){ return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function setRule(el, ok){ if(!el) return; el.classList.remove(ok? 'bad':'ok'); el.classList.add(ok? 'ok':'bad'); }
  function check(p){
    p = p || '';
    return {
      len: p.length >= 12,
      upper: /[A-Z]/.test(p),
      lower: /[a-z]/.test(p),
      digit: /[0-9]/.test(p),
      symbol: /[^A-Za-z0-9]/.test(p)
    };
  }
  function initFor(input){
    if(!input) return;
    var list = bySel('#pwChecklist');
    if(!list) return;
    function update(){
      var v = input.value || '';
      var st = check(v);
      setRule(list.querySelector('[data-rule="len"]'), st.len);
      setRule(list.querySelector('[data-rule="upper"]'), st.upper);
      setRule(list.querySelector('[data-rule="lower"]'), st.lower);
      setRule(list.querySelector('[data-rule="digit"]'), st.digit);
      setRule(list.querySelector('[data-rule="symbol"]'), st.symbol);
    }
    input.addEventListener('input', update);
    update();
  }
  document.addEventListener('DOMContentLoaded', function(){
    initFor(document.getElementById('id_password1'));
    initFor(document.getElementById('id_new_password1'));
  });
})();
