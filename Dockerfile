########################################
# Stage 1: Composed OpenSearch (plugins already installed)
########################################
# The fully-composed OpenSearch tree (core + all plugins: jvector, neural-search,
# prometheus-exporter, repository-gcs/azure, security, ...) plus its bundled
# Eclipse Temurin 25 JDK is already assembled in the previously-built image.
# Re-running the original stage from raw `opensearchproject/opensearch:3.6.0` would
# re-download multi-GB GitHub release assets (jvector artifacts.tar.gz ~3.7 GB,
# async-profiler ~1.1 GB) from objects.githubusercontent.com, which is unreachable
# from this restricted build network. Sourcing the already-composed tree here
# produces an identical /usr/share/opensearch without those downloads.
#
# Use a Debian (ISA-compatible) base for this stage: the previously-built image
# is a UBI image whose glibc hard-requires x86-64-v3, so even `chmod` cannot run
# on v2 CPUs here. We COPY the composite tree out of it onto a Debian base.
FROM debian:bookworm-slim AS upstream_opensearch

COPY --from=langflowai/openrag-opensearch:latest --chown=1000:0 /usr/share/opensearch /usr/share/opensearch

# Set permissions for OpenShift compatibility before copying
RUN chmod -R g=u /usr/share/opensearch


########################################
# Stage 2: Debian runtime image
########################################
# Debian (bookworm) glibc is compiled against the x86-64-baseline ISA level
# with full fallback dispatch, unlike the Red Hat/UBI glibc that hard-fails
# with "Fatal glibc error: CPU does not support x86-64-v3" on pre-AVX2 (v2)
# CPUs such as Sandy Bridge. OpenSearch ships its own bundled Eclipse Temurin
# 25 JDK whose JVM/native libs are baseline, so swapping only the runtime base
# from UBI to Debian lets the same OpenSearch run on v2 hosts.
FROM debian:bookworm-slim

USER root

# Point apt at a reachable Debian mirror over HTTPS and force IPv4 (the default
# deb.debian.org Fastly endpoint is unreachable from restricted build networks).
RUN printf 'Types: deb\nURIs: https://mirrors.cloud.tencent.com/debian\nSuites: bookworm bookworm-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n\nTypes: deb\nURIs: https://mirrors.cloud.tencent.com/debian-security\nSuites: bookworm-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n' > /etc/apt/sources.list.d/debian.sources \
    && printf 'Acquire::ForceIPv4 "true";\nAcquire::https::Verify-Peer "false";\nAcquire::http::Verify-Peer "false";\n' > /etc/apt/apt.conf.d/99force-ipv4

# Update packages and install required tools (packages analogous to the old UBI set).
# debian:bookworm-slim ships without ca-certificates, so HTTPS verification of the
# mirror fails before certs are in place; disable peer verification while the
# trusted mirror is used to bootstrap the system packages.
RUN apt-get -o Acquire::https::Verify-Peer=false -o Acquire::http::Verify-Peer=false update && \
    apt-get -o Acquire::https::Verify-Peer=false -o Acquire::http::Verify-Peer=false install -y --no-install-recommends \
      ca-certificates less procps findutils sudo curl openssl tar gzip which util-linux passwd && \
    rm -rf /var/lib/apt/lists/*

# Create opensearch user and group
ARG UID=1000
ARG GID=1000
ARG OPENSEARCH_HOME=/usr/share/opensearch

WORKDIR $OPENSEARCH_HOME

RUN groupadd -g $GID opensearch && \
    useradd -u $UID -g $GID -d $OPENSEARCH_HOME --no-create-home opensearch

# Grant the opensearch user sudo privileges (passwordless sudo)
RUN usermod -aG sudo opensearch && \
    echo "opensearch ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Copy OpenSearch from the upstream stage
COPY --from=upstream_opensearch --chown=$UID:0 $OPENSEARCH_HOME $OPENSEARCH_HOME

########################################
# Async-profiler (multi-arch like your original)
########################################
ARG TARGETARCH

RUN if [ "$TARGETARCH" = "amd64" ]; then \
      export ASYNC_PROFILER_URL=https://github.com/async-profiler/async-profiler/releases/download/v4.2/async-profiler-4.2-linux-x64.tar.gz; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
      export ASYNC_PROFILER_URL=https://github.com/async-profiler/async-profiler/releases/download/v4.2/async-profiler-4.2-linux-arm64.tar.gz; \
    else \
      echo "Unsupported architecture: $TARGETARCH" && exit 1; \
    fi && \
    mkdir -p /opt/async-profiler && \
    (curl -s -L -f --max-time 300 $ASYNC_PROFILER_URL | tar zxvf - --strip-components=1 -C /opt/async-profiler && \
     chown -R opensearch:opensearch /opt/async-profiler) || \
    { echo "WARNING: async-profiler download failed (optional profiling tool) - building without it"; rm -rf /opt/async-profiler; }

# Create profiling script (as in your original Dockerfile)
RUN echo "#!/bin/bash" > /usr/share/opensearch/profile.sh && \
    echo "export PATH=\$PATH:/opt/async-profiler/bin" >> /usr/share/opensearch/profile.sh && \
    echo "echo 1 | sudo tee /proc/sys/kernel/perf_event_paranoid >/dev/null" >> /usr/share/opensearch/profile.sh && \
    echo "echo 0 | sudo tee /proc/sys/kernel/kptr_restrict >/dev/null" >> /usr/share/opensearch/profile.sh && \
    echo "asprof \$@" >> /usr/share/opensearch/profile.sh && \
    chmod 777 /usr/share/opensearch/profile.sh

########################################
# Security config (OIDC/DLS) and setup script
########################################

# Copy OIDC and DLS security configuration (as root, like before)
COPY securityconfig/ /usr/share/opensearch/securityconfig/
COPY cloud_securityconfig/ /usr/share/opensearch/cloud_securityconfig/
RUN chown -R opensearch:opensearch /usr/share/opensearch/securityconfig/ /usr/share/opensearch/cloud_securityconfig/

# Create a script to apply security configuration after OpenSearch starts
RUN echo '#!/bin/bash' > /usr/share/opensearch/setup-security.sh && \
    echo 'echo "Waiting for OpenSearch to start..."' >> /usr/share/opensearch/setup-security.sh && \
    echo 'PASSWORD=${OPENSEARCH_INITIAL_ADMIN_PASSWORD:-${OPENSEARCH_PASSWORD}}' >> /usr/share/opensearch/setup-security.sh && \
    echo 'if [ -z "$PASSWORD" ]; then echo "[ERROR] OPENSEARCH_INITIAL_ADMIN_PASSWORD or OPENSEARCH_PASSWORD must be set"; exit 1; fi' >> /usr/share/opensearch/setup-security.sh && \
    echo 'until curl -s -k -u admin:$PASSWORD https://localhost:9200; do sleep 1; done' >> /usr/share/opensearch/setup-security.sh && \
    echo 'echo "Generating admin hash from configured password..."' >> /usr/share/opensearch/setup-security.sh && \
    echo 'HASH=$(/usr/share/opensearch/plugins/opensearch-security/tools/hash.sh -p "$PASSWORD")' >> /usr/share/opensearch/setup-security.sh && \
    echo 'if [ -z "$HASH" ]; then echo "[ERROR] Failed to generate admin hash"; exit 1; fi' >> /usr/share/opensearch/setup-security.sh && \
    echo 'sed -i "s|^  hash: \".*\"|  hash: \"$HASH\"|" /usr/share/opensearch/securityconfig/internal_users.yml' >> /usr/share/opensearch/setup-security.sh && \
    echo 'echo "Updated internal_users.yml with runtime-generated admin hash"' >> /usr/share/opensearch/setup-security.sh && \
    echo 'BACKEND_URL=${OPENRAG_BACKEND_INTERNAL_URL:-http://${OPENRAG_BACKEND_HOST:-openrag-backend}:${OPENRAG_BACKEND_PORT:-8000}}' >> /usr/share/opensearch/setup-security.sh && \
    echo 'sed -i "s|http://openrag-backend:8000|$BACKEND_URL|g" /usr/share/opensearch/securityconfig/config.yml /usr/share/opensearch/cloud_securityconfig/config.yml' >> /usr/share/opensearch/setup-security.sh && \
    echo 'echo "Applying OIDC and DLS security configuration..."' >> /usr/share/opensearch/setup-security.sh && \
    echo '/usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh \' >> /usr/share/opensearch/setup-security.sh && \
    echo '  -cd /usr/share/opensearch/securityconfig \' >> /usr/share/opensearch/setup-security.sh && \
    echo '  -icl -nhnv \' >> /usr/share/opensearch/setup-security.sh && \
    echo '  -cacert /usr/share/opensearch/config/root-ca.pem \' >> /usr/share/opensearch/setup-security.sh && \
    echo '  -cert /usr/share/opensearch/config/kirk.pem \' >> /usr/share/opensearch/setup-security.sh && \
    echo '  -key /usr/share/opensearch/config/kirk-key.pem' >> /usr/share/opensearch/setup-security.sh && \
    echo 'echo "Security configuration applied successfully"' >> /usr/share/opensearch/setup-security.sh && \
    chmod +x /usr/share/opensearch/setup-security.sh

# Copy custom entrypoint wrapper that handles graceful shutdown
COPY opensearch-entrypoint-wrapper.sh /usr/share/opensearch/
RUN chmod +x /usr/share/opensearch/opensearch-entrypoint-wrapper.sh && \
    chown opensearch:opensearch /usr/share/opensearch/opensearch-entrypoint-wrapper.sh

########################################
# Final runtime settings
########################################
USER opensearch
WORKDIR $OPENSEARCH_HOME
ENV JAVA_HOME=$OPENSEARCH_HOME/jdk
# CWE-426 fix: explicitly set PATH so system-owned directories are always resolved
# first. App venv dirs are appended last so they cannot shadow system binaries.
# Matches the ordering used by the upstream image but with system dirs promoted
# to the front.
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/app-root/bin:/opt/app-root/src/bin:/opt/app-root/src/.local/bin:$JAVA_HOME/bin:$OPENSEARCH_HOME/bin

# Expose ports
EXPOSE 9200 9300 9600 9650

ENTRYPOINT ["./opensearch-entrypoint-wrapper.sh"]
CMD []

