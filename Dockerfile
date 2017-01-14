FROM alpine
#RUN sed -i -e 's/v3\.[0-9][0-9]*/edge/g' /etc/apk/repositories
RUN apk update && apk add rsyslog gettext


EXPOSE 514/udp 10514

RUN mkdir -p /var/spool/rsyslog /var/lib/rsyslog/logs /var/lib/rsyslog/sources /etc/rsyslog_start.d
VOLUME ["/var/lib/rsyslog/logs","/var/lib/rsyslog/sources"]

COPY rsyslog.conf /etc
COPY rsyslog_fwd.conf /etc
COPY conf /etc/rsyslog.d
ADD rsyslog.sh /
ADD lib.sh /

#ADD liveness_check.sh /

ENTRYPOINT sh rsyslog.sh
