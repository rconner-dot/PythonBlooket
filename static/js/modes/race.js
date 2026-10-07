/**
 * Python Race (id "race") — race the bots to the finish line.
 *
 * Every correct answer drives the player's blook forward by the question's points
 * (Easy 100 / Medium 250 / Hard 500). Every 3rd answer in a row is a "Nitro" worth
 * +50%. Wrong answers stall. Bots answer simulated questions on their own clocks
 * (skill-based speed + accuracy, and — in Mixed — they pick difficulties like a
 * person would). The race ends the moment anyone crosses the line; everyone else
 * is ranked by distance. Score = distance (capped at the race length) + a
 * placement bonus.
 *
 * The rules are small pure functions (exported for tests and the balance
 * simulator); play(ctx) wires them to the DOM. One ctx.setInterval drives a race
 * clock that pauses while the tab is hidden or a dialog (e.g. "Quit?") is open,
 * and every wait goes through ctx.*, so quitting never leaks a timer.
 */

import { isModalOpen } from "../ui.js";

// ---------------------------------------------------------------------------
// Tuning
// ---------------------------------------------------------------------------

export const LENGTHS = [3000, 6000, 10000];
export const DEFAULT_LENGTH = 6000;
export const BOT_COUNTS = [3, 5];
export const NITRO_EVERY = 3; // every 3rd answer in a row…
export const NITRO_BONUS = 0.5; // …moves you +50% further
/**
 * A wrong answer stalls your engine: no new question until the stall is over
 * (counted on the race clock from the moment you answered, so reading the
 * explanation usually hides it). Misses in a row stall longer, and so do misses
 * on harder (higher-scoring) questions, so clicking random answers fast can't
 * outrun the bots.
 */
export const STALL_MS = [3000, 6000, 9000, 12000];
const DIFF_STALL = { 1: 0.75, 2: 1, 3: 1.35 };
/** Placement bonus as a fraction of the race length. */
export const PLACE_BONUS = { 1: 0.25, 2: 0.15, 3: 0.05 };
export const POINTS = { 1: 100, 2: 250, 3: 500 };
/** The mix the server uses for "Mixed" (pyblooket/questions MIXED_WEIGHTS). */
export const MIXED_WEIGHTS = { 1: 0.45, 2: 0.35, 3: 0.2 };

/**
 * Bot skill levels. Each bot draws its own average seconds-per-question from
 * `meanSec`; every question then varies ±25% and is scaled by difficulty, so a
 * Normal bot answers a Medium question every ≈ 8–16 s. Tuned with a simulator
 * (player models incl. stalls): a solid player (~80% correct, ~10 s per question)
 * wins ≈65% of default races (6,000, 3 Normal bots, Mixed); a beginner (~60%,
 * slower) wins 30–45% against Easy bots; Hard bots need ~90% accuracy and quick
 * answers; clicking random answers fast wins ≈0–10% against Normal bots.
 */
export const BOT_SKILLS = {
  easy: { id: "easy", label: "Easy", accuracy: 0.55, meanSec: [13, 16], lean: -0.08 },
  normal: { id: "normal", label: "Normal", accuracy: 0.7, meanSec: [11, 13], lean: 0 },
  hard: { id: "hard", label: "Hard", accuracy: 0.85, meanSec: [8.5, 10], lean: 0.06 },
};
/** Like people, bots are quicker and surer on easy questions, slower and shakier on hard ones. */
const DIFF_TIME = { 1: 0.75, 2: 1, 3: 1.35 };
const DIFF_ACCURACY = { 1: 0.07, 2: 0, 3: -0.08 };
const JITTER = 0.25;
/** Gentle rubber band: a bot 30% of the track ahead of you is ≈10% slower (and vice versa). */
const RUBBER_BAND = 0.35;

const TICK_MS = 100;
const COUNTDOWN_STEP_MS = 750;
const FINISH_HOLD_MS = 1100; // let the winner slide over the line before the podium
const PODIUM_MS = 4500; // podium auto-continues to RESULTS (button skips)
const TOAST_GAP_MS = 3500;

// ---------------------------------------------------------------------------
// Pure rules
// ---------------------------------------------------------------------------

export function clamp(x, lo, hi) {
  return Math.min(hi, Math.max(lo, x));
}

export function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export function fmtNum(n) {
  return Math.round(Number(n) || 0).toLocaleString("en-US");
}

/** "2:31.4" — race clock with tenths. */
export function fmtRaceTime(ms) {
  const tenths = Math.max(0, Math.floor((Number(ms) || 0) / 100));
  const s = Math.floor(tenths / 10);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}.${tenths % 10}`;
}

/** Validate the setup options (values arrive as-is from localStorage-backed settings). */
export function readOptions(raw = {}) {
  const o = raw && typeof raw === "object" ? raw : {};
  const length = LENGTHS.includes(Number(o.length)) ? Number(o.length) : DEFAULT_LENGTH;
  const bots = BOT_COUNTS.includes(Number(o.bots)) ? Number(o.bots) : 3;
  const skill = typeof o.skill === "string" && Object.prototype.hasOwnProperty.call(BOT_SKILLS, o.skill) ? o.skill : "normal";
  return { length, bots, skill };
}

export function isNitro(streak) {
  return streak > 0 && streak % NITRO_EVERY === 0;
}

/** Movement for a correct answer worth `points`, given the streak *including* this answer. */
export function moveFor(points, streak) {
  if (!points) return { gain: 0, nitro: false };
  const nitro = isNitro(streak);
  return { gain: Math.round(points * (nitro ? 1 + NITRO_BONUS : 1)), nitro };
}

/** Outcome of one answer for a racer whose current streak is `streakBefore`. */
export function answerOutcome(correct, points, streakBefore) {
  const streak = correct ? streakBefore + 1 : 0;
  return { correct: !!correct, streak, ...moveFor(correct ? points : 0, streak) };
}

/** Stall after the `missesInRow`-th wrong answer in a row on a `difficulty` question (0 = no stall). */
export function stallMs(missesInRow, difficulty = 2) {
  if (!(missesInRow > 0)) return 0;
  return Math.round(STALL_MS[Math.min(missesInRow, STALL_MS.length) - 1] * (DIFF_STALL[difficulty] || 1));
}

export function placementBonus(place, length) {
  return Math.round(((PLACE_BONUS[place] || 0) * length) / 10) * 10;
}

export function raceScore(dist, length, place) {
  return Math.round(clamp(dist, 0, length)) + placementBonus(place, length);
}

/** Expected points per question at a difficulty setting (for the "≈ N answers" hint). */
export function averagePoints(setting) {
  const d = Number(setting);
  if (POINTS[d]) return POINTS[d];
  return Object.entries(MIXED_WEIGHTS).reduce((sum, [k, w]) => sum + POINTS[k] * w, 0);
}

/**
 * Standings: whoever finished first, then everyone else by distance; on equal
 * distance, whoever got there earlier is ahead. Stable for full ties.
 */
export function rankRacers(racers) {
  return racers
    .map((r, i) => ({ r, i }))
    .sort((a, b) => {
      const fa = a.r.finishMs ?? Infinity;
      const fb = b.r.finishMs ?? Infinity;
      if (fa !== fb) return fa - fb;
      if (b.r.dist !== a.r.dist) return b.r.dist - a.r.dist;
      return (a.r.reachedMs ?? 0) - (b.r.reachedMs ?? 0) || a.i - b.i;
    })
    .map((x) => x.r);
}

export function weightedPick(weights, rng = Math.random) {
  const entries = Object.entries(weights).filter(([, w]) => w > 0);
  const total = entries.reduce((sum, [, w]) => sum + w, 0);
  let r = rng() * total;
  for (const [key, w] of entries) {
    r -= w;
    if (r < 0) return key;
  }
  return entries[entries.length - 1][0];
}

/**
 * Which difficulty a bot answers next. With a fixed game difficulty everyone gets
 * the same questions. In Mixed a bot behaves like a person: it starts from the
 * normal mix, gets braver on a streak, plays it safe right after a miss, and
 * stronger bots lean towards harder questions.
 */
export function pickBotDifficulty(setting, bot, skill, rng = Math.random) {
  const fixed = Number(setting);
  if (POINTS[fixed]) return fixed;
  let shift = skill.lean || 0;
  if (bot.streak >= 2) shift += 0.1;
  if (bot.missed) shift -= 0.12;
  const w = { ...MIXED_WEIGHTS };
  w[3] = clamp(w[3] + shift, 0.05, 0.6);
  w[1] = clamp(w[1] - shift, 0.12, 0.8);
  return Number(weightedPick(w, rng));
}

export function botAccuracy(skill, difficulty) {
  return clamp(skill.accuracy + (DIFF_ACCURACY[difficulty] || 0), 0.05, 0.98);
}

/**
 * Milliseconds a bot spends on its next question. `gap` = (bot − player distance)
 * / race length, used for the gentle rubber band.
 */
export function botThinkMs(bot, difficulty, gap = 0, rng = Math.random) {
  const jitter = 1 - JITTER + rng() * 2 * JITTER;
  const rubber = 1 + clamp(gap, -0.3, 0.3) * RUBBER_BAND;
  return Math.round(bot.meanSec * (DIFF_TIME[difficulty] || 1) * jitter * rubber * 1000);
}

export function newRacer(info, extra = {}) {
  return {
    id: info.id,
    name: info.name,
    avatar: info.avatar,
    color: info.color,
    isYou: false,
    dist: 0,
    streak: 0,
    missed: false,
    nitros: 0,
    correct: 0,
    answered: 0,
    finishMs: null,
    reachedMs: 0,
    ...extra,
  };
}

export function makeBot(info, skill, rng = Math.random) {
  const [lo, hi] = skill.meanSec;
  return newRacer(info, { meanSec: lo + rng() * (hi - lo), nextAt: 0, nextDiff: 2 });
}

/** A bot answers a `difficulty` question (pure: returns the outcome, doesn't touch the bot). */
export function botAnswer(bot, skill, difficulty, rng = Math.random) {
  const correct = rng() < botAccuracy(skill, difficulty);
  return { ...answerOutcome(correct, POINTS[difficulty] || 0, bot.streak), difficulty };
}

/** Apply an answer outcome to a racer. Returns true if it just crossed the finish line. */
export function applyOutcome(racer, outcome, length, clockMs) {
  racer.answered++;
  racer.streak = outcome.streak;
  racer.missed = !outcome.correct;
  if (outcome.correct) racer.correct++;
  if (outcome.nitro) racer.nitros++;
  if (outcome.gain > 0) {
    racer.dist = Math.min(length, racer.dist + outcome.gain);
    racer.reachedMs = clockMs;
  }
  if (racer.dist >= length && racer.finishMs == null) {
    racer.finishMs = clockMs;
    return true;
  }
  return false;
}

/** Bots from ctx.randomBots(), never wearing the player's blook. */
function pickBots(ctx, n) {
  const bots = ctx.randomBots(n);
  const used = new Set([ctx.player.avatar, ...bots.map((b) => b.avatar)]);
  const spare = ctx.shuffle(ctx.AVATARS.filter((a) => !used.has(a)));
  return bots.map((b, i) => ({
    ...b,
    id: `bot${i}`,
    avatar: b.avatar === ctx.player.avatar ? spare.pop() || "🤖" : b.avatar,
  }));
}

// ---------------------------------------------------------------------------
// Mode
// ---------------------------------------------------------------------------

export default {
  id: "race",
  name: "Python Race",
  icon: "🏁",
  tagline: "Answer fast, hit Nitro and beat the bots to the flag!",
  description:
    "Race your blook against the bots! Every correct answer drives you forward by the question's points — Easy +100, Medium +250, Hard +500 — so harder questions push you further.\n" +
    "Get 3 in a row for a 🚀 Nitro boost: +50% on that answer (again at 6, 9…). A wrong answer stalls your engine for a few seconds — longer if you keep missing — while the bots keep driving.\n" +
    "The race ends as soon as anyone crosses the line. Score = distance covered + a placement bonus (1st +25% of the track, 2nd +15%, 3rd +5%).",
  difficultySelectable: true,
  options: [
    { key: "length", label: "Race length", choices: [[3000, "3,000"], [6000, "6,000"], [10000, "10,000"]], default: DEFAULT_LENGTH },
    { key: "bots", label: "Rivals", choices: [[3, "3 bots"], [5, "5 bots"]], default: 3 },
    { key: "skill", label: "Bot skill", choices: [["easy", "Easy"], ["normal", "Normal"], ["hard", "Hard"]], default: "normal" },
  ],
  scoreLabel: "Race points",

  async play(ctx) {
    const { el } = ctx;
    const rng = Math.random;
    const opts = readOptions(ctx.settings.options);
    const L = opts.length;
    const skill = BOT_SKILLS[opts.skill];
    const setting = ctx.settings.difficulty;

    const you = newRacer({ id: "you", name: ctx.player.name || "Player", avatar: ctx.player.avatar, color: "var(--c-yellow)" }, { isYou: true });
    const bots = pickBots(ctx, opts.bots).map((b) => makeBot(b, skill, rng));
    const racers = [you, ...bots];

    const state = {
      running: false,
      over: false,
      paused: false,
      clockMs: 0,
      shownSecond: -1,
      winner: null,
      leaderId: null,
      place: 1,
      finalStretch: false,
      lastToastAt: -Infinity,
      missRun: 0, // player's wrong answers in a row
      stallMs: 0, // length of the current stall
      stallUntil: 0, // race clock (ms) when the player's engine restarts
    };
    let endRace;
    const raceEnded = new Promise((resolve) => (endRace = resolve));

    // ---- scene ---------------------------------------------------------------
    const hud = buildHud();
    const track = buildTrack();
    const askBox = el("div", { class: "race-ask" });
    const stage = el("div", { class: "game-stage race-stage" }, hud.node, track.node, askBox);
    ctx.root.append(stage);
    for (const r of racers) renderRacer(r);
    refreshStandings(false);

    function buildHud() {
      const placeNum = el("b", { class: "race-hud-big", text: "1st" });
      const distNum = el("b", { class: "race-hud-big", text: "0" });
      const distFill = el("i", { class: "race-hud-bar-fill" });
      const leaderTick = el("i", { class: "race-hud-bar-leader", hidden: true });
      const pips = Array.from({ length: NITRO_EVERY }, () => el("i", { class: "race-pip" }));
      const nitroBox = el(
        "div",
        { class: "race-hud-item race-hud-nitro", title: `${NITRO_EVERY} correct in a row = Nitro (+50%)` },
        el("span", { class: "race-hud-label", text: "Nitro" }),
        el("span", { class: "race-hud-value" }, el("span", { class: "race-pips", "aria-hidden": "true" }, pips), el("span", { class: "race-nitro-icon", "aria-hidden": "true", text: "🚀" }))
      );
      const clock = el("b", { class: "race-hud-big", text: "0:00" });
      const placeBox = el(
        "div",
        { class: "race-hud-item race-hud-place" },
        el("span", { class: "race-hud-label", text: "Place" }),
        el("span", { class: "race-hud-value" }, placeNum, el("small", { class: "race-hud-of", text: `/${racers.length}` }))
      );
      const node = el(
        "div",
        { class: "race-hud", role: "group", "aria-label": "Race status" },
        placeBox,
        el(
          "div",
          { class: "race-hud-item race-hud-dist" },
          el("span", { class: "race-hud-label", text: "Distance" }),
          el("span", { class: "race-hud-value" }, distNum, el("small", { class: "race-hud-of", text: `/${fmtNum(L)}` })),
          el("span", { class: "race-hud-bar", "aria-hidden": "true" }, distFill, leaderTick)
        ),
        nitroBox,
        el("div", { class: "race-hud-item race-hud-time" }, el("span", { class: "race-hud-label", text: "Time" }), el("span", { class: "race-hud-value" }, clock))
      );
      return { node, placeBox, placeNum, distNum, distFill, leaderTick, pips, nitroBox, clock };
    }

    function buildTrack() {
      const lanes = new Map();
      for (const r of racers) {
        const runner = el(
          "div",
          { class: "race-runner", style: { "--p": "0" } },
          el("span", { class: "race-trail", "aria-hidden": "true" }),
          el("span", { class: "race-flame", "aria-hidden": "true", text: "🔥" }),
          ctx.blook(r.avatar, { size: 40 })
        );
        const place = el("span", { class: "race-place", "aria-hidden": "true", text: "–" });
        const pct = el("span", { class: "race-pct", text: "0%" });
        const lane = el(
          "div",
          { class: ["race-lane", r.isYou && "is-you"], role: "listitem", style: { "--lane-color": r.color } },
          place,
          el("span", { class: "race-name", title: r.name, text: r.isYou ? "You" : r.name }),
          el(
            "div",
            { class: "race-road" },
            el("span", { class: "race-road-name", "aria-hidden": "true", text: r.isYou ? "YOU" : r.name }),
            el("div", { class: "race-rail" }, runner)
          ),
          pct
        );
        lanes.set(r.id, { lane, runner, place, pct });
      }
      const ruler = el(
        "div",
        { class: "race-ruler", "aria-hidden": "true" },
        el(
          "div",
          { class: "race-ruler-rail" },
          [0, 0.25, 0.5, 0.75].map((f) => el("span", { class: "race-mark", style: { "--p": String(f) }, text: f === 0 ? "START" : fmtNum(L * f) })),
          el("span", { class: "race-mark race-mark-finish", style: { "--p": "1" } }, el("span", { class: "race-flag", text: "🏁" }), fmtNum(L))
        )
      );
      const flashLayer = el("div", { class: "race-flash", "aria-hidden": "true" });
      const live = el("div", { class: "sr-only", "aria-live": "polite" });
      const node = el(
        "section",
        { class: ["race-track", racers.length > 4 && "race-many"], "aria-label": `Race track, ${fmtNum(L)} to the finish` },
        ruler,
        el("div", { class: "race-lanes", role: "list" }, [...lanes.values()].map((l) => l.lane)),
        flashLayer,
        live
      );
      return { node, lanes, flashLayer, live };
    }

    // ---- rendering -------------------------------------------------------------
    function popup(r, text, kind) {
      const { runner } = track.lanes.get(r.id);
      const node = el("span", { class: ["race-pop", `race-pop-${kind}`], "aria-hidden": "true", text });
      runner.append(node);
      ctx.setTimeout(() => node.remove(), 1400);
    }

    /** Restart a one-shot CSS animation class on an element. */
    function retrigger(node, cls, ms) {
      node.classList.remove(cls);
      void node.offsetWidth;
      node.classList.add(cls);
      if (ms) ctx.setTimeout(() => node.classList.remove(cls), ms);
    }

    function renderRacer(r, outcome = null) {
      const { lane, runner, pct } = track.lanes.get(r.id);
      const p = clamp(r.dist / L, 0, 1);
      runner.style.setProperty("--p", p.toFixed(4));
      pct.textContent = `${Math.floor(p * 100)}%`;
      lane.setAttribute("aria-label", `${r.isYou ? "You" : r.name}: ${Math.floor(p * 100)}% of the track`);
      if (!outcome) return;
      if (outcome.correct) {
        runner.classList.toggle("is-nitro-move", outcome.nitro);
        retrigger(runner, "race-go", outcome.nitro ? 1500 : 1000);
        if (outcome.nitro) retrigger(runner, "race-nitro", 1500);
        popup(r, outcome.nitro ? `🚀+${fmtNum(outcome.gain)}` : `+${fmtNum(outcome.gain)}`, outcome.nitro ? "nitro" : `d${outcome.difficulty || 2}`);
      } else {
        retrigger(runner, "race-stall", 700);
        popup(r, r.isYou ? "💨 stalled" : "💨", "stall");
      }
    }

    function renderHud() {
      hud.distFill.style.width = `${clamp(you.dist / L, 0, 1) * 100}%`;
      const filled = you.streak % NITRO_EVERY;
      hud.pips.forEach((pip, i) => pip.classList.toggle("on", i < filled));
      hud.nitroBox.classList.toggle("is-ready", filled === NITRO_EVERY - 1);
    }

    function flash(text, kind = "info", ms = 1100) {
      const node = el("span", { class: ["race-flash-text", `race-flash-${kind}`], text });
      track.flashLayer.replaceChildren(node);
      ctx.setTimeout(() => node.remove(), ms);
    }

    function announce(text) {
      track.live.textContent = text;
    }

    function maybeToast(message, type) {
      if (state.clockMs - state.lastToastAt < TOAST_GAP_MS || state.over) return;
      state.lastToastAt = state.clockMs;
      ctx.toast(message, type, 2200);
    }

    /** Re-rank everyone, update place badges/HUD, and react to lead changes. */
    function refreshStandings(react = true) {
      const ranked = rankRacers(racers);
      ranked.forEach((r, i) => {
        const { place } = track.lanes.get(r.id);
        place.textContent = String(i + 1);
        place.dataset.place = String(i + 1);
      });
      const place = ranked.indexOf(you) + 1;
      if (place !== state.place) {
        const better = place < state.place;
        state.place = place;
        if (react) retrigger(hud.placeBox, better ? "race-up" : "race-down", 700);
      }
      hud.placeNum.textContent = ordinal(place);
      hud.placeBox.dataset.place = String(place);
      const leader = ranked[0];
      const bestBot = ranked.find((r) => !r.isYou);
      hud.leaderTick.style.left = `${clamp(bestBot.dist / L, 0, 1) * 100}%`;
      if (hud.leaderTick.textContent !== bestBot.avatar) hud.leaderTick.textContent = bestBot.avatar;
      hud.leaderTick.title = `${bestBot.name} (best bot)`;
      hud.leaderTick.hidden = bestBot.dist <= 0;
      if (react && leader.dist > 0 && leader.id !== state.leaderId) {
        if (leader.isYou) {
          maybeToast("You took the lead! 🏎️", "success");
          announce("You took the lead!");
        } else if (state.leaderId === you.id) {
          maybeToast(`${leader.name} overtook you!`, "error");
          announce(`${leader.name} took the lead.`);
        }
      }
      if (leader.dist > 0) state.leaderId = leader.id;
      if (react && !state.finalStretch && leader.dist >= L * 0.8 && !state.over) {
        state.finalStretch = true;
        flash("FINAL STRETCH!", "stretch", 1400);
      }
      return ranked;
    }

    function updateClock() {
      const s = Math.floor(state.clockMs / 1000);
      if (s !== state.shownSecond) {
        state.shownSecond = s;
        hud.clock.textContent = ctx.formatTime(s);
      }
    }

    // ---- race flow -------------------------------------------------------------
    function finishLine(r) {
      if (state.over) return;
      state.over = true;
      state.running = false;
      state.winner = r;
      const { runner, lane } = track.lanes.get(r.id);
      runner.classList.add("race-finished");
      lane.classList.add("is-winner");
      track.node.classList.add("is-over");
      endRace(r);
    }

    function scheduleBot(b, first = false) {
      b.nextDiff = pickBotDifficulty(setting, b, skill, rng);
      const ms = botThinkMs(b, b.nextDiff, (b.dist - you.dist) / L, rng);
      // Stagger the first answers so the bots don't all leave the line together.
      b.nextAt = state.clockMs + (first ? ms * (0.75 + rng() * 0.35) : ms);
    }

    function botTurn(b) {
      const outcome = botAnswer(b, skill, b.nextDiff, rng);
      const crossed = applyOutcome(b, outcome, L, state.clockMs);
      renderRacer(b, outcome);
      refreshStandings();
      if (crossed) finishLine(b);
      else scheduleBot(b);
    }

    let lastTick = performance.now();
    ctx.setInterval(() => {
      const now = performance.now();
      const dt = Math.min(now - lastTick, 500);
      lastTick = now;
      if (!state.running || state.over) return;
      const paused = document.hidden || isModalOpen();
      if (paused !== state.paused) {
        state.paused = paused;
        track.node.classList.toggle("is-paused", paused);
      }
      if (paused) return;
      state.clockMs += dt;
      if (state.stallUntil && state.clockMs >= state.stallUntil) {
        state.stallUntil = 0;
        track.lanes.get(you.id).runner.classList.remove("race-stalled");
      }
      // Earliest answers first, so two bots in one tick land in the right order.
      for (const b of [...bots].sort((x, y) => x.nextAt - y.nextAt)) {
        if (state.over) break;
        if (state.clockMs >= b.nextAt) botTurn(b);
      }
      updateClock();
    }, TICK_MS);

    // Outcome of the player's answer, computed once per question (pointsLabel and
    // onAnswered both need it, whichever the engine calls first).
    const outcomes = new Map();
    function outcomeFor(res) {
      const key = res.question?.id ?? res;
      if (!outcomes.has(key)) {
        outcomes.clear();
        outcomes.set(key, { ...answerOutcome(res.correct, res.points, you.streak), difficulty: res.question?.difficulty });
      }
      return outcomes.get(key);
    }

    function onAnswered(res) {
      if (state.over) return;
      const o = outcomeFor(res);
      const crossed = applyOutcome(you, o, L, state.clockMs);
      renderRacer(you, o);
      const from = Number(hud.distNum.dataset.v || 0);
      hud.distNum.dataset.v = String(you.dist);
      ctx.animateNumber(hud.distNum, from, you.dist, 700);
      renderHud();
      if (o.nitro) {
        flash("🚀 NITRO!", "nitro", 1300);
        retrigger(hud.nitroBox, "race-nitro-fire", 1300);
        hud.pips.forEach((pip) => pip.classList.add("on"));
        ctx.setTimeout(() => renderHud(), 650);
        ctx.setTimeout(() => ctx.sfx("levelup"), 260);
        announce(`Nitro! You moved ${o.gain} forward.`);
      } else if (!o.correct) {
        retrigger(hud.nitroBox, "race-nitro-lost", 600);
      }
      state.missRun = o.correct ? 0 : state.missRun + 1;
      if (!o.correct) {
        state.stallMs = stallMs(state.missRun, o.difficulty);
        state.stallUntil = state.clockMs + state.stallMs;
        track.lanes.get(you.id).runner.classList.add("race-stalled");
      }
      refreshStandings();
      if (crossed) finishLine(you);
    }

    const askOpts = {
      correctDelay: 1100,
      onAnswered,
      pointsLabel: (res) => {
        if (state.over) return "🏁 (race over)";
        const o = outcomeFor(res);
        return o.nitro ? `+${fmtNum(o.gain)} 🚀 Nitro!` : `+${fmtNum(o.gain)}`;
      },
    };

    // Keep the answer hotkeys away from the (now frozen) question once the race is over.
    const keyGuard = (e) => {
      if (!state.over) return;
      const inOverlay = e.target instanceof Element && e.target.closest(".race-finish");
      if (/^[1-9]$/.test(e.key) || (!inOverlay && (e.key === "Enter" || e.key === " "))) e.preventDefault();
    };
    window.addEventListener("keydown", keyGuard, true);
    ctx.onCleanup(() => window.removeEventListener("keydown", keyGuard, true));

    // ---- start / finish ----------------------------------------------------------
    async function countdown() {
      const answersNeeded = Math.ceil(L / averagePoints(setting));
      const lights = Array.from({ length: 3 }, () => el("i", { class: "race-light" }));
      const lightBox = el("div", { class: "race-lights", "aria-hidden": "true" }, lights);
      const status = el("p", { class: "race-intro-status", "aria-live": "polite", text: "Engines on…" });
      askBox.replaceChildren(
        el(
          "section",
          { class: "card race-intro pop-in" },
          lightBox,
          el("h2", { class: "race-intro-title", text: "Get ready to race!" }),
          el(
            "ul",
            { class: "race-rules" },
            el("li", null, el("span", { "aria-hidden": "true", text: "✅" }), el("span", null, "Right answer = drive forward: ", el("b", { class: "race-chip diff-1", text: "+100" }), " ", el("b", { class: "race-chip diff-2", text: "+250" }), " ", el("b", { class: "race-chip diff-3", text: "+500" }))),
            el("li", null, el("span", { "aria-hidden": "true", text: "🚀" }), el("span", null, el("b", { text: "3 in a row" }), " = Nitro, +50% on that answer")),
            el("li", null, el("span", { "aria-hidden": "true", text: "💨" }), el("span", null, "Wrong answer = your engine stalls for a few seconds (the bots don't!)")),
            el("li", null, el("span", { "aria-hidden": "true", text: "🏁" }), el("span", null, `First to ${fmtNum(L)} wins — about ${answersNeeded} correct answers.`))
          ),
          status
        )
      );
      ctx.prefetch();
      await ctx.sleep(900);
      for (let i = 0; i < 3; i++) {
        lights[i].classList.add("on");
        status.textContent = String(3 - i);
        flash(String(3 - i), "count", COUNTDOWN_STEP_MS);
        ctx.sfx("tick");
        await ctx.sleep(COUNTDOWN_STEP_MS);
      }
      lightBox.classList.add("go");
      status.textContent = "GO!";
      flash("GO!", "go", 900);
      ctx.sfx("levelup");
      track.node.classList.add("is-live");
      await ctx.sleep(450);
    }

    /**
     * After a wrong answer the engine stays stalled until state.stallUntil (race
     * clock, so it also pauses with the race). Shows a small cool-down card if the
     * player clicked Continue before the stall was over.
     */
    async function waitOutStall() {
      const total = state.stallMs || 1;
      if (state.stallUntil && state.clockMs < state.stallUntil - 250 && !state.over) {
        const overheated = state.missRun >= 2;
        const left = el("b", { text: "" });
        const fill = el("i");
        askBox.replaceChildren(
          el(
            "section",
            { class: ["card", "race-stall-card", "pop-in", overheated && "is-hot"], role: "status" },
            el("div", { class: "race-stall-icon", "aria-hidden": "true", text: overheated ? "🔥" : "💨" }),
            el("h2", { class: "race-stall-title", text: overheated ? "Engine overheating!" : "Engine stalled!" }),
            el("p", { class: "race-stall-text" }, "Back on track in ", left, "…"),
            el("div", { class: "race-stall-bar", "aria-hidden": "true" }, fill),
            el("p", { class: "race-stall-hint", text: overheated ? "Misses in a row stall you longer — slow down and read the code!" : "Wrong answers stall your engine. Think it through — the bots won't wait!" })
          )
        );
        while (state.stallUntil && !state.over) {
          const ms = Math.max(0, state.stallUntil - state.clockMs);
          left.textContent = `${(ms / 1000).toFixed(1)} s`;
          fill.style.transform = `scaleX(${clamp(ms / total, 0, 1)})`;
          await Promise.race([ctx.sleep(100), raceEnded]);
        }
      }
    }

    /** On small screens the track scrolls away while answering; bring it back for each new question. */
    function bringTrackIntoView() {
      if (track.node.getBoundingClientRect().top < hud.node.getBoundingClientRect().bottom - 4) {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }

    async function finishSequence() {
      const ranked = refreshStandings(false);
      const place = ranked.indexOf(you) + 1;
      const won = place === 1;
      renderHud();
      flash(won ? "🏁 YOU WIN!" : "🏁 FINISH!", won ? "win" : "finish", 1600);
      announce(won ? "You crossed the finish line first!" : `${state.winner.name} crossed the finish line.`);
      if (won) {
        ctx.sfx("chest");
        const rect = track.lanes.get(you.id).runner.getBoundingClientRect();
        ctx.confetti({ count: 90, x: clamp((rect.left + rect.width / 2) / window.innerWidth, 0, 1), y: clamp(rect.top / window.innerHeight, 0, 1) });
      } else {
        ctx.sfx("hit");
      }
      await ctx.sleep(FINISH_HOLD_MS);

      // Podium overlay, then RESULTS.
      let skip;
      const skipped = new Promise((resolve) => (skip = resolve));
      const goBtn = el("button", { class: "btn btn-green btn-lg race-finish-go", type: "button", onClick: () => skip() }, "See results ", el("span", { "aria-hidden": "true", text: "▶" }));
      const podiumOrder = [ranked[1], ranked[0], ranked[2]].filter(Boolean);
      const podium = el(
        "div",
        { class: "race-podium" },
        podiumOrder.map((r) => {
          const pos = ranked.indexOf(r) + 1;
          return el(
            "div",
            { class: ["race-step", `race-step-${pos}`, r.isYou && "is-you"] },
            ctx.blook(r.avatar, { size: pos === 1 ? 64 : 50, className: pos === 1 ? "bounce" : "" }),
            el("span", { class: "race-step-name", text: r.isYou ? "You" : r.name }),
            el("span", { class: "race-step-sub", text: r.finishMs != null ? fmtRaceTime(r.finishMs) : `${Math.floor((r.dist / L) * 100)}%` }),
            el("span", { class: "race-step-block", text: String(pos) })
          );
        })
      );
      const line = won
        ? `You crossed the line in ${fmtRaceTime(you.finishMs)}!`
        : place <= 3
          ? `You finished ${ordinal(place)} — ${fmtNum(L - you.dist)} short of the flag.`
          : `You finished ${ordinal(place)} of ${racers.length}. Next time!`;
      const overlay = el(
        "div",
        { class: ["race-finish", won ? "is-won" : "is-lost"], role: "dialog", "aria-label": "Race results" },
        el(
          "div",
          { class: "card race-finish-card pop-in" },
          el("div", { class: "race-finish-flag", "aria-hidden": "true", text: won ? "🏆" : "🏁" }),
          el("h2", { class: "race-finish-title", text: won ? "You win the race!" : `${state.winner.name} wins!` }),
          podium,
          el("p", { class: "race-finish-line", text: line }),
          el("div", { class: "race-finish-bar", "aria-hidden": "true" }, el("i", { style: { animationDuration: `${PODIUM_MS}ms` } })),
          goBtn
        )
      );
      // Mounted on <body> (not ctx.root): the core's .screen keeps a filled transform
      // from its entrance animation, which would anchor position:fixed to the screen
      // instead of the viewport. The wrapper carries the .mode-race scope.
      const layer = el("div", { class: "mode-race race-finish-layer" }, overlay);
      document.body.append(layer);
      ctx.onCleanup(() => layer.remove());
      try {
        goBtn.focus({ preventScroll: true });
      } catch {
        /* ignore */
      }
      await Promise.race([ctx.sleep(PODIUM_MS), skipped]);

      const bonus = placementBonus(place, L);
      const details = [
        ["Placement", `${ordinal(place)} of ${racers.length}`],
        ["Finish time", you.finishMs != null ? fmtRaceTime(you.finishMs) : `Did not finish (${Math.floor((you.dist / L) * 100)}% at ${fmtRaceTime(state.clockMs)})`],
        ["Distance", `${fmtNum(Math.min(you.dist, L))} / ${fmtNum(L)}`],
        ["Placement bonus", bonus ? `+${fmtNum(bonus)}` : "—"],
        ["Nitros used", `${you.nitros} 🚀`],
        ["Correct answers", `${you.correct} / ${you.answered}`],
      ];
      if (!won) details.push(["Winner", `${state.winner.avatar} ${state.winner.name}`]);
      details.push(["Rivals", `${bots.length} ${skill.label} bots`]);
      return {
        score: raceScore(you.dist, L, place),
        won,
        headline: won ? "🏆 1st place!" : `${ordinal(place)} place`,
        details,
      };
    }

    // ---- go! -------------------------------------------------------------------
    await countdown();
    state.running = true;
    lastTick = performance.now();
    for (const b of bots) scheduleBot(b, true);

    while (!state.over) {
      bringTrackIntoView();
      await Promise.race([ctx.ask(askBox, askOpts), raceEnded]);
      await waitOutStall();
    }
    return finishSequence();
  },
};
