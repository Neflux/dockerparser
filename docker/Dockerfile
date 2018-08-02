# This FROM instruction doesn't specify a fixed image version
FROM python:latest

WORKDIR /src
ADD . /src
RUN pip install --trusted-host pypi.python.org -r requirements.txt

RUN apt-get update
RUN apt-get install -y f g h a b s d g

# This pipe could fail
RUN wget -O - https://some.site | wc -l > /number

# This ADD fetches a compressed file remotely
ADD http://example.com/big.tar.xz /usr/src/things/
RUN tar -xJf /usr/src/things/big.tar.xz -C /usr/src/things
RUN make -C /usr/src/things all

EXPOSE 80
ENV NAME MLtest
CMD ["python", "src/program.py"]
