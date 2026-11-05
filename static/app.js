// habitquest UI (vanilla JS, no build)
const $ = (s) => document.querySelector(s);
const api = (path, opts) => fetch(path, opts).then(async (r) => {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.status);
  return r.json();
});

let settings = { sound: true, effects: true, hardcore: false };
let lastLevel = 1;

// ---------- sound & level-up effects (WebAudio + CSS, toggle in settings) ----------
let audioCtx = null;
function blip(freq = 660) {
  if (!settings.sound) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(freq * 1.5, audioCtx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.3);
  } catch (e) { /* audio unavailable — stay silent */ }
}

const CONFETTI_COLORS = ["#f5c542", "#ff7043", "#7bd88f", "#61afef", "#e5484d"];
function celebrate(level) {
  const overlay = $("#levelup");
  $("#levelup-text").textContent = `⭐ Рівень ${level}!`;
  overlay.classList.add("show");
  const colors = CONFETTI_COLORS;
  for (let i = 0; i < 40; i++) {
    const bit = document.createElement("span");
    bit.className = "confetti";
    bit.style.left = `${Math.random() * 100}vw`;
    bit.style.background = colors[i % colors.length];
    bit.style.animationDelay = `${Math.random() * 0.6}s`;
    bit.style.animationDuration = `${1.4 + Math.random() * 1.2}s`;
    bit.style.transform = `rotate(${Math.random() * 360}deg)`;
    overlay.appendChild(bit);
  }
  setTimeout(() => { overlay.classList.remove("show"); overlay.innerHTML = "<span id=\"levelup-text\"></span>"; }, 2600);
}

function renderSettings() {
  $("#settings").innerHTML = `
    <label><input type="checkbox" id="set-sound" ${settings.sound ? "checked" : ""}> 🔊 Звук чек-іну</label>
    <label><input type="checkbox" id="set-effects" ${settings.effects ? "checked" : ""}> ✨ Анімація рівня</label>
    <label title="Пропущений (не заморожений) день щоденної звички = −10 XP. Для дисципліни!"><input type="checkbox" id="set-hardcore" ${settings.hardcore ? "checked" : ""}> ☠ Хардкор: пропущений день = −10 XP</label>`;
  $("#set-sound").addEventListener("change", saveSetting);
  $("#set-effects").addEventListener("change", saveSetting);
  $("#set-hardcore").addEventListener("change", saveSetting);
}

async function saveSetting() {
  const patch = { sound: $("#set-sound").checked, effects: $("#set-effects").checked,
                  hardcore: $("#set-hardcore").checked };
  settings = await api("/api/settings", { method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings: patch }) });
}

// ---------- player bar ----------
function renderPlayer(player) {
  lastLevel = player.level;
  $("#level-badge").textContent = `Lv ${player.level}`;
  $("#xp-fill").style.width = `${Math.round(100 * player.xp_in_level / Math.max(1, player.xp_for_next))}%`;
  $("#xp-text").textContent = `${player.xp_in_level}/${player.xp_for_next} XP`;
}

// ---------- categories ----------
const CAT_LABELS = { health: "💚 Здоров'я", mind: "🧠 Розум", work: "💼 Робота", home: "🏠 Дім" };
let activeCategory = null;

function renderCategoryFilter() {
  const el = $("#cat-filter");
  const cats = ["health", "mind", "work", "home"];
  el.innerHTML = `<button class="cat ${activeCategory === null ? "active" : ""}" data-cat="">Усі</button>` +
    cats.map((c) => `<button class="cat ${activeCategory === c ? "active" : ""}" data-cat="${c}">${CAT_LABELS[c]}</button>`).join("");
  el.querySelectorAll("button.cat").forEach((b) =>
    b.addEventListener("click", () => { activeCategory = b.dataset.cat || null; load(); }));
}

// ---------- quote of the day (local JSON, deterministic per date) ----------
async function renderQuote() {
  const el = $("#quote-text");
  if (!el) return;
  try {
    const q = await api("/api/quote");
    el.textContent = `«${q.ua}»`;
    $("#quote-author").textContent = `— ${q.author}`;
  } catch (e) { el.textContent = e.message; }
}

// ---------- habit templates library (one-click add) ----------
function renderTemplates(templates) {
  const el = $("#templates");
  if (!el) return;
  el.innerHTML = templates.map((t) =>
    `<button class="tpl" data-tpl="${t.id}" title="${t.name_en} · ${CAT_LABELS[t.category]}">${t.icon} ${t.name_ua}</button>`
  ).join("");
  el.querySelectorAll("button.tpl").forEach((b) =>
    b.addEventListener("click", async () => {
      try {
        await api("/api/habits/from-template", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_id: b.dataset.tpl }) });
        blip();
        load();
      } catch (e) { alert(e.message); }
    }));
}

// ---------- day view ----------
function renderDay(habits) {
  const list = $("#day-list");
  list.innerHTML = "";
  for (const h of habits) {
    const row = document.createElement("div");
    row.className = "habit-row";
    const flame = h.done_today ? "🔥" : (h.streak > 0 ? "🔥" : "❄");
    const weeklyMeta = h.schedule === "weekly" ? ` · ${h.week_count}/${h.target_per_period} цього тижня` : "";
    row.innerHTML = `
      <span class="icon">${h.icon}</span>
      <span class="name">${h.name} <span class="cat-chip" title="Категорія">${CAT_LABELS[h.category] || ""}</span>${weeklyMeta}</span>
      <span class="streak">${flame} ${h.streak}</span>
      <span class="meta">${h.done_today ? "✅ зроблено" : "очікується"}</span>`;
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = h.done_today;
    box.addEventListener("change", async () => {
      const prevLevel = lastLevel;
      let created = false;
      if (box.checked) {
        const res = await api("/api/checkin", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ habit_id: h.id }) });
        created = res.created;
      } else {
        const today = new Date().toISOString().slice(0, 10);
        await api(`/api/checkin/${h.id}/${today}`, { method: "DELETE" });
      }
      if (created) blip();
      await load();
      if (created && settings.effects && lastLevel > prevLevel) celebrate(lastLevel);
    });
    row.prepend(box);
    if (!h.done_today && h.schedule === "daily") {
      const fz = document.createElement("button");
      fz.textContent = "❄ freeze";
      fz.title = "Заморозити сьогодні (1/тиждень)";
      fz.addEventListener("click", async () => {
        try { await api("/api/freeze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ habit_id: h.id }) }); load(); }
        catch (e) { alert(e.message); }
      });
      row.append(fz);
    }
    const del = document.createElement("button");
    del.textContent = "✕";
    del.addEventListener("click", async () => { await api(`/api/habits/${h.id}`, { method: "DELETE" }); load(); });
    row.append(del);
    const chartBtn = document.createElement("button");
    chartBtn.textContent = "📈";
    chartBtn.title = "Графік серії за 30 днів";
    chartBtn.addEventListener("click", async () => {
      let panel = row.nextElementSibling;
      if (panel && panel.classList.contains("streak-chart")) { panel.remove(); return; }
      panel = document.createElement("div");
      panel.className = "streak-chart";
      row.after(panel);
      panel.textContent = "…";
      try { panel.innerHTML = streakChartSVG(await api(`/api/habits/${h.id}/series?days=30`)); }
      catch (e) { panel.textContent = e.message; }
    });
    row.append(chartBtn);
    list.appendChild(row);
  }
}

// ---------- 30-day streak chart (SVG) ----------
function streakChartSVG(data) {
  const cell = 10, gap = 2, h = 46, labelW = 4;
  const w = labelW + data.series.length * (cell + gap);
  let svg = `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg" class="streak-svg">`;
  data.series.forEach((p, i) => {
    const x = labelW + i * (cell + gap);
    const filled = p.count > 0;
    const barH = filled ? h - 14 : 4;
    svg += `<rect x="${x}" y="${h - 14 - barH}" width="${cell}" height="${barH}" rx="2"
      fill="${filled ? "var(--ok)" : "#26263a"}"><title>${p.date}: ${filled ? "виконано" : "—"}</title></rect>`;
    if (i === data.series.length - 1) {
      svg += `<text x="${x - 8}" y="${h - 2}" font-size="8" class="wk-label">сьогодні</text>`;
    }
  });
  svg += `</svg><div class="streak-chart-meta">🔥 серія: <b>${data.streak}</b> · ${data.days} дн.</div>`;
  return svg;
}

// ---------- boss battle (monthly quests) ----------
function renderQuests(quests, habits) {
  const list = $("#quest-list");
  list.innerHTML = "";
  const select = $("#q-habit");
  select.innerHTML = habits.map((h) => `<option value="${h.id}">${h.icon} ${h.name}</option>`).join("");
  for (const q of quests) {
    const hpPct = Math.max(0, 100 - Math.round(100 * q.damage / q.hp));
    const row = document.createElement("div");
    row.className = "boss" + (q.completed ? " boss-down" : "");
    row.innerHTML = `
      <div class="boss-head">
        <span class="boss-face">${q.completed ? "💀" : "👹"}</span>
        <span class="name">${q.habit_icon} ${q.habit_name}</span>
        <span class="boss-hp-text">${q.completed ? "ПЕРЕМОЖЕНО!" : `HP ${Math.max(0, q.hp - q.damage)}/${q.hp}`}</span>
      </div>
      <div class="boss-hp"><div class="boss-hp-fill" style="width:${hpPct}%"></div></div>
      <div class="boss-meta">${q.progress}/${q.target} ударів · шкода ${q.damage}/${q.hp} · нагорода ${q.reward} XP</div>`;
    list.appendChild(row);
  }
}

// ---------- new quest ----------
$("#new-quest").addEventListener("submit", async (e) => {
  e.preventDefault();
  const habitId = parseInt($("#q-habit").value, 10);
  const target = parseInt($("#q-target").value, 10) || 12;
  try {
    await api("/api/quests", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habit_id: habitId, target }) });
    load();
  } catch (err) { alert(err.message); }
});

// ---------- dashboard (XP flow SVG + wallet + level) ----------
function renderDashboard(d) {
  const cell = 12, gap = 2, h = 70, labelW = 4;
  const w = labelW + d.xp_by_day.length * (cell + gap);
  const maxX = Math.max(1, ...d.xp_by_day.map((p) => Math.max(0, p.xp)));
  const minX = Math.min(0, ...d.xp_by_day.map((p) => p.xp));
  const zeroY = h - 12 - Math.round((0 - minX) / (maxX - minX) * (h - 18));
  let svg = `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg" class="dash-svg">`;
  svg += `<line x1="0" y1="${zeroY}" x2="${w}" y2="${zeroY}" stroke="#3a3a52" stroke-width="1"/>`;
  d.xp_by_day.forEach((p, i) => {
    const x = labelW + i * (cell + gap);
    const hh = Math.round(Math.abs(p.xp) / (maxX - minX) * (h - 18));
    if (p.xp === 0) return;
    const y = p.xp > 0 ? zeroY - hh : zeroY;
    const fill = p.xp > 0 ? "url(#dashGrad)" : "#e5484d";
    svg += `<rect x="${x}" y="${y}" width="${cell}" height="${Math.max(2, hh)}" rx="2" fill="${fill}"><title>${p.date}: ${p.xp > 0 ? "+" : ""}${p.xp} XP</title></rect>`;
  });
  svg += `<defs><linearGradient id="dashGrad" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="#f5c542"/><stop offset="100%" stop-color="#ff7043"/></linearGradient></defs>`;
  svg += `</svg>`;
  $("#dashboard").innerHTML = `
    <div class="dash-cards">
      <span class="dash-card">⭐ Рівень <b>${d.player.level}</b></span>
      <span class="dash-card">💰 Монети <b>${d.coins}</b></span>
      <span class="dash-card">🛡 Щити <b>${d.shields}</b></span>
      <span class="dash-card">📈 XP за 30 дн <b>+${d.xp_earned_30d}</b></span>
      <span class="dash-card">🧾 Чек-інів <b>${d.checkins_30d}</b>/30</span>
    </div>
    <div class="dash-chart">${svg}</div>`;
}

// ---------- weekly mini-quests (3 habits × N check-ins, coin reward) ----------
function fillHabitSelects(habits) {
  const options = habits.map((h) => `<option value="${h.id}">${h.icon} ${h.name}</option>`).join("");
  for (const id of ["#wq-h1", "#wq-h2", "#wq-h3"]) $(id).innerHTML = options;
}

function renderWeeklyQuests(quests) {
  const list = $("#weekly-quests");
  list.innerHTML = quests.length ? "" : "<div class='weekly-empty'>Ще немає квесту на цей тиждень.</div>";
  for (const q of quests) {
    const bars = q.habits.map((h) => {
      const pct = Math.min(100, Math.round(100 * h.done / q.target));
      return `<div class="wq-row" title="${h.name}: ${h.done}/${q.target}">
        <span class="wq-name">${h.icon} ${h.name}</span>
        <div class="wq-bar"><div style="width:${pct}%"></div></div>
        <span class="wq-count">${h.done}/${q.target}</span></div>`;
    }).join("");
    const row = document.createElement("div");
    row.className = "weekly-quest" + (q.completed ? " wq-done" : "");
    row.innerHTML = `
      <div class="wq-head"><span>${q.completed ? "🏆" : "📅"} ${q.week}</span>
        <span class="wq-reward">${q.completed ? "нагорода отримана" : `нагорода ${q.reward} 💰`}</span></div>
      ${bars}`;
    list.appendChild(row);
  }
}

$("#new-weekly-quest").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ids = [parseInt($("#wq-h1").value, 10), parseInt($("#wq-h2").value, 10), parseInt($("#wq-h3").value, 10)];
  const target = parseInt($("#wq-target").value, 10) || 5;
  try {
    await api("/api/weekly-quests", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habit_ids: ids, target }) });
    load();
  } catch (err) { alert(err.message); }
});

// ---------- week heatmap (SVG) ----------
function renderHeatmap(grid) {
  const cell = 18, gap = 3, labelW = 46;
  const w = labelW + grid.weeks.length * (cell + gap), h = 7 * (cell + gap) + 14;
  let svg = `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">`;
  ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"].forEach((d, i) => {
    svg += `<text x="0" y="${i * (cell + gap) + 14}" font-size="9" class="wk-label">${d}</text>`;
  });
  grid.weeks.forEach((monday, wi) => {
    const counts = grid.cells[monday] || [];
    counts.forEach((c, di) => {
      const x = labelW + wi * (cell + gap), y = di * (cell + gap);
      const fill = c ? "#7bd88f" : "#26263a";
      const day = new Date(monday); day.setDate(day.getDate() + di);
      svg += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="3" fill="${fill}"><title>${day.toISOString().slice(0, 10)}: ${c ? "виконано" : "—"}</title></rect>`;
    });
  });
  svg += "</svg>";
  $("#week-heatmap").innerHTML = svg;
}

// ---------- monthly recap ----------
function renderRecap(r) {
  const maxWeek = Math.max(1, ...r.weeks.map((w) => w.count));
  const cats = Object.entries(r.per_category)
    .map(([k, v]) => v.checkins
      ? `${CAT_LABELS[k]}: <b>${v.checkins}</b> (${v.share}%, ${v.xp} XP)`
      : `${CAT_LABELS[k]}: —`)
    .join(" · ");
  const bars = r.weeks.map((w) =>
    `<div class="rbar" title="${w.week}: ${w.count}"><div style="height:${Math.round(100 * w.count / maxWeek)}%"></div><span>${w.week.slice(5)}</span></div>`).join("");
  $("#recap").innerHTML = `
    <div class="recap-grid">
      <div>🧾 Чек-інів: <b>${r.checkins}</b> (${r.active_days} активних дн.)</div>
      <div>🔥 Найдовша серія: <b>${r.longest_streak}</b> дн.</div>
      <div>⭐ XP зароблено: <b>${r.xp_earned}</b> · витрачено: <b>${r.xp_spent}</b></div>
      <div>👹 Босів переможено: <b>${r.quests_won}/${r.quests_total}</b></div>
      <div>📅 Найкращий день: <b>${r.best_day || "—"}</b>${r.best_day ? ` (${r.best_day_checkins} чек-інів)` : ""}</div>
      <div>За категоріями: ${cats}</div>
    </div>
    <div class="recap-bars">${bars}</div>
    ${r.top_habits.length ? `<div class="recap-top">Топ: ${r.top_habits.filter((h) => h.checkins).slice(0, 3).map((h) => `${h.icon} ${h.name} (${h.checkins})`).join(", ") || "—"}</div>` : ""}`;
}

async function loadRecap(month) {
  try { renderRecap(await api(`/api/recap${month ? `?month=${month}` : ""}`)); }
  catch (e) { $("#recap").textContent = e.message; }
}

$("#recap-load").addEventListener("click", () => loadRecap($("#recap-month").value));

// ---------- streak shield shop ----------
function renderShop(shop) {
  $("#shop").innerHTML = `
    <div class="shop-line">💰 Монети: <b>${shop.coins}</b> · 🛡 Щити: <b>${shop.shields}</b>
      <button id="btn-buy-shield" title="${shop.shield_effect}">Купити щит (${shop.shield_price} 💰)</button></div>`;
  $("#btn-buy-shield").addEventListener("click", async () => {
    try { await api("/api/shop/buy", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ item: "shield", qty: 1 }) }); load(); }
    catch (e) { alert(e.message); }
  });
}

// ---------- achievements editor (achievements.json UI) ----------
let editorEditId = null;  // non-null → the form edits an existing definition

function renderAchvEditor(defs) {
  $("#achv-editor-list").innerHTML = defs.map((d) =>
    `<span class="achv">${d.name} <button class="achv-edit" data-id="${d.id}" title="Редагувати">✎</button></span>`).join("");
  document.querySelectorAll(".achv-edit").forEach((b) =>
    b.addEventListener("click", () => {
      const d = defs.find((x) => x.id === b.dataset.id);
      editorEditId = d.id;
      $("#a-id").value = d.id;
      $("#a-name").value = d.name;
      $("#a-desc").value = d.description;
      $("#a-metric").value = d.metric;
      $("#a-threshold").value = d.threshold;
      $("#a-submit").textContent = "Зберегти";
    }));
}

function resetAchvForm() {
  editorEditId = null;
  $("#achv-form").reset();
  $("#a-threshold").value = 10;
  $("#a-submit").textContent = "Додати";
}

$("#achv-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = JSON.stringify({
    id: $("#a-id").value.trim(),
    name: $("#a-name").value.trim(),
    description: $("#a-desc").value.trim(),
    metric: $("#a-metric").value,
    threshold: parseInt($("#a-threshold").value, 10) || 1,
  });
  const opts = { method: editorEditId ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body };
  const url = editorEditId ? `/api/achievements/${encodeURIComponent(editorEditId)}` : "/api/achievements";
  try {
    await api(url, opts);
    resetAchvForm();
    load();
  } catch (err) { alert(err.message); }
});

// ---------- stats & achievements (definitions come from JSON) ----------
function renderStats(stats, earnedIds, defs) {
  $("#stats").innerHTML = `
    <div>🔥 Найдовша серія: <b>${stats.longest_streak}</b> дн.</div>
    <div>📈 Виконання за 30 днів: <b>${Math.round(stats.completion_rate_30d * 100)}%</b></div>
    <div>🧾 Усього чек-інів: <b>${stats.total_checkins}</b></div>`;
  $("#achievements").innerHTML = defs.map((d) =>
    `<span class="achv ${earnedIds.has(d.id) ? "" : "locked"}" title="${d.description}">${d.name}</span>`).join("");
}

// ---------- new habit ----------
$("#new-habit").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/habits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: $("#h-name").value,
      icon: $("#h-icon").value || "✅",
      schedule: $("#h-schedule").value,
      target_per_period: parseInt($("#h-target").value, 10) || 1,
      category: $("#h-category").value,
    }),
  });
  $("#h-name").value = "";
  load();
});

// ---------- export / import ----------
$("#btn-export").addEventListener("click", () => { location.href = "/api/export"; });
$("#import-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const data = JSON.parse(await file.text());
  await api("/api/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
  load();
});

// ---------- load ----------
async function load() {
  const state = await api("/api/state" + (activeCategory ? `?category=${activeCategory}` : ""));
  settings = state.settings || settings;
  renderPlayer(state.player);
  renderSettings();
  renderCategoryFilter();
  renderQuote();
  renderTemplates(await api("/api/templates"));
  renderDay(state.habits);
  renderQuests(state.quests || [], state.habits);
  fillHabitSelects(state.habits);
  renderWeeklyQuests(state.weekly_quests || []);
  renderDashboard(await api("/api/dashboard"));
  const earned = new Set(state.habits.flatMap((h) => h.achievements));
  renderHeatmap(await api("/api/heatmap?weeks=12"));
  const defs = (await api("/api/achievements")).all;
  renderStats(await api("/api/stats"), earned, defs);
  renderAchvEditor(defs);
  renderShop(await api("/api/shop"));
  renderBadges((await api("/api/badges")).badges);
  loadRecap($("#recap-month").value);
}

function renderBadges(badges) {
  $("#badges").innerHTML = badges.length
    ? badges.map((b) => `<span class="achv badge">${b.label}</span>`).join("")
    : "";
}

// ---------- PWA ----------
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {}); // offline shell
}

load();
