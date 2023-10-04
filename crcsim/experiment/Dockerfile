# Because Python 3.6 is installed on our target platform, use 3.6 for the Docker
# image.
FROM python:3.6.5-stretch

WORKDIR /code

# First install the package dependencies. By copying only requirements.txt into
# the image beforehand, Docker will re-run this step only when requirements.txt
# changes.
COPY ./requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of the experiment files. 
COPY ./ /code

# Declare the directory with experiment files as a volume
VOLUME /code