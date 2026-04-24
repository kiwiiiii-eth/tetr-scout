# TETR Scout

Floating TETR.IO scouting overlay and public league analyzer powered by the official `TETRA CHANNEL API`.

TETR Scout 是一個給 `TETR.IO` 用的公開資料工具組，現在包含兩塊：

- `CLI / HTML analyzer`
  用官方 `TETRA CHANNEL API` 分析單一玩家的 `TETRA LEAGUE` 戰績、近期狀態與低潮代理指標
- `Floating Chrome overlay`
  在 `tetr.io` 頁面上用懸浮球顯示公開玩家摘要、近期走勢與基本韌性資訊

整個專案只使用官方公開的 `https://ch.tetr.io/api/`，目標是做出「公開資料 scouting + 賽後分析」這類工具，而不是未公開協議或私有資料抓取。

English summary: TETR Scout combines a floating Chrome overlay with CLI / HTML analysis tools to surface public player stats, recent form, trend signals, and match resilience for TETR.IO players.

## 功能概覽

### CLI / HTML analyzer

- 支援 `中文 / English / 中英並列` 輸出
- 目前牌位、TR、Glicko、GXE
- 近 10 / 20 / 50 場勝率
- 目前連勝/連敗、最佳連勝/連敗
- 近況 form 字串
- 歷史 TR 變化
- 常玩時段與星期
- `tilt / slump` 代理指標
  - 連敗後下一場與接下來 3 場的勝率
  - 輸掉後快速重排 vs 冷卻後再排的恢復率
  - 長 session 前半段 vs 後半段勝率
  - 輸給低自己很多 TR 的對手後，恢復能力如何
- 最近對戰韌性
  - 輸掉第 1 局後的整場勝率
  - `0:2` 落後時的翻盤率
  - `2:3` 惜敗後下一場的恢復率
- 可輸出完整 HTML 圖表報表

### Floating Chrome overlay

- 可拖曳、可記住位置的懸浮球
- 點球後從側邊彈出 compact 面板
- `More` 才展開較長內容
- active match 場景會自動收回，避免遮住對戰資訊
- 會依瀏覽器語言自動顯示繁中或英文 UI
- 候選玩家名會綜合 `DOM`、頁面自己的 `fetch / WebSocket` 線索，以及 canvas text hook
- 透過官方 `TETRA CHANNEL API` 顯示公開 `TETRA LEAGUE` 摘要

## CLI 使用方式

```bash
python3 analyze_tetr.py <username>
```

例如：

```bash
python3 analyze_tetr.py osk --recent 30 --timezone Asia/Taipei
```

預設輸出語言是中文；如果你想切成英文或中英並列：

```bash
python3 analyze_tetr.py osk --lang en
python3 analyze_tetr.py osk --lang both
```

如果你想把 `leagueflow` 匯出成 CSV：

```bash
python3 analyze_tetr.py osk --csv output/osk_leagueflow.csv
```

如果你不想抓最近的逐場 `league records`：

```bash
python3 analyze_tetr.py osk --records-limit 0
```

如果你想抓完整可分頁歷史：

```bash
python3 analyze_tetr.py osk --records-limit all
```

如果你想直接輸出圖表版 HTML 報表：

```bash
python3 analyze_tetr.py osk --records-limit all --html-report
```

也可以自訂輸出路徑：

```bash
python3 analyze_tetr.py osk --records-limit all --html-report output/osk_full_report.html
```

## 資料來源與設計原則

這支程式只用官方文件裡有明確定義的端點：

- `/users/:user`
- `/users/:user/summaries/league`
- `/labs/leagueflow/:user`
- `/labs/league_ranks`
- `/users/:user/records/league/recent`

這樣比直接依賴未公開欄位安全，API 變動時也比較不容易壞。

## Chrome Extension

如果你想在 `tetr.io` 頁面上直接看公開玩家資料，repo 內也有 Chrome extension：

- [extension/manifest.json](extension/manifest.json)
- [extension/background.js](extension/background.js)
- [extension/content.js](extension/content.js)
- [extension/page-bridge.js](extension/page-bridge.js)
- [extension/README.md](extension/README.md)

目前這版定位是保守版公開資料 overlay，比較適合在大廳、玩家頁、配對前後、觀戰與一般瀏覽場景使用。

## Support

如果 `TETR Scout` 對你有幫助，想請我喝杯咖啡，可以用 Base：

`0x942B3968c0778DD3dDE5Ae3C81DE845744Bf0be9`

## Roadmap

- 對手強度更細分桶，例如「高自己 400 TR / 低自己 400 TR」
- 視覺化圖表，直接畫 TR 曲線與低潮區段
- 搭配自填心情或疲勞紀錄，讓「情緒」分析不只停在行為代理

## 注意

- 請使用 `https://ch.tetr.io/api/` 這組官方 `TETRA CHANNEL API`。
- 官方文件明確說明：`https://tetr.io/api/` 主遊戲 API 不可未經書面授權直接使用。
- API 有快取規則，頻繁抓同一組資料時應帶 `X-Session-ID`，並尊重 `cached_until`。

官方文件：

- https://tetr.io/about/api/
