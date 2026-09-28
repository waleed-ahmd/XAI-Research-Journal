# Wei et al. (2022) — Literature Notes

## Paper

Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed H. Chi, Quoc V. Le and Denny Zhou (2022).

"Chain-of-Thought Prompting Elicits Reasoning in Large Language Models."

NeurIPS 2022.

## Research problem

Making language models larger improved many tasks, but not multi-step reasoning tasks such as arithmetic, commonsense and symbolic reasoning.

The paper investigates whether prompting a model to write out intermediate reasoning steps before its answer can improve its performance on these tasks, without any training or finetuning.

## Main idea

Chain-of-Thought (CoT) prompting adds step-by-step reasoning to the few-shot examples given in the prompt. Each example is formatted as question → chain of thought → answer.

The model then produces its own chain of thought before giving a final answer.

The authors define a chain of thought as "a series of intermediate natural language reasoning steps that lead to the final output" (p. 2).

## Experimental setup

Models:
- GPT-3 (350M–175B, including text-davinci-002)
- LaMDA (422M–137B)
- PaLM (8B, 62B, 540B)
- UL2 20B
- Codex (code-davinci-002)

Benchmarks:
- Arithmetic: GSM8K, SVAMP, ASDiv, AQuA, MAWPS
- Commonsense: CSQA, StrategyQA, Date Understanding, Sports Understanding, SayCan
- Symbolic: last letter concatenation, coin flip

The prompts used eight hand-written examples for most maths benchmarks. Greedy decoding was used, and no models were finetuned.

The authors also ran ablations to check why CoT helps:
1. "Equation only": the model writes only an equation before the answer.
2. "Variable compute only": the model writes a sequence of dots instead of reasoning.
3. "Reasoning after answer": the chain of thought comes after the answer instead of before it.

## Main findings

- CoT substantially improved multi-step reasoning. On GSM8K, PaLM 540B improved from 17.9% to 56.9% (Table 1, p. 20).
- CoT is an emergent ability of scale. It only helped models of around 100B parameters or more. Smaller models produced "fluent but illogical" reasoning and performed worse (p. 4).
- The gains were largest on harder problems and very small on simple one-step problems.
- On GSM8K, all three ablations performed about the same as standard prompting, well below CoT. This suggests the natural-language reasoning itself is useful, rather than just extra tokens or a written equation (p. 5–6). "Equation only" did help on easier one- or two-step datasets (p. 5; Table 6, p. 23).
- Results held across different people writing the example chains of thought.
- In a manual check of 50 correct GSM8K answers from LaMDA 137B, almost all chains of thought were correct, but at least one reached the right answer through incorrect reasoning (p. 5, p. 25).

## Important concept for our research

The paper is about performance, not explainability.

The authors describe CoT as providing "an interpretable window into the behavior of the model", but in the same sentence add that "fully characterizing a model's computations that support an answer remains an open question" (p. 3).

They also describe interpretability as "just a side effect" of CoT (p. 24) and state that CoT "does not answer whether the neural network is actually 'reasoning'" (p. 9).

Faithfulness is never defined or tested. Outside the reference list, the word appears only once, as an item in a list of abilities that may emerge with scale (p. 16).

Therefore, the paper checks whether the reasoning is correct, not whether it is faithful. A chain of thought can be correct without reflecting what actually caused the answer.

## Method relevant to our project

Several parts of the paper may be useful for our experiment:

1. The "reasoning after answer" ablation is an early test of whether the model depends on its chain of thought. Lanham et al. (2023) appear to develop this into per-example faithfulness tests.
2. The error categories from the manual analysis (calculator error, symbol mapping error, one step missing, semantic understanding error) could be used to judge whether an explanation is logically correct.
3. The authors manually analysed 50 correct and 50 incorrect examples. This supports our plan of using a small number of carefully analysed examples.
4. The full prompts are given in Appendix G, so they could be reused as a "2022-style" condition.

We should investigate whether these ideas work on current models before deciding whether to use them.

## Limitations relevant to our project

The authors state that there is "no guarantee of correct reasoning paths", and that incorrect reasoning can still lead to correct answers (p. 9). They note this is more likely for multiple-choice tasks than free-response tasks (p. 25–26).

The ablations only show that the chain of thought matters on average. They do not show whether an individual explanation reflects the model's actual reasoning.

The paper's only analysis of reasoning quality is small and manual. The main text and appendix also give slightly different counts for correct answers reached through incorrect reasoning (p. 5 vs. p. 25).

Most of the models used (LaMDA, PaLM) were not publicly available (p. 30). The GPT-3 and Codex models used are also, to our knowledge, no longer offered by OpenAI (not from the paper; to be confirmed). The exact results therefore cannot be reproduced on the same models.

Current models may already score very highly on GSM8K and may have seen it during training, which could limit its usefulness for our experiment.

## Relevance to our research

This paper provides:
- the original definition of CoT prompting and its main results;
- the "interpretable window" claim that later research questions;
- evidence that the authors themselves did not claim CoT was a faithful explanation;
- early hints of unfaithfulness, such as correct answers reached through incorrect reasoning;
- ablations and error categories we could adapt;
- a baseline for comparing how CoT behaves in current models.

## Questions for our next group meeting

- Should our "then vs. now" comparison use Wei's accuracy results, or the faithfulness results from Turpin and Lanham?
- Should we use maths tasks (easy to grade, but possibly too easy for current models) or multiple-choice tasks (suits Turpin's bias test, but allows correct answers through incorrect reasoning)?
- Can we see the full reasoning of current Claude and ChatGPT models, or only a summary?
- Could Wei's error categories be used in our evaluation?
- Who will read Lanham et al. (2023)?
