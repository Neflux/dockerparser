# This FROM instruction doesn't specify a fixed image version
FROM python:latest

WORKDIR /src
ADD . /src
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# This these two apt-gets should generate only one layer
RUN apt-get update
RUN apt-get install -y f g \
h a b s \ 
d g

# This pipe could fail silently
RUN wget -O - https://some.site | wc -l > /number
RUN apt-get install -y s c g

# This ADD fetches a compressed file remotely in the wrong way
ADD http://example.com/big.tar.xz /usr/src/things/
RUN tar -xJf /usr/src/things/big.tar.xz -C /usr/src/things
RUN make -C /usr/src/things all

EXPOSE 80
ENV NAME MLtest
CMD ["python", "src/program.py"]
