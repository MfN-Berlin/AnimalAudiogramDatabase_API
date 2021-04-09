FROM python:3

LABEL Description="Data service for AAD"

# install git
RUN apt-get update \
&& apt-get -y install default-mysql-client wget git nano zip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
