// ── Player data loaded from players.js (2020–2026)
// PLAYER_DATA is defined in /static/players.js

function lookupPlayer(name) {
  const q = (name || "").toLowerCase();
  return PLAYER_DATA.find(p => p.name.toLowerCase() === q) || null;
}

// ── Autocomplete ───────────────────────────────────────────────────────────

const POS_MAP = {
  OT: "OL", G: "OL", C: "OL", FB: "OL",
  DL: "DE", EDGE: "DE",
  SAF: "S", DB: "S"
};

function mapPosition(csvPos) {
  if (!csvPos) return null;
  const p = csvPos.trim().toUpperCase();
  return POS_MAP[p] !== undefined ? POS_MAP[p] : p;
}

function initAutocomplete(inputEl, posSelectId) {
  const container = document.createElement("div");
  container.style.position = "relative";
  inputEl.parentNode.insertBefore(container, inputEl);
  container.appendChild(inputEl);

  const dropdown = document.createElement("ul");
  dropdown.className = "autocomplete-dropdown";
  container.appendChild(dropdown);

  let activeIndex = -1;

  function fillPosition(playerName) {
    if (!posSelectId) return;
    const sel = document.getElementById(posSelectId);
    if (!sel) return;
    const player = lookupPlayer(playerName);
    if (!player) return;
    const mapped = mapPosition(player.pos);
    if (!mapped) return;
    const valid = Array.from(sel.options).some(o => o.value === mapped);
    if (valid) sel.value = mapped;
  }

  function highlightMatch(name, query) {
    const idx = name.toLowerCase().indexOf(query);
    if (idx === -1) return escHtml(name);
    return escHtml(name.slice(0, idx)) +
      `<mark>${escHtml(name.slice(idx, idx + query.length))}</mark>` +
      escHtml(name.slice(idx + query.length));
  }

  function showSuggestions(query) {
    const q = query.toLowerCase();
    const matches = q.length < 2
      ? []
      : PLAYER_DATA.filter(p => p.name.toLowerCase().includes(q)).slice(0, 8);

    activeIndex = -1;
    if (matches.length === 0) { dropdown.style.display = "none"; return; }

    dropdown.innerHTML = matches.map(p => `
      <li class="autocomplete-item" data-name="${escHtml(p.name)}">
        <span class="ac-name">${highlightMatch(p.name, q)}</span>
        <span class="ac-meta">${escHtml(mapPosition(p.pos) || p.pos)} &middot; ${escHtml(p.school)}</span>
      </li>`).join("");
    dropdown.style.display = "block";

    dropdown.querySelectorAll(".autocomplete-item").forEach(item => {
      item.addEventListener("mousedown", e => {
        e.preventDefault();
        inputEl.value = item.dataset.name;
        fillPosition(item.dataset.name);
        dropdown.style.display = "none";
      });
    });
  }

  inputEl.addEventListener("input", () => showSuggestions(inputEl.value.trim()));

  inputEl.addEventListener("keydown", e => {
    const items = dropdown.querySelectorAll(".autocomplete-item");
    if (!items.length || dropdown.style.display === "none") return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      items.forEach((item, i) => item.classList.toggle("active", i === activeIndex));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, -1);
      items.forEach((item, i) => item.classList.toggle("active", i === activeIndex));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      const name = items[activeIndex].dataset.name;
      inputEl.value = name;
      fillPosition(name);
      dropdown.style.display = "none";
    } else if (e.key === "Escape") {
      dropdown.style.display = "none";
    }
  });

  inputEl.addEventListener("blur", () => {
    setTimeout(() => { dropdown.style.display = "none"; }, 150);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const AC_CONFIG = [
    ["grade-name",    "grade-position"],
    ["compare-name1", "compare-pos1"],
    ["compare-name2", "compare-pos2"],
  ];
  AC_CONFIG.forEach(([inputId, selectId]) => {
    const el = document.getElementById(inputId);
    if (el) initAutocomplete(el, selectId);
  });
});

// ── Tab switching ──────────────────────────────────────────────────────────

function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(p => p.style.display = "none");
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("pane-" + tabName).style.display = "block";
  document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

  // Clear results and errors when switching tabs
  ["grade", "compare", "create"].forEach(t => {
    const el = document.getElementById("result-" + t);
    if (el) { el.innerHTML = ""; el.style.display = "none"; }
  });
}

// ── API call wrapper ───────────────────────────────────────────────────────

async function callAPI(endpoint, body) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!data.ok) throw new Error(data.error);
  return data.data;
}

// ── Loading state ──────────────────────────────────────────────────────────

function setLoading(buttonEl, resultEl, isLoading, message = "") {
  buttonEl.disabled = isLoading;
  buttonEl.textContent = isLoading ? "Loading..." : buttonEl.dataset.originalText;
  if (isLoading) {
    resultEl.innerHTML = `<div class="loading-msg">${message}</div>`;
    resultEl.style.display = "block";
  }
}

// ── Error display ──────────────────────────────────────────────────────────

function showError(containerEl, message) {
  containerEl.innerHTML = `<div class="error-box">&#9888; ${message}</div>`;
  containerEl.style.display = "block";
}

// ── Grade badge helpers ────────────────────────────────────────────────────

function gradeClass(grade) {
  if (!grade) return "grade-d";
  if (grade.startsWith("A")) return "grade-a";
  if (grade.startsWith("B")) return "grade-b";
  if (grade.startsWith("C")) return "grade-c";
  return "grade-d";
}

function gradeBadgeHTML(grade, score) {
  const cls = gradeClass(grade);
  const scoreStr = score != null ? `<span class="score-label">${score}/100</span>` : "";
  return `<div class="grade-badge ${cls}">${escHtml(grade)}${scoreStr}</div>`;
}

// ── Utility ────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function swListHTML(items, cls) {
  if (!items || items.length === 0) return "";
  const lis = items.map(s => `<li>${escHtml(s)}</li>`).join("");
  return `<ul class="sw-list ${cls}">${lis}</ul>`;
}

// ── Render: Player Grade ───────────────────────────────────────────────────

function renderGrade(data, containerEl) {
  const title = [data.player_name, data.position].filter(Boolean).map(escHtml).join(" — ");
  const playerInfo = lookupPlayer(data.player_name);
  const schoolLine = playerInfo ? `<div class="result-school">${escHtml(playerInfo.school)}</div>` : "";
  const warning = data.data_warning
    ? `<div class="data-warning">&#9888; ${escHtml(data.data_warning)}</div>`
    : "";

  containerEl.innerHTML = `
    <div class="result-card">
      <h2>${title}</h2>
      ${schoolLine}
      ${gradeBadgeHTML(data.grade, data.score)}
      <div class="sw-section">
        <div class="sw-label">Strengths</div>
        ${swListHTML(data.strengths, "strengths")}
      </div>
      <div class="sw-section">
        <div class="sw-label">Weaknesses</div>
        ${swListHTML(data.weaknesses, "weaknesses")}
      </div>
      ${data.justification ? `<div class="justification">${escHtml(data.justification)}</div>` : ""}
      ${warning}
    </div>`;
  containerEl.style.display = "block";
}

// ── Render: Compare Players ────────────────────────────────────────────────

function renderCompare(data, containerEl) {
  const p1 = data.player1 || {};
  const p2 = data.player2 || {};

  function playerCardHTML(p) {
    const title = [p.name, p.position].filter(Boolean).map(escHtml).join(" — ");
    const info = lookupPlayer(p.name);
    const schoolLine = info ? `<div class="result-school">${escHtml(info.school)}</div>` : "";
    return `
      <div class="compare-card">
        <h3>${title}</h3>
        ${schoolLine}
        ${gradeBadgeHTML(p.grade, p.score)}
        <div class="sw-section">
          <div class="sw-label">Strengths</div>
          ${swListHTML(p.strengths, "strengths")}
        </div>
        <div class="sw-section">
          <div class="sw-label">Weaknesses</div>
          ${swListHTML(p.weaknesses, "weaknesses")}
        </div>
      </div>`;
  }

  let h2hHTML = "";
  if (data.head_to_head && data.head_to_head.length > 0) {
    const rows = data.head_to_head.map(row => {
      const v1 = escHtml(row.player1_val != null ? row.player1_val : "N/A");
      const v2 = escHtml(row.player2_val != null ? row.player2_val : "N/A");
      let winnerCell = "";
      const w = (row.winner || "").toLowerCase();
      const p1name = (p1.name || "").toLowerCase();
      const p2name = (p2.name || "").toLowerCase();
      if (w && p1name && w === p1name) {
        winnerCell = `<span class="h2h-winner">&#8592; ${escHtml(p1.name)}</span>`;
      } else if (w && p2name && w === p2name) {
        winnerCell = `<span class="h2h-winner">${escHtml(p2.name)} &#8594;</span>`;
      } else {
        winnerCell = `<span style="color:var(--text-muted)">Push</span>`;
      }
      return `<tr>
        <td>${escHtml(row.stat)}</td>
        <td>${v1}</td>
        <td>${v2}</td>
        <td>${winnerCell}</td>
      </tr>`;
    }).join("");

    h2hHTML = `
      <div class="h2h-section">
        <div class="h2h-label">Head-to-Head</div>
        <table class="h2h-table">
          <thead>
            <tr>
              <th>Stat</th>
              <th>${escHtml(p1.name || "Player 1")}</th>
              <th>${escHtml(p2.name || "Player 2")}</th>
              <th>Edge</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  const isPush = !data.verdict || data.verdict.toLowerCase().includes("push");
  const verdictInner = isPush
    ? `<div class="verdict-push">Push &#8212; Too Close to Call</div>`
    : `<div class="verdict-winner">${escHtml(data.verdict)}</div>`;
  const verdictReason = data.verdict_reason
    ? `<div class="verdict-reason">${escHtml(data.verdict_reason)}</div>`
    : "";

  const crossPosWarning = data.same_position === false
    ? `<div class="cross-pos-warning">&#9432; Cross-position comparison — each player graded against their own positional benchmarks.</div>`
    : "";

  const warning = data.data_warning
    ? `<div class="data-warning">&#9888; ${escHtml(data.data_warning)}</div>`
    : "";

  containerEl.innerHTML = `
    <div class="result-card">
      <div class="compare-cards">
        ${playerCardHTML(p1)}
        ${playerCardHTML(p2)}
      </div>
      ${h2hHTML}
      <div class="verdict-box">
        <div class="verdict-label">Verdict</div>
        ${verdictInner}
        ${verdictReason}
      </div>
      ${crossPosWarning}
      ${warning}
    </div>`;
  containerEl.style.display = "block";
}

// ── Render: Create-A-Player ────────────────────────────────────────────────

function renderCreate(data, containerEl) {
  const title = `Your Combine Grade${data.position ? " — " + escHtml(data.position) : ""}`;

  let comparablesHTML = "";
  if (data.comparable_players && data.comparable_players.length > 0) {
    const lis = data.comparable_players.map(p => {
      if (p && typeof p === "object") {
        const name = escHtml(p.name || "");
        const sim = p.similarity ? ` — <span style="color:var(--text-muted)">${escHtml(p.similarity)}</span>` : "";
        return `<li>${name}${sim}</li>`;
      }
      return `<li>${escHtml(p)}</li>`;
    }).join("");
    comparablesHTML = `
      <div class="comparables">
        <div class="sw-label">Comparable Players</div>
        <ul class="comparable-list">${lis}</ul>
      </div>`;
  }

  const draftProj = data.draft_projection
    ? `<div class="draft-proj"><span class="draft-proj-label">Draft Projection:</span>${escHtml(data.draft_projection)}</div>`
    : "";

  containerEl.innerHTML = `
    <div class="result-card">
      <h2>${title}</h2>
      ${gradeBadgeHTML(data.grade, data.score)}
      <div class="sw-section">
        <div class="sw-label">Strengths</div>
        ${swListHTML(data.strengths, "strengths")}
      </div>
      <div class="sw-section">
        <div class="sw-label">Weaknesses</div>
        ${swListHTML(data.weaknesses, "weaknesses")}
      </div>
      ${comparablesHTML}
      ${draftProj}
      ${data.justification ? `<div class="justification">${escHtml(data.justification)}</div>` : ""}
    </div>`;
  containerEl.style.display = "block";
}

// ── Submit: Player Grade ───────────────────────────────────────────────────

async function submitGrade(event) {
  event.preventDefault();
  const name = document.getElementById("grade-name").value.trim();
  const position = document.getElementById("grade-position").value;
  const btn = event.target.querySelector("button[type=submit]");
  const resultEl = document.getElementById("result-grade");

  if (!name) {
    showError(resultEl, "Please enter a player name.");
    return;
  }

  setLoading(btn, resultEl, true, "Analyzing combine data...");
  try {
    const data = await callAPI("/api/grade", { name, position: position || null });
    renderGrade(data, resultEl);
  } catch (err) {
    const msg = err.message || "Connection error. Is the server running?";
    showError(resultEl, msg);
  } finally {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText;
  }
}

// ── Submit: Compare Players ────────────────────────────────────────────────

async function submitCompare(event) {
  event.preventDefault();
  const name1 = document.getElementById("compare-name1").value.trim();
  const name2 = document.getElementById("compare-name2").value.trim();
  const pos1 = document.getElementById("compare-pos1").value;
  const pos2 = document.getElementById("compare-pos2").value;
  const btn = event.target.querySelector("button[type=submit]");
  const resultEl = document.getElementById("result-compare");

  if (!name1 || !name2) {
    showError(resultEl, "Please enter both player names.");
    return;
  }

  setLoading(btn, resultEl, true, "Comparing combine performances...");
  try {
    const data = await callAPI("/api/compare", {
      name1,
      name2,
      position1: pos1 || null,
      position2: pos2 || null
    });
    renderCompare(data, resultEl);
  } catch (err) {
    const msg = err.message || "Connection error. Is the server running?";
    showError(resultEl, msg);
  } finally {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText;
  }
}

// ── Submit: Create-A-Player ────────────────────────────────────────────────

async function submitCreate(event) {
  event.preventDefault();
  const position = document.getElementById("create-position").value;
  const btn = event.target.querySelector("button[type=submit]");
  const resultEl = document.getElementById("result-create");

  if (!position) {
    showError(resultEl, "Please select a position.");
    return;
  }

  function numVal(id) {
    const v = document.getElementById(id).value;
    return v === "" ? null : parseFloat(v);
  }

  const stats = {
    forty_yard:    numVal("stat-forty"),
    bench_reps:    numVal("stat-bench"),
    vertical_jump: numVal("stat-vertical"),
    broad_jump:    numVal("stat-broad"),
    three_cone:    numVal("stat-cone"),
    shuttle:       numVal("stat-shuttle"),
    height_in:     numVal("stat-height"),
    weight_lbs:    numVal("stat-weight")
  };

  if (Object.values(stats).every(v => v === null)) {
    showError(resultEl, "Please enter at least one combine stat.");
    return;
  }

  setLoading(btn, resultEl, true, "Comparing your numbers against NFL prospects...");
  try {
    const data = await callAPI("/api/create", { position, ...stats });
    renderCreate(data, resultEl);
  } catch (err) {
    const msg = err.message || "Connection error. Is the server running?";
    showError(resultEl, msg);
  } finally {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText;
  }
}
