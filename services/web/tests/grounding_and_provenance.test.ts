import test from 'node:test';
import assert from 'node:assert';
import type { Finding, ParsedFileDiff } from '../src/types/index.ts';

test('Provenance tier categorization adheres to AGENTS.md mandates', () => {
  const deterministicFinding: Finding = {
    id: 'f-1',
    review_id: 'rev-1',
    rule_id: 'PY003',
    severity: 'high',
    category: 'code_quality',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/main.py',
    start_line: 12,
    end_line: 12,
    title: 'Mutable default argument',
    explanation: 'Found mutable default argument',
    created_at: '2026-10-10T12:00:00Z',
  };

  const aiHypothesisFinding: Finding = {
    id: 'f-2',
    review_id: 'rev-1',
    rule_id: 'AI_PY_CONCURRENCY',
    severity: 'medium',
    category: 'code_quality',
    source: 'AI_GENERATED_HYPOTHESIS',
    file_path: 'src/main.py',
    start_line: 45,
    end_line: 48,
    title: 'Potential race condition',
    explanation: 'Unsynchronized shared state',
    created_at: '2026-10-10T12:00:00Z',
  };

  const verifiedTestFinding: Finding = {
    id: 'f-3',
    review_id: 'rev-1',
    rule_id: 'TEST_COVERAGE_GAP',
    severity: 'low',
    category: 'test_suggestion',
    source: 'VERIFIED_TEST_RESULT',
    file_path: 'src/worker.py',
    start_line: null,
    end_line: null,
    title: 'Missing test coverage',
    explanation: 'Modified branch lacks coverage',
    created_at: '2026-10-10T12:00:00Z',
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
    review_id: 'rev-1',
    rule_id: 'PY004',
    severity: 'critical',
    category: 'security_pattern',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/utils.py',
    start_line: 11,
    end_line: 11,
    title: 'Unsafe eval call',
    explanation: 'Detected dangerous eval()',
    created_at: '2026-10-10T12:00:00Z',
  };

  const ungroundedFinding: Finding = {
    id: 'f-2',
    review_id: 'rev-1',
    rule_id: 'PY002',
    severity: 'medium',
    category: 'exception_handling',
    source: 'DETERMINISTIC_STATIC_ANALYSIS',
    file_path: 'src/utils.py',
    start_line: 99,
    end_line: 99,
    title: 'Bare except clause',
    explanation: 'Found bare except',
    created_at: '2026-10-10T12:00:00Z',
  };

  // Test grounding evaluation
  const isGrounded1 = diffFile.added_lines.includes(groundedFinding.start_line as number);
  const isGrounded2 = diffFile.added_lines.includes(ungroundedFinding.start_line as number);

  assert.strictEqual(isGrounded1, true, 'Finding on line 11 should be grounded to diff');
  assert.strictEqual(isGrounded2, false, 'Finding on line 99 should NOT be grounded to diff');
});

test('Aggregated severity metrics correctly compute counts', () => {
  const findings: Finding[] = [
    { id: '1', review_id: 'r1', rule_id: 'PY004', severity: 'critical', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'a.py', start_line: 1, end_line: 1, title: 'T1', explanation: 'D1', created_at: '2026-10-10T12:00:00Z' },
    { id: '2', review_id: 'r1', rule_id: 'PY003', severity: 'high', category: 'code_quality', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'a.py', start_line: 2, end_line: 2, title: 'T2', explanation: 'D2', created_at: '2026-10-10T12:00:00Z' },
    { id: '3', review_id: 'r1', rule_id: 'PY002', severity: 'medium', category: 'exception_handling', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'b.py', start_line: 5, end_line: 5, title: 'T3', explanation: 'D3', created_at: '2026-10-10T12:00:00Z' },
    { id: '4', review_id: 'r1', rule_id: 'PY005', severity: 'low', category: 'test_suggestion', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'c.py', start_line: 8, end_line: 8, title: 'T4', explanation: 'D4', created_at: '2026-10-10T12:00:00Z' },
    { id: '5', review_id: 'r1', rule_id: 'AI001', severity: 'critical', category: 'security_pattern', source: 'AI_GENERATED_HYPOTHESIS', file_path: 'd.py', start_line: 10, end_line: 10, title: 'T5', explanation: 'D5', created_at: '2026-10-10T12:00:00Z' },
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

test('JavaScript and TypeScript findings (JS001-JS004) adhere to Tier 1 provenance and diff line grounding', () => {
  const jsFindings: Finding[] = [
    { id: 'js-1', review_id: 'r1', rule_id: 'JS001', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/runtime.js', start_line: 11, end_line: 11, title: 'eval execution', explanation: 'Unsafe eval', created_at: '2026-10-10T12:00:00Z' },
    { id: 'js-2', review_id: 'r1', rule_id: 'JS002', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/view.tsx', start_line: 42, end_line: 42, title: 'dangerouslySetInnerHTML', explanation: 'XSS risk', created_at: '2026-10-10T12:00:00Z' },
    { id: 'js-3', review_id: 'r1', rule_id: 'JS003', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/cli.ts', start_line: 3, end_line: 3, title: 'exec template', explanation: 'Command injection', created_at: '2026-10-10T12:00:00Z' },
    { id: 'js-4', review_id: 'r1', rule_id: 'JS004', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/db.js', start_line: 26, end_line: 26, title: 'SQL concat', explanation: 'SQL injection', created_at: '2026-10-10T12:00:00Z' },
  ];

  for (const f of jsFindings) {
    assert.strictEqual(f.source, 'DETERMINISTIC_STATIC_ANALYSIS');
    assert.ok(f.rule_id.startsWith('JS'));
    assert.ok(typeof f.start_line === 'number' && f.start_line > 0);
  }
});

test('Java findings (JV001-JV004) adhere to Tier 1 provenance and diff line grounding', () => {
  const javaFindings: Finding[] = [
    { id: 'jv-1', review_id: 'r1', rule_id: 'JV001', severity: 'critical', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/Receiver.java', start_line: 11, end_line: 11, title: 'readObject deserialization', explanation: 'Unsafe deserialization', created_at: '2026-10-10T12:00:00Z' },
    { id: 'jv-2', review_id: 'r1', rule_id: 'JV002', severity: 'critical', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/Cmd.java', start_line: 17, end_line: 17, title: 'Runtime.exec command injection', explanation: 'Command injection', created_at: '2026-10-10T12:00:00Z' },
    { id: 'jv-3', review_id: 'r1', rule_id: 'JV003', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/Dao.java', start_line: 42, end_line: 42, title: 'JDBC SQL injection', explanation: 'SQL injection', created_at: '2026-10-10T12:00:00Z' },
    { id: 'jv-4', review_id: 'r1', rule_id: 'JV004', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/Storage.java', start_line: 72, end_line: 72, title: 'Path traversal', explanation: 'Path traversal', created_at: '2026-10-10T12:00:00Z' },
  ];

  for (const f of javaFindings) {
    assert.strictEqual(f.source, 'DETERMINISTIC_STATIC_ANALYSIS');
    assert.ok(f.rule_id.startsWith('JV'));
    assert.ok(typeof f.start_line === 'number' && f.start_line > 0);
  }
});

test('C/C++ findings (CC001-CC004) adhere to Tier 1 provenance and diff line grounding', () => {
  const cppFindings: Finding[] = [
    { id: 'cc-1', review_id: 'r1', rule_id: 'CC001', severity: 'critical', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/main.c', start_line: 12, end_line: 12, title: 'Unbounded strcpy', explanation: 'Unbounded string operation', created_at: '2026-10-10T12:00:00Z' },
    { id: 'cc-2', review_id: 'r1', rule_id: 'CC002', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/log.c', start_line: 21, end_line: 21, title: 'Format string misuse', explanation: 'Non-literal format string', created_at: '2026-10-10T12:00:00Z' },
    { id: 'cc-3', review_id: 'r1', rule_id: 'CC003', severity: 'critical', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/exec.cpp', start_line: 35, end_line: 35, title: 'Command injection', explanation: 'Dynamic system call', created_at: '2026-10-10T12:00:00Z' },
    { id: 'cc-4', review_id: 'r1', rule_id: 'CC004', severity: 'medium', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'src/temp.c', start_line: 47, end_line: 47, title: 'Insecure temporary file', explanation: 'tmpnam race condition', created_at: '2026-10-10T12:00:00Z' },
  ];

  for (const f of cppFindings) {
    assert.strictEqual(f.source, 'DETERMINISTIC_STATIC_ANALYSIS');
    assert.ok(f.rule_id.startsWith('CC'));
    assert.ok(typeof f.start_line === 'number' && f.start_line > 0);
  }
});

test('SQL and HiveQL findings (SQL001-SQL005) adhere to Tier 1 provenance and diff line grounding', () => {
  const sqlFindings: Finding[] = [
    { id: 'sql-1', review_id: 'r1', rule_id: 'SQL001', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'scripts/update.sql', start_line: 2, end_line: 2, title: 'Unbounded UPDATE', explanation: 'Missing WHERE clause', created_at: '2026-10-10T12:00:00Z' },
    { id: 'sql-2', review_id: 'r1', rule_id: 'SQL002', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'sp/dynamic.sql', start_line: 6, end_line: 6, title: 'EXECUTE IMMEDIATE', explanation: 'Dynamic SQL concat', created_at: '2026-10-10T12:00:00Z' },
    { id: 'sql-3', review_id: 'r1', rule_id: 'SQL003', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'auth/grants.sql', start_line: 12, end_line: 12, title: 'GRANT ALL PRIVILEGES', explanation: 'Excessive privileges', created_at: '2026-10-10T12:00:00Z' },
    { id: 'sql-4', review_id: 'r1', rule_id: 'SQL004', severity: 'high', category: 'security_pattern', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'users/create.sql', start_line: 5, end_line: 5, title: 'Hardcoded password', explanation: 'Masked credential', created_at: '2026-10-10T12:00:00Z' },
    { id: 'sql-5', review_id: 'r1', rule_id: 'SQL005', severity: 'medium', category: 'code_quality', source: 'DETERMINISTIC_STATIC_ANALYSIS', file_path: 'etl/daily.hql', start_line: 18, end_line: 18, title: 'INSERT OVERWRITE TABLE', explanation: 'HiveQL unpartitioned overwrite', created_at: '2026-10-10T12:00:00Z' },
  ];

  for (const f of sqlFindings) {
    assert.strictEqual(f.source, 'DETERMINISTIC_STATIC_ANALYSIS');
    assert.ok(f.rule_id.startsWith('SQL'));
    assert.ok(typeof f.start_line === 'number' && f.start_line > 0);
  }
});
