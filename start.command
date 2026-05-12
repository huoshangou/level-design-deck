#!/bin/bash
# level-design-deck 一键启动脚本（macOS / Linux）
#
# 用法：
#   - macOS：Finder 双击此文件
#   - 终端：./start.command 或 bash start.command
#
# 功能：
#   1. cd 到脚本所在目录（避免双击时 cwd 是 $HOME）
#   2. 检查 python3 可用
#   3. 检查端口未占用（如占用先 kill 旧 server）
#   4. 后台启动 serve_editor.py
#   5. 等服务起来后自动打开浏览器到 editor

set -e
PORT=8766
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 未安装。请先装 Python 3.x"
  echo "按任意键退出..."; read -n 1
  exit 1
fi

# kill 旧 server（如端口占用）
OLD_PID=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
  echo "⚠️  端口 $PORT 被进程 $OLD_PID 占用，先 kill ..."
  kill $OLD_PID 2>/dev/null || true
  sleep 1
fi

echo "🚀 启动 level-design-deck server (port $PORT) ..."
nohup python3 tools/serve_editor.py --port $PORT > /tmp/level-design-deck-server.log 2>&1 &
SERVER_PID=$!
echo "   PID = $SERVER_PID  / 日志 = /tmp/level-design-deck-server.log"

# 等服务就绪（最多 5 秒）
for i in 1 2 3 4 5; do
  sleep 1
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/api/specs"; then
    echo "✅ Server 已就绪"
    break
  fi
done

URL="http://127.0.0.1:$PORT/editor/editor.html"
echo "🌐 打开浏览器: $URL"
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
else
  echo "   请手动在浏览器打开: $URL"
fi

echo ""
echo "─────────────────────────────────────────"
echo "deck 在后台运行（PID=$SERVER_PID）。"
echo "停止：在终端跑  kill $SERVER_PID"
echo "或：  lsof -ti:$PORT | xargs kill"
echo "─────────────────────────────────────────"
echo ""
echo "（此窗口可关闭，server 仍会运行）"
