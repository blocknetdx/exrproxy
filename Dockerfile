# Build via docker:
# docker build --build-arg cores=8 -t blocknetdx/xrouterproxy:0.4.0 .
# docker run -d --name xrproxy -p 80:80 blocknetdx/xrouterproxy:0.4.0

FROM nginx

ARG cores=1
ENV ecores=$cores

RUN apt update \
  && apt install -y --no-install-recommends \
     software-properties-common \
     ca-certificates \
     wget curl git python3 vim \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt /opt/requirements.txt

RUN apt update \
  && apt install -y --no-install-recommends \
     supervisor build-essential libssl-dev \
     python3-dev python3-pip python3-setuptools \
  && pip3 install -r /opt/requirements.txt \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Setup uwsgi dir and bitcoin lib
RUN mkdir -p /opt/uwsgi/conf \
  && git clone --depth 1 --branch blocknet https://github.com/blocknetdx/python-bitcoinlib.git \
  && cp -r python-bitcoinlib/bitcoin /opt/uwsgi

# Write nginx.conf /etc/nginx/nginx.conf
RUN echo "                                                                         \n\
user nginx;                                                                        \n\
worker_processes $ecores;                                                          \n\
                                                                                   \n\
error_log  /var/log/nginx/error.log warn;                                          \n\
pid        /var/run/nginx.pid;                                                     \n\
                                                                                   \n\
events {                                                                           \n\
    worker_connections 1024;                                                       \n\
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
                                                                                   \n\
        # Proxying connections to application servers                              \n\
        location / {                                                               \n\
                                                                                   \n\
        }                                                                          \n\
                                                                                   \n\
        include /etc/nginx/conf.d/xcloud/*.conf;                                   \n\
                                                                                   \n\
        location ~ ^/xrs?/.*$ {                                                    \n\
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
RUN echo "[supervisord]                                                           \n\
user=root                                                                         \n\
nodaemon=true                                                                     \n\
                                                                                  \n\
[program:uwsgi]                                                                   \n\
command=/usr/local/bin/uwsgi --ini /opt/uwsgi/conf/uwsgi.ini --uid nginx --socket 127.0.0.1:8080 --master --chdir /opt/uwsgi --wsgi-file xrproxy.py --die-on-term \n\
stdout_logfile=/dev/stdout                                                        \n\
stdout_logfile_maxbytes=0                                                         \n\
stderr_logfile=/dev/stderr                                                        \n\
stderr_logfile_maxbytes=0                                                         \n\
                                                                                  \n\
[program:nginx]                                                                   \n\
command=/usr/sbin/nginx -g \"daemon off;\"                                        \n\
stdout_logfile=/dev/stdout                                                        \n\
stdout_logfile_maxbytes=0                                                         \n\
stderr_logfile=/dev/stderr                                                        \n\
stderr_logfile_maxbytes=0                                                         \n\
\n" > /etc/supervisord.conf

# create sample conf file
RUN echo "# SPV sample configuration file                                                                          \n\
[uwsgi]                                                                                                            \n\
processes = $ecores                                                                                                \n\
threads = 2                                                                                                        \n\
                                                                                                                   \n\
# Set the service node private key for signing responses (mandatory)                                               \n\
set-ph = SERVICENODE_PRIVKEY=                                                                                      \n\
                                                                                                                   \n\
# Set the chain to use (mainnet, testnet, regtest) defaults to mainnet                                             \n\
#set-ph = BLOCKNET_CHAIN=mainnet                                                                                   \n\
                                                                                                                   \n\
# Optionally handle XRouter payments                                                                               \n\
#set-ph = HANDLE_PAYMENTS=true                                                                                     \n\
#set-ph = HANDLE_PAYMENTS_RPC_HOSTIP=192.168.1.20                                                                  \n\
#set-ph = HANDLE_PAYMENTS_RPC_PORT=41419                                                                           \n\
#set-ph = HANDLE_PAYMENTS_RPC_USER=test                                                                            \n\
#set-ph = HANDLE_PAYMENTS_RPC_PASS=passw                                                                           \n\
#set-ph = HANDLE_PAYMENTS_RPC_VER=2.0                                                                              \n\
                                                                                                                   \n\
# Use the following format for all tokens, replace BLOCK with the                                                  \n\
# SPV ticker name registered on the Blocknet network.                                                              \n\
#set-ph = RPC_BLOCK_HOSTIP=192.168.1.20                                                                            \n\
#set-ph = RPC_BLOCK_PORT=41419                                                                                     \n\
#set-ph = RPC_BLOCK_USER=test                                                                                      \n\
#set-ph = RPC_BLOCK_PASS=passw                                                                                     \n\
#set-ph = RPC_BLOCK_VER=2.0                                                                                        \n\
                                                                                                                   \n\
#set-ph = RPC_LTC_HOSTIP=192.168.1.20                                                                              \n\
#set-ph = RPC_LTC_PORT=9332                                                                                        \n\
#set-ph = RPC_LTC_USER=test                                                                                        \n\
#set-ph = RPC_LTC_PASS=passw                                                                                       \n\
#set-ph = RPC_LTC_VER=2.0                                                                                          \n\
\n" > /opt/uwsgi/conf/uwsgi.ini

# Python handler
COPY xrproxy.py /opt/uwsgi/xrproxy.py

VOLUME ["/opt/uwsgi/conf", "/etc/nginx/conf.d"]

EXPOSE 80

ENTRYPOINT ["supervisord"]
CMD ["-c", "/etc/supervisord.conf"]
