# Build via docker
`docker build --build-arg cores=8 -t webserver .`

# Run image
`docker run -d --name webserver -p 8192:8192 webserver:latest`
