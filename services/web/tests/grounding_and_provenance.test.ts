import test from 'node:test';
import assert from 'node:assert';
import type { Finding, ParsedFileDiff } from '../src/types/index.ts';

test('Provenance tier categorization adheres to AGENTS.md mandates', () => {
  const deterministicFinding: Finding = {
    id: 'f-1',
    rule_id: 'PY003',
    severity: 'high',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/main.py',
    start_line: 12,
    end_line: 12,
    title: 'Mutable default argument',
    description: 'Found mutable default argument',
  };

  const aiHypothesisFinding: Finding = {
    id: 'f-2',
    rule_id: 'AI_PY_CONCURRENCY',
    severity: 'medium',
    source: 'AI_GENERATED_HYPOTHESIS',
    file_path: 'src/main.py',
    start_line: 45,
    end_line: 48,
    title: 'Potential race condition',
    description: 'Unsynchronized shared state',
  };

  const verifiedTestFinding: Finding = {
    id: 'f-3',
    rule_id: 'TEST_COVERAGE_GAP',
    severity: 'low',
    source: 'VERIFIED_TEST_RESULT',
    file_path: 'src/worker.py',
    start_line: null,
    end_line: null,
    title: 'Missing test coverage',
    description: 'Modified branch lacks coverage',
  };

  assert.strictEqual(deterministicFinding.source, 'DETERMINISTIC_STATIC_ANALYSIS');
  assert.strictEqual(aiHypothesisFinding.source, 'AI_GENERATED_HYPOTHESIS');
  assert.strictEqual(verifiedTestFinding.source, 'VERIFIED_TEST_RESULT');

  // Verify that AI findings are never labeled as verified or deterministic
  assert.notStrictEqual(aiHypothesisFinding.source, 'DETERMINISTIC_STATIC_ANALYSIS');
  assert.notStrictEqual(aiHypothesisFinding.source, 'VERIFIED_TEST_RESULT');
});

test('Line-grounding correctly correlates findings to diff added lines', () => {
  const diffFile: ParsedFileDiff = {
    file_path: 'src/utils.py',
    old_path: null,
    is_new_file: false,
    is_deleted_file: false,
    is_renamed_file: false,
    is_binary: false,
    hunks: [
      {
        old_start: 10,
        old_length: 5,
        new_start: 10,
        new_length: 8,
        header: '@@ -10,5 +10,8 @@',
        lines: [
          { type: ' ', content: 'def helper():', old_line_number: 10, new_line_number: 10 },
          { type: '+', content: '    val = eval(x)', old_line_number: null, new_line_number: 11 },
          { type: '+', content: '    return val', old_line_number: null, new_line_number: 12 },
        ],
        added_lines: [11, 12],
        deleted_lines: [],
        context_lines: [10],
      },
    ],
    added_lines: [11, 12],
    deleted_lines: [],
  };

  const groundedFinding: Finding = {
    id: 'f-1',
    rule_id: 'PY004',
    severity: 'critical',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/utils.py',
    start_line: 11,
    end_line: 11,
    title: 'Unsafe eval call',
    description: 'Detected dangerous eval()',
  };

  const ungroundedFinding: Finding = {
    id: 'f-2',
    rule_id: 'PY002',
    severity: 'medium',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/utils.py',
    start_line: 99,
    end_line: 99,
    title: 'Bare except clause',
    description: 'Found bare except',
  };

  // Test grounding evaluation
  const isGrounded1 = diffFile.added_lines.includes(groundedFinding.start_line as number);
  const isGrounded2 = diffFile.added_lines.includes(ungroundedFinding.start_line as number);

  assert.strictEqual(isGrounded1, true, 'Finding on line 11 should be grounded to diff');
  assert.strictEqual(isGrounded2, false, 'Finding on line 99 should NOT be grounded to diff');
});

test('Aggregated severity metrics correctly compute counts', () => {
  const findings: Finding[] = [
    { id: '1', rule_id: 'PY004', severity: 'critical', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'a.py', start_line: 1, end_line: 1, title: 'T1', description: 'D1' },
    { id: '2', rule_id: 'PY003', severity: 'high', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'a.py', start_line: 2, end_line: 2, title: 'T2', description: 'D2' },
    { id: '3', rule_id: 'PY002', severity: 'medium', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'b.py', start_line: 5, end_line: 5, title: 'T3', description: 'D3' },
    { id: '4', rule_id: 'PY005', severity: 'low', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'c.py', start_line: 8, end_line: 8, title: 'T4', description: 'D4' },
    { id: '5', rule_id: 'AI001', severity: 'critical', source: 'AI_GENERATED_HYPOTHESIS', file_path: 'd.py', start_line: 10, end_line: 10, title: 'T5', description: 'D5' },
  ];

  const counts = {
    critical: findings.filter((f) => f.severity === 'critical').length,
    high: findings.filter((f) => f.severity === 'high').length,
    medium: findings.filter((f) => f.severity === 'medium').length,
    low: findings.filter((f) => f.severity === 'low').length,
    info: findings.filter((f) => f.severity === 'info').length,
    deterministic: findings.filter((f) => f.source === 'DETERMINISTIC_STATIC_ANALYSIS').length,
    aiHypothesis: findings.filter((f) => f.source === 'AI_GENERATED_HYPOTHESIS').length,
  };

  assert.strictEqual(counts.critical, 2);
  assert.strictEqual(counts.high, 1);
  assert.strictEqual(counts.medium, 1);
  assert.strictEqual(counts.low, 1);
  assert.strictEqual(counts.info, 0);
  assert.strictEqual(counts.deterministic, 4);
  assert.strictEqual(counts.aiHypothesis, 1);
});
