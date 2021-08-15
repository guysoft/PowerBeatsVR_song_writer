FROM guysoft/uwsgi-nginx-flask:python3.8
MAINTAINER Guy Sheffer <guysoft at gmail dot com>

ENV LISTEN_PORT 80

EXPOSE 80

RUN wget https://bootstrap.pypa.io/get-pip.py -O - | python3

COPY requirements.txt /
COPY . /powerbeatsvr
RUN pip3 install -r /requirements.txt
RUN pip3 install /powerbeatsvr
RUN mkdir -p  /tmp/static/downloads
RUN mkdir -p /tmp/uploads
RUN chmod 777 /tmp/static/downloads
RUN chmod 777 /tmp/uploads

COPY src/app /app
