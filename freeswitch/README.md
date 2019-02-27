# docker-freeswitch

Run FreeSWITCH in a Docker container

## Usage

### Build

    $ docker build -t freeswitch .

### Run

Foreground:

    $ docker run -it --net=host -e DEFAULT_PASSWORD=s3cure --name freeswitch freeswitch

Detached:

    $ docker run -itd --net=host -e DEFAULT_PASSWORD=s3cure --name freeswitch freeswitch

#### Runtime Environment Variables

There should be a reasonable amount of flexibility using the available variables. If not please raise an issue so your use case can be covered!

- `CONFIG_PREWIPE` - wipe `/etc/freeswitch` before reconfiguring in entrypoint - `true` or `false`, default is `false`
- `CONFIG_OVERLAY_GIT_URI` - URI for git clone of a custom configuration repo to overlay  on top of the default configuration
- `CONFIG_OVERLAY_GIT_PRIVATE_KEY` - SSH private key for the git repo (if required, private is recommended)
- `DEFAULT_PASSWORD` - The default password, this should always be set to override the default of `1234`
- `EC2` - Configure for EC2/VPC usage - `true` or `false`, default is `false`
- `SOFTTIMER_TIMERFD` - Whether to enable or disable timerfd - `true` or `false`, default is `true`

#### Runtime Management

Bring up the FreeSWITCH console:

    $ docker exec -it freeswitch fs_cli

Check the status of the server:

    freeswitch@internal> sofia status profile internal

Exit the console using the `/exit` command.

##### Updating and Reloading with the Overlay Repository

    $ docker exec -it freeswitch /opt/local/bin/reload.sh

#### Files and Directories

##### Directories Overview

 * `/etc/freeswitch` - home of all configuration files
 * `/var/log/freeswitch` - log files

##### Configuration Files

 * `/etc/freeswitch/vars.xml`
 * `/etc/freeswitch/sip_profiles/internal.xml`
 * `/etc/freeswitch/sip_profiles/external.xml`
 * `/etc/freeswitch/autoload_configs/switch.conf.xml`
 * `/etc/freeswitch/dialplan/default.xml` - default dialplan

#### Testing the Server

FreeSWITCH comes out of the box with a default password for registrations to users 1000-1019 as '1234'.
The default password should be changed by setting `DEFAULT_PASSWORD` with the container run.

Connect your SIP (e.g. a soft phone) with username `1000` and the value of `DEFAULT_PASSWORD`.

Once your container is running and a SIP client connected, test some extensions:

 * `5000` - Default IVR
 * `9195` - five second delay echo test
 * `9196` - standard echo test
 * `9197` - milliwatt extension
 * `9198` - Tetris music
 * `9664` - music on hold

 Conference rooms:
 * `9888` - 8k codec
 * `91616` - 16k codec; disabled
 * `93232` - 32k codec; disabled

More information: https://wiki.freeswitch.org/wiki/Getting_Started_Guide

#### Firewall Configuration

If you run a firewall on the host:

- http://wiki.freeswitch.org/wiki/Firewall
- https://freeswitch.org/confluence/display/FREESWITCH/Firewall

### Tag and Push

    $ docker tag freeswitch flaccid/freeswitch
    $ docker push flaccid/freeswitch

## Useful Resources

- https://freeswitch.org/
- https://wiki.archlinux.org/index.php/Freeswitch
- https://wiki.freeswitch.org/wiki/Getting_Started_Guide
- https://beingasysadmin.wordpress.com/2014/06/16/dockerizing-freeswitch-docker-enters-telephony-world/
- https://wiki.freeswitch.org/wiki/Getting_Started_Guide#Dialing_out_via_Gateway

See https://wiki.freeswitch.org/wiki/Freeswitch_Gui for frontends.

License and Authors
-------------------
- Author: Chris Fordham (<chris@fordham-nagy.id.au>)

```text
Copyright 2016, Chris Fordham

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
