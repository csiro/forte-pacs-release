# syntax=docker.io/docker/dockerfile:1.7-labs
FROM python:3.11

WORKDIR /code


COPY ./requirements.txt /code/requirements.txt
COPY ./icc /code/icc

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN wget -q -O- https://packagecloud.io/dcommander/libjpeg-turbo/gpgkey | gpg --dearmor >/etc/apt/trusted.gpg.d/libjpeg-turbo.gpg
RUN printf "deb [signed-by=/etc/apt/trusted.gpg.d/libjpeg-turbo.gpg] https://packagecloud.io/dcommander/libjpeg-turbo/any/ any main" > /etc/apt/sources.list.d/libjpeg-turbo.list 
RUN apt-get update -y 
RUN apt-get install -y libjpeg-turbo-official
COPY --exclude=./app/config ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--timeout-keep-alive", "30"]
