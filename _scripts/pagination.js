/*
  Client-side pagination for the Publications list.

  All citations are rendered at build time (good for SEO and for visitors with
  JS disabled) but we only display `pageSize` at a time. Year headings are
  hidden automatically when none of their citations are on the current page.
*/

(function () {
  const onLoad = () => {
    const container = document.getElementById("publications");
    const nav = document.getElementById("publications-pagination");
    if (!container || !nav) return;

    const pageSize = parseInt(container.dataset.pageSize, 10) || 20;

    const years = Array.from(container.querySelectorAll(":scope > h3"));
    const citations = Array.from(
      container.querySelectorAll(":scope > .citation-container")
    );

    if (citations.length <= pageSize) {
      nav.style.display = "none";
      return;
    }

    const totalPages = Math.ceil(citations.length / pageSize);
    let currentPage = 1;

    const renderPage = (page) => {
      currentPage = Math.min(Math.max(1, page), totalPages);
      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;

      citations.forEach((el, i) => {
        el.style.display = i >= start && i < end ? "" : "none";
      });

      // hide year headings whose citations are all off-page
      years.forEach((heading) => {
        let next = heading.nextElementSibling;
        let anyVisible = false;
        while (next && !next.matches("h3")) {
          if (
            next.matches(".citation-container") &&
            next.style.display !== "none"
          ) {
            anyVisible = true;
            break;
          }
          next = next.nextElementSibling;
        }
        heading.style.display = anyVisible ? "" : "none";
      });

      renderNav();
    };

    const makeButton = (label, page, { disabled, active, aria } = {}) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pagination-button";
      btn.innerHTML = label;
      if (active) btn.classList.add("is-active");
      if (disabled) {
        btn.disabled = true;
      } else {
        btn.addEventListener("click", () => {
          renderPage(page);
          container.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
      if (aria) btn.setAttribute("aria-label", aria);
      if (active) btn.setAttribute("aria-current", "page");
      return btn;
    };

    const makeEllipsis = () => {
      const span = document.createElement("span");
      span.className = "pagination-ellipsis";
      span.textContent = "…";
      span.setAttribute("aria-hidden", "true");
      return span;
    };

    /*
      Build a compact page list with ellipses:
      1 … (p-1) p (p+1) … last
      Always show first and last, plus a small window around the current page.
    */
    const computePageList = () => {
      const pages = new Set([1, totalPages]);
      for (let i = currentPage - 1; i <= currentPage + 1; i++) {
        if (i >= 1 && i <= totalPages) pages.add(i);
      }
      const sorted = Array.from(pages).sort((a, b) => a - b);
      const list = [];
      sorted.forEach((p, i) => {
        if (i > 0 && p - sorted[i - 1] > 1) list.push("…");
        list.push(p);
      });
      return list;
    };

    const renderNav = () => {
      nav.innerHTML = "";

      nav.appendChild(
        makeButton(
          '<i class="fa-solid fa-chevron-left"></i> Prev',
          currentPage - 1,
          { disabled: currentPage === 1, aria: "Previous page" }
        )
      );

      computePageList().forEach((item) => {
        if (item === "…") {
          nav.appendChild(makeEllipsis());
        } else {
          nav.appendChild(
            makeButton(String(item), item, {
              active: item === currentPage,
              aria: `Go to page ${item}`,
            })
          );
        }
      });

      nav.appendChild(
        makeButton(
          'Next <i class="fa-solid fa-chevron-right"></i>',
          currentPage + 1,
          { disabled: currentPage === totalPages, aria: "Next page" }
        )
      );
    };

    renderPage(1);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onLoad);
  } else {
    onLoad();
  }
})();
