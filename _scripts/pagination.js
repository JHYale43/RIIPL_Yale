/*
  Client-side pagination for the Publications list.

  All citations are rendered at build time (good for SEO and for visitors with
  JS disabled) but we only display `pageSize` at a time. Year headings are
  hidden automatically when none of their citations are on the current page.
*/

(function () {
  function init() {
    var container = document.getElementById("publications-list");
    var nav = document.getElementById("publications-pagination");
    if (!container || !nav) return;

    var pageSize = parseInt(container.getAttribute("data-page-size"), 10) || 20;

    // Collect direct children by iterating — avoids any :scope/querySelector
    // quirks and also works even if intermediate text nodes exist.
    var years = [];
    var citations = [];
    var child = container.firstElementChild;
    while (child) {
      if (child.tagName === "H3") {
        years.push(child);
      } else if (child.classList && child.classList.contains("citation-container")) {
        citations.push(child);
      }
      child = child.nextElementSibling;
    }

    if (citations.length === 0) return;
    if (citations.length <= pageSize) {
      nav.style.display = "none";
      return;
    }

    var totalPages = Math.ceil(citations.length / pageSize);
    var currentPage = 1;

    function renderPage(page) {
      currentPage = Math.min(Math.max(1, page), totalPages);
      var start = (currentPage - 1) * pageSize;
      var end = start + pageSize;

      for (var i = 0; i < citations.length; i++) {
        citations[i].style.display = i >= start && i < end ? "" : "none";
      }

      // Hide year headings whose citations are all off the current page.
      for (var j = 0; j < years.length; j++) {
        var heading = years[j];
        var next = heading.nextElementSibling;
        var anyVisible = false;
        while (next && next.tagName !== "H3") {
          if (
            next.classList &&
            next.classList.contains("citation-container") &&
            next.style.display !== "none"
          ) {
            anyVisible = true;
            break;
          }
          next = next.nextElementSibling;
        }
        heading.style.display = anyVisible ? "" : "none";
      }

      renderNav();
    }

    function makeButton(label, page, opts) {
      opts = opts || {};
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pagination-button";
      btn.innerHTML = label;
      if (opts.active) btn.classList.add("is-active");
      if (opts.disabled) {
        btn.disabled = true;
      } else {
        btn.addEventListener("click", function () {
          renderPage(page);
          container.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
      if (opts.aria) btn.setAttribute("aria-label", opts.aria);
      if (opts.active) btn.setAttribute("aria-current", "page");
      return btn;
    }

    function makeEllipsis() {
      var span = document.createElement("span");
      span.className = "pagination-ellipsis";
      span.textContent = "\u2026";
      span.setAttribute("aria-hidden", "true");
      return span;
    }

    function computePageList() {
      var pages = {};
      pages[1] = true;
      pages[totalPages] = true;
      for (var i = currentPage - 1; i <= currentPage + 1; i++) {
        if (i >= 1 && i <= totalPages) pages[i] = true;
      }
      var sorted = Object.keys(pages)
        .map(function (p) { return parseInt(p, 10); })
        .sort(function (a, b) { return a - b; });
      var list = [];
      for (var k = 0; k < sorted.length; k++) {
        if (k > 0 && sorted[k] - sorted[k - 1] > 1) list.push("\u2026");
        list.push(sorted[k]);
      }
      return list;
    }

    function renderNav() {
      nav.innerHTML = "";
      nav.style.display = "";

      nav.appendChild(
        makeButton(
          '<i class="fa-solid fa-chevron-left"></i> Prev',
          currentPage - 1,
          { disabled: currentPage === 1, aria: "Previous page" }
        )
      );

      var list = computePageList();
      for (var i = 0; i < list.length; i++) {
        var item = list[i];
        if (item === "\u2026") {
          nav.appendChild(makeEllipsis());
        } else {
          nav.appendChild(
            makeButton(String(item), item, {
              active: item === currentPage,
              aria: "Go to page " + item
            })
          );
        }
      }

      nav.appendChild(
        makeButton(
          'Next <i class="fa-solid fa-chevron-right"></i>',
          currentPage + 1,
          { disabled: currentPage === totalPages, aria: "Next page" }
        )
      );
    }

    renderPage(1);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
