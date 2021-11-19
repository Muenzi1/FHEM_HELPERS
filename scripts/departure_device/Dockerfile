# Python Base Image from https://hub.docker.com/r/arm64v8/python/
# FROM amd64/python:3-slim
FROM python:3.9-slim AS compile-image

# RUN apt-get update && \ 
#     apt-get install -y --no-install-recommends build-essential \
#         libzbar-dev \ 
#         libssl-dev \
#         libsodium-dev \
#         cargo \ 
#         rustc


RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install wheel
RUN pip install -r requirements.txt

COPY src/ /opt/fhem/scripts



FROM python:3.9-slim

# copy only the dependencies installation from the 1st stage image
COPY --from=compile-image /opt/venv /opt/venv
COPY --from=compile-image /opt/fhem/scripts /opt/fhem/scripts

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /opt/fhem/scripts

CMD [ "python", "./request_db_api.py" ]