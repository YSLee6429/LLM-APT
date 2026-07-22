"""Deterministically extract one source program from an untrusted model response."""

from __future__ import annotations

import re
from dataclasses import dataclass

from llmapt.domain.errors import EvaluationError

_FENCE = re.compile(r"```(?P<label>[^\n`]*)\n(?P<body>.*?)```", re.DOTALL)


@dataclass(frozen=True, slots=True)
class ExtractedSource:
    source: str
    used_fence: bool
    fence_label: str | None


def extract_candidate_source(
    raw_text: str,
    expected_language: str,
    *,
    maximum_bytes: int = 1_000_000,
) -> ExtractedSource:
    """Select a single fenced block, or use plain text when no fence is present."""

    if maximum_bytes < 1:
        raise ValueError("maximum_bytes must be positive")
    matches = list(_FENCE.finditer(raw_text))
    if matches:
        normalized_expected = expected_language.casefold().lstrip(".")
        matching = [
            match
            for match in matches
            if match.group("label").strip().casefold().lstrip(".") == normalized_expected
        ]
        selected_matches = matching or matches
        if len(selected_matches) != 1:
            raise EvaluationError("model response contains multiple ambiguous source blocks")
        selected = selected_matches[0]
        source = selected.group("body").strip()
        label = selected.group("label").strip() or None
        used_fence = True
    else:
        source = raw_text.strip()
        label = None
        used_fence = False

    if not source:
        raise EvaluationError("model response does not contain source code")
    if len(source.encode("utf-8")) > maximum_bytes:
        raise EvaluationError("candidate source exceeds the configured size limit")
    return ExtractedSource(source=source, used_fence=used_fence, fence_label=label)
