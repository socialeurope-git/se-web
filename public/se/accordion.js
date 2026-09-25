/* Key Insights accordion: minimal replacement for the WordPress Interactivity script.
   Markup: .wp-block-accordion-item > .wp-block-accordion-heading > button.wp-block-accordion-heading__toggle ; .wp-block-accordion-panel[hidden] */
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.wp-block-accordion-heading__toggle'); if (!btn) return;
  var item = btn.closest('.wp-block-accordion-item'); if (!item) return;
  var panel = item.querySelector('.wp-block-accordion-panel'); var open = item.classList.toggle('is-open');
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  if (panel) { if (open) panel.removeAttribute('hidden'); else panel.setAttribute('hidden', 'until-found'); }
});
