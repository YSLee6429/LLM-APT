import pytest

from llmapt.application.source_extraction import extract_candidate_source
from llmapt.domain.errors import EvaluationError


def test_plain_source_is_trimmed() -> None:
    extracted = extract_candidate_source("\nint main() {}\n", "cpp")

    assert extracted.source == "int main() {}"
    assert extracted.used_fence is False
    assert extracted.fence_label is None


def test_matching_language_fence_wins_over_explanation_block() -> None:
    response = """Reasoning:
```text
Use a loop.
```
```cpp
int main() { return 0; }
```
"""

    extracted = extract_candidate_source(response, "cpp")

    assert extracted.source == "int main() { return 0; }"
    assert extracted.used_fence is True
    assert extracted.fence_label == "cpp"


def test_ambiguous_source_blocks_are_rejected() -> None:
    response = "```cpp\nfirst\n```\n```cpp\nsecond\n```"

    with pytest.raises(EvaluationError, match="multiple ambiguous"):
        extract_candidate_source(response, "cpp")


def test_empty_and_oversized_sources_are_rejected() -> None:
    with pytest.raises(EvaluationError, match="does not contain"):
        extract_candidate_source("   ", "cpp")
    with pytest.raises(EvaluationError, match="size limit"):
        extract_candidate_source("abcd", "cpp", maximum_bytes=3)
