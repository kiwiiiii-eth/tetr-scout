(() => {
  if (window.__tetrScoutBridgeInstalled) {
    return;
  }
  window.__tetrScoutBridgeInstalled = true;

  const EVENT_NAME = "tetr-scout:network-candidates";
  const KEY_HINT_PATTERN = /(user(name)?|player(name)?s?|opponent|enemy|owner|winner|loser|victor|target|foe|rival|left|right)/i;
  const STOP_WORDS = new Set([
    "AFTER",
    "ATTACK",
    "BACK",
    "BEFORE",
    "CTRL",
    "THE",
    "END",
    "FRAME",
    "FT3",
    "FT5",
    "HOLD",
    "LEFT",
    "NEXT",
    "PIECES",
    "RIGHT",
    "SCORE",
    "TIME",
    "USE",
    "VS",
    "DOWN",
    "SEEK",
    "SPEED",
    "DECREASE",
    "MATCH",
    "PLAYER",
    "PLAYERS",
    "QUEUE",
    "GAME",
    "TETR",
    "TETRIO",
    "TETRA"
  ]);
  const emittedNames = new Set();

  const normalizeCandidate = (value) => {
    const trimmed = String(value || "").trim();
    if (!/^[A-Za-z0-9_]{3,16}$/.test(trimmed)) {
      return "";
    }
    if (/^\d+$/.test(trimmed)) {
      return "";
    }
    if (STOP_WORDS.has(trimmed.toUpperCase())) {
      return "";
    }
    return trimmed;
  };

  const emitNames = (names, source, weight) => {
    const unique = [...new Set(names.map(normalizeCandidate).filter(Boolean))]
      .filter((name) => !emittedNames.has(name));

    if (!unique.length) {
      return;
    }

    unique.forEach((name) => emittedNames.add(name));
    window.dispatchEvent(
      new CustomEvent(EVENT_NAME, {
        detail: {
          names: unique,
          source,
          weight
        }
      })
    );
  };

  const extractNamesFromText = (text) => {
    if (typeof text !== "string" || !text) {
      return [];
    }

    const names = [];
    const quotedRegex = /"(?:username|user|owner|opponent|winner|loser|target|rival|enemy)"\s*:\s*"([A-Za-z0-9_]{3,16})"/gi;
    for (const match of text.matchAll(quotedRegex)) {
      names.push(match[1]);
    }

    return names;
  };

  const extractNamesFromValue = (value, keyHint = "", depth = 0, names = []) => {
    if (depth > 5 || value === null || value === undefined) {
      return names;
    }

    if (typeof value === "string") {
      const normalized = normalizeCandidate(value);
      if (normalized && (KEY_HINT_PATTERN.test(keyHint) || normalized.includes("_") || /[0-9]/.test(normalized))) {
        names.push(normalized);
      }
      return names;
    }

    if (Array.isArray(value)) {
      for (const item of value.slice(0, 30)) {
        extractNamesFromValue(item, keyHint, depth + 1, names);
      }
      return names;
    }

    if (typeof value === "object") {
      for (const [key, child] of Object.entries(value).slice(0, 40)) {
        const nextHint = KEY_HINT_PATTERN.test(key) ? key : keyHint;
        extractNamesFromValue(child, nextHint, depth + 1, names);
      }
    }

    return names;
  };

  const inspectMessage = (data, source) => {
    if (typeof data === "string") {
      const trimmed = data.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
          const parsed = JSON.parse(trimmed);
          emitNames(extractNamesFromValue(parsed), source, 18);
        } catch {
          emitNames(extractNamesFromText(trimmed), source, 14);
        }
      } else {
        emitNames(extractNamesFromText(trimmed), source, 12);
      }
      return;
    }

    if (data instanceof Blob && data.size > 0 && data.size < 200_000) {
      data.text()
        .then((text) => inspectMessage(text, source))
        .catch(() => {});
    }
  };

  const installCanvasHook = (prototype, source) => {
    if (!prototype || prototype.__tetrScoutHooked) {
      return;
    }
    prototype.__tetrScoutHooked = true;

    const wrapMethod = (methodName) => {
      const original = prototype[methodName];
      if (typeof original !== "function") {
        return;
      }

      prototype[methodName] = function patchedTextMethod(text, ...args) {
        try {
          const names = extractNamesFromValue(text, "username");
          if (names.length) {
            emitNames(names, source, 26);
          }
        } catch {
          // Ignore canvas text extraction issues.
        }
        return original.call(this, text, ...args);
      };
    };

    wrapMethod("fillText");
    wrapMethod("strokeText");
  };

  const OriginalWebSocket = window.WebSocket;
  window.WebSocket = function TetrScoutWebSocket(...args) {
    const socket = new OriginalWebSocket(...args);
    socket.addEventListener("message", (event) => {
      inspectMessage(event.data, "websocket");
    });
    return socket;
  };
  window.WebSocket.prototype = OriginalWebSocket.prototype;
  Object.setPrototypeOf(window.WebSocket, OriginalWebSocket);

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);

    try {
      const requestUrl = String(args[0]?.url || args[0] || "");
      if (requestUrl.includes("tetr.io") || requestUrl.includes("osk.sh")) {
        const clone = response.clone();
        const contentType = clone.headers.get("content-type") || "";
        if (contentType.includes("json") || requestUrl.includes("/api/")) {
          clone.text()
            .then((text) => inspectMessage(text, "fetch"))
            .catch(() => {});
        }
      }
    } catch {
      // Ignore bridge inspection errors.
    }

    return response;
  };

  installCanvasHook(window.CanvasRenderingContext2D?.prototype, "canvas");
  installCanvasHook(window.OffscreenCanvasRenderingContext2D?.prototype, "canvas");
})();
