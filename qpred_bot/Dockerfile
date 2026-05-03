FROM python:3.11-slim

WORKDIR /app

# 国内镜像可加速 (按需开启)
# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建数据 / 日志目录
RUN mkdir -p /app/data /app/logs

# 时区
ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
