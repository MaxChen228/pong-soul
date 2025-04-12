# 🕹️ Pong Soul - 復古風格 AI 街機乒乓對戰

> **一款融合復古街機美學與 AI 對戰的乒乓遊戲。**  
> 與訓練好的 AI 關主正面對決，每一關都是一次挑戰。

---

## 🎮 遊戲特色

- 🧠 與強化學習訓練出來的 AI 模型對戰（使用 `.pth`）
- 🕹️ 街機復古風畫面：像素比例、掃描線特效、像素字體
- ⏱️ 開場倒數動畫（3...2...1... START）
- 🟥 玩家與 AI 擁有生命值（血條），失誤只扣血、不重開
- 🎯 通關條件清晰，勝利/失敗後有動畫彈幕
- 📜 關卡設定可自定（YAML 格式設定速度、角度、旋轉等）

---

## 📦 安裝方式

```bash
git clone https://github.com/MaxChen228/pong-soul.git
cd pong-soul
python -m venv venv
source venv/bin/activate  # Windows 用 .\venv\Scripts\activate
pip install -r requirements.txt
python game/main.py
