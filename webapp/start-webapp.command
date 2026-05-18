#!/bin/bash
# level-design-deck webapp 启动脚本（M4 / B 阶段）
#
# 与根目录 ../start.command（老 serve_editor.py）并存，端口不同：
#   ../start.command     → :8766 跑老 editor.html
#   ./start-webapp.command → :8766 跑新 FastAPI（如老的已停）/ 8767 兜底
#
# 用法：
#   - macOS：Finder 双击此文件
#   - 终端：./start-webapp.command 或 bash start-webapp.command

set -e
WEBAPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WEBAPP_DIR"

PRIMARY_PORT=8766
FALLBACK_PORT=8767

if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "❌ 缺 .venv/bin/uvicorn。请先建 venv 并装依赖："
  echo "   cd $WEBAPP_DIR"
  echo "   python3 -m venv .venv"
  echo "   .venv/bin/pip install --no-index --find-links wheels/ fastapi 'uvicorn[standard]' pydantic python-multipart watchfiles"
  echo "按任意键退出..."; read -n 1
  exit 1
fi

# 选端口：优先 8766，被占就 8767
PORT=$PRIMARY_PORT
if lsof -ti:$PORT >/dev/null 2>&1; then
  echo "⚠️  端口 $PRIMARY_PORT 被占用（可能老 serve_editor.py 在跑），改用 $FALLBACK_PORT"
  PORT=$FALLBACK_PORT
  if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "❌ 端口 $FALLBACK_PORT 也被占。手动 kill 旧进程后再试：lsof -ti:$PRIMARY_PORT,$FALLBACK_PORT | xargs kill"
    read -n 1; exit 1
  fi
fi

echo "🚀 启动 webapp (port $PORT) ..."
nohup .venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port $PORT \
  > /tmp/level-design-deck-webapp.log 2>&1 &
SERVER_PID=$!
echo "   PID=$SERVER_PID  日志=/tmp/level-design-deck-webapp.log"

for i in 1 2 3 4 5; do
  sleep 1
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/api/health"; then
    echo "✅ Server 已就绪"
    break
  fi
done

URL="http://127.0.0.1:$PORT/api/health"
echo "🌐 健康检查: $URL"
if command -v open >/dev/null 2>&1; then
  open "$URL"
fi

echo ""
echo "─────────────────────────────────────────"
echo "webapp 在后台运行（PID=$SERVER_PID, port=$PORT）"
echo "前端 dev：cd frontend && pnpm dev → http://localhost:5173"
echo "老 editor：http://127.0.0.1:$PORT/legacy/editor.html"
echo "停止：kill $SERVER_PID  或  lsof -ti:$PORT | xargs kill"
echo "─────────────────────────────────────────"
