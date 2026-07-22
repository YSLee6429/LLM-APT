import pytest

from llmapt.application.reducer import TokenDeltaReducer


@pytest.mark.asyncio
async def test_token_delta_reducer_removes_irrelevant_tokens() -> None:
    async def fails(value: bytes) -> bool:
        return b"trigger" in value.split()

    result = await TokenDeltaReducer().reduce(b"noise trigger extra\n", fails)

    assert result.minimized_input == b"trigger"
    assert result.attempts >= 2


@pytest.mark.asyncio
async def test_token_delta_reducer_preserves_empty_input() -> None:
    async def never(_value: bytes) -> bool:
        return False

    result = await TokenDeltaReducer().reduce(b"\n\t", never)

    assert result.minimized_input == b"\n\t"
    assert result.attempts == 0
