FROM ubuntu:18.04

RUN apt-get update && apt-get install -y python2.7 python3.6 python-pip
RUN apt-get install -y build-essential g++ cmake libboost-all-dev libglib2.0-dev castxml python-pip git-core python3-setuptools
RUN apt-get install -y virtualenv python3-pip

WORKDIR /usr/src/zucc

COPY ./ ./

RUN virtualenv -p python3 venv \
    && . venv/bin/activate \
	&& make dist
RUN pip3 install dist/*.whl

WORKDIR /usr/src/grader
ENV LANG C.UTF-8

CMD [ "zucc" ]
