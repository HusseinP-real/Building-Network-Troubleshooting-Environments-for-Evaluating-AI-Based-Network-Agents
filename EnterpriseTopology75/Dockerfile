FROM kathara/frr:latest
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends keepalived dnsmasq-base dnsutils && rm -rf /var/lib/apt/lists/*
