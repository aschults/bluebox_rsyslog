FROM alpine
#RUN sed -i -e 's/v3\.[0-9][0-9]*/edge/g' /etc/apk/repositories
RUN apk update && apk add rsyslog gettext


EXPOSE 514/udp

RUN mkdir -p /var/spool/rsyslog /etc/rsyslog_start.d
#RUN mkdir -p /var/spool/squid/cache /var/log/squid ; chown -R squid:squid /var/spool/squid/cache /var/log/squid
#VOLUME ["/var/spool/squid/cache", "/var/log/squid", "/var/spool/squid/ssl"]

COPY rsyslog.conf /etc
COPY rsyslog_fwd.conf /etc
COPY conf /etc/rsyslog.d
ADD rsyslog.sh /
ADD lib.sh /

#ADD liveness_check.sh /

ENTRYPOINT sh rsyslog.sh
