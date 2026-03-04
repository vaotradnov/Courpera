/* Small form/init helpers (CSP-safe) */
(function () {
  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function initSubjectToggle() {
    var subjectSel = document.getElementById('id_subject_choice');
    var wrap = document.getElementById('new-subject-wrap');
    var input = document.getElementById('id_new_subject');
    if (!subjectSel || !wrap || !input) return;

    function update() {
      var isOther = subjectSel.value === '__other__';
      // If prefilled value exists, show as well
      if (input.value && input.value.trim() && subjectSel.value !== input.value) {
        isOther = true;
      }
      wrap.classList.toggle('hidden', !isOther);
      input.disabled = !isOther;
      if (isOther) { input.focus(); }
    }
    subjectSel.addEventListener('change', update);
    update();
  }

  function focusQuizInputs() {
    // Focus add-choice input if present
    var addChoiceForm = document.querySelector('form input[name="action"][value="add_choice"]');
    if (addChoiceForm && addChoiceForm.form) {
      var choiceText = addChoiceForm.form.querySelector('input[type="text"], textarea');
      if (choiceText) {
        try { choiceText.focus(); choiceText.select && choiceText.select(); } catch (e) {}
      }
    }
    // Focus add-question input if present
    var addQForm = document.querySelector('form input[name="action"][value="add_question"]');
    if (addQForm && addQForm.form) {
      var qText = addQForm.form.querySelector('textarea, input[type="text"]');
      if (qText) {
        try { qText.focus(); qText.select && qText.select(); } catch (e) {}
      }
    }
  }

  onReady(function () {
    initSubjectToggle();
    focusQuizInputs();
  });
})();

