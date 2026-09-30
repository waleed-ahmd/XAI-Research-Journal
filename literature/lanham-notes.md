# Lanham et al. (2023) — Measuring Faithfulness in Chain-of-Thought Reasoning

## Paper

Tamera Lanham et al. (2023)

**Measuring Faithfulness in Chain-of-Thought Reasoning**

---

## What is the paper about?

The paper asks whether the Chain-of-Thought (CoT) produced by an LLM is actually
related to how the model arrives at its final answer.

The main concern is:

> A reasoning trace can look convincing without necessarily being the reasoning
> that caused the model's answer.

The authors therefore test faithfulness by intervening on the generated CoT and
observing whether the final answer changes.

---

## Main tests

### 1. Early Answering

The authors truncate the CoT at different points and ask the model for its answer.

If the answer changes as more reasoning is provided, this suggests that the model
is using the CoT.

If the answer is already fixed very early, later reasoning may be post-hoc.

### 2. Adding Mistakes

A mistake is deliberately inserted into one step of the CoT.

The model then continues the reasoning and produces an answer.

If the mistake affects the final answer, this provides evidence that the model is
actually conditioning on the reasoning.

### 3. Filler Tokens

The authors replace the CoT with meaningless filler tokens.

This tests whether CoT improves performance simply because the model gets more
test-time computation.

They found no meaningful accuracy improvement from filler tokens, suggesting that
extra computation alone does not explain the CoT benefit.

### 4. Paraphrasing

Parts of the CoT are paraphrased before the model continues reasoning.

If the exact wording contained important hidden information, paraphrasing should
hurt performance.

The authors generally found similar performance after paraphrasing.

---

## Main findings

- CoT faithfulness varies considerably between tasks.
- Some tasks show much stronger dependence on CoT than others.
- Faithfulness is not simply a fixed property of an LLM.
- Model capability and task difficulty appear to affect faithfulness.
- In many tasks, larger models showed less faithful reasoning.
- The 13B model was more faithful than the 175B model on most of their tested
  tasks.

---

## Important limitation

The authors cannot directly observe the model's actual internal reasoning.

Therefore, their experiments provide evidence about possible unfaithfulness but
cannot establish ground-truth faithfulness.

They also acknowledge that their tests may not cover every possible failure mode
and that additional experiments are needed.

---

## Relevance to our research

The most useful idea for us is the **intervention-based approach**.

Instead of only asking whether an explanation looks correct, we can ask:

> What happens to the model's behaviour when we change the explanation?

This gives us a measurable way of studying faithfulness.

---

## Connection with Turpin et al.

Turpin et al. mainly investigate whether information in the input/context can
influence the answer without appearing in the CoT.

Lanham et al. instead intervene directly on the generated CoT.

So they test related but different failure modes:

1. Change the input/context → observe the explanation and answer.
2. Change the explanation → observe the answer.

---

## Open questions

- Are the existing tests sufficient?
- Can different faithfulness tests be combined?
- Which parts of a reasoning trace actually matter for the final decision?
- Can we predict when a CoT is likely to be unfaithful?
- Do these findings hold for newer LLMs?
- Does the problem also occur in tool-using/agentic systems?
- Can faithfulness be evaluated without access to hidden model states?

---

## Key takeaway

Lanham et al. move the problem from:

**"Does the explanation look reasonable?"**

to:

**"Does the model actually depend on the reasoning it provides?"**

This intervention-based perspective is particularly relevant to our research.