FROM python:3.12-alpine
WORKDIR /srv
COPY frontend/index.html frontend/demo.html frontend/demo.js frontend/styles.css /srv/
COPY preview/confidentialite.html /srv/confidentialite.html
COPY preview/server.py /opt/cleantandem_preview.py
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/opt/cleantandem_preview.py"]
