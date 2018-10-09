FROM ubuntu:18.04

RUN apt-get update && apt-get install -y python2.7 python3.6 python-pip
RUN apt-get install -y build-essential g++ cmake libboost-all-dev libglib2.0-dev castxml python-pip git-core python3-setuptools
RUN apt-get install -y python3-setuptools
RUN echo 'alias python=python3' >> ~/.bashrc

WORKDIR /usr/src/zucc

COPY ./ ./

RUN pip install -r requirements.txt \
	&& pip install -r requirements_dev.txt \
	&& make install 

WORKDIR /usr/src/grader

CMD [ "zucc" ]