const API_ROOT = "https://ch.tetr.io/api";
const API_CACHE = new Map();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "tetr-scout:analyze-user") {
    return false;
  }

  analyzeUser(String(message.username || ""))
    .then((payload) => sendResponse({ ok: true, payload }))
    .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));

  return true;
});

async function analyzeUser(usernameInput) {
  const username = normalizeUsername(usernameInput);
  if (!username) {
    throw new Error("Invalid username");
  }

  const sessionId = crypto.randomUUID();
  const [userPayload, summaryPayload, leagueflowPayload, recentRecordsPayload] = await Promise.all([
    apiFetch(`/users/${encodeURIComponent(username)}`, { sessionId }),
    apiFetch(`/users/${encodeURIComponent(username)}/summaries/league`, { sessionId }),
    apiFetch(`/labs/leagueflow/${encodeURIComponent(username)}`, { sessionId }),
    apiFetch(`/users/${encodeURIComponent(username)}/records/league/recent`, {
      sessionId,
      query: { limit: 40 }
    })
  ]);

  const user = userPayload.data;
  const summary = summaryPayload.data;
  const leagueflowMatches = loadLeagueflowMatches(leagueflowPayload);
  const effectiveMatches = leagueflowMatches.filter((match) => match.bucket !== null);
  const recentRecords = loadRecentRecords(recentRecordsPayload, user._id);

  const recent20 = summarizeWindow(effectiveMatches, 20);
  const recent50 = summarizeWindow(effectiveMatches, 50);
  const rollingWinRate = buildRollingWinRateSeries(effectiveMatches, 20);
  const trTrend = effectiveMatches.slice(-80).map((match) => ({
    ts: match.ts,
    value: match.trAfter
  }));

  return {
    user: {
      id: user._id,
      username: user.username,
      country: user.country || null
    },
    summary: {
      rank: summary.rank || "n/a",
      tr: summary.tr ?? null,
      gxe: summary.gxe ?? null,
      standing: summary.standing ?? null,
      gamesPlayed: summary.gamesplayed ?? 0,
      gamesWon: summary.gameswon ?? 0,
      apm: summary.apm ?? null,
      pps: summary.pps ?? null,
      vs: summary.vs ?? null,
      lifetimeWinRate: rate(summary.gameswon, summary.gamesplayed)
    },
    trend: {
      currentStreak: describeCurrentStreak(effectiveMatches),
      bestWinStreak: longestRun(effectiveMatches, "W"),
      bestLossStreak: longestRun(effectiveMatches, "L"),
      form: effectiveMatches.slice(-10).map((match) => match.bucket).join(""),
      recent20,
      recent50,
      trSeries: trTrend,
      rollingWinRate
    },
    resilience: summarizeResilience(recentRecords),
    recentMatches: recentRecords.slice(0, 8)
  };
}

function normalizeUsername(username) {
  const trimmed = username.trim();
  if (!/^[A-Za-z0-9_]{3,16}$/.test(trimmed)) {
    return null;
  }
  return trimmed.toLowerCase();
}

function buildCacheKey(path, query) {
  const url = new URL(`${API_ROOT}${path}`);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function apiFetch(path, { query = {}, sessionId }) {
  const cacheKey = buildCacheKey(path, query);
  const cached = API_CACHE.get(cacheKey);
  const now = Date.now();
  if (cached && cached.expiresAt > now) {
    return cached.payload;
  }

  const url = new URL(`${API_ROOT}${path}`);
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
      "X-Session-ID": sessionId
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while requesting ${path}`);
  }

  const payload = await response.json();
  if (!payload.success) {
    throw new Error(payload.error?.msg || `API request failed for ${path}`);
  }

  const expiresAt = Number.isFinite(Number(payload.cache?.cached_until))
    ? Number(payload.cache.cached_until)
    : now + 60_000;

  API_CACHE.set(cacheKey, { payload, expiresAt });
  return payload;
}

function loadLeagueflowMatches(payload) {
  const raw = payload.data || {};
  const startTime = Number(raw.startTime || 0);
  return (raw.points || [])
    .map((point) => {
      const [offset, resultCode, trAfter, opponentTr] = point;
      return {
        ts: startTime + Number(offset),
        bucket: bucketFromResult(Number(resultCode)),
        trAfter: Number(trAfter),
        opponentTr: Number(opponentTr)
      };
    })
    .sort((left, right) => left.ts - right.ts);
}

function loadRecentRecords(payload, ownerId) {
  return (payload.data?.entries || [])
    .map((entry) => {
      const leaderboard = entry.results?.leaderboard || [];
      const selfRow = leaderboard.find((row) => String(row.id) === String(ownerId));
      const opponentRow = leaderboard.find((row) => String(row.id) !== String(ownerId));
      const roundBuckets = [];

      for (const roundRows of entry.results?.rounds || []) {
        const selfRound = roundRows.find((row) => String(row.id) === String(ownerId));
        const opponentRound = roundRows.find((row) => String(row.id) !== String(ownerId));
        if (!selfRound || !opponentRound) {
          continue;
        }
        if (selfRound.alive && !opponentRound.alive) {
          roundBuckets.push("W");
        } else if (!selfRound.alive && opponentRound.alive) {
          roundBuckets.push("L");
        }
      }

      const result = entry.extras?.result || "unknown";
      return {
        ts: Date.parse(entry.ts),
        bucket: result === "victory" ? "W" : result === "defeat" ? "L" : null,
        opponentUsername: opponentRow?.username || "unknown",
        score: selfRow && opponentRow ? `${selfRow.wins}-${opponentRow.wins}` : "n/a",
        selfWins: selfRow?.wins ?? null,
        opponentWins: opponentRow?.wins ?? null,
        roundBuckets,
        opponentPreTr: entry.extras?.league?.[opponentRow?.id]?.[0]?.tr ?? null
      };
    })
    .filter((record) => Number.isFinite(record.ts))
    .sort((left, right) => right.ts - left.ts);
}

function bucketFromResult(resultCode) {
  if (resultCode === 1 || resultCode === 3) {
    return "W";
  }
  if (resultCode === 2 || resultCode === 4) {
    return "L";
  }
  if (resultCode === 5) {
    return "T";
  }
  return null;
}

function summarizeWindow(matches, size) {
  const window = matches.slice(-size).filter((match) => match.bucket === "W" || match.bucket === "L");
  const wins = window.filter((match) => match.bucket === "W").length;
  const losses = window.filter((match) => match.bucket === "L").length;
  const trDelta = window.length >= 2 ? window[window.length - 1].trAfter - window[0].trAfter : null;
  return {
    size: window.length,
    winRate: rate(wins, wins + losses),
    wins,
    losses,
    trDelta,
    avgOpponentTr: average(window.map((match) => match.opponentTr))
  };
}

function buildRollingWinRateSeries(matches, windowSize) {
  const clean = matches.filter((match) => match.bucket === "W" || match.bucket === "L");
  if (clean.length < windowSize) {
    return [];
  }

  const points = [];
  for (let index = windowSize - 1; index < clean.length; index += 1) {
    const window = clean.slice(index - windowSize + 1, index + 1);
    const wins = window.filter((match) => match.bucket === "W").length;
    points.push({
      ts: clean[index].ts,
      value: wins / windowSize
    });
  }
  return downsample(points, 80);
}

function summarizeResilience(records) {
  const round1LossBuckets = [];
  const round1WinBuckets = [];
  const zeroTwoComebacks = [];

  for (const record of records) {
    if (record.roundBuckets[0] === "L") {
      round1LossBuckets.push(record.bucket);
    }
    if (record.roundBuckets[0] === "W") {
      round1WinBuckets.push(record.bucket);
    }
    if (record.roundBuckets[0] === "L" && record.roundBuckets[1] === "L") {
      zeroTwoComebacks.push(record.bucket);
    }
  }

  return {
    sampleSize: records.length,
    afterRound1LossWinRate: rateFromBuckets(round1LossBuckets),
    afterRound1LossSamples: round1LossBuckets.length,
    afterRound1WinWinRate: rateFromBuckets(round1WinBuckets),
    afterRound1WinSamples: round1WinBuckets.length,
    zeroTwoComebackRate: rateFromBuckets(zeroTwoComebacks),
    zeroTwoSamples: zeroTwoComebacks.length
  };
}

function describeCurrentStreak(matches) {
  if (!matches.length) {
    return "n/a";
  }

  const lastBucket = matches[matches.length - 1].bucket;
  if (!lastBucket) {
    return "n/a";
  }

  let count = 0;
  for (let index = matches.length - 1; index >= 0; index -= 1) {
    if (matches[index].bucket !== lastBucket) {
      break;
    }
    count += 1;
  }
  return `${lastBucket}${count}`;
}

function longestRun(matches, target) {
  let best = 0;
  let current = 0;
  for (const match of matches) {
    if (match.bucket === target) {
      current += 1;
      best = Math.max(best, current);
    } else {
      current = 0;
    }
  }
  return best;
}

function average(values) {
  const clean = values.filter((value) => Number.isFinite(value));
  if (!clean.length) {
    return null;
  }
  return clean.reduce((sum, value) => sum + value, 0) / clean.length;
}

function rate(numerator, denominator) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) {
    return null;
  }
  return numerator / denominator;
}

function rateFromBuckets(values) {
  const clean = values.filter((value) => value === "W" || value === "L");
  if (!clean.length) {
    return null;
  }
  return clean.filter((value) => value === "W").length / clean.length;
}

function downsample(points, limit) {
  if (points.length <= limit) {
    return points;
  }

  const sampled = [];
  const lastIndex = points.length - 1;
  for (let index = 0; index < limit; index += 1) {
    const sourceIndex = Math.round((index * lastIndex) / (limit - 1));
    sampled.push(points[sourceIndex]);
  }
  return sampled;
}
