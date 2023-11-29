FROM python:3.11-slim

ENV VIRTUAL_ENV=/venv

RUN useradd heroku_scaling_scheduler --create-home && mkdir /app $VIRTUAL_ENV && chown -R heroku_scaling_scheduler /app $VIRTUAL_ENV

WORKDIR /app

# Install poetry at the system level
RUN pip install --no-cache poetry==1.5.0

USER heroku_scaling_scheduler

RUN python -m venv $VIRTUAL_ENV

ENV PATH=$VIRTUAL_ENV/bin:$PATH

COPY --chown=heroku_scaling_scheduler pyproject.toml poetry.lock ./

RUN pip install --no-cache --upgrade pip && poetry install --no-dev --no-root && rm -rf $HOME/.cache

COPY --chown=heroku_scaling_scheduler . .

# Run poetry install again to install our project
RUN poetry install --no-dev

CMD ["/venv/bin/heroku-scaling-scheduler"]
