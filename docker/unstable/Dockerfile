FROM docker.io/library/python:3.12.6-slim@sha256:3915ca5721d1ea28844b2db538a46bf48dd13bf3cf623a1e956049eac66f5351

# This file is generated from docker:unstable in Taskfile.yml
COPY var/requirements.txt /var/tmp/build/

RUN \
    pip install -r /var/tmp/build/requirements.txt

COPY dist/*.whl /var/tmp/build/

RUN \
    pip install --no-deps /var/tmp/build/*.whl && \
    rdfpipe --version

ENTRYPOINT [ ]
