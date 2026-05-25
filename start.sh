#!/bin/bash
# 报销材料管理系统 - 启动脚本
# 用法: ./start.sh [port]
# 默认端口: 1444

PORT=${1:-1444}
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/app.pid"
LOG_FILE="$PROJECT_DIR/app.log"

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "错误: 应用已在运行 (PID: $OLD_PID)"
        echo "如需重启请先运行: ./stop.sh"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

cd "$PROJECT_DIR" || exit 1

# 检查依赖
echo "检查依赖..."
pip3 install -r requirements.txt -q 2>&1 | tail -1

# 启动应用（后台运行）
echo "启动应用 (端口: $PORT)..."
nohup python3 app.py > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

# 等待启动完成
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo "应用已启动 (PID: $PID)"
    echo "访问地址: http://localhost:$PORT"
    echo "日志文件: $LOG_FILE"
else
    echo "启动失败，请检查日志: $LOG_FILE"
    cat "$LOG_FILE"
    exit 1
fi
