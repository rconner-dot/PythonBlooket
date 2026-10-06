/**
 * PLACEHOLDER for the "Time Attack" mode — will be replaced by the real
 * implementation. Asks 5 questions and reports the points earned.
 * See ../engine.js for the full mode contract.
 */
export default {
  id: "blitz",
  name: "Time Attack",
  icon: "⚡",
  tagline: "Beat the clock — rack up points before time runs out!",
  description: "Answer as many questions as you can before the timer hits zero. Fast answers and streaks earn bonus points.\nWrong answers cost you precious seconds!",
  difficultySelectable: true,
  options: [{"key": "duration", "label": "Time limit", "choices": [[60, "1 min"], [90, "1.5 min"], [120, "2 min"]], "default": 90}],
  scoreLabel: "Points",

  async play(ctx) {
    const { el } = ctx;
    const total = 5;
    let score = 0;
    const progress = el("span", { class: "hud-pill", text: `Question 1/${total}` });
    const scorePill = el("span", { class: "hud-pill" }, `${this.scoreLabel}: `, el("b", { text: "0" }));
    const area = el("div");
    ctx.root.append(el("div", { class: "game-stage" }, el("div", { class: "hud" }, progress, scorePill), area));
    for (let i = 0; i < total; i++) {
      progress.textContent = `Question ${i + 1}/${total}`;
      await ctx.ask(area, {
        timeLimit: 20,
        wrongDelay: 2500,
        onAnswered: (res) => {
          score += res.points;
          ctx.animateNumber(scorePill.querySelector("b"), score - res.points, score, 500);
        },
      });
    }
    const won = ctx.stats.correct >= 3;
    return {
      score,
      won,
      headline: won ? "Nice work, Pythonista!" : "Keep practising!",
      details: [
        ["Questions", String(total)],
        ["Correct", `${ctx.stats.correct}/${total}`],
      ],
    };
  },
};
