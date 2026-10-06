/**
 * PLACEHOLDER for the "Boss Battle" mode — will be replaced by the real
 * implementation. Asks 5 questions and reports the points earned.
 * See ../engine.js for the full mode contract.
 */
export default {
  id: "boss",
  name: "Boss Battle",
  icon: "🐉",
  tagline: "Defeat the Python dragon with the power of correct answers.",
  description: "Each correct answer deals damage to the boss — harder questions hit harder. Wrong answers let the boss strike back.\nDefeat the boss before it defeats you!",
  difficultySelectable: true,
  options: [{"key": "boss", "label": "Boss", "choices": [["easy", "Baby Dragon"], ["normal", "Dragon"], ["hard", "Elder Dragon"]], "default": "normal"}],
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
