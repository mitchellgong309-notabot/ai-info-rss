/* 分类过滤 + 前端搜索（基于 search-index.json，标题/来源/分类子串匹配） */
(function () {
  "use strict";

  // 注册 Service Worker（PWA 离线阅读）。sw.js 位于站点根，
  // 通过 <link rel="manifest"> 的地址推导，兼容子路径部署（如 /ai-info-rss/）。
  if ("serviceWorker" in navigator) {
    var manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) {
      var swUrl = new URL("sw.js", manifestLink.href).href;
      navigator.serviceWorker.register(swUrl).catch(function (e) {
        console.warn("SW 注册失败:", e);
      });
    }
  }

  // 分类过滤
  var buttons = document.querySelectorAll(".filter-btn");
  if (buttons.length) {
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        buttons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        var cat = btn.dataset.filter;
        document.querySelectorAll(".item").forEach(function (el) {
          var show = cat === "all" || el.dataset.category === cat;
          el.classList.toggle("hidden", !show);
        });
        document.querySelectorAll(".date-group").forEach(function (g) {
          var any = g.querySelectorAll(".item:not(.hidden)").length > 0;
          g.classList.toggle("hidden", !any);
        });
      });
    });
  }

  // 搜索：回车跳转到第一条匹配结果
  var box = document.getElementById("search-box");
  if (!box) return;
  var root = location.pathname.indexOf("/articles/") !== -1 ? "../" : "";
  fetch(root + "search-index.json")
    .then(function (r) { return r.ok ? r.json() : []; })
    .then(function (index) {
      box.addEventListener("keydown", function (e) {
        if (e.key !== "Enter") return;
        var q = box.value.trim().toLowerCase();
        if (!q) return;
        var hit = index.find(function (it) {
          return (it.title + " " + it.source + " " + it.category).toLowerCase().includes(q);
        });
        if (hit) {
          location.href = root + "articles/" + hit.id + ".html";
        } else {
          box.classList.add("no-hit");
          setTimeout(function () { box.classList.remove("no-hit"); }, 600);
        }
      });
    })
    .catch(function () { /* 索引缺失时静默 */ });
})();
