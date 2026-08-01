/**
 * lang-switch.js — English/Arabic switcher for the bilingual slimv docs.
 *
 * Build layout (from the Makefile):
 *   build/html/en/   ← English
 *   build/html/ar/   ← Arabic   (siblings under build/html/)
 *
 * Detects the current language from <html lang>, then injects a switcher into
 * the RTD sidebar pointing at the same page in the other-language build. Uses
 * Sphinx's data-content_root so it works at any page depth, over file:// or
 * http://.
 */
document.addEventListener("DOMContentLoaded", function () {
    var lang = document.documentElement.lang || "en";
    var other = lang === "ar" ? "en" : "ar";
    var contentRoot =
        document.documentElement.getAttribute("data-content_root") || "./";

    var href = window.location.href;
    var rootUrl = resolveUrl(href, contentRoot);          // .../html/<lang>/
    var pageRel = href.slice(rootUrl.length) || "index.html";
    var otherRoot = resolveUrl(rootUrl, "../" + other + "/");
    var otherUrl = otherRoot + pageRel;

    var linkText = lang === "ar" ? "English" : "العربية";
    var label = lang === "ar" ? "Switch to English" : "التبديل إلى العربية";

    var switcher = document.createElement("div");
    switcher.className = "lang-switcher";
    switcher.innerHTML =
        '<a href="' + otherUrl + '" title="' + label + '">' +
        '<span class="lang-switcher-icon">🌐</span> ' + linkText + "</a>";

    var sideSearch = document.querySelector(".wy-side-nav-search");
    if (sideSearch) {
        sideSearch.appendChild(switcher);
    }
});

/** Minimal relative-URL resolver (handles ./ , ../ , and nested ../). */
function resolveUrl(base, rel) {
    var a = base.split("/");
    a.pop(); // drop the current file component
    var parts = rel.split("/");
    for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        if (p === "" || p === ".") continue;
        if (p === "..") a.pop();
        else a.push(p);
    }
    return a.join("/") + "/";
}
