#!/bin/bash

set -e

echo "Creating tarball..."
tar -czf /tmp/joaocli.tar.gz .

scp -i ../Default.pem /tmp/joaocli.tar.gz ubuntu@18.224.133.3:/home/ubuntu
rm /tmp/joaocli.tar.gz
echo "Uploaded tarball to AWS."

ssh -i ../Default.pem ubuntu@18.224.133.3 << EOF
  sudo rm -rf joaocli
  mkdir joaocli
  mv joaocli.tar.gz joaocli
  cd joaocli
  tar -xzf joaocli.tar.gz
  rm joaocli.tar.gz
  ./stop.sh
  echo "HOST_IP=18.224.133.3" > frontend/.env

  docker build -t logger-website .
  docker run -t -i -p 80:80 -p 3000:3000 -v /home/ubuntu/joaocli:/code -d --rm logger-website > log.txt
  echo "Finished"
EOF
