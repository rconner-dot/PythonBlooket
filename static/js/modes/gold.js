/**
 * Gold Quest (id "gold") — Blooket-style treasure hunt against three bots.
 *
 * Loop: ctx.ask() a question. Correct -> pick 1 of 3 face-down chests; the chosen
 * one flips, then all three are revealed. Chests hold gold scaled by the question's
 * points, x2 / x3 multipliers (capped), "steal 25%" and "swap" (the player picks a
 * victim), "lose 25%" or nothing. Bots open chests in the background on their own
 * timers. Most gold when the countdown hits 0:00 wins.
 *
 * The rules are small pure functions (exported for tests and the balance
 * simulator); play(ctx) wires them to the DOM. Every timer goes through ctx.* and
 * every wait rejects with AbortError when the game ends, so quitting never leaks.
 */

// ---------------------------------------------------------------------------
// Tuning
// ---------------------------------------------------------------------------

const PLAYER_ID = "you";
const CHEST_COUNT = 3;
const NEXT_DELAY_MS = 2600; // auto-continue after a chest is resolved
const TIMEUP_DELAY_MS = 3200; // "Time's up!" standings before RESULTS
const PICK_GUARD_MS = 300; // ignore chest clicks right after they appear (double-clicks)

/** Chest odds for the player (relative weights). Gold is the most common prize. */
export const CHEST_WEIGHTS = { gold: 46, double: 10, triple: 4, steal: 10, swap: 5, lose: 12, nothing: 13 };

/**
 * Bot skill levels. A bot "answers a question" every `turn` seconds (random in the
 * range), gets it right with probability `accuracy`, and then opens a chest like
 * the player. Tuned with a simulator so that on Normal the best bot ends up
 * roughly level with a good player (≈80% correct, ≈10 s per question).
 */
export const BOT_SKILLS = {
  easy: { label: "Easy", accuracy: 0.55, turn: [13, 21], goldScale: 0.75, aim: 0.35, weights: { ...CHEST_WEIGHTS, steal: 6, swap: 2 } },
  normal: { label: "Normal", accuracy: 0.7, turn: [11, 17], goldScale: 0.95, aim: 0.6, weights: { ...CHEST_WEIGHTS, steal: 7, swap: 3 } },
  hard: { label: "Hard", accuracy: 0.8, turn: [9.5, 14.5], goldScale: 1.05, aim: 0.8, weights: { ...CHEST_WEIGHTS, steal: 8, swap: 4 } },
};

export const OUTCOMES = {
  gold: { icon: "💰", name: "Gold", tone: "gold" },
  double: { icon: "✨", name: "Double gold!", tone: "double" },
  triple: { icon: "💎", name: "Triple gold!", tone: "triple" },
  steal: { icon: "🦹", name: "Steal 25%", tone: "steal" },
  swap: { icon: "🔄", name: "Swap!", tone: "swap" },
  lose: { icon: "💸", name: "Lose 25%", tone: "lose" },
  nothing: { icon: "💨", name: "Nothing", tone: "nothing" },
};

const POINTS_BY_DIFFICULTY = { 1: 100, 2: 250, 3: 500 };
/** Bots, like people, are a bit quicker/more accurate on easy questions and slower on hard ones. */
const ACCURACY_ADJUST = { 100: 0.06, 250: 0, 500: -0.08 };
const TURN_SCALE = { 1: 0.85, 2: 1, 3: 1.2 };
const MEDALS = ["🥇", "🥈", "🥉"];
const CONSOLATIONS = [
  "No chest this time — the next one's yours!",
  "No chest… but now you know! 🧠",
  "Shake it off — more chests ahead!",
  "The chests will wait for you. Keep going!",
];

// ---------------------------------------------------------------------------
// Pure rules
// ---------------------------------------------------------------------------

export function round10(x) {
  return Math.round(x / 10) * 10;
}

/** 12,345 — or 123K for really big piles (keeps the phone strip narrow). */
export function fmtGold(n) {
  const v = Math.round(Number(n) || 0);
  return Math.abs(v) >= 100000 ? `${Math.round(v / 1000)}K` : v.toLocaleString();
}

/** "+1,200" / "−300" / "±0" */
export function signedGold(n) {
  const v = Math.round(Number(n) || 0);
  return `${v > 0 ? "+" : v < 0 ? "−" : "±"}${fmtGold(Math.abs(v))}`;
}

export function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

/** Pick a key of `weights` with probability proportional to its weight. */
export function weightedPick(weights, rng = Math.random) {
  const entries = Object.entries(weights).filter(([, w]) => w > 0);
  if (!entries.length) return "nothing";
  const total = entries.reduce((sum, [, w]) => sum + w, 0);
  let r = rng() * total;
  for (const [key, w] of entries) {
    r -= w;
    if (r < 0) return key;
  }
  return entries[entries.length - 1][0];
}

/** Base points of a question at `difficulty` (1|2|3|'mixed'). */
export function questionPoints(difficulty, rng = Math.random) {
  if (POINTS_BY_DIFFICULTY[difficulty]) return POINTS_BY_DIFFICULTY[difficulty];
  return [100, 250, 500][Math.floor(rng() * 3)];
}

/** Seconds until a bot's next "question" (scaled by the game's question difficulty). */
export function botTurnSeconds(skill, difficulty, rng = Math.random) {
  const [lo, hi] = skill.turn;
  return (lo + rng() * (hi - lo)) * (TURN_SCALE[difficulty] || 1);
}

/** Gold in a plain gold chest: points × (0.5–1.5), rounded to 10. */
export function goldAmount(points, rng = Math.random, scale = 1) {
  return Math.max(10, round10(points * (0.5 + rng()) * scale));
}

/** Max gain from a multiplier chest, so one lucky chest can't run away with the game. */
export function multiplierCap(points, factor) {
  const base = 2000 + 4 * points;
  return factor >= 3 ? base * 1.5 : base;
}

export function multiplierGain(gold, factor, points) {
  return Math.min(Math.max(0, gold) * (factor - 1), multiplierCap(points, factor));
}

export function stealAmount(gold, pct = 25) {
  const g = Math.max(0, gold);
  return Math.min(g, round10((g * pct) / 100));
}

/**
 * Chest odds adjusted to the situation: multipliers/losses are duds with no gold,
 * there is nothing to steal while every rival is broke, and the leader never
 * rolls a swap (it could only hurt them).
 */
export function chestWeights(selfGold, othersGold, base = CHEST_WEIGHTS) {
  const w = { ...base };
  if (selfGold <= 0) {
    w.double *= 0.2;
    w.triple *= 0.2;
    w.lose *= 0.3;
  }
  if (Math.max(0, ...othersGold) <= 0) w.steal = 0;
  if (!othersGold.some((g) => g > selfGold)) w.swap = 0; // a swap only shows up when it could help
  return w;
}

export function rollOutcome(points, weights, rng = Math.random, goldScale = 1) {
  const type = weightedPick(weights, rng);
  if (type === "gold") return { type, amount: goldAmount(points, rng, goldScale) };
  if (type === "steal" || type === "lose") return { type, pct: 25 };
  return { type };
}

export function rollChests(points, selfGold, othersGold, rng = Math.random, n = CHEST_COUNT) {
  const weights = chestWeights(selfGold, othersGold);
  return Array.from({ length: n }, () => rollOutcome(points, weights, rng));
}

/**
 * Gold changes for an outcome. `targetGold` is the steal/swap victim's gold.
 * Returns {self, target} deltas (target is 0 unless steal/swap).
 */
export function resolveOutcome(outcome, selfGold, targetGold = 0, points = 100) {
  switch (outcome.type) {
    case "gold":
      return { self: outcome.amount, target: 0 };
    case "double":
      return { self: multiplierGain(selfGold, 2, points), target: 0 };
    case "triple":
      return { self: multiplierGain(selfGold, 3, points), target: 0 };
    case "steal": {
      const amount = stealAmount(targetGold, outcome.pct || 25);
      return { self: amount, target: 0 - amount }; // 0 - x, not -x: no "-0"
    }
    case "swap":
      return { self: targetGold - selfGold, target: selfGold - targetGold };
    case "lose":
      return { self: 0 - stealAmount(selfGold, outcome.pct || 25), target: 0 };
    default:
      return { self: 0, target: 0 };
  }
}

/** Big text + small caption for the back of a revealed chest. */
export function chestFace(outcome) {
  switch (outcome.type) {
    case "gold":
      return { big: `+${fmtGold(outcome.amount)}`, small: "Gold" };
    case "double":
      return { big: "×2", small: "Double!" };
    case "triple":
      return { big: "×3", small: "Triple!" };
    case "steal":
      return { big: "25%", small: "Steal" };
    case "swap":
      return { big: "⇄", small: "Swap" };
    case "lose":
      return { big: "−25%", small: "Lose" };
    default:
      return { big: "0", small: "Nothing" };
  }
}

export function richest(players) {
  return players.reduce((best, p) => (!best || p.gold > best.gold ? p : best), null);
}

function randomItem(list, rng) {
  return list[Math.floor(rng() * list.length)];
}

/** Bots rob the leader with probability `aim`, otherwise someone random who has gold. */
export function pickStealTarget(others, rng = Math.random, aim = 0.7) {
  const withGold = others.filter((p) => p.gold > 0);
  if (!withGold.length) return null;
  return rng() < aim ? richest(withGold) : randomItem(withGold, rng);
}

/**
 * Bots swap with the richest rival with probability `aim`, otherwise with a random
 * rival who is richer than them. With nobody richer they must take the least-bad swap.
 */
export function pickSwapTarget(self, others, rng = Math.random, aim = 0.7) {
  const richer = others.filter((p) => p.gold > self.gold);
  if (!richer.length || rng() < aim) return richest(others);
  return randomItem(richer, rng);
}

/**
 * One background "turn" for a bot: answer (maybe wrong), open a chest, pick a
 * victim if needed. Pure: returns the event (or null for a wrong answer) without
 * changing anyone's gold.
 */
export function simulateBotTurn(bot, players, skill, difficulty, rng = Math.random) {
  const points = questionPoints(difficulty, rng);
  if (rng() >= skill.accuracy + (ACCURACY_ADJUST[points] || 0)) return null;
  const others = players.filter((p) => p.id !== bot.id);
  const weights = chestWeights(bot.gold, others.map((p) => p.gold), skill.weights);
  let outcome = rollOutcome(points, weights, rng, skill.goldScale);
  let target = null;
  if (outcome.type === "steal") target = pickStealTarget(others, rng, skill.aim);
  else if (outcome.type === "swap") target = pickSwapTarget(bot, others, rng, skill.aim);
  if ((outcome.type === "steal" || outcome.type === "swap") && !target) outcome = { type: "nothing" };
  const d = resolveOutcome(outcome, bot.gold, target ? target.gold : 0, points);
  return { bot, outcome, points, target, selfDelta: d.self, targetDelta: d.target };
}

/** Players sorted by gold (desc); ties keep their previous order so rows don't jitter. */
export function rankPlayers(players, previousOrder = []) {
  const prev = new Map(previousOrder.map((id, i) => [id, i]));
  return players
    .map((p, i) => ({ p, i }))
    .sort((a, b) => b.p.gold - a.p.gold || (prev.get(a.p.id) ?? a.i) - (prev.get(b.p.id) ?? b.i))
    .map((x) => x.p);
}

/** 1-based place; ties share the better place. */
export function placementOf(players, id) {
  const me = players.find((p) => p.id === id);
  return 1 + players.filter((p) => p.id !== id && p.gold > me.gold).length;
}

/** The RESULT object for the engine. */
export function buildResult({ players, tally, skillLabel, minutes }) {
  const me = players.find((p) => p.id === PLAYER_ID);
  const place = placementOf(players, PLAYER_ID);
  const won = place === 1 && me.gold > 0;
  const tied = won && players.some((p) => p.id !== PLAYER_ID && p.gold === me.gold);
  const leader = richest(players.filter((p) => p.id !== PLAYER_ID));
  let headline;
  if (place === 1 && !won) headline = "No gold for anyone — try again!";
  else if (won && tied) headline = `You tied for 1st with ${fmtGold(me.gold)} gold!`;
  else if (won) headline = `You won with ${fmtGold(me.gold)} gold!`;
  else if (place === 2 && leader && leader.gold - me.gold <= Math.max(300, leader.gold * 0.15)) headline = "2nd place — so close!";
  else if (place === players.length) headline = `${ordinal(place)} place — keep practising!`;
  else headline = `${ordinal(place)} place`;

  const standings = rankPlayers(players).map((p) => {
    const pl = placementOf(players, p.id);
    const tag = MEDALS[pl - 1] || `#${pl}`;
    return [`${tag} ${p.avatar} ${p.id === PLAYER_ID ? `${p.name} (you)` : p.name}`, `${fmtGold(p.gold)} gold`];
  });

  const details = [
    ["Placement", `${MEDALS[place - 1] || "🏅"} ${ordinal(place)} of ${players.length}`],
    ...standings,
    ["Chests opened", String(tally.chests)],
    ["Biggest chest", tally.biggest ? `+${fmtGold(tally.biggest.gain)} (${tally.biggest.label})` : "—"],
    ["Gold stolen", tally.stolen ? `${fmtGold(tally.stolen)} gold` : "0"],
    ["Stolen from you", tally.stolenFromYou ? `${fmtGold(tally.stolenFromYou)} gold` : "0"],
    ["Game", `${minutes} min · ${skillLabel} bots`],
  ];
  return { score: Math.max(0, Math.round(me.gold)), won, headline, details };
}

// ---------------------------------------------------------------------------
// Artwork
// ---------------------------------------------------------------------------

const CHEST_SVG = `<svg viewBox="0 0 120 104" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
  <ellipse cx="60" cy="98" rx="50" ry="5" fill="rgba(0,0,0,.28)"/>
  <path d="M10 50V32Q10 12 32 12H88Q110 12 110 32V50Z" fill="#c9772f" stroke="#5e2c0c" stroke-width="4" stroke-linejoin="round"/>
  <path d="M16 27Q22 19 34 18" stroke="#e9a35f" stroke-width="4" fill="none" stroke-linecap="round"/>
  <rect x="10" y="50" width="100" height="44" rx="6" fill="#a65a22" stroke="#5e2c0c" stroke-width="4"/>
  <path d="M14 72H106" stroke="#7d3f14" stroke-width="3" opacity=".55"/>
  <rect x="22" y="12" width="12" height="82" fill="#ffc21a" stroke="#9c6b00" stroke-width="3"/>
  <rect x="86" y="12" width="12" height="82" fill="#ffc21a" stroke="#9c6b00" stroke-width="3"/>
  <rect x="8" y="46" width="104" height="9" rx="3" fill="#ffd34d" stroke="#9c6b00" stroke-width="3"/>
  <rect x="47" y="40" width="26" height="28" rx="6" fill="#ffe27a" stroke="#9c6b00" stroke-width="3"/>
  <circle cx="60" cy="51" r="4" fill="#5e2c0c"/>
  <path d="M60 53V61" stroke="#5e2c0c" stroke-width="4" stroke-linecap="round"/>
  <path d="M25 16V24" stroke="#fff3b0" stroke-width="2.5" stroke-linecap="round" opacity=".9"/>
  <path d="M89 16V24" stroke="#fff3b0" stroke-width="2.5" stroke-linecap="round" opacity=".9"/>
</svg>`;

// ---------------------------------------------------------------------------
// Small DOM helpers (all abortable / cleaned up via ctx)
// ---------------------------------------------------------------------------

function abortErrorFrom(ctx) {
  const reason = ctx.signal && ctx.signal.reason;
  if (reason && reason.name === "AbortError") return reason;
  try {
    return new DOMException("Game ended", "AbortError");
  } catch {
    const err = new Error("Game ended");
    err.name = "AbortError";
    return err;
  }
}

/**
 * Promise that settles via `setup(resolve, addCleanup)` and rejects with
 * AbortError when the game ends. Cleanups run exactly once either way.
 */
function waitFor(ctx, setup) {
  return new Promise((resolve, reject) => {
    if (ctx.aborted) return reject(abortErrorFrom(ctx));
    const offs = [];
    let settled = false;
    const settle = (fn, value) => {
      if (settled) return;
      settled = true;
      while (offs.length) {
        try {
          offs.pop()();
        } catch {
          /* ignore */
        }
      }
      fn(value);
    };
    const onAbort = () => settle(reject, abortErrorFrom(ctx));
    ctx.signal.addEventListener("abort", onAbort, { once: true });
    offs.push(() => ctx.signal.removeEventListener("abort", onAbort));
    try {
      setup((value) => settle(resolve, value), (fn) => offs.push(fn));
    } catch (err) {
      settle(reject, err);
    }
  });
}

function isTyping(target) {
  return !!target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

/** Hotkeys are off while a dialog (e.g. "Quit this game?") is open or while typing. */
function keyAllowed(e) {
  return !e.defaultPrevented && !e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey && !isTyping(e.target) && !document.querySelector(".modal-overlay");
}

function prefersReducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// The game
// ---------------------------------------------------------------------------

async function runGoldQuest(ctx) {
  const { el } = ctx;
  const opts = ctx.settings.options || {};
  const minutes = [3, 5, 7].includes(Number(opts.duration)) ? Number(opts.duration) : 5;
  const skillKey = BOT_SKILLS[opts.bots] ? opts.bots : "normal";
  const skill = BOT_SKILLS[skillKey];
  const totalMs = minutes * 60 * 1000;
  const rng = Math.random;
  const reducedMotion = prefersReducedMotion();

  // ---- players ------------------------------------------------------------
  const me = {
    id: PLAYER_ID,
    name: ctx.player?.name || ctx.settings.playerName || "Player",
    avatar: ctx.player?.avatar || ctx.settings.avatar || "🐸",
    gold: 0,
    isPlayer: true,
  };
  const botList = ctx.randomBots(3);
  const usedAvatars = new Set([me.avatar, ...botList.map((b) => b.avatar)]);
  for (const b of botList) {
    if (b.avatar !== me.avatar) continue; // never give a bot the player's blook
    const spare = (ctx.AVATARS || []).find((a) => !usedAvatars.has(a));
    if (spare) {
      b.avatar = spare;
      usedAvatars.add(spare);
    }
  }
  const bots = botList.map((b, i) => ({ id: `bot${i}`, name: b.name, avatar: b.avatar, gold: 0, isPlayer: false, timer: 0 }));
  const players = [me, ...bots];
  const tally = { chests: 0, biggest: null, stolen: 0, stolenFromYou: 0 };

  let over = false;
  let endAt = 0;
  let order = players.map((p) => p.id);
  let resolveFinished;
  const finished = new Promise((r) => (resolveFinished = r));
  const boardListeners = new Set();

  /** Never resolves; rejects with AbortError when the game is finished/quit. */
  const halt = () => waitFor(ctx, () => {});
  /** Await something, then freeze if the clock ran out meanwhile. */
  const guard = async (promise) => {
    const value = await promise;
    if (over) await halt();
    return value;
  };

  // ---- layout ---------------------------------------------------------------
  const timerText = el("span", { class: "gold-timer-text", text: ctx.formatTime(totalMs / 1000) });
  const timerFill = el("span", { class: "gold-timer-fill" });
  const timerBox = el(
    "div",
    { class: "gold-timer", role: "timer", "aria-label": "Time left" },
    el("span", { class: "gold-timer-icon", "aria-hidden": "true", text: "⏰" }),
    el("span", { class: "gold-timer-body" }, el("span", { class: "gold-timer-label", text: "Time left" }), timerText, el("span", { class: "gold-timer-track", "aria-hidden": "true" }, timerFill))
  );

  const rows = new Map();
  const boardList = el("ol", { class: "gold-board-list", style: { "--n": players.length } });
  for (const p of players) {
    const num = el("b", { class: "gold-row-num", text: "0" });
    const rank = el("span", { class: "gold-row-rank", "aria-hidden": "true", text: "1" });
    const row = el(
      "li",
      { class: ["gold-row", p.isPlayer && "gold-row-me"], style: { "--rank": players.indexOf(p) } },
      rank,
      el("span", { class: "gold-row-blook" }, ctx.blook(p.avatar, { size: 40 }), el("span", { class: "gold-crown", "aria-hidden": "true", text: "👑" })),
      el(
        "span",
        { class: "gold-row-info" },
        el("span", { class: "gold-row-name" }, el("span", { class: "gold-row-name-text", text: p.name }), p.isPlayer ? el("span", { class: "gold-you", text: "You" }) : null),
        el("span", { class: "gold-row-gold" }, el("span", { class: "gold-coin", "aria-hidden": "true" }), num)
      )
    );
    boardList.append(row);
    rows.set(p.id, { row, num, rank, shown: 0 });
  }

  const feedList = el("ul", { class: "gold-feed-list" });
  const feed = el(
    "section",
    { class: "gold-feed", "aria-label": "Recent chests" },
    el("h3", { class: "gold-side-title", text: "Live feed" }),
    feedList
  );
  feedList.append(el("li", { class: "gold-feed-empty", text: "Chests opened by everyone show up here." }));

  const aside = el(
    "aside",
    { class: "gold-side", "aria-label": "Time and leaderboard" },
    timerBox,
    el("section", { class: "gold-board", "aria-label": "Leaderboard" }, el("h3", { class: "gold-side-title", text: "Leaderboard" }), boardList),
    feed
  );

  const hudGold = el("b", { class: "gold-hud-num", text: "0" });
  const hudPlace = el("b", { class: "gold-hud-place", text: "1st" });
  const hudChests = el("b", { text: "0" });
  const hud = el(
    "div",
    { class: "gold-hud" },
    el("div", { class: "gold-hud-pill gold-hud-gold" }, el("span", { class: "gold-coin gold-coin-lg", "aria-hidden": "true" }), el("span", { class: "gold-hud-label", text: "Your gold" }), hudGold),
    el("div", { class: "gold-hud-pill" }, el("span", { "aria-hidden": "true", text: "🏆" }), el("span", { class: "gold-hud-label", text: "Place" }), hudPlace),
    el("div", { class: "gold-hud-pill" }, el("span", { "aria-hidden": "true", text: "🎁" }), el("span", { class: "gold-hud-label", text: "Chests" }), hudChests)
  );
  const stage = el("div", { class: "gold-stage" });
  const game = el("div", { class: "gold-game" }, aside, el("div", { class: "gold-main" }, hud, stage));
  ctx.root.append(game);

  // Sticky sidebar / phone strip sit right under the app's sticky top bar.
  const topbar = document.querySelector(".game-topbar");
  const syncTop = () => game.style.setProperty("--gold-top", `${topbar ? topbar.getBoundingClientRect().height : 64}px`);
  syncTop();
  if (topbar && typeof ResizeObserver === "function") {
    const ro = new ResizeObserver(syncTop);
    ro.observe(topbar);
    ctx.onCleanup(() => ro.disconnect());
  }

  // ---- number tweening (own rAF loop so it stops on quit) --------------------
  const tweens = new WeakMap();
  function tween(node, from, to, ms = 700) {
    const prev = tweens.get(node);
    if (prev) prev.cancelled = true;
    if (reducedMotion || from === to || ms <= 0) {
      node.textContent = fmtGold(to);
      return;
    }
    const job = { cancelled: false };
    tweens.set(node, job);
    const t0 = performance.now();
    const step = (now) => {
      if (job.cancelled || ctx.aborted) return;
      const p = Math.min(1, (now - t0) / ms);
      node.textContent = fmtGold(from + (to - from) * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function restartClass(node, cls) {
    node.classList.remove(cls);
    void node.offsetWidth;
    node.classList.add(cls);
  }

  function floatDelta(id, delta) {
    const r = rows.get(id);
    if (!r || !delta) return;
    const bubble = el("span", { class: ["gold-float", delta > 0 ? "gold-float-up" : "gold-float-down"], "aria-hidden": "true", text: signedGold(delta) });
    r.row.append(bubble);
    r.row.classList.add("gold-row-floating"); // lift the row so its bubble isn't hidden under a neighbour
    ctx.setTimeout(() => {
      bubble.remove();
      if (!r.row.querySelector(".gold-float")) r.row.classList.remove("gold-row-floating");
    }, 1400);
    restartClass(r.row, delta > 0 ? "gold-flash-up" : "gold-flash-down");
  }

  // ---- leaderboard ------------------------------------------------------------
  let lastLeaderToast = 0;
  let iWasLeading = false;
  function refreshBoard(deltas = {}) {
    const ranked = rankPlayers(players, order);
    order = ranked.map((p) => p.id);
    ranked.forEach((p, i) => {
      const r = rows.get(p.id);
      const place = placementOf(players, p.id);
      r.row.style.setProperty("--rank", i);
      r.rank.textContent = String(place);
      r.row.dataset.place = String(place);
      r.row.classList.toggle("gold-row-leader", place === 1 && p.gold > 0);
      r.row.setAttribute("aria-label", `${ordinal(place)}: ${p.isPlayer ? `${p.name} (you)` : p.name}, ${fmtGold(p.gold)} gold`);
      if (r.shown !== p.gold) {
        tween(r.num, r.shown, p.gold);
        r.shown = p.gold;
      }
    });
    for (const [id, d] of Object.entries(deltas)) floatDelta(id, d);

    const place = placementOf(players, PLAYER_ID);
    hudPlace.textContent = ordinal(place);
    hudPlace.dataset.place = String(place);
    if (Number(hudGold.dataset.value || 0) !== me.gold) {
      tween(hudGold, Number(hudGold.dataset.value || 0), me.gold);
      hudGold.dataset.value = String(me.gold);
      restartClass(hudGold, "gold-bump");
    }
    const leading = place === 1 && me.gold > 0 && bots.every((b) => b.gold < me.gold);
    if (leading && !iWasLeading && !over && performance.now() - lastLeaderToast > 20000) {
      lastLeaderToast = performance.now();
      const t = ctx.toast("You took the lead!", "success", 2200);
      setToastIcon(t, "👑");
    }
    iWasLeading = leading;
    for (const fn of boardListeners) fn();
  }

  function setToastIcon(node, icon) {
    const iconEl = node && node.querySelector && node.querySelector(".toast-icon");
    if (iconEl) iconEl.textContent = icon;
  }

  function logEvent(p, text, tone) {
    const empty = feedList.querySelector(".gold-feed-empty");
    if (empty) empty.remove();
    feedList.prepend(
      el(
        "li",
        { class: ["gold-feed-item", `gold-tone-${tone}`] },
        ctx.blook(p.avatar, { size: 26 }),
        el("span", { class: "gold-feed-text" }, el("b", { text: p.isPlayer ? "You" : p.name }), " ", text)
      )
    );
    while (feedList.children.length > 5) feedList.lastElementChild.remove();
  }

  function describe(type, gain, target, actorIsPlayer) {
    const tName = target ? (target.isPlayer ? "you" : target.name) : "";
    switch (type) {
      case "gold":
        return `found ${signedGold(gain)} gold`;
      case "double":
        return gain > 0 ? `doubled up! ${signedGold(gain)}` : "doubled… zero 😅";
      case "triple":
        return gain > 0 ? `tripled! ${signedGold(gain)}` : "tripled… zero 😅";
      case "steal":
        return gain > 0 ? `stole ${fmtGold(gain)} from ${tName}` : `tried to rob ${tName} — empty pockets!`;
      case "swap":
        return `swapped with ${tName} (${signedGold(gain)})`;
      case "lose":
        return gain < 0 ? `lost ${fmtGold(-gain)} gold` : "lost 25%… of nothing";
      default:
        return actorIsPlayer ? "found an empty chest" : "found nothing";
    }
  }

  // ---- clock ------------------------------------------------------------------
  let lastWhole = Infinity;
  let tickId = 0;
  function tick() {
    if (over) return;
    const leftMs = Math.max(0, endAt - performance.now());
    const left = leftMs / 1000;
    timerText.textContent = ctx.formatTime(left);
    timerFill.style.transform = `scaleX(${leftMs / totalMs})`;
    timerBox.classList.toggle("gold-timer-warn", left <= 60 && left > 15);
    timerBox.classList.toggle("gold-timer-urgent", left <= 15);
    const whole = Math.ceil(left);
    if (left <= 5 && whole < lastWhole && whole > 0) ctx.sfx("tick");
    lastWhole = whole;
    if (leftMs <= 0) endGame();
  }

  // ---- bots -------------------------------------------------------------------
  function scheduleBot(bot, first = false) {
    const seconds = first ? 3 + rng() * 6 : botTurnSeconds(skill, ctx.settings.difficulty, rng);
    bot.timer = ctx.setTimeout(() => {
      if (over) return;
      botTurn(bot);
      scheduleBot(bot);
    }, seconds * 1000);
  }

  function botTurn(bot) {
    const ev = simulateBotTurn(bot, players, skill, ctx.settings.difficulty, rng);
    if (!ev) return; // got the question wrong
    const { outcome, target, selfDelta, targetDelta } = ev;
    bot.gold = Math.max(0, bot.gold + selfDelta);
    if (target) target.gold = Math.max(0, target.gold + targetDelta);
    const deltas = { [bot.id]: selfDelta };
    if (target) deltas[target.id] = targetDelta;
    refreshBoard(deltas);
    logEvent(bot, describe(outcome.type, selfDelta, target, false), OUTCOMES[outcome.type].tone);

    if (target && target.isPlayer && targetDelta !== 0) {
      if (outcome.type === "steal") {
        tally.stolenFromYou += -targetDelta;
        setToastIcon(ctx.toast(`${bot.name} stole ${fmtGold(-targetDelta)} gold from you!`, "error", 3200), bot.avatar);
        ctx.sfx("hit");
      } else if (outcome.type === "swap") {
        const msg = targetDelta < 0 ? `${bot.name} swapped gold with you! (${signedGold(targetDelta)})` : `${bot.name} swapped with you — lucky! (${signedGold(targetDelta)})`;
        setToastIcon(ctx.toast(msg, targetDelta < 0 ? "error" : "success", 3200), bot.avatar);
        ctx.sfx(targetDelta < 0 ? "hit" : "levelup");
      }
    }
  }

  // ---- waiting for input --------------------------------------------------------
  /** Resolve with the index of the clicked button (or its 1..n hotkey). */
  function waitChoice(buttons, guardMs = PICK_GUARD_MS) {
    const shownAt = performance.now();
    return waitFor(ctx, (done, onCleanup) => {
      const ready = () => performance.now() - shownAt >= guardMs;
      buttons.forEach((btn, i) => {
        const onClick = () => {
          if (ready() && !btn.disabled) done(i);
        };
        btn.addEventListener("click", onClick);
        onCleanup(() => btn.removeEventListener("click", onClick));
      });
      const onKey = (e) => {
        if (!keyAllowed(e) || !buttons[0].isConnected) return;
        const n = Number(e.key);
        if (Number.isInteger(n) && n >= 1 && n <= buttons.length && !buttons[n - 1].disabled) {
          e.preventDefault();
          if (ready()) done(n - 1);
        }
      };
      document.addEventListener("keydown", onKey);
      onCleanup(() => document.removeEventListener("keydown", onKey));
    });
  }

  /** "Next ▶" button + auto-continue bar; click / Enter / Space skips. */
  function waitContinue(container, { label = "Next question", ms = NEXT_DELAY_MS, btnClass = "btn-blue" } = {}) {
    const btn = el("button", { class: ["btn", btnClass, "gold-next"], type: "button" }, `${label} `, el("span", { "aria-hidden": "true", text: "▶" }));
    const bar = el("span", { class: "gold-autobar", "aria-hidden": "true" }, el("i", { style: { animationDuration: `${ms}ms` } }));
    const wrap = el("div", { class: "gold-next-row" }, btn, bar);
    container.append(wrap);
    try {
      btn.focus({ preventScroll: true });
    } catch {
      /* ignore */
    }
    const shownAt = performance.now();
    return waitFor(ctx, (done, onCleanup) => {
      const id = ctx.setTimeout(done, ms);
      onCleanup(() => ctx.clearTimeout(id));
      const onClick = () => done();
      btn.addEventListener("click", onClick);
      onCleanup(() => btn.removeEventListener("click", onClick));
      const onKey = (e) => {
        if (!keyAllowed(e) || !btn.isConnected) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (performance.now() - shownAt > 350) done();
        }
      };
      document.addEventListener("keydown", onKey);
      onCleanup(() => document.removeEventListener("keydown", onKey));
    }).then(() => {
      btn.disabled = true;
    });
  }

  function scrollStageIntoView() {
    const top = stage.getBoundingClientRect().top;
    const stickyBottom = aside.getBoundingClientRect().bottom;
    const narrow = window.matchMedia && window.matchMedia("(max-width: 760px)").matches;
    const limit = narrow ? stickyBottom : Number.parseFloat(getComputedStyle(game).getPropertyValue("--gold-top")) || 64;
    if (top < limit - 1 || top > window.innerHeight * 0.6) {
      window.scrollTo({ top: Math.max(0, window.scrollY + top - limit - 12), behavior: reducedMotion ? "auto" : "smooth" });
    }
  }

  // ---- chests -------------------------------------------------------------------
  function renderChestPhase(points, question) {
    const lo = fmtGold(Math.max(10, round10(points * 0.5)));
    const hi = fmtGold(round10(points * 1.5));
    const chests = Array.from({ length: CHEST_COUNT }, (_, i) =>
      el(
        "button",
        { class: "gold-chest", type: "button", style: { "--i": i }, "aria-label": `Open chest ${i + 1}` },
        el(
          "span",
          { class: "gold-chest-inner" },
          el(
            "span",
            { class: "gold-chest-face gold-chest-front" },
            el("span", { class: "gold-chest-art", html: CHEST_SVG }),
            el("span", { class: "gold-chest-key", "aria-hidden": "true", text: String(i + 1) })
          ),
          el("span", { class: "gold-chest-face gold-chest-back", "aria-hidden": "true" })
        )
      )
    );
    const result = el("div", { class: "gold-result-area", "aria-live": "polite" });
    const diffLabel = question?.difficulty_label || { 100: "Easy", 250: "Medium", 500: "Hard" }[points] || "";
    const panel = el(
      "section",
      { class: "gold-chest-phase", "aria-label": "Pick a treasure chest" },
      el("h2", { class: "gold-phase-title" }, el("span", { "aria-hidden": "true", text: "🎁 " }), "Pick a chest!"),
      el(
        "p",
        { class: "gold-phase-sub" },
        el("span", { class: `gold-diff-pill diff-${{ 100: 1, 250: 2, 500: 3 }[points] || 1}`, text: `${diffLabel} · ${points}` }),
        " ",
        el("span", { text: `Gold chests hold ${lo}–${hi}` })
      ),
      el("div", { class: "gold-chests" }, chests),
      result
    );
    stage.replaceChildren(panel);
    return { panel, chests, result };
  }

  function revealChest(chest, outcome, { chosen = false } = {}) {
    const info = OUTCOMES[outcome.type];
    const face = chestFace(outcome);
    const back = chest.querySelector(".gold-chest-back");
    back.className = `gold-chest-face gold-chest-back gold-tone-${info.tone}`;
    back.replaceChildren(
      el("span", { class: "gold-back-icon", "aria-hidden": "true", text: info.icon }),
      el("span", { class: "gold-back-big", text: face.big }),
      el("span", { class: "gold-back-small", text: face.small })
    );
    back.removeAttribute("aria-hidden");
    chest.querySelector(".gold-chest-front").setAttribute("aria-hidden", "true");
    chest.setAttribute("aria-label", `${chosen ? "Your chest" : "Other chest"}: ${face.small} ${face.big}`);
    chest.classList.add("gold-chest-flipped", chosen ? "gold-chest-chosen" : "gold-chest-other");
    if (chosen) chest.append(el("span", { class: "gold-chest-ribbon", "aria-hidden": "true", text: "Yours!" }));
  }

  function burstFrom(node, count = 60) {
    try {
      const r = node.getBoundingClientRect();
      ctx.confetti({ count, x: (r.left + r.width / 2) / window.innerWidth, y: (r.top + r.height / 3) / window.innerHeight });
    } catch {
      /* decoration only */
    }
  }

  function resultBanner(tone, icon, title, sub) {
    return el(
      "div",
      { class: ["gold-result", `gold-tone-${tone}`] },
      el("span", { class: "gold-result-icon", "aria-hidden": "true", text: icon }),
      el("div", { class: "gold-result-text" }, el("strong", { text: title }), sub ? el("span", { text: sub }) : null)
    );
  }

  /** Steal / swap: choose a bot. Values refresh live while bots keep playing. */
  async function pickVictim(kind, area) {
    const ranked = rankPlayers(bots, order);
    const buttons = ranked.map((b, i) => {
      const goldEl = el("span", { class: "gold-victim-gold" });
      const gainEl = el("span", { class: "gold-victim-gain" });
      const btn = el(
        "button",
        { class: "gold-victim", type: "button" },
        el("span", { class: "gold-victim-key", "aria-hidden": "true", text: String(i + 1) }),
        ctx.blook(b.avatar, { size: 44 }),
        el("span", { class: "gold-victim-who" }, el("span", { class: "gold-victim-name", text: b.name }), goldEl),
        gainEl
      );
      return { btn, bot: b, goldEl, gainEl };
    });
    const update = () => {
      for (const v of buttons) {
        const gain = kind === "steal" ? stealAmount(v.bot.gold) : v.bot.gold - me.gold;
        v.goldEl.textContent = `${fmtGold(v.bot.gold)} gold`;
        v.gainEl.textContent = signedGold(gain);
        v.gainEl.className = `gold-victim-gain ${gain > 0 ? "is-up" : gain < 0 ? "is-down" : "is-zero"}`;
        v.btn.setAttribute("aria-label", `${kind === "steal" ? "Steal from" : "Swap with"} ${v.bot.name}: ${fmtGold(v.bot.gold)} gold, you'd get ${signedGold(gain)}`);
      }
    };
    update();
    boardListeners.add(update);
    const title =
      kind === "steal"
        ? el("h3", { class: "gold-picker-title" }, "🦹 Steal 25% — who's your target?")
        : el("h3", { class: "gold-picker-title" }, "🔄 Swap! Trade gold totals with…");
    const picker = el("div", { class: ["gold-picker", `gold-picker-${kind}`] }, title, el("div", { class: "gold-victims" }, buttons.map((v) => v.btn)));
    area.replaceChildren(picker);
    try {
      buttons[0].btn.focus({ preventScroll: true });
    } catch {
      /* ignore */
    }
    try {
      picker.scrollIntoView({ block: "nearest", behavior: reducedMotion ? "auto" : "smooth" });
    } catch {
      /* ignore */
    }
    try {
      const idx = await guard(waitChoice(buttons.map((v) => v.btn), 150));
      ctx.sfx("click");
      return buttons[idx].bot;
    } finally {
      boardListeners.delete(update);
    }
  }

  async function chestRound(points, question) {
    const outcomes = rollChests(points, me.gold, bots.map((b) => b.gold), rng);
    const view = renderChestPhase(points, question);
    scrollStageIntoView();
    try {
      view.chests[0].focus({ preventScroll: true });
    } catch {
      /* ignore */
    }

    const pick = await guard(waitChoice(view.chests));
    const chosen = view.chests[pick];
    tally.chests++;
    hudChests.textContent = String(tally.chests);
    view.panel.classList.add("gold-picked");
    for (const c of view.chests) c.disabled = true;
    chosen.classList.add("gold-chest-opening");
    ctx.sfx("click");
    await guard(ctx.sleep(reducedMotion ? 50 : 420));
    chosen.classList.remove("gold-chest-opening");
    revealChest(chosen, outcomes[pick], { chosen: true });
    ctx.sfx("chest");
    await guard(ctx.sleep(reducedMotion ? 50 : 650));
    view.chests.forEach((c, i) => {
      if (i === pick) return;
      ctx.setTimeout(() => revealChest(c, outcomes[i]), reducedMotion ? 0 : 140 * (i < pick ? i : i - 1));
    });

    const outcome = outcomes[pick];
    const type = outcome.type;
    let gain = 0;
    let banner;
    let celebrate = false;

    if (type === "steal" || type === "swap") {
      await guard(ctx.sleep(reducedMotion ? 50 : 500));
      if (type === "steal" && bots.every((b) => b.gold <= 0)) {
        banner = resultBanner("nothing", "🕳️", "Nobody has any gold to steal!", "Their pockets are empty.");
      } else {
        const victim = await pickVictim(type, view.result);
        const d = resolveOutcome(outcome, me.gold, victim.gold, points);
        gain = d.self;
        me.gold = Math.max(0, me.gold + d.self);
        victim.gold = Math.max(0, victim.gold + d.target);
        refreshBoard({ [me.id]: d.self, [victim.id]: d.target });
        logEvent(me, describe(type, d.self, victim, true), OUTCOMES[type].tone);
        if (type === "steal") {
          tally.stolen += d.self;
          banner = d.self > 0
            ? resultBanner("steal", victim.avatar, `You stole ${fmtGold(d.self)} gold!`, `Sorry, ${victim.name}! 😈`)
            : resultBanner("nothing", victim.avatar, `${victim.name}'s pockets were empty!`, "Nothing to steal.");
          ctx.sfx(d.self > 0 ? "hit" : "click");
          celebrate = d.self >= points * 2;
        } else {
          banner =
            d.self >= 0
              ? resultBanner("swap", "🔄", `Swapped with ${victim.name}: ${signedGold(d.self)}!`, `You now have ${fmtGold(me.gold)} gold.`)
              : resultBanner("lose", "🔄", `Swapped with ${victim.name}: ${signedGold(d.self)}`, "Ouch — they had less than you.");
          ctx.sfx(d.self > 0 ? "levelup" : "wrong");
          celebrate = d.self >= points * 2;
        }
      }
    } else {
      const d = resolveOutcome(outcome, me.gold, 0, points);
      gain = d.self;
      me.gold = Math.max(0, me.gold + d.self);
      refreshBoard({ [me.id]: d.self });
      logEvent(me, describe(type, d.self, null, true), OUTCOMES[type].tone);
      if (type === "gold") {
        banner = resultBanner("gold", "💰", `+${fmtGold(gain)} gold!`, gain >= points * 1.3 ? "A heavy one! 💪" : null);
      } else if (type === "double" || type === "triple") {
        const factor = type === "double" ? 2 : 3;
        const capped = gain > 0 && gain >= multiplierCap(points, factor);
        banner =
          gain > 0
            ? resultBanner(type, OUTCOMES[type].icon, `${OUTCOMES[type].name} ${signedGold(gain)}`, capped ? "Max bonus for this question!" : null)
            : resultBanner("nothing", OUTCOMES[type].icon, `${OUTCOMES[type].name}`, `…but ${factor} × 0 is still 0 😅`);
        if (gain > 0) {
          ctx.sfx("levelup");
          celebrate = true;
        }
      } else if (type === "lose") {
        banner =
          gain < 0
            ? resultBanner("lose", "💸", `Oh no! You lost ${fmtGold(-gain)} gold`, "25% of your pile flew away…")
            : resultBanner("nothing", "💸", "Lose 25%… of nothing!", "Lucky you had no gold yet.");
        if (gain < 0) {
          ctx.sfx("wrong");
          restartClass(chosen, "gold-chest-sad");
        }
      } else {
        banner = resultBanner("nothing", "💨", "Nothing inside…", "Just dust and cobwebs.");
      }
    }

    if (gain > 0 && (!tally.biggest || gain > tally.biggest.gain)) tally.biggest = { gain, label: OUTCOMES[type].name.replace(/!$/, "") };
    if (celebrate && !reducedMotion) burstFrom(chosen, type === "triple" ? 110 : 60);

    view.result.replaceChildren(banner);
    await guard(waitContinue(view.result));
  }

  // ---- time's up -------------------------------------------------------------------
  function endGame() {
    if (over) return;
    over = true;
    for (const b of bots) ctx.clearTimeout(b.timer);
    ctx.clearInterval(tickId);
    timerText.textContent = "0:00";
    timerFill.style.transform = "scaleX(0)";
    timerBox.classList.remove("gold-timer-warn");
    timerBox.classList.add("gold-timer-urgent", "gold-timer-done");
    boardListeners.clear();

    const result = buildResult({ players, tally, skillLabel: skill.label, minutes });
    const ranked = rankPlayers(players, order);
    const list = el(
      "ol",
      { class: "gold-final-list" },
      ranked.map((p, i) => {
        const pl = placementOf(players, p.id);
        return el(
          "li",
          { class: ["gold-final-row", p.isPlayer && "gold-row-me", pl === 1 && "gold-final-winner"], style: { "--i": i } },
          el("span", { class: "gold-final-medal", "aria-hidden": "true", text: MEDALS[pl - 1] || `${pl}` }),
          ctx.blook(p.avatar, { size: 44 }),
          el("span", { class: "gold-final-name", text: p.isPlayer ? `${p.name} (you)` : p.name }),
          el("span", { class: "gold-final-gold" }, el("span", { class: "gold-coin", "aria-hidden": "true" }), fmtGold(p.gold)),
          el("span", { class: "sr-only", text: `${ordinal(pl)} place` })
        );
      })
    );
    const panel = el(
      "section",
      { class: ["gold-timeup", result.won ? "is-win" : "is-loss"], role: "status" },
      el("div", { class: "gold-timeup-clock", "aria-hidden": "true", text: "⏰" }),
      el("h2", { class: "gold-timeup-title", text: "Time's up!" }),
      el("p", { class: "gold-timeup-sub", text: result.headline }),
      list
    );
    // Replacing the stage detaches any open question card, so its hotkeys stop too.
    stage.replaceChildren(panel);
    ctx.sfx("levelup");
    try {
      window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
    } catch {
      /* ignore */
    }
    waitContinue(panel, { label: "See results", ms: TIMEUP_DELAY_MS, btnClass: "btn-green" }).then(
      () => resolveFinished(result),
      () => {} // quit during the splash: the engine handles it
    );
  }

  // ---- main loop -----------------------------------------------------------------------
  async function loop() {
    for (;;) {
      if (over) await halt();
      let consoled = false;
      const res = await guard(
        ctx.ask(stage, {
          correctDelay: 900,
          pointsLabel: () => "🎁 Chest time!",
          onAnswered: (r) => {
            if (over || r.correct || consoled) return;
            consoled = true;
            const head = stage.querySelector(".q-banner-head");
            if (head) head.append(el("span", { class: "gold-consolation", text: CONSOLATIONS[Math.floor(rng() * CONSOLATIONS.length)] }));
          },
        })
      );
      if (res.correct) await chestRound(res.points || res.question?.points || 100, res.question);
      if (!over) scrollStageIntoView();
    }
  }

  endAt = performance.now() + totalMs;
  tickId = ctx.setInterval(tick, 250);
  tick();
  bots.forEach((b) => scheduleBot(b, true));
  refreshBoard();

  return Promise.race([loop(), finished]);
}

export default {
  id: "gold",
  name: "Gold Quest",
  icon: "💰",
  color: "#ffb703",
  tagline: "Answer questions, open chests — steal, swap and double your way to the most gold!",
  description:
    "Race the clock against 3 bots! Answer a question correctly to pick 1 of 3 treasure chests: gold, double or triple gold, steal 25% from a rival, swap totals with someone… or lose 25%, or nothing at all. Wrong answers get no chest — and watch out, the bots steal too!\n" +
    "Harder questions are worth more, so their chests are bigger: Easy (100 pts) chests hold about 50–150 gold, Medium (250) about 130–380 and Hard (500) about 250–750. Have the most gold when time runs out to win — your gold is your score.",
  difficultySelectable: true,
  options: [
    { key: "duration", label: "Game length", choices: [[3, "3 min"], [5, "5 min"], [7, "7 min"]], default: 5 },
    { key: "bots", label: "Bot skill", choices: [["easy", "Easy"], ["normal", "Normal"], ["hard", "Hard"]], default: "normal" },
  ],
  scoreLabel: "Gold",

  async play(ctx) {
    return runGoldQuest(ctx);
  },
};
