/* ─── Microsoft Dev News Feed - App ─────────────────────────────── */

(function () {
  "use strict";

  // ─── State ──────────────────────────────────────────────────────
  var articles = [];
  var filteredArticles = [];
  var currentCategory = "all";
  var currentTimeFilter = "all";
  var currentSort = "date-desc";
  var searchQuery = "";
  var bookmarks = new Set();
  var showBookmarksOnly = false;
  var categories = {};

  // ─── Blog Tag Colors ────────────────────────────────────────────
  var COLORS = [
    { bg: "rgba(0, 120, 212, 0.15)", fg: "#58a6ff" },
    { bg: "rgba(99, 179, 237, 0.15)", fg: "#63b3ed" },
    { bg: "rgba(129, 140, 248, 0.15)", fg: "#818cf8" },
    { bg: "rgba(167, 139, 250, 0.15)", fg: "#a78bfa" },
    { bg: "rgba(192, 132, 252, 0.15)", fg: "#c084fc" },
    { bg: "rgba(244, 114, 182, 0.15)", fg: "#f472b6" },
    { bg: "rgba(251, 146, 60, 0.15)", fg: "#fb923c" },
    { bg: "rgba(250, 204, 21, 0.15)", fg: "#facc15" },
    { bg: "rgba(74, 222, 128, 0.15)", fg: "#4ade80" },
    { bg: "rgba(45, 212, 191, 0.15)", fg: "#2dd4bf" },
    { bg: "rgba(34, 211, 238, 0.15)", fg: "#22d3ee" },
    { bg: "rgba(56, 189, 248, 0.15)", fg: "#38bdf8" },
    { bg: "rgba(248, 113, 113, 0.15)", fg: "#f87171" },
    { bg: "rgba(253, 186, 116, 0.15)", fg: "#fdba74" },
    { bg: "rgba(134, 239, 172, 0.15)", fg: "#86efac" },
    { bg: "rgba(147, 197, 253, 0.15)", fg: "#93c5fd" },
    { bg: "rgba(196, 181, 253, 0.15)", fg: "#c4b5fd" },
    { bg: "rgba(249, 168, 212, 0.15)", fg: "#f9a8d4" },
    { bg: "rgba(253, 224, 71, 0.15)", fg: "#fde047" },
    { bg: "rgba(110, 231, 183, 0.15)", fg: "#6ee7b7" },
  ];

  var blogColorMap = {};
  var colorIndex = 0;

  function getBlogColor(blogid) {
    if (!blogColorMap[blogid]) {
      blogColorMap[blogid] = COLORS[colorIndex % COLORS.length];
      colorIndex++;
    }
    return blogColorMap[blogid];
  }

  // ─── Category Lookup ────────────────────────────────────────────
  var blogToCategory = {};

  function buildCategoryMap() {
    for (var cat in categories) {
      var blogs = categories[cat];
      for (var i = 0; i < blogs.length; i++) {
        blogToCategory[blogs[i]] = cat;
      }
    }
  }

  function getCategoryForBlog(blogid) {
    return blogToCategory[blogid] || "Other";
  }

  // ─── Date Helpers ───────────────────────────────────────────────
  function formatRelativeDate(isoStr) {
    if (!isoStr) return "";
    try {
      var d = new Date(isoStr);
      var now = new Date();
      var diff = now - d;
      var hours = Math.floor(diff / 3600000);
      var days = Math.floor(diff / 86400000);

      if (hours < 1) return "Just now";
      if (hours < 24) return hours + "h ago";
      if (days === 1) return "Yesterday";
      if (days < 7) return days + "d ago";
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch (e) {
      return "";
    }
  }

  function getDateGroup(isoStr) {
    if (!isoStr) return "Unknown";
    try {
      var d = new Date(isoStr);
      var now = new Date();
      var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var articleDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      var diff = Math.floor((today - articleDay) / 86400000);

      if (diff === 0) return "Today";
      if (diff === 1) return "Yesterday";
      if (diff < 7) return "This Week";
      if (diff < 14) return "Last Week";
      return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    } catch (e) {
      return "Unknown";
    }
  }

  function isWithinTimeFilter(isoStr, filter) {
    if (filter === "all") return true;
    if (!isoStr) return false;
    try {
      var d = new Date(isoStr);
      var now = new Date();
      var diff = now - d;

      switch (filter) {
        case "today": return diff < 86400000;
        case "week": return diff < 604800000;
        case "month": return diff < 2592000000;
        default: return true;
      }
    } catch (e) {
      return true;
    }
  }

  // ─── Bookmarks ──────────────────────────────────────────────────
  function loadBookmarks() {
    try {
      var saved = localStorage.getItem("msdevfeed-bookmarks");
      if (saved) {
        var arr = JSON.parse(saved);
        bookmarks = new Set(arr);
      }
    } catch (e) { /* ignore */ }
  }

  function saveBookmarks() {
    try {
      localStorage.setItem("msdevfeed-bookmarks", JSON.stringify(Array.from(bookmarks)));
    } catch (e) { /* ignore */ }
  }

  function toggleBookmark(link) {
    if (bookmarks.has(link)) {
      bookmarks.delete(link);
    } else {
      bookmarks.add(link);
    }
    saveBookmarks();
    renderArticles();
  }

  // ─── Theme ──────────────────────────────────────────────────────
  function loadTheme() {
    var saved = localStorage.getItem("msdevfeed-theme");
    if (saved) {
      document.documentElement.setAttribute("data-theme", saved);
    }
    updateThemeButton();
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme");
    var next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("msdevfeed-theme", next);
    updateThemeButton();
  }

  function updateThemeButton() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var theme = document.documentElement.getAttribute("data-theme");
    btn.textContent = theme === "light" ? "\u263E" : "\u2600";
    btn.title = theme === "light" ? "Switch to dark mode" : "Switch to light mode";
  }

  // ─── Escape HTML ────────────────────────────────────────────────
  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ─── Filtering ──────────────────────────────────────────────────
  function applyFilters() {
    filteredArticles = articles.filter(function (a) {
      // Category filter
      if (currentCategory !== "all") {
        var cat = getCategoryForBlog(a.blogid);
        if (cat !== currentCategory) return false;
      }

      // Time filter
      if (!isWithinTimeFilter(a.published, currentTimeFilter)) return false;

      // Search
      if (searchQuery) {
        var q = searchQuery.toLowerCase();
        var match =
          (a.title && a.title.toLowerCase().indexOf(q) !== -1) ||
          (a.summary && a.summary.toLowerCase().indexOf(q) !== -1) ||
          (a.blog && a.blog.toLowerCase().indexOf(q) !== -1) ||
          (a.author && a.author.toLowerCase().indexOf(q) !== -1);
        if (!match) return false;
      }

      // Bookmarks only
      if (showBookmarksOnly && !bookmarks.has(a.link)) return false;

      return true;
    });

    // Sort
    filteredArticles.sort(function (a, b) {
      switch (currentSort) {
        case "date-asc":
          return (a.published || "").localeCompare(b.published || "");
        case "blog":
          return (a.blog || "").localeCompare(b.blog || "");
        default: // date-desc
          return (b.published || "").localeCompare(a.published || "");
      }
    });

    renderArticles();
    updateResultsCount();
  }

  // ─── Render Category Pills ──────────────────────────────────────
  function renderCategoryPills() {
    var container = document.getElementById("category-filters");
    if (!container) return;

    // Count articles per category
    var counts = { all: articles.length };
    for (var i = 0; i < articles.length; i++) {
      var cat = getCategoryForBlog(articles[i].blogid);
      counts[cat] = (counts[cat] || 0) + 1;
    }

    var html = '<button class="category-pill active" data-category="all">' +
      'All <span class="pill-count">' + counts.all + '</span></button>';

    var catNames = Object.keys(categories);
    for (var j = 0; j < catNames.length; j++) {
      var name = catNames[j];
      var count = counts[name] || 0;
      if (count > 0) {
        html += '<button class="category-pill" data-category="' + escapeHtml(name) + '">' +
          escapeHtml(name) + ' <span class="pill-count">' + count + '</span></button>';
      }
    }

    container.innerHTML = html;

    // Bind clicks
    var pills = container.querySelectorAll(".category-pill");
    for (var k = 0; k < pills.length; k++) {
      pills[k].addEventListener("click", function () {
        var allPills = container.querySelectorAll(".category-pill");
        for (var m = 0; m < allPills.length; m++) {
          allPills[m].classList.remove("active");
        }
        this.classList.add("active");
        currentCategory = this.getAttribute("data-category");
        applyFilters();
      });
    }
  }

  // ─── Render Articles ────────────────────────────────────────────
  function renderArticles() {
    var container = document.getElementById("articles-container");
    var noResults = document.getElementById("no-results");
    if (!container) return;

    if (filteredArticles.length === 0) {
      container.innerHTML = "";
      if (noResults) noResults.style.display = "block";
      return;
    }

    if (noResults) noResults.style.display = "none";

    // Group by date
    var groups = {};
    var groupOrder = [];
    for (var i = 0; i < filteredArticles.length; i++) {
      var group = getDateGroup(filteredArticles[i].published);
      if (!groups[group]) {
        groups[group] = [];
        groupOrder.push(group);
      }
      groups[group].push(filteredArticles[i]);
    }

    var html = "";
    for (var g = 0; g < groupOrder.length; g++) {
      var groupName = groupOrder[g];
      var groupArticles = groups[groupName];

      html += '<div class="date-section fade-in">';
      html += '<h2 class="date-header">' + escapeHtml(groupName) + ' &middot; ' + groupArticles.length + ' articles</h2>';
      html += '<div class="articles-grid">';

      for (var j = 0; j < groupArticles.length; j++) {
        html += renderArticleCard(groupArticles[j]);
      }

      html += '</div></div>';
    }

    container.innerHTML = html;

    // Bind bookmark buttons
    var btns = container.querySelectorAll(".article-bookmark");
    for (var b = 0; b < btns.length; b++) {
      btns[b].addEventListener("click", function () {
        toggleBookmark(this.getAttribute("data-link"));
      });
    }
  }

  function renderArticleCard(article) {
    var color = getBlogColor(article.blogid);
    var isNew = false;
    try {
      isNew = (new Date() - new Date(article.published)) < 86400000;
    } catch (e) { /* ignore */ }

    var isBookmarked = bookmarks.has(article.link);
    var hasAiSummary = article.ai_summary === true;

    var card = '<div class="article-card">';

    // Top row: blog tag + badges
    card += '<div class="article-card-top">';
    card += '<span class="article-blog-tag" style="background:' + color.bg + ';color:' + color.fg + '">' +
      escapeHtml(article.blog) + '</span>';
    card += '<div style="display:flex;gap:0.375rem;align-items:center">';
    if (hasAiSummary) {
      card += '<span class="article-ai-badge">AI</span>';
    }
    if (isNew) {
      card += '<span class="article-new-badge">NEW</span>';
    }
    card += '</div></div>';

    // Title
    card += '<h3 class="article-title"><a href="' + escapeHtml(article.link) + '" target="_blank" rel="noopener">' +
      escapeHtml(article.title) + '</a></h3>';

    // Summary
    if (article.summary) {
      card += '<p class="article-summary">' + escapeHtml(article.summary) + '</p>';
    }

    // Footer
    card += '<div class="article-footer">';
    card += '<div class="article-meta">';
    card += '<span class="article-author">\u270D ' + escapeHtml(article.author) + '</span>';
    card += '<span class="article-date">' + formatRelativeDate(article.published) + '</span>';
    card += '</div>';
    card += '<button class="article-bookmark' + (isBookmarked ? ' active' : '') + '" data-link="' + escapeHtml(article.link) + '" title="Bookmark">' +
      (isBookmarked ? '\u2605' : '\u2606') + '</button>';
    card += '</div>';

    card += '</div>';
    return card;
  }

  // ─── Update Results Count ───────────────────────────────────────
  function updateResultsCount() {
    var el = document.getElementById("results-count");
    if (el) {
      el.textContent = filteredArticles.length + " of " + articles.length + " articles";
    }
  }

  // ─── Fetch Data ─────────────────────────────────────────────────
  function fetchFeeds() {
    var loading = document.getElementById("loading");
    if (loading) loading.style.display = "flex";

    fetch("data/feeds.json")
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to fetch feeds");
        return res.json();
      })
      .then(function (data) {
        articles = data.articles || [];
        categories = data.categories || {};

        buildCategoryMap();

        // Update header
        var lastUpdated = document.getElementById("last-updated");
        if (lastUpdated && data.lastupdated) {
          var d = new Date(data.lastupdated);
          lastUpdated.textContent = d.toLocaleDateString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit",
          });
        }

        var totalEl = document.getElementById("total-articles");
        if (totalEl) {
          totalEl.textContent = articles.length;
        }

        // Show digest
        if (data.digest) {
          var digestEl = document.getElementById("digest-text");
          var banner = document.getElementById("digest-banner");
          if (digestEl && banner) {
            digestEl.textContent = data.digest;
            banner.classList.add("visible");
          }
        }

        renderCategoryPills();
        applyFilters();

        if (loading) loading.style.display = "none";
      })
      .catch(function (err) {
        console.error("Error loading feeds:", err);
        if (loading) loading.style.display = "none";
        var container = document.getElementById("articles-container");
        if (container) {
          container.innerHTML = '<div class="no-results"><div class="no-results-icon">&#9888;</div>' +
            '<div class="no-results-text">Failed to load articles</div>' +
            '<div class="no-results-hint">Check the console for details</div></div>';
        }
      });
  }

  // ─── Event Bindings ─────────────────────────────────────────────
  function bindEvents() {
    // Search
    var searchInput = document.getElementById("search-input");
    if (searchInput) {
      var debounce;
      searchInput.addEventListener("input", function () {
        clearTimeout(debounce);
        debounce = setTimeout(function () {
          searchQuery = searchInput.value.trim();
          applyFilters();
        }, 200);
      });
    }

    // Time filter
    var timeSelect = document.getElementById("time-filter");
    if (timeSelect) {
      timeSelect.addEventListener("change", function () {
        currentTimeFilter = this.value;
        applyFilters();
      });
    }

    // Sort
    var sortSelect = document.getElementById("sort-select");
    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        currentSort = this.value;
        applyFilters();
      });
    }

    // Theme toggle
    var themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", toggleTheme);
    }

    // Bookmarks toggle
    var bookmarkBtn = document.getElementById("bookmarks-toggle");
    if (bookmarkBtn) {
      bookmarkBtn.addEventListener("click", function () {
        showBookmarksOnly = !showBookmarksOnly;
        this.classList.toggle("active", showBookmarksOnly);
        this.title = showBookmarksOnly ? "Show all articles" : "Show bookmarks only";
        applyFilters();
      });
    }
  }

  // ─── PWA Registration ──────────────────────────────────────────
  function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").then(function () {
        console.log("Service worker registered");
      }).catch(function (err) {
        console.log("Service worker registration failed:", err);
      });
    }
  }

  // ─── Init ───────────────────────────────────────────────────────
  function init() {
    loadTheme();
    loadBookmarks();
    bindEvents();
    registerServiceWorker();
    fetchFeeds();
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
