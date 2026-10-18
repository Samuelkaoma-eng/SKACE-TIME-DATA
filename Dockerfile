# syntax=docker/dockerfile:1.7
#
# Static results site for the paradata pipeline, built for Dokploy.
#
# The pipeline runs here, at build time, on the synthetic datasets that ship
# with the repository, and the audit notebook is executed on one run. The
# finished page and every output CSV are then served by nginx, so nothing runs
# when a visitor opens the site and there is no upload, no account and no live
# Python process to go wrong. Every push to
# main rebuilds the image, so the page always reports the commit it came from.
#
#   docker build -t paradata-site .
#   docker run --rm -p 8080:8080 paradata-site     # http://localhost:8080

ARG PYTHON_IMAGE=python:3.14-slim
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.27-alpine

# ---------------------------------------------------------------------------
# Stage 1: the commit this image was built from, shown on the page and /health.
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS version

# Dokploy builds from a clone, so .git is in the context. .dockerignore lets
# through only HEAD, refs/heads and packed-refs, which hold commit ids and
# nothing else. ".gi[t]" matches .git when present and nothing otherwise, so a
# context without .git still builds; the version is then "unknown" unless
# BUILD_VERSION is passed as a build argument.
ARG BUILD_VERSION=""
WORKDIR /src
COPY requirements-validated.txt .gi[t] ./
RUN set -eu; \
    v="${BUILD_VERSION}"; \
    if [ -z "$v" ] && [ -f HEAD ]; then \
        head="$(cat HEAD)"; \
        case "$head" in \
            "ref: "*) ref="${head#ref: }"; \
                if [ -f "$ref" ]; then v="$(cat "$ref")"; \
                elif [ -f packed-refs ]; then v="$({ grep " ${ref}\$" packed-refs || :; } | cut -d' ' -f1)"; fi ;; \
            *) v="$head" ;; \
        esac; \
    fi; \
    printf '%s' "$v" | tr -cd '0-9a-f' | cut -c1-12 > /version; \
    echo "Built from commit: $(cat /version)"

# ---------------------------------------------------------------------------
# Stage 2: run the pipeline and write the site.
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app
COPY requirements-validated.txt ./

# What the pipeline imports, plus what executing and rendering the audit
# notebook needs (matplotlib, seaborn, a kernel and nbconvert). The rest of
# requirements.txt, JupyterLab and the test tools, stays out. The validated
# lock is applied as constraints, so each package is installed at the version
# the September 2026 release was validated with. --only-binary keeps a
# compiler out: a missing wheel stops the build here and says so.
RUN pip install --only-binary=:all: -c requirements-validated.txt \
        pandas numpy scipy scikit-learn statsmodels \
        matplotlib seaborn ipykernel nbclient nbconvert nbformat \
 && pip check

COPY run_pipeline.py ./
COPY src/ ./src/
COPY scripts/__init__.py scripts/build_results_site.py ./scripts/
COPY notebooks/System_Audit_Report.ipynb ./notebooks/
COPY data/odk.csv data/surveycto.csv data/ground_truth_labels.csv ./data/
COPY data/synthetic_datasets/n500/ ./data/synthetic_datasets/n500/
COPY --from=version /version ./VERSION

RUN BUILD_VERSION="$(cat VERSION)" python scripts/build_results_site.py --out /site

# ---------------------------------------------------------------------------
# Stage 3: what runs. nginx as an unprivileged user, serving files only.
# ---------------------------------------------------------------------------
FROM ${NGINX_IMAGE} AS runtime

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /site /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
