# Parto dall'immagine di python2.7 come immagine di base
FROM python:latest

# Imposto la working directory a /src
WORKDIR /src

# Copio i contenuti della root in /src nel container
ADD . /src

# Installo i moduli python necessari
RUN pip install --trusted-host pypi.python.org -r requirements.txt
RUN wget -O - https://some.site | wc -l > /number

ADD http://example.com/big.tar.xz /usr/src/things/
RUN tar -xJf /usr/src/things/big.tar.xz -C /usr/src/things
RUN make -C /usr/src/things all

# Apro la porta 80 fuori dal container
EXPOSE 80

# Variabile d'ambiente
ENV NAME MLtest

# Lancio il programma principale quando il container è inizializzato
CMD ["python", "src/program.py"]
