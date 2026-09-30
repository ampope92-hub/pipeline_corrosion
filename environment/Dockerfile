# The cell's own toolchain is Fortran, so the agent's project is compiled with gfortran.
# Canonical Python base: the harness runs on it, and nothing here needs a Python numerics stack.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# gfortran is the whole toolchain: the model is written against the intrinsics, with no
# external library, so nothing has to be fetched at solve time on an offline box.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gfortran \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

# The project the agent completes, and the inspection export.
COPY predictor /app/predictor
COPY data /app/data
RUN chmod +x /app/predictor/build.sh && mkdir -p /app/out

WORKDIR /app
