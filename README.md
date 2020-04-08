# docker-python-base
Docker python base project.

```
sudo docker build -t logger-website .
sudo docker run -t -i -p 8888:80 -p 3000:3000 -v $(pwd):/code --rm logger-website

sudo docker build -t logger-website . && sudo docker run -t -i -p 8888:80 -p 3000:3000 -v $(pwd):/code --rm logger-website

ssh -i ../Default.pem ubuntu@18.224.133.3
```
