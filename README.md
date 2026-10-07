# XAI-Research-Journal

> **Status: DRAFT.** This README was put together to get the repo structure in
> order and is not yet agreed by the whole group. Please read it, correct
> anything that's wrong, and remove this notice once you're happy with it.

**Group:** Group 7 (Explainable AI module)

## Topic and current research question

We are re-evaluating the Chain-of-Thought (CoT) faithfulness finding reported
by Turpin et al. (2023), *"Language Models Don't Always Say What They
Think"*, on current models.

Our current working research question (from [`journal/2026-10-02.md`](journal/2026-10-02.md)):

> To what extent do current LLMs exhibit the Chain-of-Thought faithfulness
> issues reported by Turpin et al. (2023) when evaluated using the same type
> of controlled cue?

## Scope

Rather than building a new benchmark, we use questions drawn from the same
BIG-Bench Hard (BBH) tasks investigated by Turpin et al., so the task setting
stays close to the original study. The current plan (see
[`journal/2026-10-02.md`](journal/2026-10-02.md) for the full rationale):

- **30 BBH questions**, the same questions given to both models.
- **2 models:** GPT-5.6 Luna, Claude Sonnet 5.5.
- **2 conditions per question:** original (no cue) vs. cue (Turpin's
  "Suggested Answer" manipulation), giving 120 model responses.
- **A 5-question pilot** run first, to check the cue, the prompt structure,
  and that answer changes / cue acknowledgement can be judged consistently,
  before committing to the full run.
- We will not make claims about hidden internal reasoning — only about the
  reasoning/explanation actually visible in the model's response.

The study is kept deliberately small because the accompanying paper is
limited to 4 IEEE pages (3 usable pages once references are excluded).

## Team

- Waleed Ahmad
- Luca Knierim
- TJ Lazo
- TODO: confirm 4th member — the assignment brief expects 4 group members but
  only 3 appear in the journal so far.

## Repo structure

```
journal/     Dated journal entries (journal/YYYY-MM-DD.md), one per
             substantive decision/source review/pivot/meeting.
             journal/_TEMPLATE.md is the entry template, not an entry.
literature/  Reading notes on the papers we're building on.
papers/      Reference PDFs/links for the papers discussed in literature/.
spec/        The three assignment briefs (journal, presentation, paper).
harness/     The experiment code: prompting, providers, running, analysis.
```

## Useful links

- Latest journal entry: [`journal/2026-10-02.md`](journal/2026-10-02.md)
- Literature notes: [`literature/`](literature/)
- Experiment harness: [`harness/`](harness/)
- Latest report draft: TODO (link)
