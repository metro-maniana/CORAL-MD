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
RUN useradd -u 4200 user && chown -R user:user /home/user

USER user

COPY --from=build --chown=user:user /home/user/web/.pixi/envs/default /home/user/web/.pixi/envs/default
COPY --from=build --chown=user:user --chmod=0755 /home/user/web/entrypoint.sh /home/user/web/entrypoint.sh
COPY --from=build --chown=user:user /home/user/web/chebi /home/user/web/chebi
COPY --from=build --chown=user:user /home/user/web/blast /home/user/web/blast

COPY --chown=user:user ./ligand_service ./ligand_service
COPY --chown=user:user ./theme ./theme
COPY --chown=user:user ./manage.py .

RUN mkdir -p /home/user/web/user_uploads && chown -R user:user /home/user/web/user_uploads

ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=True

ENTRYPOINT [ "/home/user/web/entrypoint.sh" ]
