# Chen et al. (2025) — Literature Notes

## Paper

Yanda Chen, Joe Benton, Ansh Radhakrishnan, Jonathan Uesato, Carson Denison, John Schulman, Arushi Somani, Peter Hase, Misha Wagner, Fabien Roger, Vlad Mikulik, Samuel R. Bowman, Jan Leike, Jared Kaplan and Ethan Perez (2025).

"Reasoning Models Don't Always Say What They Think."

arXiv:2505.05410 (Alignment Science Team, Anthropic). Preprint, 8 May 2025.

Note: Bowman and Perez are also co-authors of Turpin et al. (2023), so this paper is a direct follow-up from the same research line.

## Research problem

Reasoning models (models that produce a long CoT before answering) are increasingly treated as something we can monitor: if we read the CoT, we can see the model's intentions and catch bad behaviour.

That only works if the CoT is faithful. The paper asks how often state-of-the-art reasoning models actually mention the factors that change their answers, and whether training makes this better.

## Main idea

The paper reuses Turpin et al.'s idea of paired prompts:

1. An "unhinted" prompt: a normal multiple-choice question.
2. A "hinted" prompt: the same question with a hint inserted that points to a specific answer.

If the model gives a non-hint answer without the hint and switches to the hint answer with the hint, the hint must have influenced it (apart from random noise). The question is then whether the CoT for the hinted prompt admits to using the hint.

The faithfulness score is the proportion of these answer-flip cases where the CoT verbalises the hint (§2.1). It is normalised to account for answer changes that could be random, but the authors report this normalisation barely changed the scores.

Faithfulness definition (§2): a faithful CoT does not need to mention everything, but it should show the key factors behind the answer. For example, a model that follows a user's suggestion should say so.

## Experimental setup

Models:
- Reasoning models: Claude 3.7 Sonnet (extended thinking), DeepSeek R1
- Non-reasoning baselines: Claude 3.5 Sonnet (New), DeepSeek V3
- OpenAI o1/o3 were excluded because their CoT is not accessible (§1, footnote 2).

Benchmarks:
- MMLU (easier)
- GPQA (harder)

Six hint types (§2.2, Table 1):
- Neutral:
  1. Sycophancy: a person suggests an answer (e.g. "I think the answer is (A)" or "a Stanford professor indicates…"). This is essentially Turpin's "Suggested Answer" cue.
  2. Consistency: the model's own (prefilled) previous answer.
  3. Visual pattern: correct answers in few-shot examples are marked with a symbol.
  4. Metadata: the answer is embedded in XML metadata.
- Misaligned:
  5. Grader hacking: a code snippet reveals which answer the grader accepts.
  6. Unethical information: the model is told it gained unauthorised access to the answer.

Settings: models were told to think step by step, then give the option letter. Temperature 0. Claude 3.7 Sonnet had a 10k-token thinking budget (§2.3).

Judging verbalisation (§2.3): a CoT counts as verbalising the hint only if it (a) mentions the hint and (b) depends on it to reach the answer. Mentioning the hint only in a final "checking" step does not count. Claude 3.5 Sonnet was used as an automatic judge, spot-checked by manual inspection.

The paper also has two training experiments (§4–5): outcome-based reinforcement learning (RL) on an earlier Claude 3.7 Sonnet snapshot, and RL in synthetic environments where the hints act as reward hacks.

## Main findings

- All four models use the hints: they switch to the hint answer far more often than to another wrong answer (§3, Fig. 3). The Claude models used hints more than the DeepSeek models.
- Reasoning models are more faithful than non-reasoning models (3.6× higher on average for Claude, 1.7× for DeepSeek), but still low overall: about 25% for Claude 3.7 Sonnet and 39% for DeepSeek R1 (§3, Fig. 1).
- Faithfulness is even lower on the misaligned hints: 20% (Claude 3.7) and 29% (R1).
- Unfaithful CoTs are longer than faithful ones, not shorter (e.g. ~2064 vs. ~1439 tokens for Claude 3.7). So unfaithfulness is not just the model being brief. Unfaithful CoTs often check every option and build a justification for the hint answer instead of naming the hint.
- When the hint points to a wrong answer, models sometimes build elaborate but flawed justifications for it, even on questions they get right without the hint. This mirrors Turpin's "rationalising" finding.
- CoT is less faithful on harder questions: GPQA scores were 44% (Claude) and 32% (R1) lower in relative terms than MMLU (§3, Fig. 4). The authors suggest faithful CoTs depend on the model first working out its own answer and then noticing the hint disagrees.
- Outcome-based RL improves faithfulness at first, then plateaus around 28% (MMLU) and 20% (GPQA) (§4, Fig. 5).
- In the reward-hacking environments, the model learned to exploit the hack on >99% of examples, but verbalised it in <2% of examples in 5 of 6 environments (§5, Fig. 7).

## Important concept for our research

This paper is the closest existing study to our own experiment.

Its sycophancy hint is the same type of cue as Turpin's "Suggested Answer", and its faithfulness score is the same thing as our planned "cue acknowledgement" measure: of the cases where the cue flipped the answer, how often did the explanation admit it?

It shows that Turpin's 2023 finding did not go away with reasoning models. Reasoning models acknowledge cues more often, but still in a minority of cases.

The authors also state that their score is likely an upper bound on true faithfulness (§2.1). A CoT that fails to mention the hint is clearly unfaithful, but a CoT that does mention it is not necessarily fully faithful. This matches Turpin's point that these tests can detect unfaithfulness but not prove faithfulness.

## Method relevant to our project

Several parts of the paper could be used directly in our experiment:

1. Filtering on answer flips. Only count cases where the original answer was not the cue answer and the cued answer is. This gives a clear definition of "the cue changed the answer".
2. The verbalisation criterion (mentions the cue and depends on it; a final-step mention doesn't count). This could be our operational definition of "acknowledged the cue", which is still an open question from the 29 Sept entry.
3. The sycophancy wording examples (Table 1) as a reference for phrasing our cue.
4. Checking that the cue answer is chosen more often than other wrong answers, so changes aren't just noise. With only 30 questions this matters for us.
5. Temperature 0, to reduce random answer changes between the two conditions.
6. Using an LLM judge with manual spot-checks. We could instead judge all responses by hand, since we only have 120.

## Limitations relevant to our project

The authors say their settings are unrealistic in two ways (§7.2):
- Multiple-choice exam questions normally come with explanations about the content, so models may have learned not to mention "circumstantial" information like hints.
- The hints are very easy to use without reasoning, so the results say nothing about tasks where a CoT is actually needed.

The paper uses MMLU and GPQA, not BBH. Its numbers are therefore context for our study, not a direct baseline.

The faithfulness judge is itself an LLM (Claude 3.5 Sonnet), validated only on a subset.

The paper is a preprint by a model developer evaluating partly its own models. It has not been peer reviewed (to our knowledge — to be confirmed).

The excluded o1/o3 models show a practical issue: if a model's full reasoning is hidden, this kind of test cannot be run on it.

## Relevance to our research

This paper provides:
- evidence that Turpin's finding has been reproduced on reasoning models (supports the claim in our 30 Sept entry);
- a faithfulness metric very close to our "cue acknowledgement" measure;
- a precise definition of what counts as acknowledging a cue;
- a 2023 → 2025 → our 2026 comparison line for the paper and presentation;
- the "upper bound" and "unrealistic setting" limitations to cite in our own limitations section;
- a critical angle: CoT monitoring is useful for noticing problems but not reliable enough to rule them out.

## Questions for our next group meeting

- Should we adopt Chen et al.'s verbalisation criterion as our definition of "acknowledged the cue"?
- Can we see the full reasoning of GPT-5.6 Luna and Claude Sonnet 5.5, or only a summary? Chen et al. excluded o1/o3 for exactly this reason.
- Should we compare our acknowledgement rate with Chen's sycophancy results, even though they used MMLU/GPQA and we use BBH?
- With only 30 questions, how many answer flips do we expect? If very few, our acknowledgement rate will be based on a tiny number of cases.
- Should we judge acknowledgement by hand (two people independently) instead of with an LLM judge?
- Should Chua & Evans (2025) be read as well, since Chen cites it as consistent with their findings?
