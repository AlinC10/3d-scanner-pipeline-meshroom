# docker run --gpus all -it -v "D:\Docker_Meshroom:/runpod-volume" meshroom_pipeline

FROM nvidia/cuda:12.9.2-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y python3 python3-venv

WORKDIR /app
COPY . .

RUN python3 -m venv /app/.venv
RUN /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install -r requirements.txt

CMD ["/app/.venv/bin/python", "main.py"]