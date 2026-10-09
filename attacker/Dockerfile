FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       nmap \
       hydra \
       openssh-client \
       sshpass \
       ca-certificates \
       bash \
       coreutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /scenarios

COPY scenarios/ /scenarios/

CMD ["sleep", "infinity"]
