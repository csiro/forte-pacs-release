FROM python:3.11

WORKDIR /code

COPY docker/rq-worker/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

ENV PYTHONPATH="${PYTHONPATH}:/code"

CMD ["sh","-c", "rq worker -u $redis_url $qido_queue_name"]
