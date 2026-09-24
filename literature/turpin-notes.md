# Turpin et al. (2023) — Literature Notes

## Paper

Miles Turpin, Julian Michael, Ethan Perez and Samuel R. Bowman (2023).

"Language Models Don't Always Say What They Think:
Unfaithful Explanations in Chain-of-Thought Prompting."

NeurIPS 2023.

## Research problem

The paper investigates whether Chain-of-Thought (CoT) explanations faithfully represent the reasons behind an LLM's predictions.

The authors distinguish between an explanation being plausible and being faithful. An explanation may sound reasonable and support the final answer without accurately representing the factors that influenced the model's prediction.

## Main idea

The researchers deliberately introduce biasing features into model inputs and observe whether the model's predictions change.

If a biasing feature changes the model's prediction but the CoT explanation does not acknowledge that feature, this provides evidence that the explanation is unfaithful.

The paper uses counterfactual comparisons between inputs with and without particular features.

## Experimental setup

Models:
- GPT-3.5 (text-davinci-003)
- Claude 1.0

Benchmarks:
- BIG-Bench Hard (BBH)
- Bias Benchmark for QA (BBQ)

For BBH, 13 tasks were selected and 3,299 examples were used for evaluation.

Two main biasing features were tested:
1. "Answer is Always A" — answer options in demonstrations were reordered so the correct answer was always A.
2. "Suggested Answer" — the prompt suggested a particular answer.

The authors compared zero-shot and few-shot CoT and also compared CoT with No-CoT.

## Main findings

- CoT explanations can be systematically unfaithful.
- Biasing features could substantially influence model predictions without being mentioned in the generated explanations.
- Models sometimes changed their explanations to rationalise newly generated incorrect answers.
- In a sample of 104 unfaithful explanations, up to 73% supported the bias-consistent answer.
- 15% of the sampled unfaithful explanations had no obvious errors, showing that an explanation can appear reasonable while still being unfaithful.
- On BBQ, models sometimes used evidence inconsistently in ways associated with social stereotypes.

## Important concept for our research

Plausibility and faithfulness are different.

An explanation can:
- sound logical;
- support the final answer; and
- contain no obvious reasoning error,

while still failing to represent the factors that actually influenced the model's prediction.

Therefore, simply asking whether a CoT explanation "makes sense" is not enough to establish faithfulness.

## Method relevant to our project

The counterfactual/perturbation approach may be useful for our own experiment.

Possible general procedure:

1. Give the model an original input.
2. Record its answer and CoT explanation.
3. Change one controlled feature of the input.
4. Record the new answer and CoT explanation.
5. Compare the model's behaviour with what its explanations claim is important.

We should investigate the approach further before deciding whether to use it.

## Limitations relevant to our project

The authors state that their evaluation can identify examples of unfaithfulness but cannot prove that an explanation is faithful.

Their tests mainly involve relatively small input modifications and therefore do not establish whether an explanation accurately predicts model behaviour across a much wider range of inputs.

This limitation should be considered if we adapt their methodology.

## Relevance to our research

This paper provides:
- strong motivation for investigating CoT faithfulness;
- a distinction between plausible and faithful explanations;
- an example of an empirical method for testing faithfulness;
- possible ideas for designing controlled perturbation experiments;
- an important limitation that we should consider when interpreting experimental results.

## Questions for our next group meeting

- Can we adapt the counterfactual approach to a smaller student-scale experiment?
- What type of task would make faithfulness easier to evaluate?
- What should we change in the input?
- How should we measure whether the explanation and model behaviour are consistent?
- Can the approach from this paper be combined with methods from Lanham et al. (2023)?