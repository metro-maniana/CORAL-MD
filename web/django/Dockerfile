FROM ghcr.io/prefix-dev/pixi:latest AS build

WORKDIR /home/user/web

COPY ./pyproject.toml .
COPY ./pixi.lock .
RUN pixi install --locked
RUN pixi shell-hook -s bash > /shell-hook
RUN echo "#!/bin/bash" > /home/user/web/entrypoint.sh
RUN cat /shell-hook >> /home/user/web/entrypoint.sh
RUN echo 'exec "$@"' >> /home/user/web/entrypoint.sh

COPY ./setup ./setup
RUN . /home/user/web/entrypoint.sh && python /home/user/web/setup/getchebi.py
RUN . /home/user/web/entrypoint.sh && python /home/user/web/setup/makeblastdb.py

FROM debian:bookworm-slim AS production
WORKDIR /home/user/web
RUN apt-get update && apt-get install curl -y

RUN useradd -u 4200 user && chown -R user:user /home/user

COPY --from=build --chown=user:user /home/user/web/.pixi/envs/default /home/user/web/.pixi/envs/default
COPY --from=build --chown=user:user --chmod=0755 /home/user/web/entrypoint.sh /home/user/web/entrypoint.sh
COPY --from=build --chown=user:user /home/user/web/chebi /home/user/web/chebi
COPY --from=build --chown=user:user /home/user/web/blast /home/user/web/blast

WORKDIR /home/user/web
COPY --chown=user:user . .

RUN id
USER user 
ENV NVM_DIR=/home/user/.nvm
RUN mkdir -p $NVM_DIR \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install v22.19.0 \
    && nvm which node \
    && node -v \
    && npm -v
ENV PATH=$NVM_DIR/versions/node/v22.19.0/bin/:$PATH

COPY --chown=user:user . .

ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=True

RUN mkdir -p /home/user/web/user_uploads && chown -R user:user /home/user/web/user_uploads
RUN mkdir -p /home/user/web/staticfiles && chown -R user:user /home/user/web/staticfiles

COPY --chown=user:user ./example_results ./user_uploads

ENTRYPOINT [ "/home/user/web/entrypoint.sh" ]
CMD ["sh", "./django/docker_entrypoint.sh"]
