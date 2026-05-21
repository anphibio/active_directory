FROM prom/alertmanager:v0.27.0

USER root

COPY entrypoint.sh /usr/local/bin/admanager-alertmanager-entrypoint.sh
RUN chmod +x /usr/local/bin/admanager-alertmanager-entrypoint.sh

USER nobody

ENTRYPOINT ["/usr/local/bin/admanager-alertmanager-entrypoint.sh"]
