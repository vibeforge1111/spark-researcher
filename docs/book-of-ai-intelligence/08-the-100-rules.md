# Chapter 8: The 100 Rules

This appendix is the compact version of the full book.

It is meant to be read like a checklist you can revisit after the stories and explanations.

## What Real Intelligence Looks Like

1. Do not confuse sounding smart with being smart.
2. A smart AI should solve new problems, not just repeat old answers.
3. Good writing is not the same as good thinking.
4. Confidence is not proof.
5. Real intelligence shows up when the problem changes a little.
6. A strong AI can explain why it did something.
7. A strong AI can notice when it may be wrong.
8. A strong AI improves when given feedback.
9. A strong AI can transfer what it learned to a new situation.
10. Real intelligence is flexibility, not memorization.

## How To Avoid Training Junk

11. Do not feed the model lots of low-value repetitive text.
12. Remove boilerplate, spam, and empty filler.
13. Do not reward the AI for being verbose just to sound impressive.
14. Do not train mostly on easy examples.
15. Do not let the AI learn shortcuts that only work on benchmarks.
16. Do not use messy labels and inconsistent formats.
17. Do not mix good data and bad data without filtering.
18. Do not assume more data always means better data.
19. Do not keep weak examples just because they are easy to collect.
20. Bad training data creates fake intelligence.

## How To Train For Actual Intelligence

21. Train on tasks that require thinking, not just pattern matching.
22. Give it problems with ambiguity, tradeoffs, and uncertainty.
23. Include tasks that need multi-step reasoning.
24. Teach it to compare options, not just produce one answer.
25. Train it to check its own work.
26. Train it to revise after feedback.
27. Train it on edge cases, not just common cases.
28. Include examples where the first answer is wrong.
29. Reward correction, not just speed.
30. The best training teaches the AI how to think, not what phrase to use.

## How Trainers Usually Improve Models

31. Start broad, then narrow down.
32. First build general ability, then teach useful behavior.
33. Use human feedback where the right answer is subtle.
34. Use automated grading where the rules are clear.
35. Use strong evaluators, not weak ones.
36. Improve the data, not just the model size.
37. Study failures closely.
38. Retrain using the failures that matter most.
39. Keep testing after every major change.
40. Good training is iterative, not one big magic run.

## How To Tell Primitive From Intelligent Behavior

41. Primitive AI repeats patterns it has seen before.
42. Intelligent AI handles new combinations.
43. Primitive AI falls apart when wording changes.
44. Intelligent AI still gets the idea.
45. Primitive AI gives polished nonsense.
46. Intelligent AI asks better questions or flags uncertainty.
47. Primitive AI overcommits.
48. Intelligent AI knows when to stop and verify.
49. Primitive AI wins on familiar test sets.
50. Intelligent AI survives real-world messiness.

## How Not To Over-Optimize For Benchmarks

51. Benchmarks are useful, but they are not reality.
52. A high score can still hide shallow understanding.
53. Always test on private internal tasks too.
54. Change the wording and see if the model still works.
55. Test on real user jobs, not just benchmark questions.
56. Look for cases where the AI cheats the metric.
57. Reward usefulness, not just score.
58. Watch for benchmark contamination.
59. Keep some evals hidden from the training process.
60. If the model only got better on the scoreboard, be suspicious.

## How Specialization Actually Works

61. Specialized AI gets good by focusing on a narrow job.
62. Define the job clearly before training.
63. Build tests for that exact job first.
64. Collect examples from real failures in that job.
65. Use domain experts to judge quality.
66. Teach the AI the real constraints of the field.
67. Give it the right tools for that field.
68. Do not make it general if you only need it to do one thing very well.
69. Narrow scope often beats broad ambition.
70. Specialists improve fastest when the target is concrete.

## The Lightweight Systems Lesson

71. Do not try to put everything into the model itself.
72. Use tools for tool-like work.
73. Use retrieval for changing facts.
74. Use calculators for math.
75. Use code for precise operations.
76. Use search when the answer changes over time.
77. Use external memory instead of bloating prompts.
78. Keep the live context clean and small.
79. Smaller, cleaner systems often outperform bloated ones.
80. Good structure is often better than brute force.

## How Memory Is Usually Done Well

81. Not everything should become memory.
82. Short-term context is for the current task.
83. Long-term memory is for durable facts and preferences.
84. Store summaries, not giant transcript dumps.
85. Only keep memories that help later.
86. Attach source and date when possible.
87. Let bad memories be corrected or deleted.
88. Do not treat random conversation residue as knowledge.
89. Retrieve only the few memories that matter.
90. Memory without hygiene becomes noise.

## How Self-Improving Agents Should Work

91. Do not let the AI freely rewrite itself with no guardrails.
92. Let it propose improvements, then test them.
93. Every change should have a measurable reason.
94. Run changes in shadow mode first.
95. Keep rollback options ready.
96. Humans should approve important persistent changes.
97. Reward real gains, not prettier wording.
98. Use failures to guide where improvement happens next.
99. Keep complexity under control as the system evolves.
100. A self-improving system is only good if it becomes better without becoming messier, less truthful, or less safe.
