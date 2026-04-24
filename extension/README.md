# TETR Scout Chrome Extension

這是一個保守版的 `TETR.IO` Chrome extension MVP。

它現在比較像工具型懸浮球，而不是固定右側大面板：

- 預設只顯示一顆可拖曳的浮動球
- 點球後從側邊彈出面板
- 讓你點選候選玩家，或手動輸入 username
- 透過官方 `TETRA CHANNEL API` 顯示公開 `TETRA LEAGUE` 摘要
- 顯示近期勝率、TR 趨勢、最近幾場對戰與基本韌性指標
- 預設 `compact`，只顯示關鍵資訊
- `More` 才展開圖表與較長內容
- active match 場景會自動收回，避免擋住遊戲資訊

## 安裝

1. 打開 `chrome://extensions`
2. 啟用右上角 `Developer mode`
3. 選 `Load unpacked`
4. 選這個資料夾：`extension/`

## 這版做什麼

- 使用 `background service worker` 呼叫官方 `https://ch.tetr.io/api/`
- 使用 `content script` 在 `tetr.io` 插入可拖曳懸浮球與彈出面板
- 自動掃描頁面可見文字，列出可能的玩家名稱
- 另外透過 `page-bridge.js` 從頁面自己的 `fetch / WebSocket` 與 canvas text hook 補強候選名稱
- 點一下候選名稱就會抓資料
- 點空白處或按 `Esc` 就能收回面板
- 懸浮球位置會記住

## 這版不做什麼

- 不直接讀遊戲私有狀態
- 不在內容上做「打哪裡比較好」這種對戰建議
- 不保證每個畫面都能 100% 自動辨識正確對手

## 已知限制

- TETR.IO 介面大量使用 canvas / 動態渲染，玩家名稱不一定總在 DOM 裡
- 雖然現在有 `DOM + network + canvas text` 三層候選來源，仍然可能誤判或漏抓
- active match 場景為了不擋畫面，面板會自動收回；需要時要再點球展開
- 這版比較適合用在大廳、玩家頁、配對前後、觀戰與一般瀏覽場景

## 合規提醒

這個擴充套件只用官方公開 API 與頁面可見文字，不碰未公開端點。

但是否適合在排位進行中使用，仍然要以 TETR.IO 官方規則與官方解釋為準。若你擔心競技公平或風險，建議只在非對戰中場景使用。
