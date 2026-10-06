/**
 * PLACEHOLDER for the "Survival" mode — will be replaced by the real
 * implementation. Asks 5 questions and reports the points earned.
 * See ../engine.js for the full mode contract.
 */
export default {
  id: "survival",
  name: "Survival",
  icon: "❤️",
  tagline: "Three lives. Questions get harder. How long can you last?",
  description: "You start with 3 lives. Every wrong answer costs a life, and the questions get harder (and worth more) the longer you survive.\nHow high can you score before your lives run out?",
  difficultySelectable: false,
  options: [{"key": "lives", "label": "Lives", "choices": [[1, "1 ❤️"], [3, "3 ❤️"], [5, "5 ❤️"]], "default": 3}],
  scoreLabel: "Score",

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
