#!/bin/bash
# level-design-deck webapp 一键启动（后端 + 前端）
#
# 双击启动，自动处理端口冲突，打开浏览器

set -e
WEBAPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WEBAPP_DIR"

BACKEND_PORT=8766
FRONTEND_PORT=5173

# -- 杀旧进程 --
for p in $BACKEND_PORT $FRONTEND_PORT; do
  if lsof -ti:$p >/dev/null 2>&1; then
    echo "🔧 释放端口 $p ..."
    lsof -ti:$p | xargs kill 2>/dev/null || true
    sleep 0.5
  fi
done

# -- 启动后端 --
if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "❌ 缺 .venv/bin/uvicorn"
  echo "   cd $WEBAPP_DIR && python3 -m venv .venv && .venv/bin/pip install --no-index --find-links wheels/ fastapi 'uvicorn[standard]' pydantic python-multipart watchfiles"
  read -n 1; exit 1
fi

echo "🚀 启动后端 (port $BACKEND_PORT) ..."
nohup .venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port $BACKEND_PORT \
  > /tmp/level-design-deck-webapp.log 2>&1 &
BACKEND_PID=$!

for i in 1 2 3 4 5; do
  sleep 1
  if curl -sf -o /dev/null "http://127.0.0.1:$BACKEND_PORT/api/health"; then
    echo "✅ 后端就绪 (PID=$BACKEND_PID)"
    break
  fi
done

# -- 启动前端 --
FRONTEND_DIR="$WEBAPP_DIR/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "❌ 前端依赖未安装，请先: cd $FRONTEND_DIR && npm install"
  read -n 1; exit 1
fi

echo "🚀 启动前端 (port $FRONTEND_PORT) ..."
nohup bash -c "cd '$FRONTEND_DIR' && npx vite --host 127.0.0.1 --port $FRONTEND_PORT --strictPort" \
  > /tmp/level-design-deck-frontend.log 2>&1 &
FRONTEND_PID=$!

for i in 1 2 3 4 5; do
  sleep 1
  if curl -sf -o /dev/null "http://127.0.0.1:$FRONTEND_PORT"; then
    echo "✅ 前端就绪 (PID=$FRONTEND_PID)"
    break
  fi
done

# -- 打开浏览器 --
URL="http://localhost:$FRONTEND_PORT"
echo "🌐 打开 $URL"
if command -v open >/dev/null 2>&1; then
  open "$URL"
fi

echo ""
echo "─────────────────────────────────────────"
echo "后端: http://127.0.0.1:$BACKEND_PORT (PID=$BACKEND_PID)"
echo "前端: $URL (PID=$FRONTEND_PID)"
echo "日志: /tmp/level-design-deck-webapp.log"
echo "      /tmp/level-design-deck-frontend.log"
echo "停止: kill $BACKEND_PID $FRONTEND_PID"
echo "─────────────────────────────────────────"
