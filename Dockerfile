FROM python:3.13-slim

ENV VIRTUAL_ENV=/venv

RUN useradd heroku_scheduled_scaling --create-home && mkdir /app $VIRTUAL_ENV && chown -R heroku_scheduled_scaling /app $VIRTUAL_ENV

WORKDIR /app

# Install poetry at the system level
RUN pip install --no-cache poetry==2.1.1

USER heroku_scheduled_scaling

RUN python -m venv $VIRTUAL_ENV

ENV PATH=$VIRTUAL_ENV/bin:$PATH

COPY --chown=heroku_scheduled_scaling pyproject.toml poetry.lock ./

RUN pip install --no-cache --upgrade pip && poetry install --no-dev --no-root && rm -rf $HOME/.cache

COPY --chown=heroku_scheduled_scaling . .

RUN poetry install --no-dev

CMD ["/venv/bin/heroku-scheduled-scaling"]
