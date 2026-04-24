const ROOT_ID = "tetr-scout-host";
const NETWORK_EVENT = "tetr-scout:network-candidates";
const POSITION_STORAGE_KEY = "tetr-scout:bubble-position";
const BUBBLE_SIZE = 56;
const BUBBLE_MARGIN = 14;
const STOP_WORDS = new Set([
  "ABOUT",
  "ACCOUNT",
  "ACHIEVEMENTS",
  "ADVANCED",
  "AGAIN",
  "ANONYMOUS",
  "BACK",
  "BLITZ",
  "CHAT",
  "CONFIG",
  "COUNTRY",
  "CURRENTLY",
  "CUSTOM",
  "DISCORD",
  "EDIT",
  "EMPTY",
  "ENTER",
  "EXIT",
  "EXPERT",
  "FRIENDS",
  "GAME",
  "GLOBAL",
  "HOME",
  "HOW",
  "INGAME",
  "ISSUE",
  "JOIN",
  "LEADERBOARDS",
  "MATCH",
  "MERCH",
  "MODIFIED",
  "MULTIPLAYER",
  "MUSIC",
  "NEWS",
  "OPTIONS",
  "PATCH",
  "PERFORMANCE",
  "PERSONAL",
  "PLAY",
  "PLAYERS",
  "PLAYING",
  "QUICK",
  "RANK",
  "RECENT",
  "REFRESH",
  "REPLAY",
  "RESET",
  "RETURN",
  "ROOM",
  "RULES",
  "SAVE",
  "SCORE",
  "SETTINGS",
  "SOLO",
  "SOUND",
  "SPECTATE",
  "STANDING",
  "START",
  "STATS",
  "SUPPORT",
  "SYS",
  "TEAM",
  "TERMS",
  "THE",
  "TETR",
  "TETRA",
  "TETRALEAGUE",
  "TETRIO",
  "TIME",
  "TRACKER",
  "UPDATE",
  "USE",
  "DOWN",
  "SEEK",
  "SPEED",
  "DECREASE",
  "WARNING",
  "WELCOME",
  "WORLD",
  "XP",
  "ZEN"
]);
const UI_LANG = (navigator.language || "").toLowerCase().startsWith("zh") ? "zh" : "en";
const UI_LOCALE = UI_LANG === "zh" ? "zh-TW" : "en-US";
const I18N = {
  zh: {
    toggle_title: "切換 TETR Scout",
    panel_title: "公開玩家快照",
    panel_subtitle: "預設精簡模式，避免遮住對戰資訊。",
    close: "關閉",
    more: "更多",
    less: "收起",
    username_placeholder: "輸入或選擇玩家名稱",
    analyze: "分析",
    candidate_usernames: "候選玩家名稱",
    invalid_username: "請輸入有效的玩家名稱。",
    fetch_failed: "抓取玩家資料失敗。",
    loading: "正在載入 {name}...",
    showing: "目前顯示 {name}",
    idle: "請選擇畫面上的玩家，或手動輸入名稱。",
    no_candidates: "目前還沒有高可信度名稱。等頁面資料進來，或直接手動輸入。",
    candidate_title: "信心 {score} · DOM {dom} · 網路 {network}",
    source_dom: "DOM",
    source_network: "網路",
    source_network_dom: "網路+DOM",
    empty_title: "這個面板會顯示什麼",
    empty_item_1: "目前牌位、TR、生涯勝率、APM/PPS/VS",
    empty_item_2: "從公開 leagueflow 推出的近 20 / 50 場趨勢",
    empty_item_3: "最近對戰列表與逐局韌性指標",
    empty_item_4: "候選名稱會優先採用 live 頁面的網路資料，而不是靜態 UI 文字",
    empty_item_5: "如果名字還是抓不到，可以手動輸入",
    rank: "牌位",
    lifetime_wr: "生涯勝率",
    last_20: "近 20 場",
    streak: "連續紀錄",
    form_note: "近況 {form}",
    wins_note: "{wins}/{games} 勝",
    tr_note: "TR {tr}",
    apm_pps_vs: "APM / PPS / VS",
    summary_stats_note: "目前 summary 數值",
    comeback_0_2: "0:2 翻盤",
    samples_note: "{count} 筆",
    country_hidden: "未公開國家",
    public_league_data: "公開聯盟資料",
    round_level_read: "逐局讀值",
    after_round1_loss: "第 1 局先輸後",
    after_round1_win: "第 1 局先贏後",
    best_streaks: "最佳連續紀錄",
    compact_mode: "精簡模式",
    compact_hint: "只有在需要圖表或對戰歷史時再開 More。面板在 active match 期間會自動收起。",
    rolling_win_rate: "滾動勝率",
    tr_trend: "TR 走勢",
    recent_match_list: "近期對戰列表",
    chart_not_enough: "目前公開資料不足，還畫不出這張圖。",
    chart_latest: "最新值：{value}",
    recent_records_empty: "公開 API 沒有回傳近期對戰 records。",
    unknown: "未知",
    score_label: "比分",
    na: "n/a"
  },
  en: {
    toggle_title: "Toggle TETR Scout",
    panel_title: "Public Player Snapshot",
    panel_subtitle: "Compact by default so it does not cover active match information.",
    close: "Close",
    more: "More",
    less: "Less",
    username_placeholder: "Enter or pick a username",
    analyze: "Analyze",
    candidate_usernames: "Candidate Usernames",
    invalid_username: "Enter a valid username.",
    fetch_failed: "Failed to fetch player data.",
    loading: "Loading {name}...",
    showing: "Showing {name}",
    idle: "Select a visible player or type a username.",
    no_candidates: "No strong usernames yet. Wait for page data, or type one manually.",
    candidate_title: "Confidence {score} · DOM {dom} · Network {network}",
    source_dom: "DOM",
    source_network: "Network",
    source_network_dom: "Network+DOM",
    empty_title: "What this panel shows",
    empty_item_1: "Current rank, TR, lifetime win rate, APM/PPS/VS",
    empty_item_2: "Last 20 and 50 match trend from public leagueflow",
    empty_item_3: "Recent match list and round-level resilience from public records",
    empty_item_4: "Candidate names prefer network data from the live page over static UI text",
    empty_item_5: "If a name is still missing, type it manually",
    rank: "Rank",
    lifetime_wr: "Lifetime WR",
    last_20: "Last 20",
    streak: "Streak",
    form_note: "Form {form}",
    wins_note: "{wins}/{games} wins",
    tr_note: "TR {tr}",
    apm_pps_vs: "APM / PPS / VS",
    summary_stats_note: "Current summary stats",
    comeback_0_2: "0-2 comeback",
    samples_note: "{count} samples",
    country_hidden: "country hidden",
    public_league_data: "public league data",
    round_level_read: "Round-Level Read",
    after_round1_loss: "After dropping round 1",
    after_round1_win: "After winning round 1",
    best_streaks: "Best streaks",
    compact_mode: "Compact Mode",
    compact_hint: "Open More only when you need charts or match history. The panel auto-hides during active matches.",
    rolling_win_rate: "Rolling Win Rate",
    tr_trend: "TR Trend",
    recent_match_list: "Recent Match List",
    chart_not_enough: "Not enough public data for this chart yet.",
    chart_latest: "Latest: {value}",
    recent_records_empty: "No recent records returned by the public API.",
    unknown: "unknown",
    score_label: "score",
    na: "n/a"
  }
};

const state = {
  selectedUsername: "",
  candidates: [],
  loading: false,
  error: "",
  payload: null,
  collapse: true,
  compact: true,
  scanTimer: null,
  networkCandidateScores: new Map(),
  autoCollapseTimer: null,
  bubblePosition: null,
  suppressToggleClick: false,
  drag: {
    active: false,
    moved: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0
  }
};

bootstrap();

function t(key, vars = {}) {
  const table = I18N[UI_LANG] || I18N.en;
  const raw = table[key] || I18N.en[key] || key;
  return raw.replace(/\{(\w+)\}/g, (_match, name) => String(vars[name] ?? ""));
}

function bootstrap() {
  const existingHost = document.getElementById(ROOT_ID);
  if (existingHost) {
    existingHost.remove();
  }

  const host = document.createElement("div");
  host.id = ROOT_ID;
  document.documentElement.append(host);
  injectPageBridge();
  state.bubblePosition = loadBubblePosition();

  const shadow = host.attachShadow({ mode: "open" });
  shadow.innerHTML = `
    <style>${buildStyles()}</style>
    <aside class="shell">
      <button class="toggle" type="button" title="${escapeHtml(t("toggle_title"))}">
        <span class="toggle-ring"></span>
        <span class="toggle-label">TS</span>
      </button>
      <section class="panel">
        <header class="hero">
          <div>
            <div class="eyebrow">TETR Scout</div>
            <h1>${escapeHtml(t("panel_title"))}</h1>
            <p>${escapeHtml(t("panel_subtitle"))}</p>
          </div>
          <div class="panel-actions">
            <button class="ghost-button details-toggle" type="button">${escapeHtml(t("more"))}</button>
            <button class="ghost-button close-button" type="button" aria-label="${escapeHtml(t("close"))}">×</button>
          </div>
        </header>
        <div class="controls">
          <input class="username-input" type="text" placeholder="${escapeHtml(t("username_placeholder"))}" spellcheck="false" />
          <button class="analyze-button" type="button">${escapeHtml(t("analyze"))}</button>
        </div>
        <div class="section">
          <div class="section-title">${escapeHtml(t("candidate_usernames"))}</div>
          <div class="candidate-list"></div>
        </div>
        <div class="status"></div>
        <div class="body"></div>
      </section>
    </aside>
  `;

  const toggle = shadow.querySelector(".toggle");
  const analyzeButton = shadow.querySelector(".analyze-button");
  const input = shadow.querySelector(".username-input");
  const closeButton = shadow.querySelector(".close-button");
  const detailsToggle = shadow.querySelector(".details-toggle");
  const panel = shadow.querySelector(".panel");

  toggle.addEventListener("click", () => {
    if (state.suppressToggleClick) {
      state.suppressToggleClick = false;
      return;
    }
    state.collapse = !state.collapse;
    if (!state.collapse) {
      clearAutoCollapse();
      scheduleAutoCollapseIfNeeded();
    } else {
      blurPanelInputs(shadow);
    }
    render(shadow);
  });

  closeButton.addEventListener("click", () => {
    state.collapse = true;
    clearAutoCollapse();
    blurPanelInputs(shadow);
    render(shadow);
  });

  detailsToggle.addEventListener("click", () => {
    state.compact = !state.compact;
    scheduleAutoCollapseIfNeeded();
    render(shadow);
  });

  analyzeButton.addEventListener("click", () => {
    analyzeUsername(input.value.trim(), shadow);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      analyzeUsername(input.value.trim(), shadow);
    }
  });

  window.addEventListener(NETWORK_EVENT, (event) => {
    const names = Array.isArray(event.detail?.names) ? event.detail.names : [];
    const baseWeight = Number(event.detail?.weight) || 14;
    let changed = false;

    for (const rawName of names) {
      const normalized = normalizeCandidate(rawName);
      if (!normalized) {
        continue;
      }

      const previous = state.networkCandidateScores.get(normalized) || 0;
      const next = Math.min(previous + baseWeight, 100);
      if (next !== previous) {
        state.networkCandidateScores.set(normalized, next);
        changed = true;
      }
    }

    if (changed) {
      refreshCandidates(shadow);
    }
  });

  const observer = new MutationObserver(() => {
    if (state.scanTimer) {
      clearTimeout(state.scanTimer);
    }
    state.scanTimer = window.setTimeout(() => refreshCandidates(shadow), 700);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
  });

  shadow.querySelector(".panel").addEventListener("mouseenter", () => {
    clearAutoCollapse();
  });

  shadow.querySelector(".panel").addEventListener("mouseleave", () => {
    scheduleAutoCollapseIfNeeded();
  });

  installBubbleDrag(toggle, shadow);

  document.addEventListener("pointerdown", (event) => {
    if (state.collapse) {
      return;
    }
    if (event.composedPath().includes(host)) {
      return;
    }
    state.collapse = true;
    clearAutoCollapse();
    blurPanelInputs(shadow);
    render(shadow);
  }, true);

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !state.collapse) {
      state.collapse = true;
      clearAutoCollapse();
      blurPanelInputs(shadow);
      render(shadow);
    }
  });

  window.addEventListener("resize", () => {
    state.bubblePosition = clampBubblePosition(state.bubblePosition || getDefaultBubblePosition());
    render(shadow);
  });

  refreshCandidates(shadow);
  render(shadow);
}

function installBubbleDrag(toggle, shadow) {
  toggle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) {
      return;
    }

    const drag = state.drag;
    drag.active = true;
    drag.moved = false;
    drag.pointerId = event.pointerId;
    drag.startX = event.clientX;
    drag.startY = event.clientY;
    drag.originX = state.bubblePosition?.x ?? getDefaultBubblePosition().x;
    drag.originY = state.bubblePosition?.y ?? getDefaultBubblePosition().y;

    toggle.setPointerCapture(event.pointerId);
  });

  toggle.addEventListener("pointermove", (event) => {
    const drag = state.drag;
    if (!drag.active || drag.pointerId !== event.pointerId) {
      return;
    }

    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
      drag.moved = true;
    }

    state.bubblePosition = clampBubblePosition({
      x: drag.originX + dx,
      y: drag.originY + dy
    });
    applyBubblePosition(shadow.querySelector(".shell"));
  });

  const finishDrag = (event) => {
    const drag = state.drag;
    if (!drag.active || drag.pointerId !== event.pointerId) {
      return;
    }

    drag.active = false;
    toggle.releasePointerCapture?.(event.pointerId);

    if (drag.moved) {
      state.suppressToggleClick = true;
      persistBubblePosition();
      render(shadow);
    }
  };

  toggle.addEventListener("pointerup", finishDrag);
  toggle.addEventListener("pointercancel", finishDrag);
}

function refreshCandidates(shadow) {
  state.candidates = findVisibleCandidates();
  const autoCandidate = pickAutoCandidate(state.candidates);
  if (!state.selectedUsername && autoCandidate) {
    analyzeUsername(autoCandidate, shadow, { silentInputSync: true });
    return;
  }
  render(shadow);
}

function pickAutoCandidate(candidates) {
  if (candidates.length === 1) {
    return candidates[0].name;
  }
  if (candidates.length >= 2 && candidates[0].score >= candidates[1].score + 6 && candidates[0].source !== "dom") {
    return candidates[0].name;
  }
  return "";
}

function findVisibleCandidates() {
  const domScores = new Map();
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  let visited = 0;

  while (node && visited < 1800) {
    visited += 1;
    const parent = node.parentElement;
    if (!parent || parent.closest(`#${ROOT_ID}`) || !isVisible(parent)) {
      node = walker.nextNode();
      continue;
    }

    const rawText = node.textContent?.trim() || "";
    if (!rawText || rawText.length > 64) {
      node = walker.nextNode();
      continue;
    }

    for (const token of extractCandidateTokens(rawText)) {
      addCandidateScore(domScores, token, scoreToken(token, rawText, parent, viewport));
    }

    node = walker.nextNode();
  }

  collectAttributeCandidates(domScores, viewport);

  const merged = new Map();
  for (const [name, score] of domScores) {
    merged.set(name, score);
  }
  for (const [name, score] of state.networkCandidateScores) {
    merged.set(name, (merged.get(name) || 0) + score);
  }

  return [...merged.entries()]
    .map(([name, score]) => {
      const domScore = domScores.get(name) || 0;
      const networkScore = state.networkCandidateScores.get(name) || 0;
      return {
        name,
        score,
        domScore,
        networkScore,
        source: domScore > 0 && networkScore > 0 ? "network+dom" : networkScore > 0 ? "network" : "dom"
      };
    })
    .filter((entry) => entry.score > 2)
    .sort((left, right) => right.score - left.score || left.name.localeCompare(right.name))
    .slice(0, 6);
}

function injectPageBridge() {
  if (document.getElementById("tetr-scout-bridge")) {
    return;
  }

  const script = document.createElement("script");
  script.id = "tetr-scout-bridge";
  script.src = chrome.runtime.getURL("page-bridge.js");
  script.async = false;
  (document.head || document.documentElement).append(script);
  script.onload = () => script.remove();
}

function collectAttributeCandidates(scores, viewport) {
  const elements = document.querySelectorAll("[aria-label], [title], [alt], [data-user], [data-username]");
  let visited = 0;

  for (const element of elements) {
    if (visited >= 800) {
      break;
    }
    visited += 1;

    if (!(element instanceof HTMLElement) || element.closest(`#${ROOT_ID}`) || !isVisible(element)) {
      continue;
    }

    const values = [
      element.getAttribute("aria-label"),
      element.getAttribute("title"),
      element.getAttribute("alt"),
      element.getAttribute("data-user"),
      element.getAttribute("data-username")
    ].filter(Boolean);

    for (const value of values) {
      const trimmed = value.trim();
      if (!trimmed || trimmed.length > 64) {
        continue;
      }

      for (const token of extractCandidateTokens(trimmed)) {
        addCandidateScore(scores, token, scoreToken(token, trimmed, element, viewport) + 1);
      }
    }
  }
}

function extractCandidateTokens(text) {
  const candidates = new Set();
  const exact = normalizeCandidate(text);
  if (exact) {
    candidates.add(exact);
  }

  const matches = text.matchAll(/\b[A-Za-z0-9_]{3,16}\b/g);
  for (const match of matches) {
    const normalized = normalizeCandidate(match[0]);
    if (normalized) {
      candidates.add(normalized);
    }
  }

  return [...candidates];
}

function normalizeCandidate(value) {
  const trimmed = value.trim();
  if (!/^[A-Za-z0-9_]{3,16}$/.test(trimmed)) {
    return "";
  }
  if (/^\d+$/.test(trimmed)) {
    return "";
  }
  if (trimmed.length <= 3 && trimmed === trimmed.toUpperCase() && !trimmed.includes("_")) {
    return "";
  }
  if (STOP_WORDS.has(trimmed.toUpperCase())) {
    return "";
  }
  return trimmed;
}

function scoreToken(token, rawText, element, viewport) {
  let score = 1;
  if (rawText === token) {
    score += 2;
  }
  if (/^(SPAN|DIV|A|H1|H2|H3|BUTTON)$/.test(element.tagName)) {
    score += 1;
  }

  const context = [element.textContent, element.parentElement?.textContent]
    .filter(Boolean)
    .join(" ")
    .toUpperCase();

  if (context.includes(" VS ") || context.includes("PLAYERS") || context.includes("PLAYING")) {
    score += 1;
  }
  if (token.includes("_")) {
    score += 2;
  }
  if (/[0-9]/.test(token)) {
    score += 1;
  }
  score += positionScore(element.getBoundingClientRect(), viewport);

  return score;
}

function positionScore(rect, viewport) {
  let score = 0;
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;

  if (
    centerY >= viewport.height * 0.08 &&
    centerY <= viewport.height * 0.24 &&
    centerX >= viewport.width * 0.34 &&
    centerX <= viewport.width * 0.84
  ) {
    score += 3;
  }

  if (
    centerY >= viewport.height * 0.78 &&
    centerY <= viewport.height * 0.96
  ) {
    score += 3;
  }

  if (rect.width <= 380 && rect.height <= 90) {
    score += 1;
  }

  return score;
}

function addCandidateScore(scores, token, delta) {
  if (!token || !Number.isFinite(delta) || delta <= 0) {
    return;
  }
  const previous = scores.get(token) || 0;
  scores.set(token, previous + delta);
}

function isVisible(element) {
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
    return false;
  }
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

async function analyzeUsername(username, shadow, options = {}) {
  const normalized = normalizeCandidate(username);
  if (!normalized) {
    state.error = t("invalid_username");
    render(shadow);
    return;
  }

  state.selectedUsername = normalized;
  state.loading = true;
  state.error = "";
  state.payload = null;

  if (!options.silentInputSync) {
    shadow.querySelector(".username-input").value = normalized;
  }

  blurPanelInputs(shadow);
  render(shadow);

  const response = await chrome.runtime.sendMessage({
    type: "tetr-scout:analyze-user",
    username: normalized
  });

  state.loading = false;
  if (!response?.ok) {
    state.error = response?.error || t("fetch_failed");
    state.payload = null;
    render(shadow);
    return;
  }

  state.payload = response.payload;
  scheduleAutoCollapseIfNeeded();
  blurPanelInputs(shadow);
  render(shadow);
}

function render(shadow) {
  const shell = shadow.querySelector(".shell");
  const status = shadow.querySelector(".status");
  const body = shadow.querySelector(".body");
  const candidateList = shadow.querySelector(".candidate-list");
  const input = shadow.querySelector(".username-input");
  const detailsToggle = shadow.querySelector(".details-toggle");
  const toggle = shadow.querySelector(".toggle");

  shell.classList.toggle("collapsed", state.collapse);
  shell.classList.toggle("compact", state.compact);
  applyBubblePosition(shell);
  detailsToggle.textContent = state.compact ? t("more") : t("less");
  const bubbleLabel = state.payload?.user?.username
    ? state.payload.user.username.replace(/_/g, "").slice(0, 2).toUpperCase() || "TS"
    : "TS";
  toggle.innerHTML = `
    <span class="toggle-ring"></span>
    <span class="toggle-label">${escapeHtml(bubbleLabel)}</span>
  `;
  toggle.classList.toggle("active", !state.collapse);

  if (document.activeElement !== input && state.selectedUsername) {
    input.value = state.selectedUsername;
  }

  status.textContent = state.loading
    ? t("loading", { name: state.selectedUsername })
    : state.error
      ? state.error
      : state.payload
        ? t("showing", { name: state.payload.user.username })
        : t("idle");
  status.className = `status${state.error ? " error" : state.loading ? " loading" : ""}`;

  candidateList.innerHTML = "";
  if (!state.candidates.length) {
    const empty = document.createElement("div");
    empty.className = "hint";
    empty.textContent = t("no_candidates");
    candidateList.append(empty);
  } else {
    for (const candidate of state.candidates) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `candidate${candidate.name === state.selectedUsername ? " active" : ""}`;
      button.innerHTML = `
        <span class="candidate-name">${escapeHtml(candidate.name)}</span>
        <span class="candidate-source">${escapeHtml(formatCandidateSource(candidate.source))}</span>
      `;
      button.title = t("candidate_title", {
        score: candidate.score,
        dom: candidate.domScore,
        network: candidate.networkScore
      });
      button.addEventListener("click", () => analyzeUsername(candidate.name, shadow));
      candidateList.append(button);
    }
  }

  if (!state.payload) {
    body.innerHTML = `
      <section class="empty">
        <div class="empty-title">${escapeHtml(t("empty_title"))}</div>
        <ul>
          <li>${escapeHtml(t("empty_item_1"))}</li>
          <li>${escapeHtml(t("empty_item_2"))}</li>
          <li>${escapeHtml(t("empty_item_3"))}</li>
          <li>${escapeHtml(t("empty_item_4"))}</li>
          <li>${escapeHtml(t("empty_item_5"))}</li>
        </ul>
      </section>
    `;
    return;
  }

  body.innerHTML = renderPayload(state.payload);
}

function renderPayload(payload) {
  const summary = payload.summary;
  const trend = payload.trend;
  const resilience = payload.resilience;
  const coreCards = [
    card(t("rank"), escapeHtml(summary.rank || t("na")), t("tr_note", { tr: formatNumber(summary.tr) })),
    card(t("lifetime_wr"), formatRate(summary.lifetimeWinRate), t("wins_note", { wins: summary.gamesWon, games: summary.gamesPlayed })),
    card(t("last_20"), formatRate(trend.recent20?.winRate), t("tr_note", { tr: formatSigned(trend.recent20?.trDelta, 0) })),
    card(t("streak"), escapeHtml(trend.currentStreak || t("na")), t("form_note", { form: escapeHtml(trend.form || t("na")) }))
  ].join("");

  const extraCards = [
    card(t("apm_pps_vs"), `${formatNumber(summary.apm, 1)} / ${formatNumber(summary.pps, 2)} / ${formatNumber(summary.vs, 1)}`, t("summary_stats_note")),
    card(t("comeback_0_2"), formatRate(resilience.zeroTwoComebackRate), t("samples_note", { count: resilience.zeroTwoSamples }))
  ].join("");

  return `
    <section class="identity">
      <div>
        <div class="player-name">${escapeHtml(payload.user.username)}</div>
        <div class="subtle">${escapeHtml(payload.user.country || t("country_hidden"))} · ${escapeHtml(t("public_league_data"))}</div>
      </div>
    </section>
    <section class="card-grid">${coreCards}</section>
    <section class="mini-grid">${extraCards}</section>
    <section class="panel-block quick-block">
      <div class="block-title">${escapeHtml(t("round_level_read"))}</div>
      <div class="metric-list">
        <div class="metric-row"><span>${escapeHtml(t("after_round1_loss"))}</span><strong>${formatRate(resilience.afterRound1LossWinRate)}</strong></div>
        <div class="metric-row"><span>${escapeHtml(t("after_round1_win"))}</span><strong>${formatRate(resilience.afterRound1WinWinRate)}</strong></div>
        <div class="metric-row"><span>${escapeHtml(t("best_streaks"))}</span><strong>W${trend.bestWinStreak} / L${trend.bestLossStreak}</strong></div>
      </div>
    </section>
    ${state.compact ? `
      <section class="panel-block compact-tip">
        <div class="block-title">${escapeHtml(t("compact_mode"))}</div>
        <div class="hint">${escapeHtml(t("compact_hint"))}</div>
      </section>
    ` : `
      <section class="panel-block">
        <div class="block-title">${escapeHtml(t("rolling_win_rate"))}</div>
        ${renderMiniChart(trend.rollingWinRate, { percent: true, color: "#f67b47" })}
      </section>
      <section class="panel-block">
        <div class="block-title">${escapeHtml(t("tr_trend"))}</div>
        ${renderMiniChart(trend.trSeries, { percent: false, color: "#6dd6a8" })}
      </section>
      <section class="panel-block">
        <div class="block-title">${escapeHtml(t("recent_match_list"))}</div>
        ${renderRecentMatches(payload.recentMatches)}
      </section>
    `}
  `;
}

function isLikelyInMatch() {
  const text = (document.body?.innerText || "").toUpperCase();
  return text.includes("HOLD") && text.includes("NEXT") && (text.includes("FT3") || text.includes("FT5") || text.includes("VS SCORE"));
}

function getDefaultBubblePosition() {
  return {
    x: Math.max(BUBBLE_MARGIN, window.innerWidth - BUBBLE_SIZE - 18),
    y: Math.max(BUBBLE_MARGIN, window.innerHeight - BUBBLE_SIZE - 20)
  };
}

function clampBubblePosition(position) {
  const fallback = getDefaultBubblePosition();
  const source = position || fallback;
  const maxX = Math.max(BUBBLE_MARGIN, window.innerWidth - BUBBLE_SIZE - BUBBLE_MARGIN);
  const maxY = Math.max(BUBBLE_MARGIN, window.innerHeight - BUBBLE_SIZE - BUBBLE_MARGIN);
  return {
    x: Math.min(maxX, Math.max(BUBBLE_MARGIN, Number(source.x) || fallback.x)),
    y: Math.min(maxY, Math.max(BUBBLE_MARGIN, Number(source.y) || fallback.y))
  };
}

function loadBubblePosition() {
  try {
    const raw = localStorage.getItem(POSITION_STORAGE_KEY);
    if (!raw) {
      return getDefaultBubblePosition();
    }
    return clampBubblePosition(JSON.parse(raw));
  } catch {
    return getDefaultBubblePosition();
  }
}

function persistBubblePosition() {
  try {
    localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(state.bubblePosition));
  } catch {
    // Ignore persistence errors.
  }
}

function applyBubblePosition(shell) {
  if (!shell) {
    return;
  }

  const position = clampBubblePosition(state.bubblePosition || getDefaultBubblePosition());
  state.bubblePosition = position;
  shell.style.left = `${position.x}px`;
  shell.style.top = `${position.y}px`;
  shell.classList.toggle("panel-left", position.x < window.innerWidth * 0.42);
  shell.classList.toggle("panel-right", position.x >= window.innerWidth * 0.42);
}

function clearAutoCollapse() {
  if (state.autoCollapseTimer) {
    clearTimeout(state.autoCollapseTimer);
    state.autoCollapseTimer = null;
  }
}

function blurPanelInputs(shadow) {
  const input = shadow?.querySelector(".username-input");
  if (input && shadow.activeElement === input) {
    input.blur();
  }
}

function scheduleAutoCollapseIfNeeded() {
  clearAutoCollapse();
  if (state.collapse) {
    return;
  }
  if (!isLikelyInMatch()) {
    return;
  }

  state.autoCollapseTimer = window.setTimeout(() => {
    state.collapse = true;
    const shadow = document.getElementById(ROOT_ID)?.shadowRoot;
    blurPanelInputs(shadow);
    if (shadow) {
      render(shadow);
    }
  }, state.compact ? 5000 : 2500);
}

function renderMiniChart(points, options) {
  if (!points?.length) {
    return `<div class="hint">${escapeHtml(t("chart_not_enough"))}</div>`;
  }

  const width = 320;
  const height = 120;
  const padding = 8;
  const xs = points.map((point) => point.ts);
  const ys = points.map((point) => Number(point.value));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  let minY = Math.min(...ys);
  let maxY = Math.max(...ys);
  if (options.percent) {
    minY = 0;
    maxY = 1;
  }
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }

  const mapX = (value) => {
    if (maxX === minX) {
      return width / 2;
    }
    return padding + ((value - minX) / (maxX - minX)) * (width - padding * 2);
  };
  const mapY = (value) => {
    return padding + (1 - (value - minY) / (maxY - minY)) * (height - padding * 2);
  };

  const path = points.map((point) => `${mapX(point.ts).toFixed(1)},${mapY(point.value).toFixed(1)}`).join(" ");
  const lastValue = points[points.length - 1].value;

  return `
    <svg viewBox="0 0 ${width} ${height}" class="chart" role="img">
      <polyline points="${path}" fill="none" stroke="${options.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
    </svg>
    <div class="chart-note">${escapeHtml(t("chart_latest", { value: options.percent ? formatRate(lastValue) : formatNumber(lastValue) }))}</div>
  `;
}

function renderRecentMatches(matches) {
  if (!matches?.length) {
    return `<div class="hint">${escapeHtml(t("recent_records_empty"))}</div>`;
  }

  return `
    <div class="match-list">
      ${matches.map((match) => `
        <div class="match-row">
          <div>
            <div class="match-opponent">${escapeHtml(match.opponentUsername || t("unknown"))}</div>
            <div class="subtle">${formatTimestamp(match.ts)} · ${escapeHtml(t("score_label"))} ${escapeHtml(match.score)}</div>
          </div>
          <div class="pill ${match.bucket === "W" ? "win" : match.bucket === "L" ? "loss" : ""}">
            ${escapeHtml(match.bucket || "?")}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function card(label, value, note) {
  return `
    <article class="card">
      <div class="card-label">${escapeHtml(label)}</div>
      <div class="card-value">${value}</div>
      <div class="card-note">${escapeHtml(note)}</div>
    </article>
  `;
}

function formatCandidateSource(source) {
  if (source === "network+dom") {
    return t("source_network_dom");
  }
  if (source === "network") {
    return t("source_network");
  }
  return t("source_dom");
}

function formatRate(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : t("na");
}

function formatNumber(value, digits = 2) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : t("na");
}

function formatSigned(value, digits = 0) {
  return Number.isFinite(value) ? `${value >= 0 ? "+" : ""}${Number(value).toFixed(digits)}` : t("na");
}

function formatTimestamp(value) {
  if (!Number.isFinite(value)) {
    return t("na");
  }
  return new Intl.DateTimeFormat(UI_LOCALE, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function buildStyles() {
  return `
    :host {
      all: initial;
    }
    .shell {
      pointer-events: none;
    }
    .shell, .shell * {
      box-sizing: border-box;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    .shell {
      position: fixed;
      left: 0;
      top: 0;
      width: ${BUBBLE_SIZE}px;
      height: ${BUBBLE_SIZE}px;
      z-index: 2147483647;
      overflow: visible;
      color: #171210;
    }
    .toggle {
      pointer-events: auto;
      position: absolute;
      inset: 0;
      appearance: none;
      border: none;
      border-radius: 999px;
      background: linear-gradient(135deg, #f67b47, #ffc568);
      color: #171210;
      font-weight: 700;
      min-width: 54px;
      height: 54px;
      padding: 0 14px;
      cursor: pointer;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
      transition: transform 140ms ease, box-shadow 140ms ease;
      user-select: none;
      touch-action: none;
      overflow: hidden;
    }
    .toggle:hover {
      transform: translateY(-1px) scale(1.03);
      box-shadow: 0 16px 34px rgba(0, 0, 0, 0.34);
    }
    .toggle.active {
      box-shadow: 0 16px 36px rgba(246, 123, 71, 0.34);
    }
    .toggle-ring {
      position: absolute;
      inset: 4px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.22);
      opacity: 0.65;
    }
    .toggle-label {
      position: relative;
      z-index: 1;
      font-size: 12px;
      letter-spacing: 0.08em;
      font-weight: 800;
    }
    .panel {
      pointer-events: auto;
      position: absolute;
      bottom: 0;
      width: min(308px, calc(100vw - 36px));
      max-height: min(62vh, 560px);
      overflow: auto;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.18);
      background:
        radial-gradient(circle at top right, rgba(246, 123, 71, 0.16), transparent 30%),
        linear-gradient(180deg, rgba(25, 20, 18, 0.95), rgba(15, 13, 12, 0.92));
      box-shadow: 0 30px 60px rgba(0, 0, 0, 0.34);
      color: #f3ebe4;
      padding: 12px;
      opacity: 1;
      transform: translateY(0) scale(1);
      transition: opacity 140ms ease, transform 140ms ease, visibility 140ms ease;
    }
    .panel-left .panel {
      left: calc(100% + 12px);
    }
    .panel-right .panel {
      right: calc(100% + 12px);
    }
    .collapsed .panel {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transform: translateY(8px) scale(0.96);
    }
    .hero {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .hero h1 {
      margin: 0;
      font-size: 16px;
    }
    .hero p, .subtle, .hint, .card-note, .chart-note {
      color: rgba(243, 235, 228, 0.7);
    }
    .eyebrow, .section-title, .block-title, .card-label {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
      color: rgba(243, 235, 228, 0.55);
    }
    .hero p {
      margin: 6px 0 0;
      font-size: 11px;
      line-height: 1.5;
    }
    .panel-actions {
      display: flex;
      gap: 6px;
      flex-shrink: 0;
    }
    .ghost-button {
      appearance: none;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: rgba(255, 255, 255, 0.06);
      color: rgba(243, 235, 228, 0.88);
      border-radius: 12px;
      padding: 8px 10px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .close-button {
      min-width: 34px;
      padding: 8px 0;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      margin-top: 10px;
    }
    .username-input {
      appearance: none;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.08);
      color: inherit;
      padding: 10px 12px;
      outline: none;
    }
    .analyze-button, .candidate {
      appearance: none;
      border: none;
      cursor: pointer;
    }
    .analyze-button {
      border-radius: 14px;
      padding: 10px 12px;
      font-weight: 700;
      color: #171210;
      background: linear-gradient(135deg, #6dd6a8, #ffc568);
    }
    .section {
      margin-top: 10px;
    }
    .candidate-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .candidate {
      padding: 8px 10px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.08);
      color: inherit;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .candidate.active {
      background: rgba(109, 214, 168, 0.22);
      outline: 1px solid rgba(109, 214, 168, 0.45);
    }
    .candidate-name {
      font-weight: 700;
    }
    .candidate-source {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: rgba(243, 235, 228, 0.6);
    }
    .status {
      margin-top: 10px;
      border-radius: 14px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.06);
      font-size: 12px;
    }
    .status.loading {
      background: rgba(246, 197, 104, 0.16);
    }
    .status.error {
      background: rgba(246, 123, 71, 0.18);
    }
    .body {
      margin-top: 10px;
      display: grid;
      gap: 10px;
    }
    .empty {
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.05);
      padding: 14px;
    }
    .empty-title {
      font-weight: 700;
      margin-bottom: 8px;
    }
    .empty ul {
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
    }
    .identity {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .player-name {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .card, .panel-block {
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.05);
      padding: 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .card-value {
      margin-top: 5px;
      font-size: 16px;
      font-weight: 700;
      line-height: 1.2;
    }
    .panel-block {
      display: grid;
      gap: 10px;
    }
    .compact .panel-block {
      gap: 8px;
    }
    .compact-tip {
      display: none;
    }
    .compact .compact-tip {
      display: grid;
    }
    .chart {
      display: block;
      width: 100%;
      height: auto;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 12px;
    }
    .metric-list {
      display: grid;
      gap: 8px;
    }
    .metric-row, .match-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    .metric-row strong {
      font-size: 14px;
    }
    .match-list {
      display: grid;
      gap: 10px;
    }
    .match-opponent {
      font-weight: 700;
    }
    .pill {
      min-width: 36px;
      text-align: center;
      border-radius: 999px;
      padding: 6px 8px;
      background: rgba(255, 255, 255, 0.08);
      font-weight: 700;
    }
    .pill.win {
      background: rgba(109, 214, 168, 0.18);
    }
    .pill.loss {
      background: rgba(246, 123, 71, 0.18);
    }
    @media (max-width: 720px) {
      .shell {
        width: ${BUBBLE_SIZE}px;
        height: ${BUBBLE_SIZE}px;
      }
      .panel {
        width: min(300px, calc(100vw - 24px));
      }
    }
  `;
}
