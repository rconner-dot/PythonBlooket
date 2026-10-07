/**
 * Boss Battle — defeat a Python-themed boss by answering questions correctly.
 *
 *  - Correct answer: deal damage = question points (100 / 250 / 500), +10% per
 *    consecutive correct answer before it (max +50%); Hard questions have a 20%
 *    chance to CRIT for ×2.
 *  - Wrong answer / timeout: the boss hits back for 15–30 HP (Hardcore 20–35),
 *    +5 once it is enraged (below 30% HP).
 *  - Ends when the boss (win) or the player (defeat) reaches 0 HP.
 *    Score = damage dealt + (win ? 1,000 + remaining HP × 20 : 0).
 *
 * The game rules live in the small pure functions exported below (no DOM, no
 * randomness unless a roll is omitted); play() wires them to the battle view.
 * See ../engine.js for the mode contract.
 */

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

export const BOSSES = {
  serpent: {
    id: "serpent",
    name: "Syntax Serpent",
    emoji: "🐍",
    hp: 2500,
    shot: "🧪",
    intro: "Sssso… you think your code will parse?",
    enrage: "Hisss! Now I'm truly unparseable!",
    defeat: "SyntaxError: unexpected… defeat… sss…",
    win: "Your program has been s-s-squashed!",
    taunts: [
      "SyntaxError: invalid move!",
      "Missing a colon? Missing a dodge, too!",
      "Expected an indented block… of armor!",
      "Unexpected EOF while dodging!",
      "Sssso close… but it doesn't parse!",
      "Unmatched ')' — and unmatched skills!",
    ],
  },
  golem: {
    id: "golem",
    name: "Null Pointer Golem",
    emoji: "🗿",
    hp: 5000,
    shot: "🪨",
    intro: "None shall pass!",
    enrage: "raise RageError from None!",
    defeat: "Process finished with exit code… None…",
    win: "None shall pass. I told you!",
    taunts: [
      "AttributeError: 'NoneType' has no attribute 'chance'!",
      "Your answer evaluated to None!",
      "if you:  # falsy, as expected!",
      "I am None. I am unstoppable!",
      "Null and void — just like that answer!",
      "Stone-cold TypeError!",
    ],
  },
  dragon: {
    id: "dragon",
    name: "Infinite Loop Dragon",
    emoji: "🐉",
    hp: 9000,
    shot: "🔥",
    intro: "Welcome to my loop. There is no exit.",
    enrage: "while True: rage += 1",
    defeat: "KeyboardInterrupt?! Nooo…",
    win: "Infinite Loop: 1, You: 0!",
    taunts: [
      "while True: burn(you)",
      "I'll keep attacking… forever!",
      "RecursionError: maximum burns exceeded!",
      "break? There is no break!",
      "for hp in range(you, 0, -1): 🔥",
      "My loop never ends. Your HP does!",
    ],
  },
};

const GENERIC_TAUNTS = [
  "IndentationError: your defenses!",
  "TypeError: can't add 'you' to 'winners'!",
  "KeyError: 'correct_answer'!",
  "Traceback (most recent call last): YOU!",
  "ZeroDivisionError: your chances / 0!",
  "IndexError: answer out of range!",
  "NameError: name 'victory' is not defined!",
  "return None  # just like your answer!",
  "assert you_win  # AssertionError!",
  "Did you forget to import skill?",
  "ValueError: invalid literal for win(): 'you'",
  "try: dodge()  except: ouch!",
];

const TIMEOUT_TAUNTS = [
  "TimeoutError: too slow!",
  "Did you call time.sleep() on the job?",
  "Tick tock… KeyboardInterrupt!",
];

const HURT_LINES = [
  "Ouch! Unhandled exception!",
  "Argh! That one compiled!",
  "Grr… lucky guess!",
  "My stack trace!",
  "Hey! Who taught you Python?!",
  "Ow! That wasn't in my docstring!",
];

const CRIT_LINES = ["CRITICAL ERROR!", "MemoryError: too much damage!", "Fatal Python error!", "Segfault?! In Python?!"];

export const PLAYER_HP = { normal: 100, hardcore: 60 };
const ATTACK_RANGE = { normal: [15, 30], hardcore: [20, 35] };
const ENRAGE_BONUS = 5;
const ENRAGE_FRACTION = 0.3;
const CRIT_CHANCE = 0.2;
const COMBO_STEP = 0.1;
const COMBO_MAX = 0.5;
const WIN_BONUS = 1000;
const HP_BONUS = 20;
const TIMER_SECONDS = 25;

// ---------------------------------------------------------------------------
// Pure game logic
// ---------------------------------------------------------------------------

const fmt = (n) => Math.round(Number(n) || 0).toLocaleString("en-US");

/** Damage bonus for `streak` consecutive correct answers before this one: +10% each, max +50%. */
export function comboBonus(streak) {
  const n = Math.max(0, Math.floor(Number(streak) || 0));
  return Math.min(COMBO_MAX, Math.round(n * COMBO_STEP * 100) / 100);
}

/** A correct answer's hit. roll < 0.2 on a Hard (difficulty 3) question = critical (×2). */
export function computeHit({ points, difficulty, streak = 0, roll = Math.random() }) {
  const bonus = comboBonus(streak);
  const crit = Number(difficulty) === 3 && roll < CRIT_CHANCE;
  const damage = Math.round((Number(points) || 0) * (1 + bonus) * (crit ? 2 : 1));
  return { damage, crit, bonus };
}

/** Inclusive [min, max] damage of the boss's counter-attack. */
export function attackRange({ hardcore = false, enraged = false } = {}) {
  const [lo, hi] = ATTACK_RANGE[hardcore ? "hardcore" : "normal"];
  const extra = enraged ? ENRAGE_BONUS : 0;
  return [lo + extra, hi + extra];
}

/** Boss counter-attack damage for a roll in [0, 1). */
export function bossAttackDamage({ hardcore = false, enraged = false, roll = Math.random() } = {}) {
  const [lo, hi] = attackRange({ hardcore, enraged });
  return lo + Math.min(hi - lo, Math.max(0, Math.floor(roll * (hi - lo + 1))));
}

/** The boss enrages below 30% HP (but not once it is defeated). */
export function isEnraged(hp, maxHp) {
  return hp > 0 && hp < maxHp * ENRAGE_FRACTION;
}

export function finalScore({ damageDealt, won, playerHp }) {
  return Math.round((Number(damageDealt) || 0) + (won ? WIN_BONUS + Math.max(0, playerHp) * HP_BONUS : 0));
}

export function hpTone(hp, max) {
  const f = max > 0 ? hp / max : 0;
  return f > 0.5 ? "high" : f > 0.25 ? "mid" : "low";
}

/** Pick a line, avoiding the recently used ones when possible. */
export function pickLine(lines, recent = [], roll = Math.random()) {
  const fresh = lines.filter((l) => !recent.includes(l));
  const pool = fresh.length ? fresh : lines;
  return pool[Math.min(pool.length - 1, Math.max(0, Math.floor(roll * pool.length)))];
}

export function initialState(bossMax, playerMax) {
  return {
    bossHp: bossMax,
    bossMax,
    playerHp: playerMax,
    playerMax,
    combo: 0,
    bestCombo: 0,
    damageDealt: 0,
    damageTaken: 0,
    crits: 0,
    answered: 0,
    correct: 0,
    enraged: false,
  };
}

/**
 * Apply one answered question to the battle. Pure: returns the next state and
 * an event describing what happened (for the view).
 *   hit:    {type:'hit', damage, crit, bonus, overkill, killed, enragedNow}
 *   attack: {type:'attack', damage, enraged, ko, timedOut}
 */
export function applyAnswer(state, { correct, points, difficulty, timedOut = false }, { hardcore = false, critRoll = Math.random(), attackRoll = Math.random() } = {}) {
  const s = { ...state, answered: state.answered + 1 };
  if (correct) {
    const hit = computeHit({ points, difficulty, streak: state.combo, roll: critRoll });
    s.bossHp = Math.max(0, state.bossHp - hit.damage);
    s.damageDealt = state.damageDealt + hit.damage;
    s.crits = state.crits + (hit.crit ? 1 : 0);
    s.correct = state.correct + 1;
    s.combo = state.combo + 1;
    s.bestCombo = Math.max(state.bestCombo, s.combo);
    s.enraged = state.enraged || isEnraged(s.bossHp, s.bossMax);
    return {
      state: s,
      event: {
        type: "hit",
        ...hit,
        overkill: Math.max(0, hit.damage - state.bossHp),
        killed: s.bossHp <= 0,
        enragedNow: !state.enraged && s.enraged,
      },
    };
  }
  const damage = bossAttackDamage({ hardcore, enraged: state.enraged, roll: attackRoll });
  s.playerHp = Math.max(0, state.playerHp - damage);
  s.damageTaken = state.damageTaken + damage;
  s.combo = 0;
  return { state: s, event: { type: "attack", damage, enraged: state.enraged, ko: s.playerHp <= 0, timedOut: !!timedOut } };
}

/** Text for the "Correct! …" banner of the question card. */
export function hitLabel(event) {
  if (!event || event.type !== "hit") return "";
  const combo = event.bonus > 0 ? ` (+${Math.round(event.bonus * 100)}% combo)` : "";
  return event.crit ? `💥 CRITICAL! ${fmt(event.damage)} damage${combo}` : `⚔️ ${fmt(event.damage)} damage${combo}`;
}

/** Normalised mode options. */
export function readConfig(options = {}) {
  const o = options && typeof options === "object" ? options : {};
  const boss = Object.prototype.hasOwnProperty.call(BOSSES, o.boss) ? o.boss : "golem";
  const hp = o.hp === "hardcore" ? "hardcore" : "normal";
  const timer = Number(o.timer);
  return { boss, hp, hardcore: hp === "hardcore", timeLimit: Number.isFinite(timer) && timer > 0 ? timer : 0 };
}

export function buildResult({ boss, state, won, seconds, hardcore = false, formatTime = (s) => `${Math.round(s)}s` }) {
  const details = [
    ["Boss", `${boss.emoji} ${boss.name}`],
    ["Damage dealt", fmt(state.damageDealt)],
    ["Critical hits", String(state.crits)],
    ["Questions", `${state.answered} (${state.correct} correct)`],
    ["HP left", `${state.playerHp} / ${state.playerMax}${hardcore ? " (Hardcore 💀)" : ""}`],
  ];
  if (won) details.push(["Victory bonus", `+${fmt(WIN_BONUS + state.playerHp * HP_BONUS)} (1,000 + ${state.playerHp} HP × 20)`]);
  else details.push(["Boss HP left", `${fmt(state.bossHp)} / ${fmt(state.bossMax)}`]);
  details.push(["Time taken", formatTime(seconds)]);
  return {
    score: finalScore({ damageDealt: state.damageDealt, won, playerHp: state.playerHp }),
    won,
    headline: won ? `Victory! The ${boss.name} is defeated!` : `Defeated… The ${boss.name} wins this round!`,
    details,
  };
}

// ---------------------------------------------------------------------------
// Battle view (DOM + effects). Every timer goes through ctx so quitting is clean.
// ---------------------------------------------------------------------------

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

/** Re-trigger a CSS animation class. */
function restartClass(node, cls, others = []) {
  node.classList.remove(cls, ...others);
  void node.offsetWidth;
  node.classList.add(cls);
}

function createBattleView(ctx, boss, cfg, state) {
  const { el } = ctx;
  const recentLines = [];

  // ---- HP bars ------------------------------------------------------------
  function hpBar({ label, max, kind }) {
    const ghost = el("div", { class: "boss-hp-ghost" });
    const fill = el("div", { class: "boss-hp-fill" });
    const bar = el(
      "div",
      {
        class: ["boss-hp", `boss-hp-${kind}`],
        role: "progressbar",
        "aria-label": label,
        "aria-valuemin": "0",
        "aria-valuemax": String(max),
        "aria-valuenow": String(max),
        dataset: { tone: "high" },
      },
      ghost,
      fill
    );
    const num = el("b", { text: fmt(max) });
    const text = el("span", { class: "boss-hp-text" }, num, el("span", { class: "boss-hp-max", text: ` / ${fmt(max)}` }));
    let shown = max;
    return {
      bar,
      text,
      set(hp) {
        const pct = `${Math.max(0, Math.min(1, hp / max)) * 100}%`;
        fill.style.width = pct;
        ghost.style.width = pct;
        bar.setAttribute("aria-valuenow", String(Math.max(0, hp)));
        bar.dataset.tone = hpTone(hp, max);
        ctx.animateNumber(num, shown, Math.max(0, hp), 550);
        shown = Math.max(0, hp);
      },
    };
  }

  // ---- boss card ------------------------------------------------------------
  const bossEmoji = el("span", { class: "boss-foe-emoji", text: boss.emoji });
  const bossBody = el("div", { class: "boss-foe-body boss-enter" }, bossEmoji);
  const bossFx = el("div", { class: "boss-fx" });
  const bossSprite = el("div", { class: "boss-foe-sprite", "aria-hidden": "true" }, el("div", { class: "boss-foe-aura" }), bossBody, bossFx);
  const rageBadge = el("span", { class: "boss-rage-badge", hidden: true }, el("span", { "aria-hidden": "true", text: "😡 " }), "Enraged");
  const bossHp = hpBar({ label: `${boss.name} HP`, max: state.bossMax, kind: "foe" });
  const status = el("p", { class: "boss-foe-status" });
  const taunt = el("p", { class: "boss-taunt", hidden: true });
  const sayBox = el("div", { class: "boss-foe-say" }, status, taunt);
  const foeCard = el(
    "section",
    { class: ["boss-card", "boss-foe", `boss-foe-${boss.id}`], "aria-label": `Boss: ${boss.name}` },
    bossSprite,
    el(
      "div",
      { class: "boss-foe-info" },
      el("div", { class: "boss-card-head" }, el("h2", { class: "boss-foe-name", text: boss.name }), rageBadge),
      el("div", { class: "boss-hp-row" }, el("span", { class: "boss-hp-label", text: "HP" }), bossHp.text),
      bossHp.bar,
      sayBox
    )
  );

  // ---- player card ----------------------------------------------------------
  const heroBlook = ctx.blook(ctx.player.avatar, { size: 60 });
  const heroFx = el("div", { class: "boss-fx", "aria-hidden": "true" });
  const heroAvatar = el(
    "div",
    { class: "boss-hero-avatar" },
    heroBlook,
    cfg.hardcore ? el("span", { class: "boss-hc-badge", "aria-hidden": "true", title: "Hardcore", text: "💀" }) : null,
    heroFx
  );
  const heroHp = hpBar({ label: "Your HP", max: state.playerMax, kind: "hero" });
  const comboCount = el("span", { class: "boss-combo-count" });
  const comboBonusText = el("span", { class: "boss-combo-bonus" });
  const comboSuffix = el("span", { class: "boss-combo-suffix" });
  const combo = el("div", { class: "boss-combo", dataset: { level: 0 } }, comboCount, el("span", null, comboBonusText, comboSuffix));
  const heroCard = el(
    "section",
    { class: ["boss-card", "boss-hero"], "aria-label": "You" },
    heroAvatar,
    el(
      "div",
      { class: "boss-hero-info" },
      el(
        "div",
        { class: "boss-card-head" },
        el("span", { class: "boss-hero-name", text: ctx.player.name || "Player" }),
        cfg.hardcore ? el("span", { class: "boss-tag-hardcore", title: "Hardcore: 60 HP, harder hits" }, el("span", { "aria-hidden": "true", text: "💀" }), el("span", { class: "boss-tag-text", text: " Hardcore" })) : null
      ),
      el("div", { class: "boss-hp-row" }, el("span", { class: "boss-hp-label", text: "HP" }), heroHp.text),
      heroHp.bar,
      combo
    )
  );

  const banner = el("div", { class: "boss-banner", hidden: true, role: "status" });
  const arena = el("div", { class: "boss-arena" }, foeCard, heroCard, banner);
  const dock = el("div", { class: "boss-dock" }, arena);
  const qArea = el("div", { class: "boss-question" });
  const live = el("p", { class: "sr-only", "aria-live": "polite" });
  ctx.root.append(dock, el("div", { class: "game-stage boss-stage" }, qArea, live));

  // Full-screen flash lives on <body> (position: fixed inside an animated
  // ancestor would be clipped to it), so remove it ourselves on cleanup.
  const flashEl = el("div", { class: "boss-flash", "aria-hidden": "true" });
  document.body.append(flashEl);
  ctx.onCleanup(() => flashEl.remove());

  // Keep the sticky dock right below the game top bar.
  const topbar = ctx.root.parentElement ? ctx.root.parentElement.querySelector(".game-topbar") : null;
  const syncTop = () => {
    if (topbar) ctx.root.style.setProperty("--boss-top", `${Math.round(topbar.getBoundingClientRect().height)}px`);
  };
  syncTop();
  window.addEventListener("resize", syncTop);
  ctx.onCleanup(() => window.removeEventListener("resize", syncTop));

  // ---- small helpers ----------------------------------------------------------
  const motion = !reducedMotion();
  const later = (ms, fn) => (ms > 0 ? ctx.setTimeout(fn, ms) : fn());

  function updateStatus() {
    const [lo, hi] = attackRange({ hardcore: cfg.hardcore, enraged: state.enraged });
    status.textContent = `${state.enraged ? "😡" : "⚔️"} Strikes back for ${lo}–${hi} HP`;
  }

  function updateCombo(n, bump = false) {
    const bonus = comboBonus(n);
    combo.dataset.level = String(Math.min(5, n));
    comboCount.textContent = n > 0 ? `🔥 ×${n}` : "⚔️ No combo";
    comboBonusText.textContent = n > 0 ? `+${Math.round(bonus * 100)}%` : "";
    comboSuffix.textContent = n > 0 ? (bonus >= COMBO_MAX ? " MAX" : " dmg") : "";
    combo.title = n > 0 ? `${n} in a row: your next hit deals +${Math.round(bonus * 100)}% damage` : "Answer correctly in a row for bonus damage";
    if (bump && n > 0) restartClass(combo, "boss-bump");
  }

  function line(list) {
    const text = pickLine(list, recentLines);
    recentLines.push(text);
    if (recentLines.length > 5) recentLines.shift();
    return text;
  }

  let sayTimer = 0;
  function say(text, { kind = "taunt", ms = 3000, stay = false } = {}) {
    if (sayTimer) ctx.clearTimeout(sayTimer);
    sayTimer = 0;
    taunt.textContent = text;
    taunt.dataset.kind = kind;
    taunt.hidden = false;
    sayBox.classList.add("has-taunt");
    restartClass(taunt, "boss-pop");
    if (!stay)
      sayTimer = ctx.setTimeout(() => {
        taunt.hidden = true;
        sayBox.classList.remove("has-taunt");
      }, ms);
  }

  function announce(text) {
    live.textContent = text;
  }

  function floatText(layer, content, cls) {
    const dx = Math.round((Math.random() - 0.5) * 36);
    const node = el("span", { class: ["boss-float", cls], style: { "--dx": `${dx}px` } }, content);
    layer.append(node);
    ctx.setTimeout(() => node.remove(), 1400);
  }

  function flash(kind) {
    flashEl.className = `boss-flash boss-flash-${kind}`;
    void flashEl.offsetWidth;
    flashEl.classList.add("is-on");
  }

  /** Fly an emoji from one element to another; returns the travel time in ms. */
  function shoot(from, to, emoji, ms) {
    if (!motion || typeof arena.animate !== "function") return 0;
    const a = arena.getBoundingClientRect();
    const f = from.getBoundingClientRect();
    const t = to.getBoundingClientRect();
    if (!a.width || !f.width || !t.width) return 0;
    const x0 = f.left + f.width / 2 - a.left;
    const y0 = f.top + f.height / 2 - a.top;
    const dx = t.left + t.width / 2 - a.left - x0;
    const dy = t.top + t.height / 2 - a.top - y0;
    const shot = el("span", { class: "boss-shot", "aria-hidden": "true", text: emoji, style: { left: `${x0}px`, top: `${y0}px` } });
    arena.append(shot);
    shot.animate(
      [
        { transform: "translate(-50%, -50%) scale(0.5) rotate(0deg)", opacity: 0.3 },
        { transform: `translate(${dx * 0.5}px, ${dy * 0.5 - 26}px) translate(-50%, -50%) scale(1.25) rotate(200deg)`, opacity: 1, offset: 0.5 },
        { transform: `translate(${dx}px, ${dy}px) translate(-50%, -50%) scale(0.9) rotate(400deg)`, opacity: 1 },
      ],
      { duration: ms, easing: "ease-in", fill: "forwards" }
    );
    ctx.setTimeout(() => shot.remove(), ms + 30);
    return ms;
  }

  function enrage() {
    foeCard.classList.add("is-enraged");
    rageBadge.hidden = false;
    updateStatus();
    say(boss.enrage, { kind: "rage", ms: 3200 });
    ctx.sfx("wrong");
    ctx.toast(`The ${boss.name} is ENRAGED! Its attacks now deal +${ENRAGE_BONUS} damage.`, "error");
  }

  // ---- reactions to an answer -------------------------------------------------
  function onHit(ev, s) {
    updateCombo(s.combo, true);
    restartClass(heroAvatar, "boss-hop");
    const travel = shoot(heroAvatar, bossSprite, ev.crit ? "🌟" : "⚡", 240);
    announce(
      `${ev.crit ? "Critical hit! " : "Hit! "}You deal ${fmt(ev.damage)} damage. ${boss.name} has ${fmt(s.bossHp)} of ${fmt(s.bossMax)} HP left.`
    );
    later(travel, () => {
      bossHp.set(s.bossHp);
      restartClass(bossBody, ev.killed ? "boss-dying" : "boss-hurt", ["boss-enter", "boss-hurt", "boss-lunge", "boss-laugh"]);
      ctx.sfx("hit");
      if (ev.crit) {
        floatText(bossFx, [el("small", { text: "CRITICAL!" }), `-${fmt(ev.damage)}`], "boss-float-crit");
        ctx.setTimeout(() => ctx.sfx("hit"), 110);
        flash("crit");
        restartClass(arena, "boss-quake");
      } else {
        floatText(bossFx, `-${fmt(ev.damage)}`, "boss-float-hit");
      }
      if (ev.killed) {
        say(boss.defeat, { kind: "hurt", stay: true });
        ctx.setTimeout(() => {
          floatText(bossFx, "💥", "boss-float-boom");
          ctx.sfx("chest");
        }, motion ? 650 : 0);
      } else if (ev.enragedNow) {
        ctx.setTimeout(enrage, motion ? 500 : 0);
      } else if (ev.crit) {
        say(line(CRIT_LINES), { kind: "hurt" });
      } else if (Math.random() < 0.5) {
        say(line(HURT_LINES), { kind: "hurt", ms: 2200 });
      }
    });
  }

  function onAttack(ev, s) {
    updateCombo(0);
    restartClass(bossBody, "boss-lunge", ["boss-enter", "boss-hurt", "boss-laugh"]);
    const travel = shoot(bossSprite, heroAvatar, boss.shot, 300);
    announce(`${ev.timedOut ? "Time's up! " : ""}The ${boss.name} hits you for ${ev.damage} damage. You have ${s.playerHp} of ${s.playerMax} HP left.`);
    later(travel, () => {
      heroHp.set(s.playerHp);
      restartClass(heroCard, "boss-hit");
      floatText(heroFx, `-${ev.damage}`, "boss-float-hurt");
      ctx.sfx("hit");
      flash("hurt");
      restartClass(arena, "boss-quake");
      if (ev.ko) {
        heroCard.classList.add("is-ko");
        say(boss.win, { kind: "taunt", stay: true });
        ctx.setTimeout(() => restartClass(bossBody, "boss-laugh", ["boss-lunge"]), 350);
      } else {
        say(line(ev.timedOut ? TIMEOUT_TAUNTS : boss.taunts.concat(GENERIC_TAUNTS)));
      }
    });
  }

  // ---- public API -----------------------------------------------------------
  updateStatus();
  updateCombo(0);
  ctx.setTimeout(() => say(boss.intro, { kind: "intro", ms: 3200 }), motion ? 450 : 0);

  return {
    qArea,
    apply(event, s) {
      state = s;
      if (event.type === "hit") onHit(event, s);
      else onAttack(event, s);
    },
    /** Scroll the next question's top back into view below the sticky dock. */
    revealQuestion() {
      const top = qArea.getBoundingClientRect().top;
      const sticky = window.getComputedStyle(dock).position === "sticky";
      const limit = (sticky ? dock.getBoundingClientRect().bottom : topbar ? topbar.getBoundingClientRect().bottom : 0) + 10;
      if (top < limit - 2) window.scrollBy({ top: top - limit, behavior: motion ? "smooth" : "auto" });
    },
    async victory() {
      announce(`Victory! The ${boss.name} is defeated!`);
      showBanner("win", "🏆", "Victory!");
      ctx.sfx("levelup");
      const r = bossSprite.getBoundingClientRect();
      if (r.width) ctx.confetti({ count: 120, x: (r.left + r.width / 2) / window.innerWidth, y: (r.top + r.height / 2) / window.innerHeight });
      await ctx.sleep(1900);
    },
    async defeat() {
      announce("Defeated! You ran out of HP.");
      showBanner("lose", "💀", "Defeated…");
      await ctx.sleep(1500);
    },
  };

  function showBanner(kind, icon, text) {
    banner.replaceChildren(el("span", { class: "boss-banner-icon", "aria-hidden": "true", text: icon }), el("strong", { text }));
    banner.className = `boss-banner boss-banner-${kind}`;
    banner.hidden = false;
    if (window.getComputedStyle(dock).position !== "sticky") {
      try {
        dock.scrollIntoView({ block: "start", behavior: motion ? "smooth" : "auto" });
      } catch {
        /* ignore */
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Mode
// ---------------------------------------------------------------------------

export default {
  id: "boss",
  name: "Boss Battle",
  icon: "🐉",
  tagline: "Answer right to smash a Python boss — before it smashes you!",
  description:
    "Every correct answer hits the boss for the question's points — Easy 100, Medium 250, Hard 500 — so harder questions hit harder. " +
    "Each answer in a row adds +10% damage (up to +50%), and Hard questions have a 20% chance to CRIT for double damage.\n" +
    "A wrong answer or timeout lets the boss strike back for 15–30 HP (20–35 in Hardcore), and below 30% HP it enrages and hits 5 harder. " +
    "The Serpent has 2,500 HP, the Golem 5,000 and the Dragon 9,000.\n" +
    "Score = damage dealt, plus 1,000 and 20 per HP left if you win.",
  difficultySelectable: true,
  options: [
    {
      key: "boss",
      label: "Boss",
      choices: [
        ["serpent", "Syntax Serpent 🐍"],
        ["golem", "Null Pointer Golem 🗿"],
        ["dragon", "Infinite Loop Dragon 🐉"],
      ],
      default: "golem",
    },
    {
      key: "hp",
      label: "Your HP",
      choices: [
        ["normal", "Normal · 100 HP"],
        ["hardcore", "Hardcore · 60 HP"],
      ],
      default: "normal",
    },
    {
      key: "timer",
      label: "Question timer",
      choices: [
        [TIMER_SECONDS, `${TIMER_SECONDS} s`],
        [0, "Off"],
      ],
      default: TIMER_SECONDS,
    },
  ],
  scoreLabel: "Score",

  async play(ctx) {
    const cfg = readConfig(ctx.settings && ctx.settings.options);
    const boss = BOSSES[cfg.boss];
    let state = initialState(boss.hp, PLAYER_HP[cfg.hp]);
    const startedAt = performance.now();
    const view = createBattleView(ctx, boss, cfg, state);

    while (state.bossHp > 0 && state.playerHp > 0) {
      view.revealQuestion();
      // pointsLabel runs just before onAnswered, so resolve each answer once.
      const outcomes = new WeakMap();
      const outcomeFor = (r) => {
        if (!outcomes.has(r)) {
          outcomes.set(
            r,
            applyAnswer(
              state,
              { correct: r.correct, points: r.points || (r.question && r.question.points) || 0, difficulty: r.question && r.question.difficulty, timedOut: r.timedOut },
              { hardcore: cfg.hardcore }
            )
          );
        }
        return outcomes.get(r);
      };
      await ctx.ask(view.qArea, {
        timeLimit: cfg.timeLimit,
        correctDelay: 1300,
        pointsLabel: (r) => hitLabel(outcomeFor(r).event),
        onAnswered: (r) => {
          const { state: next, event } = outcomeFor(r);
          state = next;
          view.apply(event, state);
        },
      });
    }

    const won = state.bossHp <= 0;
    const seconds = (performance.now() - startedAt) / 1000;
    if (won) await view.victory();
    else await view.defeat();
    return buildResult({ boss, state, won, seconds, hardcore: cfg.hardcore, formatTime: ctx.formatTime });
  },
};
