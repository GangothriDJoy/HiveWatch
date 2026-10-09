# Owner: Member 4
# Builds the tiny capture container: Alpine Linux + tcpdump + capture.sh
FROM alpine:3.20
RUN apk add --no-cache tcpdump
COPY capture.sh /capture.sh
RUN chmod +x /capture.sh
ENTRYPOINT ["/capture.sh"]
