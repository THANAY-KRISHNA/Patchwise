"""Unit tests for RuleOnlyProvider offline review execution."""
from datetime import datetime, timezone
import pytest
from src.github.models import GitHubPullRequest
from src.parser.diff_parser import parse_unified_diff
from src.providers.base import ReviewContext
from src.providers.rule_only import RuleOnlyProvider
from src.schemas.findings import FindingProvenance

SAMPLE_PR_DIFF = """diff --git a/app/service.py b/app/service.py
index 1000000..2000000 100644
--- a/app/service.py
+++ b/app/service.py
@@ -1,4 +1,8 @@
 def process():
-    pass
+    # Mutable default inside function definition
+    def helper(items=[]):
+        return items
+    val = eval("1 + 1")
+    return helper()
"""


@pytest.mark.asyncio
async def test_rule_only_provider_offline_review():
    parsed_diff = parse_unified_diff(SAMPLE_PR_DIFF)
    pr_meta = GitHubPullRequest(
        number=10,
        title="Offline PR test",
        state="open",
        html_url="https://github.com/org/repo/pull/10",
        base_commit_sha="1111111111111111111111111111111111111111",
        head_commit_sha="2222222222222222222222222222222222222222",
        base_ref="main",
        head_ref="test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    context = ReviewContext(
        repository="org/repo",
        pr_number=10,
        pr_metadata=pr_meta,
        parsed_diff=parsed_diff,
    )

    provider = RuleOnlyProvider()
    result = await provider.review(context)

    assert result.provider_name == "rule_only"
    assert result.grounded_findings_count > 0
    assert len(result.findings) == result.grounded_findings_count

    # Verify all findings are classified as DETERMINISTIC_STATIC_ANALYSIS
    for f in result.findings:
        assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
        assert f.start_line in parsed_diff.files[0].added_lines
