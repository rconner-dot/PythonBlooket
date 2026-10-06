/**
 * PLACEHOLDER for the "Python Race" mode — will be replaced by the real
 * implementation. Asks 5 questions and reports the points earned.
 * See ../engine.js for the full mode contract.
 */
export default {
  id: "race",
  name: "Python Race",
  icon: "🏁",
  tagline: "Every right answer moves you closer to the finish line.",
  description: "Race against bots on a code track. Each correct answer pushes your blook forward — harder questions push you further.\nReach the finish line first to win!",
  difficultySelectable: true,
  options: [{"key": "length", "label": "Track length", "choices": [["short", "Short"], ["medium", "Medium"], ["long", "Long"]], "default": "medium"}],
  scoreLabel: "Distance",

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
