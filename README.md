# Blocknet Enterprise XRouter Proxy
https://github.com/blocknetdx/exrproxy
https://hub.docker.com/r/blocknetdx/exrproxy

The XRouter Proxy acts as a reverse proxy (similar to a load balancer) for all your XRouter services and oracles. The reverse proxy is comprised of an nginx web server and a uwsgi python handler. This repository is officially supported by the Blocknet core team. Please feel free to submit any issues or requests.

In order for your requests to be properly validated by the XRouter network you will need to specify your Service Node's private key. Note* this is not a wallet private key and as a result no coin private keys should be used. This is a unique Service Node key that's not associated with any funds. **Do not specify any coin private keys in these configurations**. 

## Autobuilder [currently in development]

The Blocknet Autobuilder can be used to autoconfigure and create docker-compose.yaml:

Preview: https://github.com/blocknetdx/exrproxy-env/tree/dev

## Quick setup

XRouter Proxy is designed to work in docker a environment, although this is not a mandatory requirement. A `uwsgi.ini` configuration file is required to hook up the services and oracles that need to be exposed through the proxy.

Please adjust the `uwsgi.ini` file below to work with your desired setup. `processes` and `threads` indicate how you can leverage multi-threading on the server to support more simultaneous requests. Keep in mind performance is directly related to your hardware capabilities.

*/opt/uwsgiconf/uwsgi.ini*
```
# SPV sample configuration file
[uwsgi]
processes = 8
threads = 2

# Place your Service Node private key here (this is not a wallet private key!)
# Allows the XRouter Proxy to sign packets on your Service Node's behalf
# DO NOT SHARE THIS KEY
set-ph = SERVICENODE_PRIVKEY=cV1bo3ME3qvw9Sxzo72skbFsAQ6ihyT6F8VXMe8mzv6EJoqFVXMV

# mainnet or testnet
set-ph = BLOCKNET_CHAIN=testnet

# Support local plugins
#set-ph = PLUGINS=evm_passthrough

# Handle XRouter payments
set-ph = HANDLE_PAYMENTS=true
set-ph = HANDLE_PAYMENTS_RPC_HOSTIP=192.168.1.25
set-ph = HANDLE_PAYMENTS_RPC_PORT=41419
set-ph = HANDLE_PAYMENTS_RPC_USER=user
set-ph = HANDLE_PAYMENTS_RPC_PASS=pass
set-ph = HANDLE_PAYMENTS_RPC_VER=2.0

# Sample SPV RPC configuration
set-ph = RPC_BLOCK_HOSTIP=192.168.1.25
set-ph = RPC_BLOCK_PORT=41419
set-ph = RPC_BLOCK_USER=user
set-ph = RPC_BLOCK_PASS=pass
set-ph = RPC_BLOCK_VER=2.0

# Sample XCloud plugin configuration
set-ph = URL_SomeCustomPlugin_HOSTIP=192.168.1.5
set-ph = URL_SomeCustomPlugin_PORT=8080

```

*Start the xrouter proxy container*

```
docker run -d --name=xrproxy -p 9090:80 -v=/opt/uwsgiconf:/opt/uwsgi/conf blocknetdx/exrproxy:latest
```

*Test if proxy is running*

```
curl -X POST -H "content-type: application/json" --data-binary '[]' 127.0.0.1:9090/
```

*Test if endpoint is running*

```
curl -X POST -H "content-type: application/json" --data-binary '[]' 127.0.0.1:9090/xr/BLOCK/xrGetBlockCount
```

## uwsgi.ini configuration

The nginx python web application responsible for reverse proxying to XRouter endpoints, obtains configuration options from the `uwsgi.ini` file. This file should be used to wire up and connect backend endpoints to the XRouter Proxy web server.

### SPV RPC endpoint

Format: `RPC_[CURRENCY]_[VAR]`

Supported options:

| Option                  | Description   |
| -------------------     | ------------- |
| `RPC_[CURRENCY]_HOSTIP` | Ip address of the endpoint |
| `RPC_[CURRENCY]_PORT`   | Endpoint's port number |
| `RPC_[CURRENCY]_USER`   | RPC username |
| `RPC_[CURRENCY]_PASS`   | RPC password |
| `RPC_[CURRENCY]_VER`    | RPC json version (ETH, parity and geth typically require "2.0") |

```
set-ph = RPC_BLOCK_HOSTIP=192.168.1.25
set-ph = RPC_BLOCK_PORT=41414
set-ph = RPC_BLOCK_USER=user
set-ph = RPC_BLOCK_PASS=pass
set-ph = RPC_BLOCK_VER=2.0
```

### XCloud Plugin RPC endpoint

Format: `RPC_[PLUGIN_NAME]_[VAR]`

The main difference between SPV and XCloud plugin RPC configurations is the additional `_METHOD` variable in the XCloud plugin config. 

Supported options:

| Option                  | Description   |
| -------------------     | ------------- |
| `RPC_[PLUGIN_NAME]_HOSTIP` | Ip address of the endpoint |
| `RPC_[PLUGIN_NAME]_PORT`   | Endpoint's port number |
| `RPC_[PLUGIN_NAME]_USER`   | RPC username |
| `RPC_[PLUGIN_NAME]_PASS`   | RPC password |
| `RPC_[PLUGIN_NAME]_VER`    | RPC json version (ETH, parity and geth typically require "2.0") |
| `RPC_[PLUGIN_NAME]_METHOD` | RPC method to be called |

```
set-ph = RPC_BLOCK_HOSTIP=192.168.1.25
set-ph = RPC_BLOCK_PORT=41414
set-ph = RPC_BLOCK_USER=user
set-ph = RPC_BLOCK_PASS=pass
set-ph = RPC_BLOCK_VER=2.0
set-ph = RPC_BLOCK_METHOD=getblockcount
``` 

### URL endpoint

Format: `URL_[PLUGIN_NAME]_[VAR]`

Supported options:

| Option                     | Description   |
| ----------------------     | ------------- |
| `URL_[PLUGIN_NAME]_HOSTIP` | Plugin ip address (for docker specify container ip address) |
| `URL_[PLUGIN_NAME]_PORT`   | Plugin's port number |

```
set-ph = URL_LTCGetBlockCount_HOSTIP=172.17.0.2
set-ph = URL_LTCGetBlockCount_PORT=9332
``` 

## NGINX configs for XCloud Plugins

An nginx config file can be used to expose an XCloud plugin through the XRouter Proxy server. This is an alternative setup and will bypass the built in python handler. The tradeoff is that the proxy will not sign return packets, however, you have full control of handling the request without any middleware. By default the XRouter protocol expects plugins to exist at the endpoint `/xrs/PluginName`.

These nginx XCloud plugins bypass the internal reverse proxy handler that we've provided, as a result you will be responsible for signing requests with the proper Service Node key manually as well as handling any payments from XRouter clients. If you do not want to do this, consider using the [URL endpoint](#URL-endpoint) plugin type that we've provided in the default reverse proxy handler. 

The XRouter Proxy container has a volume that mounts to `/etc/nginx`, the `conf.d` directory in here is where all nginx XCloud plugin endpoints are installed. This can be mounted via a docker volume:

```
# Assumes this directory exists: /opt/nginxconfs/conf.d/xcloud
docker run -v=/opt/nginxconfs:/etc/nginx blocknetdx/exrproxy:latest
``` 

*Sample nginx XCloud plugin conf: /opt/nginxconfs/conf.d/xcloud/LTCGetBlockCount.conf*

```
location = /xrs/LTCGetBlockCount {
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Host $server_name;
    proxy_pass http://192.168.1.5:9091;
}
```

## Handle XRouter Payments

The XRouter protocol allows Service Nodes to charge for specific services. The payment transaction is included along with the request packet. XRouter Proxy can handle submitting this to the Blocknet network on your behalf. Currently all XRouter fees are paid in BLOCK. XRouter Proxy will require the RPC credentials for the client responsible for handling the payment transaction.

Supported options:

| Option                       | Description   |
| ---------------------------  | ------------- |
| `HANDLE_PAYMENTS`            | Specify `true` (1) or `false` (0) |
| `HANDLE_PAYMENTS_ENFORCE`    | Specify `true` (1) or `false` (0). Enforces payment (may slow down requests) |
| `HANDLE_PAYMENTS_RPC_HOSTIP` | Ip address of the endpoint |
| `HANDLE_PAYMENTS_RPC_PORT`   | Endpoint's port number |
| `HANDLE_PAYMENTS_RPC_USER`   | RPC username |
| `HANDLE_PAYMENTS_RPC_PASS`   | RPC password |
| `HANDLE_PAYMENTS_RPC_VER`    | RPC json version |

*In `/opt/uwsgiconf/uwsgi.ini`*
```
set-ph = HANDLE_PAYMENTS=true
set-ph = HANDLE_PAYMENTS_ENFORCE=false
set-ph = HANDLE_PAYMENTS_RPC_HOSTIP=192.168.1.25
set-ph = HANDLE_PAYMENTS_RPC_PORT=41414
set-ph = HANDLE_PAYMENTS_RPC_USER=user
set-ph = HANDLE_PAYMENTS_RPC_PASS=pass
set-ph = HANDLE_PAYMENTS_RPC_VER=2.0
```

## EXR Passthrough plugin

This enable the eth json-rpc passthrough plugin allowing the EXR snode to deliver free and paid calls to the eth backend.

*In `/opt/uwsgiconf/uwsgi.ini`*
```
set-ph = PLUGINS=evm_passthrough
```

## Docker

https://hub.docker.com/r/blocknetdx/exrproxy/tags

Volumes that can be used with the XRouter Proxy container:

| Volume              | Description   |
| ------------------- | ------------- |
| `/opt/uwsgi/conf`   | Should contain the `uwsgi.ini` config |
| `/etc/nginx`        | Contains all the nginx configuration files. Specifically any custom XCloud plugin endpoints |

### Full docker run example w/ volumes:

```
docker run -d --name=xrproxy -p 9090:80 -v=/opt/uwsgiconf:/opt/uwsgi/conf -v=/opt/nginxconfs:/etc/nginx blocknetdx/exrproxy:latest
```

### Build Dockerfile

```
docker build --build-arg cores=4 -t blocknetdx/exrproxy:latest . 
```

## Debugging

### Local

```
uwsgi --ini uwsgiconf/test_uwsgi.ini --protocol=http --socket :9090 -w wsgi:app --virtualenv venv --honour-stdin --enable-threads --die-on-term
```

*With evm_passthrough plugin enabled (requires postgresql)*
```
DB_HOST=localhost DB_USERNAME=ethproxy DB_PASSWORD=password DB_DATABASE=eth ETH_HOST=localhost:8545 ETH_USER=test ETH_PASS=pass uwsgi --ini uwsgiconf/test_uwsgi.ini --protocol=http --socket :9090 -w wsgi:app --virtualenv venv --honour-stdin --enable-threads --die-on-term
```

*Sample test_uwsgi.ini*
```
[uwsgi]
processes = 1
threads = 1

set-ph = SERVICENODE_PRIVKEY=cTXWkw5CnrLsmXqcM3pdynQRqLLiBQRVF9pgDaxH97KQteQ4cq3e
set-ph = BLOCKNET_CHAIN=testnet
#set-ph = PLUGINS=evm_passthrough

set-ph = HANDLE_PAYMENTS=true
set-ph = HANDLE_PAYMENTS_RPC_HOSTIP=localhost
set-ph = HANDLE_PAYMENTS_RPC_PORT=41419
set-ph = HANDLE_PAYMENTS_RPC_USER=test
set-ph = HANDLE_PAYMENTS_RPC_PASS=pass
set-ph = HANDLE_PAYMENTS_RPC_VER=2.0
```

# License

```
MIT License

Copyright (c) 2019-2020 The Blocknet developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
