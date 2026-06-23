from __future__ import annotations

from .filters import Filter
from .models import RejectedToken, SelectionResult, WalletTokenContext


class TokenSelector:
    def __init__(self, filters: list[Filter]) -> None:
        self._filters = filters

    def select(self, tokens: list[WalletTokenContext]) -> SelectionResult:
        selected: list[WalletTokenContext] = []
        rejected: list[RejectedToken] = []

        for token in tokens:
            for f in self._filters:
                decision = f(token)
                if not decision.keep:
                    rejected.append(
                        RejectedToken(
                            token=token,
                            reason=decision.reason or type(f).__name__,
                        )
                    )
                    break
            else:
                selected.append(token)

        return SelectionResult(selected=selected, rejected=rejected)
