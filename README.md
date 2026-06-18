# pmresearch

Polymarket token analytics — строит market universe для адреса кошелька.

## Установка

```bash
pip install -e ".[dev]"
```

## Пример (Jupyter notebook)

```python
import clickhouse_connect
from pmresearch.repositories import WalletTradedTokenRepository, TokenMetadataRepository
from pmresearch.filters import ExcludeTagsFilter, ActiveMarketFilter, MinTradesFilter, BinaryOutcomeFilter
from pmresearch.selector import TokenSelector
from pmresearch.resolver import OutcomePairResolver
from pmresearch.builder import WalletMarketUniverseBuilder

# 1. Клиент ClickHouse (или ClickHouseGateway из db.py)
client = clickhouse_connect.get_client(
    host="localhost", port=8123, username="default", password=""
)

# 2. Репозитории
wallet_repo   = WalletTradedTokenRepository(client)
metadata_repo = TokenMetadataRepository(client)

# 3. Фильтры и селектор
selector = TokenSelector([
    ExcludeTagsFilter({"Crypto", "Sports"}),
    ActiveMarketFilter(),          # end_ts > now
    MinTradesFilter(5),
    BinaryOutcomeFilter(),         # только Yes/No рынки
])

# 4. Резолвер пар
resolver = OutcomePairResolver(client)

# 5. Builder
builder = WalletMarketUniverseBuilder(wallet_repo, metadata_repo, selector, resolver)

# 6. Запуск
ADDRESS = "0x9D84CE0306F8551E02EFEF1680475FC0F1DC1344"
result = builder.build(ADDRESS)

print(f"Traded tokens   : {result.traded_count}")
print(f"Enriched        : {result.enriched_count}")
print(f"Selected        : {result.selected_count}")
print(f"Rejected        : {result.rejected_count}")
print(f"Yes/No pairs    : {len(result.pairs)}")
print(f"Reject reasons  : {result.selection.stats}")

# Пары
for pair in result.pairs[:5]:
    print(pair.question, "→ traded:", pair.wallet_traded_outcome)
```

## Архитектура

```
WalletTradedTokenRepository  — trades_bq → list[TradedTokenStats]
TokenMetadataRepository      — tokens    → list[EnrichedTradedToken]  (batch)
TokenSelector                — фильтры   → SelectionResult
OutcomePairResolver          — tokens    → list[TokenPair]            (batch)
WalletMarketUniverseBuilder  — связывает всё вместе
```

## Тесты

```bash
pytest
```

Тесты не требуют подключения к ClickHouse: `build_pairs` и фильтры — чистые функции.
