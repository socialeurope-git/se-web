// Header search bar toggle (Snippet "se-search-bar" of the WordPress site, unchanged)
(function () {
  var form = document.getElementById("se-search-bar");
  if (!form) return;
  var input = form.querySelector("[data-se-search-input]");
  var btns = Array.prototype.slice.call(document.querySelectorAll("[data-se-search-toggle]"));
  function set(open, focusBtn) {
    form.hidden = !open;
    btns.forEach(function (b) { b.setAttribute("aria-expanded", open ? "true" : "false"); });
    if (open) input.focus(); else if (focusBtn) focusBtn.focus();
  }
  var opener = null; // the trigger that opened the row gets focus back on Escape (desktop and mobile bars both carry one)
  btns.forEach(function (b) {
    b.addEventListener("click", function (e) { e.preventDefault(); opener = b; set(form.hidden, b); });
  });
  form.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    set(false, opener || btns.filter(function (b) { return b.offsetParent !== null; })[0] || btns[0]);
  });
  form.addEventListener("submit", function (e) { if (!input.value.trim()) e.preventDefault(); });
})();
