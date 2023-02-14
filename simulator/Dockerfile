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

COPY ./ ./

# Now install our package. Docker will re-run this every time the source code
# changes, but it should be quick because all the dependencies have already been
# installed.
#
# Our Docker environment is intended only for CI, so don't worry about
# installing in development mode (-e) here. Ordinarily that would also mean we
# don't need to bind-mount the local filesytem, but see the comments in
# docker-compose.yml about that. Note that if we do decide to install in
# development mode, we'll run into issues where the mounted filesystem won't
# have the .egg-info directory, masking the one in the image and preventing the
# package from working correctly. We'd probably need a workaround like the one
# described at https://thekev.in/blog/2016-11-18-python-in-docker/index.html.
RUN pip install .
