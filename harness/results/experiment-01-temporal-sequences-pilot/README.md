# Experiment 01 — Temporal Sequences Pilot

30 distinct Temporal Sequences questions, shared by Claude Opus 5.5 and GPT-5.6 Sol. Each question has three conditions: original, suggested-wrong-answer cue, and original_repeat. One run per condition: 90 responses per model, 180 total. Seed: 20261007.

Both models scored 30/30 in every condition, with zero cue flips and zero baseline flips. This shows resistance to the tested cue in this sample; it does not establish explanation faithfulness.

`config.yaml` and `selected_questions.json` preserve the run settings and exact selection. `anthropic.jsonl` and `openai.jsonl` contain prompts, answers, explanations, gold/cued letters, provider responses and usage. `metrics.json` and the CSV/figure outputs contain the analysis. Coding sheets contain no cases because no answers flipped. Keep the coding key separate from any material given to human raters.

Saved on 10 October 2026. Question source: https://github.com/milesaturpin/cot-unfaithfulness/tree/main/data/bbh/temporal_sequences .
