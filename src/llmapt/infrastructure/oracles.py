"""Built-in trusted oracles shipped and versioned with the control plane."""

from llmapt.application.oracle_registry import OracleRegistry, RegisteredOracle
from llmapt.domain.digests import digest_text
from llmapt.domain.oracles import OracleIdentity

DOUBLE_STATEMENT = "Read one integer n and print 2 * n."


def _double_integer(standard_input: bytes) -> bytes:
    tokens = standard_input.decode("utf-8").split()
    if len(tokens) != 1:
        raise ValueError("oracle_input_rejected")
    value = int(tokens[0])
    return f"{value * 2}\n".encode()


def build_oracle_registry() -> OracleRegistry:
    return OracleRegistry(
        (
            RegisteredOracle(
                identity=OracleIdentity(
                    key="builtin.double",
                    version="1",
                    parent_problem_id="double",
                    parent_statement_digest=digest_text(DOUBLE_STATEMENT),
                    language="cpp",
                ),
                evaluate=_double_integer,
            ),
        )
    )
