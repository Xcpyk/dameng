/* 大梦 · 前端。无构建、无依赖。 */
(() => {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const LS = {
    core: "dm.coreOnly",
    theme: "dm.theme",
    mod: "dm.module",
    name: "dm.name",
    lang: "dm.lang",
  };

  const state = {
    bank: null,
    answers: {},
    moduleId: null,
    coreOnly: false,
    lang: "zh",
    ui: {},
    languages: [],
  };
  const timers = new Map();
  let toastTimer = null;

  const esc = (s) =>
    String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const charCount = (t) => (t || "").replace(/\s/g, "").length;
  const answered = (qid) => Boolean((state.answers[qid] || "").trim());

  function t(key, vars) {
    let s = state.ui && state.ui[key];
    if (typeof s !== "string") s = key;
    if (vars) {
      for (const k of Object.keys(vars)) {
        s = s.split(`{${k}}`).join(String(vars[k]));
      }
    }
    return s;
  }

  function currentLanguage() {
    return (
      state.languages.find((l) => l.code === state.lang) || {
        code: state.lang,
        name: state.lang,
      }
    );
  }

  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) {
      let msg = r.status;
      try { msg = (await r.json()).error || msg; } catch (_) {}
      throw new Error(msg);
    }
    return r.json();
  }

  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || r.status);
    return data;
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2800);
  }

  /* ---------- theme ---------- */
  function applyTheme() {
    const saved = localStorage.getItem(LS.theme);
    if (saved) document.documentElement.dataset.theme = saved;
    else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.dataset.theme = "dark";
    }
  }
  function toggleTheme() {
    const isDark = document.documentElement.dataset.theme === "dark";
    const next = isDark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(LS.theme, next);
  }

  /* ---------- i18n ---------- */
  function applyStaticI18n() {
    document.documentElement.lang = state.lang === "zh" ? "zh-CN" : state.lang;
    document.title = t("docTitle");
    for (const el of $$("[data-i18n]")) el.textContent = t(el.dataset.i18n);
    for (const el of $$("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);
    for (const el of $$("[data-i18n-placeholder]")) el.placeholder = t(el.dataset.i18nPlaceholder);
    for (const el of $$("[data-i18n-title]")) el.title = t(el.dataset.i18nTitle);
    for (const el of $$("[data-i18n-aria]")) el.setAttribute("aria-label", t(el.dataset.i18nAria));

    $("#coreBtn").textContent = state.coreOnly ? t("all") : t("core");
    const langBtn = $("#langBtn");
    langBtn.title = t("language");
    langBtn.setAttribute("aria-label", t("language"));
    $("#langLabel").textContent = currentLanguage().name;

    const nameInput = $("#exportName");
    if (nameInput && (!nameInput.value || ["我", "Me", "私", "나"].includes(nameInput.value))) {
      nameInput.value = localStorage.getItem(LS.name) || t("me");
    }
  }

  function renderLangMenu() {
    const menu = $("#langMenu");
    menu.innerHTML = state.languages
      .map(
        (l) => `<button type="button" class="lang-option${l.code === state.lang ? " active" : ""}"
          data-lang="${l.code}" role="option" aria-selected="${l.code === state.lang}">
          <span>${esc(l.name)}</span>
          <span class="lang-check">${l.code === state.lang ? "✓" : ""}</span>
        </button>`
      )
      .join("");
    $("#langLabel").textContent = currentLanguage().name;
  }

  function closeLangMenu() {
    $("#langMenu").hidden = true;
    $("#langBtn").setAttribute("aria-expanded", "false");
  }

  function toggleLangMenu() {
    const menu = $("#langMenu");
    menu.hidden = !menu.hidden;
    $("#langBtn").setAttribute("aria-expanded", String(!menu.hidden));
  }

  async function flushAll() {
    const qids = Array.from(timers.keys());
    if (!qids.length) return;
    const answers = {};
    for (const qid of qids) {
      clearTimeout(timers.get(qid));
      timers.delete(qid);
      answers[qid] = state.answers[qid] || "";
    }
    try {
      await postJSON("/api/answers", { answers });
    } catch (err) {
      toast(t("toastSaveFail", { msg: err.message }));
    }
  }

  async function setLanguage(code) {
    if (code === state.lang) {
      closeLangMenu();
      return;
    }
    if (!state.languages.some((l) => l.code === code)) return;
    const btn = $("#langBtn");
    btn.disabled = true;
    closeLangMenu();
    try {
      await flushAll();
      const bank = await getJSON(`/api/bank?lang=${encodeURIComponent(code)}`);
      state.bank = bank;
      state.ui = bank.ui || {};
      state.lang = bank.lang || code;
      state.languages = bank.languages || state.languages;
      localStorage.setItem(LS.lang, state.lang);
      const url = new URL(location.href);
      url.searchParams.set("lang", state.lang);
      history.replaceState(null, "", url);

      applyStaticI18n();
      renderLangMenu();
      renderHelp(bank.meta);
      renderNav();
      renderModule(state.moduleId, { scrollTop: true });
      $("#searchInput").value = "";
      $("#searchResults").hidden = true;
      $("#exportResult").hidden = true;
      $("#exportResult").innerHTML = "";
      updateChrome();
    } catch (err) {
      toast(t("errorLoad", { msg: err.message }));
    } finally {
      btn.disabled = false;
    }
  }

  /* ---------- stats ---------- */
  function moduleStats(m, coreOnly = state.coreOnly) {
    const qs = coreOnly ? m.questions.filter((q) => q.core) : m.questions;
    const a = qs.filter((q) => answered(q.full_id)).length;
    return { total: qs.length, answered: a };
  }

  function totalStats(coreOnly = state.coreOnly) {
    if (!state.bank) return { total: 0, answered: 0 };
    let total = 0, a = 0;
    for (const m of state.bank.modules) {
      const s = moduleStats(m, coreOnly);
      total += s.total;
      a += s.answered;
    }
    return { total, answered: a };
  }

  function totalChars() {
    return Object.values(state.answers).reduce((n, text) => n + charCount(text), 0);
  }

  /* ---------- chrome ---------- */
  function updateChrome() {
    if (!state.bank) return;
    const core = totalStats(true);
    const all = totalStats(false);
    const s = state.coreOnly ? core : all;
    const pct = s.total ? Math.round((s.answered / s.total) * 100) : 0;
    $("#progressLabel").textContent = state.coreOnly
      ? t("progressCore", { a: s.answered, b: s.total })
      : t("progressAll", { a: s.answered, b: s.total });
    $("#progressFill").style.width = pct + "%";
    $("#sideCount").textContent = t("progressCore", { a: core.answered, b: core.total });

    for (const btn of $$(".nav-item")) {
      const m = state.bank.modules.find((x) => x.id === btn.dataset.id);
      if (!m) continue;
      const ms = moduleStats(m);
      const ct = btn.querySelector(".ct");
      const bar = btn.querySelector(".nav-bar i");
      if (ct) ct.textContent = `${ms.answered}/${ms.total}`;
      if (bar) bar.style.width = ms.total ? `${(ms.answered / ms.total) * 100}%` : "0%";
      btn.classList.toggle("done", ms.total > 0 && ms.answered === ms.total);
    }

    const cov = $("#exportCoverage");
    if (cov) {
      cov.innerHTML = `<span>${esc(t("exportCoverageAnswered", { a: all.answered, b: all.total }))}</span>
        <span>${esc(t("exportCoverageCore", { a: core.answered, b: core.total }))}</span>
        <span>${esc(t("exportCoverageChars", { n: totalChars().toLocaleString() }))}</span>`;
    }
  }

  /* ---------- nav ---------- */
  function renderNav() {
    const nav = $("#nav");
    nav.innerHTML = state.bank.modules
      .map((m) => {
        const s = moduleStats(m);
        const pct = s.total ? (s.answered / s.total) * 100 : 0;
        const active = m.id === state.moduleId ? " active" : "";
        const done = s.total > 0 && s.answered === s.total ? " done" : "";
        return `<button class="nav-item${active}${done}" data-id="${m.id}" title="${esc(m.title)}">
          <span class="num">${m.id.slice(1)}</span>
          <span class="nm">${esc(m.title)}</span>
          <span class="ct">${s.answered}/${s.total}</span>
          <span class="nav-bar"><i style="width:${pct}%"></i></span>
        </button>`;
      })
      .join("");
  }

  function updateNavActive() {
    for (const btn of $$(".nav-item")) {
      btn.classList.toggle("active", btn.dataset.id === state.moduleId);
    }
  }

  /* ---------- module render ---------- */
  function renderModule(id, opts = {}) {
    const m =
      state.bank.modules.find((x) => x.id === id) || state.bank.modules[0];
    if (!m) return;
    state.moduleId = m.id;
    localStorage.setItem(LS.mod, m.id);

    const idx = state.bank.modules.indexOf(m) + 1;
    const all = m.questions;
    const qs = state.coreOnly ? all.filter((q) => q.core) : all;
    const s = moduleStats(m);
    const coreN = all.filter((q) => q.core).length;

    const content = $("#content");
    content.innerHTML = `
      <header class="module-head">
        <p class="eyebrow">${esc(
          t("chapterEyebrow", {
            id: m.id,
            n: String(idx).padStart(2, "0"),
            total: state.bank.modules.length,
          })
        )}</p>
        <h2>${esc(m.title)}</h2>
        <p class="module-sub">${esc(m.subtitle)}</p>
        <p class="module-why">${esc(m.why)}</p>
        <div class="module-meta">
          <span>${esc(t("suggested"))} <b>${esc(m.time)}</b></span>
          <span>${esc(t("coreCount", { n: coreN }))}</span>
          <span>${esc(t("thisChapter", { a: s.answered, b: s.total }))}</span>
          <span>${esc(t("allChars", { n: totalChars().toLocaleString() }))}</span>
        </div>
      </header>
      ${
        qs.map(renderQuestion).join("") ||
        `<div class="empty-filter">${esc(t("emptyCore"))}</div>`
      }
      <div class="module-foot">
        <span class="note">${esc(t("moduleNote"))}</span>
        <div style="display:flex;gap:8px">
          ${
            idx > 1
              ? `<button class="btn ghost" data-nav="${state.bank.modules[idx - 2].id}">${esc(t("prev"))}</button>`
              : ""
          }
          ${
            idx < state.bank.modules.length
              ? `<button class="btn" data-nav="${state.bank.modules[idx].id}">${esc(t("next"))}</button>`
              : ""
          }
        </div>
      </div>`;

    content.classList.remove("module-enter");
    void content.offsetWidth;
    content.classList.add("module-enter");

    for (const q of qs) {
      const ta = content.querySelector(`textarea[data-qid="${q.full_id}"]`);
      if (ta) {
        ta.value = state.answers[q.full_id] || "";
        autoGrow(ta);
      }
      if (q.type === "scale") initScale(q);
      updateCardCount(q.full_id);
      const has = answered(q.full_id);
      setCardStatus(
        q.full_id,
        has ? "saved" : "",
        has ? (q.type === "scale" ? t("selected") : t("saved")) : ""
      );
    }

    updateNavActive();
    updateChrome();
    if (opts.scrollTop !== false) window.scrollTo({ top: 0, behavior: "auto" });
    if (opts.focusQid) {
      requestAnimationFrame(() => {
        const card = content.querySelector(`[data-full-id="${opts.focusQid}"]`);
        if (!card) return;
        card.scrollIntoView({ block: "center", behavior: "auto" });
        const field = card.querySelector("textarea, input[type=range]");
        if (field) field.focus({ preventScroll: true });
      });
    }
  }

  function renderQuestion(q) {
    const num = q.id.replace(/^Q/, "");
    const probes = (q.probes || []).map((p) => `<li>${esc(p)}</li>`).join("");
    const hint = q.hint
      ? `<button class="hint-toggle" type="button" data-hint="${q.full_id}">${esc(t("hintShow"))}</button>
         <div class="q-hint" data-hint-box="${q.full_id}" hidden>
           <p>${esc(q.hint)}</p>
           ${probes ? `<details><summary>${esc(t("probes"))}</summary><ul>${probes}</ul></details>` : ""}
         </div>`
      : "";

    let field;
    if (q.type === "scale") {
      field = `<div class="scale-wrap" data-scale="${q.full_id}">
        <div class="scale-top">
          <div class="scale-read" data-read="${q.full_id}">—</div>
        </div>
        <input type="range" min="1" max="10" step="1" value="5" data-qid="${q.full_id}"
               aria-label="${esc(q.title)}" style="--pct:44%">
        <div class="scale-ticks">${[1,2,3,4,5,6,7,8,9,10].map((n) => `<span>${n}</span>`).join("")}</div>
        <div class="scale-labels"><span>${esc(q.left)}</span><span>${esc(q.right)}</span></div>
      </div>`;
    } else {
      field = `<div class="answer-wrap">
        <textarea class="answer" data-qid="${q.full_id}" rows="3" aria-label="${esc(q.title)}"
          placeholder="${esc(t("placeholder"))}"></textarea>
      </div>`;
    }

    return `<article class="q" data-full-id="${q.full_id}">
      <div class="q-head">
        <span class="q-num">${num}</span>
        <h3>${esc(q.title)}</h3>
        ${q.core ? `<span class="q-tag">${esc(t("questionCore"))}</span>` : ""}
      </div>
      <p class="q-prompt">${esc(q.prompt)}</p>
      ${field}
      <div class="q-foot">
        <span data-count="${q.full_id}">${esc(t("wordCount", { n: 0 }))}</span>
        ${hint}
        <span class="q-status" data-status-for="${q.full_id}"></span>
      </div>
    </article>`;
  }

  function initScale(q) {
    const rg = document.querySelector(`input[type=range][data-qid="${q.full_id}"]`);
    if (!rg) return;
    const has = answered(q.full_id);
    if (has) rg.value = Number(state.answers[q.full_id]) || 5;
    paintScale(q.full_id, has ? Number(rg.value) : null);
  }

  function paintScale(qid, value) {
    const read = document.querySelector(`[data-read="${qid}"]`);
    const rg = document.querySelector(`input[type=range][data-qid="${qid}"]`);
    if (!read || !rg) return;
    if (value == null) {
      read.innerHTML = "—";
    } else {
      read.innerHTML = `${value}<small>/ 10</small>`;
    }
    const pct = ((Number(rg.value) - 1) / 9) * 100;
    rg.style.setProperty("--pct", pct + "%");
  }

  function autoGrow(ta) {
    ta.style.height = "auto";
    ta.style.height = Math.min(Math.max(ta.scrollHeight + 2, 108), 640) + "px";
  }

  function updateCardCount(qid) {
    const el = document.querySelector(`[data-count="${qid}"]`);
    if (el) el.textContent = t("wordCount", { n: charCount(state.answers[qid]).toLocaleString() });
  }

  function setCardStatus(qid, stateName, text) {
    const el = document.querySelector(`[data-status-for="${qid}"]`);
    if (!el) return;
    el.dataset.state = stateName || "";
    el.textContent = text || "";
  }

  /* ---------- saving ---------- */
  function scheduleSave(qid) {
    clearTimeout(timers.get(qid));
    timers.set(qid, setTimeout(() => saveAnswer(qid), 700));
  }

  async function saveAnswer(qid) {
    clearTimeout(timers.get(qid));
    timers.delete(qid);
    setCardStatus(qid, "saving", t("saving"));
    try {
      await postJSON("/api/answers", { id: qid, text: state.answers[qid] || "" });
      setCardStatus(qid, "saved", answered(qid) ? t("saved") : "");
      updateChrome();
    } catch (err) {
      setCardStatus(qid, "error", t("saveError"));
      toast(t("toastSaveFail", { msg: err.message }));
    }
  }

  function flushPending() {
    const qids = Array.from(timers.keys());
    if (!qids.length) return;
    const answers = {};
    for (const qid of qids) answers[qid] = state.answers[qid] || "";
    try {
      navigator.sendBeacon(
        "/api/answers",
        new Blob([JSON.stringify({ answers })], { type: "application/json" })
      );
    } catch (_) {}
  }

  /* ---------- search ---------- */
  function bindSearch() {
    const input = $("#searchInput");
    const box = $("#searchResults");
    let timer = null;

    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const kw = input.value.trim().toLowerCase();
        if (!kw) {
          box.hidden = true;
          box.innerHTML = "";
          return;
        }
        const hits = [];
        for (const m of state.bank.modules) {
          for (const q of m.questions) {
            const hay = `${q.full_id} ${q.title} ${q.prompt} ${(q.tags || []).join(" ")}`.toLowerCase();
            if (hay.includes(kw)) hits.push({ m, q });
            if (hits.length >= 14) break;
          }
          if (hits.length >= 14) break;
        }
        box.innerHTML = hits.length
          ? hits
              .map(
                ({ m, q }) =>
                  `<button class="search-item" data-mod="${m.id}" data-q="${q.full_id}">
                    ${esc(q.title)}
                    <small>${m.id} ${esc(m.title)}${q.core ? " · " + esc(t("questionCore")) : ""}</small>
                  </button>`
              )
              .join("")
          : `<div class="search-empty">${esc(t("searchEmpty"))}</div>`;
        box.hidden = false;
      }, 120);
    });

    box.addEventListener("click", (e) => {
      const btn = e.target.closest(".search-item");
      if (!btn) return;
      const qid = btn.dataset.q;
      const m = state.bank.modules.find((x) => x.id === btn.dataset.mod);
      const q = m.questions.find((x) => x.full_id === qid);
      input.value = "";
      box.hidden = true;
      if (state.coreOnly && q && !q.core) {
        state.coreOnly = false;
        localStorage.setItem(LS.core, "0");
        $("#coreBtn").setAttribute("aria-pressed", "false");
        $("#coreBtn").textContent = t("core");
        renderNav();
      }
      renderModule(m.id, { scrollTop: false, focusQid: qid });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-wrap")) box.hidden = true;
    });
  }

  /* ---------- events ---------- */
  function bindSidebarScroll() {
    const sidebar = $("#sidebar");
    if (!sidebar) return;
    let timer = null;
    sidebar.addEventListener(
      "scroll",
      () => {
        sidebar.classList.add("is-scrolling");
        clearTimeout(timer);
        timer = setTimeout(() => sidebar.classList.remove("is-scrolling"), 850);
      },
      { passive: true }
    );
  }

  function bind() {
    bindSidebarScroll();
    $("#themeBtn").addEventListener("click", toggleTheme);

    $("#langBtn").addEventListener("click", (e) => {
      e.stopPropagation();
      toggleLangMenu();
    });
    $("#langMenu").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-lang]");
      if (!btn) return;
      await setLanguage(btn.dataset.lang);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".lang-wrap")) closeLangMenu();
    });

    $("#coreBtn").addEventListener("click", () => {
      state.coreOnly = !state.coreOnly;
      localStorage.setItem(LS.core, state.coreOnly ? "1" : "0");
      $("#coreBtn").setAttribute("aria-pressed", state.coreOnly ? "true" : "false");
      $("#coreBtn").textContent = state.coreOnly ? t("all") : t("core");
      renderNav();
      renderModule(state.moduleId, { scrollTop: true });
    });

    $("#nav").addEventListener("click", (e) => {
      const btn = e.target.closest(".nav-item");
      if (!btn) return;
      renderModule(btn.dataset.id, { scrollTop: true });
    });

    $("#content").addEventListener("input", (e) => {
      const ta = e.target.closest("textarea.answer");
      if (ta) {
        const qid = ta.dataset.qid;
        state.answers[qid] = ta.value;
        autoGrow(ta);
        updateCardCount(qid);
        setCardStatus(qid, "", ta.value.trim() ? t("unsaved") : "");
        scheduleSave(qid);
        updateChrome();
        return;
      }
      const rg = e.target.closest('input[type="range"][data-qid]');
      if (rg) {
        const qid = rg.dataset.qid;
        const v = Number(rg.value);
        state.answers[qid] = String(v);
        paintScale(qid, v);
        setCardStatus(qid, "", t("unsaved"));
        scheduleSave(qid);
        updateChrome();
      }
    });

    $("#content").addEventListener("click", (e) => {
      const hintBtn = e.target.closest(".hint-toggle");
      if (hintBtn) {
        const box = document.querySelector(`[data-hint-box="${hintBtn.dataset.hint}"]`);
        if (box) {
          box.hidden = !box.hidden;
          hintBtn.textContent = box.hidden ? t("hintShow") : t("hintHide");
        }
        return;
      }
      const navBtn = e.target.closest("[data-nav]");
      if (navBtn) renderModule(navBtn.dataset.nav, { scrollTop: true });
    });

    $("#content").addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        const ta = e.target.closest("textarea.answer");
        if (!ta) return;
        e.preventDefault();
        saveAnswer(ta.dataset.qid);
        const fields = $$("textarea.answer, input[type=range]", $("#content"));
        const i = fields.indexOf(ta);
        const next = fields[i + 1];
        if (next) next.focus({ preventScroll: true });
      }
    });

    document.addEventListener("click", (e) => {
      const closer = e.target.closest("[data-close]");
      if (closer) closeModal(closer.dataset.close);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeModal("exportModal");
        closeModal("helpModal");
        closeLangMenu();
      }
    });

    $("#brand").addEventListener("click", (e) => {
      e.preventDefault();
      renderModule(state.bank.modules[0].id, { scrollTop: true });
    });

    $("#helpBtn").addEventListener("click", () => {
      $("#helpModal").hidden = false;
    });
    $("#exportBtn").addEventListener("click", openExport);
    $("#doExport").addEventListener("click", doExport);
    $("#exportName").addEventListener("change", (e) => {
      localStorage.setItem(LS.name, e.target.value.trim() || t("me"));
    });

    window.addEventListener("beforeunload", flushPending);
    bindSearch();
  }

  function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  }

  /* ---------- export ---------- */
  function openExport() {
    if (!state.bank) return;
    $("#exportModal").hidden = false;
    $("#exportResult").hidden = true;
    $("#exportResult").innerHTML = "";
    updateChrome();
  }

  async function doExport() {
    const btn = $("#doExport");
    const result = $("#exportResult");
    const name = ($("#exportName").value || t("me")).trim() || t("me");
    localStorage.setItem(LS.name, name);
    btn.disabled = true;
    btn.textContent = t("exportGenerating");
    result.hidden = true;
    try {
      await flushAll();
      const data = await postJSON("/api/export", { name, lang: state.lang });
      const files = data.files
        .map((f) => {
          const key = "file" + f.kind.charAt(0).toUpperCase() + f.kind.slice(1);
          const translated = t(key);
          const label = translated === key ? f.label : translated;
          return `<div class="result-file">
            <span class="rf-label">${esc(label)}</span>
            <span>
              <a href="/api/download?path=${encodeURIComponent(f.path)}" download>${esc(t("download"))}</a>
              <button type="button" data-copy="${esc(f.path)}">${esc(t("copy"))}</button>
            </span>
            <span class="rf-path">${esc(f.path)}</span>
          </div>`;
        })
        .join("");
      const suggestions = `<ul class="export-suggestions">
        ${(data.suggestions || []).map((s) => `<li>${esc(s)}</li>`).join("")}
      </ul>`;
      result.innerHTML = `
        <div class="result-file" style="border-bottom:1px solid var(--line)">
          <span class="rf-label" style="color:var(--good)">${esc(t("exportDone"))}</span>
          <span></span>
          <span class="rf-path">${esc(data.dir)}</span>
        </div>
        ${files}
        <div class="export-next">${esc(t("exportNext"))}</div>
        ${suggestions}`;
      result.hidden = false;
      result.querySelectorAll("[data-copy]").forEach((b) => {
        b.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(b.dataset.copy);
            toast(t("copyOk"));
          } catch (_) {
            toast(t("copyFail"));
          }
        });
      });
      updateChrome();
    } catch (err) {
      result.innerHTML = `<p class="export-err">${esc(t("exportFail", { msg: err.message }))}</p>`;
      result.hidden = false;
    } finally {
      btn.disabled = false;
      btn.textContent = t("exportGenerate");
    }
  }

  /* ---------- help ---------- */
  function renderHelp(meta) {
    $("#helpRules").innerHTML = (meta.rules || [])
      .map((r) => `<li>${esc(r)}</li>`)
      .join("");
    $("#helpEthics").textContent = meta.ethics || "";
  }

  /* ---------- boot ---------- */
  async function boot() {
    applyTheme();
    bind();

    const savedLang = localStorage.getItem(LS.lang);
    const urlLang = new URLSearchParams(location.search).get("lang");
    const navLang = (navigator.language || "zh").slice(0, 2).toLowerCase();
    const initial =
      urlLang || savedLang || (["zh", "en", "ja", "ko"].includes(navLang) ? navLang : "zh");

    try {
      const [bank, ans] = await Promise.all([
        getJSON(`/api/bank?lang=${encodeURIComponent(initial)}`),
        getJSON("/api/answers"),
      ]);
      state.bank = bank;
      state.ui = bank.ui || {};
      state.lang = bank.lang || "zh";
      state.languages = bank.languages || [];
      state.answers = ans.answers || {};
      state.coreOnly = localStorage.getItem(LS.core) === "1";
      localStorage.setItem(LS.lang, state.lang);

      applyStaticI18n();
      renderLangMenu();
      renderHelp(bank.meta);
      $("#coreBtn").setAttribute("aria-pressed", state.coreOnly ? "true" : "false");
      $("#coreBtn").textContent = state.coreOnly ? t("all") : t("core");
      $("#exportName").value = localStorage.getItem(LS.name) || t("me");

      const savedMod = localStorage.getItem(LS.mod);
      const first = bank.modules[0]?.id;
      const target = bank.modules.some((m) => m.id === savedMod) ? savedMod : first;
      state.moduleId = target;

      renderNav();
      renderModule(target, { scrollTop: false });
      updateChrome();
    } catch (err) {
      const fallback = `打不开档案：${err.message}<br><br>请确认 python3 app.py 仍在运行，然后刷新页面。`;
      $("#content").innerHTML = `<div class="empty-filter">${fallback}</div>`;
    }
  }

  boot();
})();
