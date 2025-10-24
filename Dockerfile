# 使用 Python 3.10 slim 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 拷贝项目文件到镜像
COPY . /app

# 设置环境变量：matiec 可执行文件路径
ENV PATH="/app/emulator/matiec:${PATH}"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    bison \
    flex \
    git \
    automake \
    autoconf \
    libtool \
    && rm -rf /var/lib/apt/lists/*

# 编译 Linux 版本 matiec
RUN cd /app/emulator/matiec && \
    autoreconf -i && \
    ./configure && \
    make

# 升级 pip 并安装 Python 依赖
RUN pip install --upgrade pip
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# 暴露端口（根据项目需要）
EXPOSE 5000 5555 8765

# 并行启动两个 Python 程序
CMD ["bash", "-c", "python emulator/editor/xml_uploader.py & python emulator/editor/Laucher.py Blink Blink & wait"]
