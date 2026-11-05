// habitquest UI (vanilla JS, no build)
const $ = (s) => document.querySelector(s);
const api = (path, opts) => fetch(path, opts).then(async (r) => {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.status);
  return r.json();
});

// ---------- player bar ----------
function renderPlayer(player) {
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
      if (box.checked) {
        await api("/api/checkin", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ habit_id: h.id }) });
      } else {
        const today = new Date().toISOString().slice(0, 10);
        await api(`/api/checkin/${h.id}/${today}`, { method: "DELETE" });
      }
      load();
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
    list.appendChild(row);
  }
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
  renderPlayer(state.player);
  renderCategoryFilter();
  renderDay(state.habits);
  renderQuests(state.quests || [], state.habits);
  const earned = new Set(state.habits.flatMap((h) => h.achievements));
  renderHeatmap(await api("/api/heatmap?weeks=12"));
  renderStats(await api("/api/stats"), earned, (await api("/api/achievements")).all);
  renderShop(await api("/api/shop"));
  renderBadges((await api("/api/badges")).badges);
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
