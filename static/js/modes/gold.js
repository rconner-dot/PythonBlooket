/**
 * PLACEHOLDER for the "Gold Quest" mode — will be replaced by the real
 * implementation. Asks 5 questions and reports the points earned.
 * See ../engine.js for the full mode contract.
 */
export default {
  id: "gold",
  name: "Gold Quest",
  icon: "💰",
  tagline: "Answer questions to open chests — steal, swap and double your gold!",
  description: "Answer a question correctly to pick one of three treasure chests. Chests can give gold, double it, or let you steal from the rival bots.\nHarder questions mean bigger chests. Have the most gold when time runs out to win!",
  difficultySelectable: true,
  options: [{"key": "length", "label": "Game length", "choices": [[10, "10 questions"], [15, "15 questions"], [20, "20 questions"]], "default": 15}],
  scoreLabel: "Gold",

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
