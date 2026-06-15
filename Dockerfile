FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（PyMuPDF、Pillow 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn==22.0.0

# 复制应用代码
COPY . .

# 确保上传目录存在（运行时会被 volume 覆盖）
RUN mkdir -p uploads

# 非 root 用户运行（提高安全性）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 1444

# 使用 Gunicorn 启动（4 workers，支持高并发）
CMD ["gunicorn", "--bind", "0.0.0.0:1444", "--workers", "4", "--timeout", "120", "app:create_app()"]
