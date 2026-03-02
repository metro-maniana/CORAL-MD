FROM ghcr.io/prefix-dev/pixi:latest AS build

WORKDIR /home/user/web

COPY . .
RUN pixi install --locked
RUN pixi shell-hook -s bash > /shell-hook
RUN echo "#!/bin/bash" > /home/user/web/entrypoint.sh
RUN cat /shell-hook >> /home/user/web/entrypoint.sh
RUN echo 'exec "$@"' >> /home/user/web/entrypoint.sh


FROM debian:bookworm-slim AS production 
WORKDIR /home/user/web
COPY --from=build /home/user/web/.pixi/envs/default /home/user/web/.pixi/envs/default
COPY --from=build --chmod=0755 /home/user/web/entrypoint.sh /home/user/web/entrypoint.sh

RUN useradd -m -u 4200 user && chown -R user:user /home/user
WORKDIR /home/user/web

COPY ./setup ./setup
RUN . /home/user/web/entrypoint.sh && python /home/user/web/setup/makeblastdb.py
RUN . /home/user/web/entrypoint.sh && python /home/user/web/setup/getchebi.py 

ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=True

COPY --chown=user:user ./ligand_service ./ligand_service
COPY --chown=user:user ./theme ./theme
COPY --chown=user:user ./manage.py .
COPY --chown=user:user ./example_results ./user_uploads

ENTRYPOINT [ "/home/user/web/entrypoint.sh" ]
