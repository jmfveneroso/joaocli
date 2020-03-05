FROM python:3

# Replace shell with bash.
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Add VIM and Git to allow manual maintenance.
RUN apt-get update && apt-get install -y \
  vim \
  git

# Install pip packages and create the code directory.
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
ADD . /code/

# Install NodeJS mostly for precompiling tools.
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 8.10.0
RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/v0.31.2/install.sh | bash
RUN source $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

# Add node and npm to path to make sure the commands are available.
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Confirm installation.
RUN node -v
RUN npm -v

# Autodocs for javascript using sphinx.
RUN npm install -g jsdoc

# Build assets.
RUN cd /code/frontend && npm install && npm run build

ENTRYPOINT ["./start.sh"]
