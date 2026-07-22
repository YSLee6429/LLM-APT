import type { ProblemDefinition } from "../api/types";

export const exampleProblem: ProblemDefinition = {
  problem_id: "boundary-last-segment",
  title: "最后一个连续区间",
  statement: "给定整数序列，统计所有由相同元素构成的极大连续区间数量。单元素区间同样计入答案。",
  language: "zh-CN",
  tests: [
    { case_id: "single", standard_input: "1\n7\n", expected_output: "1\n", hidden: false },
    { case_id: "alternating", standard_input: "5\n1 2 1 2 1\n", expected_output: "5\n" },
    { case_id: "last-run", standard_input: "6\n1 1 2 3 3 3\n", expected_output: "3\n" },
  ],
  limits: {
    time_limit_ms: 1000,
    memory_limit_mb: 256,
    process_limit: 1,
    output_limit_bytes: 1048576,
  },
  output_policy: "trim_trailing_whitespace",
};

export const exampleProblemJson = JSON.stringify(exampleProblem, null, 2);
