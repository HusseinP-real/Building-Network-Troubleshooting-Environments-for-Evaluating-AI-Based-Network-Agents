FROM kathara/frr:latest
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 curl iproute2 iputils-ping procps && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.title="SOFT3888 eBGP data centre fabric" org.opencontainers.image.version="1"
