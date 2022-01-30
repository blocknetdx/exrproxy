# Copyright (c) 2019-2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

# Build via docker:
# docker build --build-arg cores=8 --build-arg workerconns=2048 -t proxy .
# docker run -d --name proxy -p 80:80 proxy:latest

FROM nginx

RUN apt update \
  && apt install -y --no-install-recommends \
     software-properties-common \
     ca-certificates \
     wget curl git python3 nano \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt /opt/requirements.txt

RUN apt update \
  && apt install -y --no-install-recommends \
     supervisor build-essential libssl-dev \
     python3-dev python3-pip python3-setuptools \
  && pip3 install -r /opt/requirements.txt \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install certbot
RUN apt-get update && apt-get upgrade -y && apt-get dist-upgrade -y

RUN apt-get install -y ca-certificates

RUN apt-get install gnupg -y

RUN add-apt-repository ppa:certbot/certbot -y

RUN apt install python-certbot-nginx -y

# Setup uwsgi dir
RUN mkdir -p /opt/uwsgi/conf 

ARG cores=1
ENV ecores=$cores
ARG workerconns=1024
ENV eworkerconns=$workerconns

# Write nginx.conf /etc/nginx/nginx.conf
RUN echo "                                                                         \n\
user nginx;                                                                        \n\
worker_processes $ecores;                                                          \n\
                                                                                   \n\
error_log  /var/log/nginx/error.log warn;                                          \n\
pid        /var/run/nginx.pid;                                                     \n\
                                                                                   \n\
events {                                                                           \n\
    worker_connections $eworkerconns;                                              \n\
}                                                                                  \n\
                                                                                   \n\
http {                                                                             \n\
    include       /etc/nginx/mime.types;                                           \n\
    default_type  application/octet-stream;                                        \n\
    #sendfile     on;                                                              \n\
    #gzip         on;                                                              \n\
    keepalive_timeout  65;                                                         \n\
                                                                                   \n\
    log_format  main '\$remote_addr - \$remote_user [\$time_local] \"\$request\" ' \n\
                          '\$status \$body_bytes_sent \"\$http_referer\" '         \n\
                          '\"\$http_user_agent\" \"\$http_x_forwarded_for\"';      \n\
                                                                                   \n\
    access_log  /var/log/nginx/access.log  main;                                   \n\
                                                                                   \n\
    # Configuration containing list of application servers                         \n\
    upstream uwsgicluster {                                                        \n\
        server 127.0.0.1:8080;                                                     \n\
        # server 127.0.0.1:8081;                                                   \n\
        # ..                                                                       \n\
        # .                                                                        \n\
    }                                                                              \n\
                                                                                   \n\
    # Configuration for Nginx                                                      \n\
    server {                                                                       \n\
        # Running port                                                             \n\
        listen 80;                                                                 \n\
        #listen              443 ssl;                                              \n\
        #server_name         www.example.com;                                      \n\
        #ssl_certificate     www.example.com.crt;                                  \n\
        #ssl_certificate_key www.example.com.key;                                  \n\
                                                                                   \n\
        # Proxying connections to application servers                              \n\
        location / {                                                               \n\
                                                                                   \n\
        }                                                                          \n\
                                                                                   \n\
        include /etc/nginx/conf.d/xcloud/*.conf;                                   \n\
                                                                                   \n\
        location ~ ^/v1?/.*$ {                                                     \n\
            root               /opt/uwsgi;                                         \n\
            include            uwsgi_params;                                       \n\
            uwsgi_pass         uwsgicluster;                                       \n\
            proxy_redirect     off;                                                \n\
            proxy_set_header   Host \$host;                                        \n\
            proxy_set_header   X-Real-IP \$remote_addr;                            \n\
            proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;        \n\
            proxy_set_header   X-Forwarded-Host \$server_name;                     \n\
        }                                                                          \n\
    }                                                                              \n\
                                                                                   \n\
    include /etc/nginx/conf.d/*.conf;                                              \n\
}                                                                                  \n\
                                                                                   \n\
\n" > /etc/nginx/nginx.conf

# uwsgi params
RUN echo "uwsgi_param  QUERY_STRING       \$query_string;                          \n\
uwsgi_param  REQUEST_METHOD     \$request_method;                                  \n\
uwsgi_param  CONTENT_TYPE       \$content_type;                                    \n\
uwsgi_param  CONTENT_LENGTH     \$content_length;                                  \n\
                                                                                   \n\
uwsgi_param  REQUEST_URI        \$request_uri;                                     \n\
uwsgi_param  PATH_INFO          \$document_uri;                                    \n\
uwsgi_param  DOCUMENT_ROOT      \$document_root;                                   \n\
uwsgi_param  SERVER_PROTOCOL    \$server_protocol;                                 \n\
uwsgi_param  REQUEST_SCHEME     \$scheme;                                          \n\
uwsgi_param  HTTPS              \$https if_not_empty;                              \n\
                                                                                   \n\
uwsgi_param  REMOTE_ADDR        \$remote_addr;                                     \n\
uwsgi_param  REMOTE_PORT        \$remote_port;                                     \n\
uwsgi_param  SERVER_PORT        \$server_port;                                     \n\
uwsgi_param  SERVER_NAME        \$server_name;                                     \n\
\n" > /opt/uwsgi/uwsgi_params

# supervisord
RUN echo "[supervisord]                                                            \n\
user=root                                                                          \n\
nodaemon=true                                                                      \n\
                                                                                   \n\
[program:uwsgi]                                                                    \n\
command=/usr/local/bin/uwsgi --ini /opt/uwsgi/conf/uwsgi.ini --uid nginx --socket 127.0.0.1:8080 --master --chdir /opt/uwsgi --wsgi-file proxy.py --die-on-term \n\
stdout_logfile=/dev/stdout                                                         \n\
stdout_logfile_maxbytes=0                                                          \n\
stderr_logfile=/dev/stderr                                                         \n\
stderr_logfile_maxbytes=0                                                          \n\
                                                                                   \n\
[program:nginx]                                                                    \n\
command=/usr/sbin/nginx -g \"daemon off;\"                                         \n\
stdout_logfile=/dev/stdout                                                         \n\
stdout_logfile_maxbytes=0                                                          \n\
stderr_logfile=/dev/stderr                                                         \n\
stderr_logfile_maxbytes=0                                                          \n\
\n" > /etc/supervisord.conf

# create sample conf file
RUN echo "# Sample configuration file                                              \n\
[uwsgi]                                                                            \n\
processes = $ecores                                                                \n\
threads = 2                                                                        \n\
                                                                                   \n\
\n" > /opt/uwsgi/conf/uwsgi.ini

# Python handler
COPY proxy.py /opt/uwsgi/proxy.py

VOLUME ["/opt/uwsgi/conf", "/etc/nginx"]

EXPOSE 80 443

ENTRYPOINT ["supervisord"]
CMD ["-c", "/etc/supervisord.conf"]
