FROM debian:jessie

ENV CONFIG_PREWIPE false
ENV EC2 false
ENV SOFTTIMER_TIMERFD true
ENV DEFAULT_PASSWORD 1234
ENV DEBIAN_FRONTEND noninteractive

# Note, the additional packages are installed for use case reasons:
# - xmlstarlet for XML manipulation via ENTRYPOINT
# - git for overly configuration from a git repository
# - vim for dev/test editing in the fs container

RUN apt-get update && apt-get -y install curl psmisc && \
      curl https://files.freeswitch.org/repo/deb/debian/freeswitch_archive_g0.pub | apt-key add - && \
      echo "deb http://files.freeswitch.org/repo/deb/freeswitch-1.6/ jessie main" > /etc/apt/sources.list.d/freeswitch.list && \
      apt-get -y update && apt-get -y upgrade && \
      apt-get -y install xmlstarlet git vim freeswitch-all freeswitch-all-dbg gdb && \
      rm -rf /var/lib/apt/lists/*

#VOLUME /etc/freeswitch
#VOLUME /var/lib/freeswitch
#VOLUME /var/log/freeswitch
#VOLUME /usr/share/freeswitch

EXPOSE 5060/tcp 5060/udp 5080/tcp 5080/udp
EXPOSE 5066/tcp 7443/tcp
EXPOSE 8021/tcp

# RTP port range (we leave uncommented currently, user decides at runtime)
# EXPOSE 16384-32768/udp
# see https://www.engagespark.com/blog/rtp-port-ranges-for-freeswitch-in-docker
# noting issues such as:
# https://github.com/moby/moby/issues/14288
# https://github.com/moby/moby/issues/14856

COPY entry.sh /opt/local/bin/entry.sh
COPY reload.sh /opt/local/bin/reload.sh
#RUN killall freeswitch
RUN rm -rf /etc/freeswitch

ENTRYPOINT ["/opt/local/bin/entry.sh"]

CMD ["freeswitch", "-c", "-nf"]
