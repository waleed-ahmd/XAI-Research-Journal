all findings in these notes are in correspondence to the period of time for when they were found. Reasoning within LMs have ofcourse improved and changed since then.

- **Sec1 chain of though prompting pages 1-3** 
    - "the goal of this paper is to endow language models with the ability to generate a similar chain of thought" — similar to that of humans. e.g. After she.... Then she.... She gives.... the answers is .....
    - Put more simple, "A coherent series of intermediate reasoning steps that lead to the final answer for a problem"
    - LLMs can show chain of thought thinking if chain of thought examples are included in the prompt
        - [We will show that sufficiently large2language models can generate chains of thought if demonstrations of chain-of-thought reasoning are provided in the exemplars for few-shot prompting.]
    - The paper states several attractive properties chain of thought thinking has for facilitating reasoning in LLMs [1. First, chain of thought, in principle, allows models to decompose multi-step problems into intermediate steps, which means that additional computation can be allocated to problems that require more reasoning steps. 2. Second, a chain of thought provides an interpretable window into the behavior of the model, suggesting how it might have arrived at a particular answer and providing opportunities to debug where the reasoning path went wrong (although fully characterizing a model’s computations that support an answer remains an open question). 3. Third, chain-of-thought reasoning can be used for tasks such as math word problems, commonsense reasoning, and symbolic manipulation, and is potentially applicable (at least in principle) to any task that humans can solve via language. 4. Finally, chain-of-thought reasoning can be readily elicited in sufficiently large off-the-shelf language models simply by including examples]
    - The paper states using empirical experiments to observe the utility of chain‒of-thought prompting for arithmetic reasoning, common sense reasoning and symbolic reasoning.
    - Surprisingly, "[arithmetic reasoning is a task wherelanguage models often struggle]". Also, chain-of-thought prompting with a 540B param LM performs similarly in comparison to a task specific fine tuned model on several tasks showing LMs typically struggle with arithmetic reasoning regardless of the type of model in use.
    - The experimental setup the paper states is that they have five math word problem benchmarks they're gonna use to evaluate standard prompting vs chain of thought prompting. i.e. "few-shot prompting" where multiple examples of input and output pairs are included in the prompt VS the same but including a chain-of-thought with each output.

    **The GSM8k jump**
        GSM8k is a benchmark of grade school math word problems and was hte hardest arithmetic benchmark in the paper.

        in Table 1 (Page 20) figure 2(page 2) shows the accuracy of the model "PaLM 540B" on GSM8k
            With standard prompting (quesiton -> answer) — Accuracy: 17.9%
    
            With chain of thought prompting(examples included chain of thought) — Accuracy: 56.9%

            The best model before this was GPT-3 175B which was specifically fine tuned for maths and had an Accuracy of 55%.

        the same model trippled its accuracy with no additional training and why people treat the chain of thought steps it produces as explanations.
- 
- **Sec2 Ablations**
    - Ablation Study::An experimental study where components of a system are removed or reduced to understand their contribution to the overall performance.[ablation]
    - The paper states three different types of chain of thought prompting
        - Equation only: "where the models is prompted to output only a mathematical equation before giving the answer"
            - Does not help much for GSM8k benchmark implying the questions stated there are too complex to translate into an equation without the natural langauge reasoning steps in chain og thought
            - for one/two-step problems however, performance is improved
        - variable compute only: "the model is prompted to output a sequence of dots equal to the number of character in the equation needed to solve the problem." This is to make the model spend more on computation on harder problems as there will be more dots. harder problem = longer equation = longer dot sequence to force model to generate more tokens before producing answer
            - This variant performed the same as the baseline showing that more computation does not mean better output but it still reinforces the benefit of expressing intermediate steps via natural language which is what the equation only method ommitted.
        - Chain of thought after answer: "model is given the chain of thought prompt after the answer is produced" this is to help see whether the model actually depends on the produced chain of thought to give the final answer
            - performed the same as the baseline reinforcing again the benefit using the chain of thought.
    - **Robustness of chain of thought:**
        - Surprsingly, [varying the permutation offew-shot exemplars can cause the accuracy of GPT-3 on SST-2 to range from near chance (54.3%) to near state of the art (93.4%) (Zhao et al., 2021)]
            - put simply, the examples in fewshot examples — switching up the order of which they're given in the prompt can drastically change the accruacy of a model like gpt 3
        - in this section they had the 3 authors of this paper provide their own chain of thought reasoning for a fixed set of input and outputs to be included in their prompt. With their different chain of thought reasoning, all 3 authors' prompts outperformed the standard baseline by a large margin showing that chain of thought doesnt depend on a particular linguistic style.
        - Surprisingly, varying the permutation of few shot examples (i.e. without the chain of thought reasoning included) the accuracy changes a lot but when you include the chain of thought with the exemplars, and then change the permutation of the examples again the accuracy does not change much.
            - This is just showing that — chain of thought regardless of the order when included in the prompt, improves accuracy.
    - **Page 9 - Limitations and conclusion**
        - As for limitations, we first qualify that although chain of thought emulates the thought processes ofhuman reasoners, this does not answer whether the neural network is actually “reasoning,” which we leave as an open question.
             - i.e. The chain of thought prompts we give to the model make it generate text that looks like a reasoning chain but we dont actually know whether its performing a genuine logical solution or just producing plausible sounding steps. Xai observation: black box technique will never allow us to tell, glass box however???
             - if we cant see its actual reasoning, we cant guarantee the generated steps have integrity.
        - Second, although the cost of manually augmenting exemplars withchains of thought is minimal in the few-shot setting, such annotation costs could be prohibitive for finetuning (though this could potentially be surmounted with synthetic data generation, or zero-shot generalization).
            - i.e. adding a chaint of thought to a few shot example is cheap when you only have a handful of example. However, finetuning a model for this would require thousands of annotated examples which would be expensive to write by hand.
                - this means if the community wanted to apply chain of thought thinking to scale, we'd need automated ways to generate the chain of thought traces OR even just methods that work without any manual chain of thought data.
        - Third, there is no guarantee of correct reasoning paths, which can lead to both correctand incorrect answers; improving factual generations of language models is an open direction for future work
            - i.e. the model can produce a chain of thought that seems to be logical but may contain mistakes or false statements and by coincidence, will end up with a final answer that is correct.
            - this limits the reliability of chain of thought for things like medical advice, legal reasoning etc.
        - Finally,the emergence of chain-of-thought reasoning only at large model scales makes it costly to serve in real-world applications; further research could explore how to induce reasoning in smaller models.
            - chain of thought benefits appear only for very large models and deploying them is expensive in terms of compute, latency and energy. (out dated clearly)
    - **Conclusions**
        - [We have explored chain-of-thought prompting as a simple and broadly applicable method for enhancing reasoning in language models.]
        - Chain of thought prompting expands the set of problems that LLMs can handle. The author hopes this will inspire further work on language-based approaches to reasoning.
        - 
        - 


