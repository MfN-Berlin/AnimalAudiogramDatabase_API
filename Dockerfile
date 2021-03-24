FROM python:3

LABEL Description="Data service for AAD"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
