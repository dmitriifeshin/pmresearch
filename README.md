# pmresearch

Polymarket token analytics — строит market universe для адреса кошелька.

## Установка

```bash
pip install -e ".[dev]"       # тесты
pip install -e ".[dev,plot]"  # тесты + matplotlib для графиков
```

## Пример (Jupyter notebook)

```python
import clickhouse_connect
from pmresearch.repositories import (
    WalletTokenStatsRepository,
    TokenMarketStatsRepository,
    TokenMetadataRepository,
)
from pmresearch.builder import WalletTokenContextBuilder, WalletMarketUniverseBuilder
from pmresearch.filters import (
    ExcludeTagsFilter,
    ActiveMarketFilter,
    MinWalletTradesFilter,
    MinMarketTradesFilter,
    BinaryOutcomeFilter,
)
from pmresearch.selector import TokenSelector
from pmresearch.resolver import OutcomePairResolver

# 1. Клиент ClickHouse
client = clickhouse_connect.get_client(
    host="localhost", port=8123, username="default", password=""
)

# 2. Репозитории
wallet_stats_repo  = WalletTokenStatsRepository(client)
market_stats_repo  = TokenMarketStatsRepository(client)
metadata_repo      = TokenMetadataRepository(client)

# 3. Фильтры и селектор
selector = TokenSelector([
    ExcludeTagsFilter({"Crypto", "Sports"}),
    ActiveMarketFilter(),           # end_ts > now
    MinWalletTradesFilter(5),       # минимум сделок у конкретного адреса
    MinMarketTradesFilter(20),      # минимум сделок по рынку вообще
    BinaryOutcomeFilter(),          # только Yes/No рынки
])

# 4. Builder контекстов и резолвер пар
context_builder = WalletTokenContextBuilder()
resolver = OutcomePairResolver(client)

# 5. Главный builder
builder = WalletMarketUniverseBuilder(
    wallet_stats_repo=wallet_stats_repo,
    market_stats_repo=market_stats_repo,
    metadata_repo=metadata_repo,
    context_builder=context_builder,
    selector=selector,
    resolver=resolver,
)

# 6. Запуск
ADDRESS = "0x9D84CE0306F8551E02EFEF1680475FC0F1DC1344"
result = builder.build(ADDRESS)

print(f"Wallet stats    : {result.wallet_stats_count}")
print(f"Market stats    : {result.market_stats_count}")
print(f"Metadata        : {result.metadata_count}")
print(f"Contexts        : {result.contexts_count}")
print(f"Selected        : {result.selected_count}")
print(f"Rejected        : {result.rejected_count}")
print(f"Yes/No pairs    : {len(result.pairs)}")
print(f"Reject reasons  : {result.selection.stats}")

# Пары
for pair in result.pairs[:5]:
    print(pair.question, "→ traded:", pair.wallet_traded_outcome)
```

## Архитектура пайплайна

```
address
  ↓
WalletTokenStatsRepository.get_stats()    — trades_bq WHERE address=?  → list[WalletTokenStats]
  ↓
TokenMarketStatsRepository.get_stats()    — trades_bq JOIN input_tokens → list[TokenMarketStats]
  ↓
TokenMetadataRepository.get_metadata()    — tokens    JOIN input_tokens → list[TokenMetadata]
  ↓
WalletTokenContextBuilder.build()         — склейка по token_id         → list[WalletTokenContext]
  ↓
TokenSelector.select()                    — фильтры                     → SelectionResult
  ↓
OutcomePairResolver.resolve_pairs()       — tokens JOIN input_conditions → list[TokenPair]
```

### Модели

| Модель | Описание |
|---|---|
| `WalletTokenStats` | Статистика конкретного адреса по token_id (trades_count, volume, buy/sell) |
| `TokenMarketStats` | Глобальная статистика token_id по всем адресам (last_price, unique_traders) |
| `TokenMetadata` | Справочная информация: question, outcome, condition_id, end_ts, tags |
| `WalletTokenContext` | Итоговый контекст: wallet_stats + market_stats + metadata (последние два могут быть None) |
| `SelectionResult` | selected + rejected с методом `.stats` (counts by reason) |
| `TokenPair` | Yes/No пара токенов с привязкой к тому, что торговал кошелёк |

### ClickHouse external data

Репозитории `TokenMarketStatsRepository` и `TokenMetadataRepository` передают список token_id
через temporary table `input_tokens` (ExternalData), а не через `IN (...)`. Это позволяет
избежать огромных SQL-строк при большом числе токенов.

## Tag-level overview

Анализ поведения адреса по тегам поверх результата основного пайплайна.

```python
from pmresearch.tag_analysis import TagMetricsBuilder, TagMetricsPlotter

# result — WalletMarketUniverseResult от builder.build(address)
tag_result = TagMetricsBuilder().build_from_universe_result(
    result,
    tags=["Politics", "Sports", "Crypto"],
)

# summary по тегам
tag_result.summary_table()
# [{"tag": "Politics", "tokens_count": 12, "total_usd_buy_volume": 340.5,
#   "mean_roi": nan, "median_roi": nan, "winrate": nan}, ...]

# per-tag графики
plotter = TagMetricsPlotter(tag_result)

fig = plotter.plot_usd_buy_volume_distribution("Politics")
fig = plotter.plot_time_to_end_distribution("Politics")
fig = plotter.plot_market_popularity_distribution("Politics", kind="unique_traders_count")
fig = plotter.plot_pnl_vs_buy_volume("Politics")    # Y-ось nan до реализации PnL

# cross-tag overview
fig = plotter.plot_tokens_count_by_tag()
fig = plotter.plot_total_buy_volume_by_tag()
fig = plotter.plot_median_roi_by_tag()

# все 6 графиков для одного тега
figs = plotter.plot_all_for_tag("Politics")
```

### Статус метрик

| Метрика | Источник | Статус |
|---|---|---|
| `usd_buy_volume` | `wallet_stats.wallet_buy_usd_volume` | ✓ готово |
| `time_to_end_at_entry_hours` | `metadata.end_ts - wallet_first_trade_ts` | ✓ готово |
| `market_trades_count` | `market_stats.market_trades_count` | ✓ готово |
| `market_volume` | `market_stats.market_volume` | ✓ готово |
| `unique_traders_count` | `market_stats.unique_traders_count` | ✓ готово |
| `pnl` | — | TODO: нужно подтвердить единицы `wallet_sell_token_volume` |
| `roi` | `pnl / usd_buy_volume` | TODO: зависит от PnL |
| `avg_buy_price` | — | TODO: нужно подтвердить единицы `last_price` |

## Тесты

```bash
pytest
```

Тесты не требуют подключения к ClickHouse:
- `WalletTokenContextBuilder` и фильтры — чистые функции
- `build_pairs` — чистая функция
- репозитории тестируются через capturing mock client
- `TagMetricsBuilder` и `TagMetricsPlotter` — тестируются без ClickHouse
