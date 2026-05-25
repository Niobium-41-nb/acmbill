#!/bin/bash
# 报销材料管理系统 - 停止脚本
# 用法: ./stop.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "未找到 PID 文件，尝试通过进程名停止..."
    PID=$(pgrep -f "python3 app.py" 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "停止应用 (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 1
        # 强制终止
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
            echo "已强制终止应用"
        else
            echo "应用已停止"
        fi
    else
        echo "应用未在运行"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")
if [ -z "$PID" ]; then
    echo "PID 文件为空"
    rm -f "$PID_FILE"
    exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
    echo "应用未在运行 (PID: $PID)"
    rm -f "$PID_FILE"
    exit 0
fi

echo "停止应用 (PID: $PID)..."
kill "$PID" 2>/dev/null
sleep 1

# 检查是否成功停止
if kill -0 "$PID" 2>/dev/null; then
    echo "等待进程结束..."
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "强制终止应用..."
        kill -9 "$PID" 2>/dev/null
    fi
fi

rm -f "$PID_FILE"
echo "应用已停止"
