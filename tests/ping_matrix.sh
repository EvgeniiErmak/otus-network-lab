#!/bin/bash
# Матрица связности: каждый хост пингует все 7 хостов стенда
cd "$(dirname "$0")/.."
TARGETS="inetRouter=192.168.255.1 centralRouter=192.168.0.1 centralServer=192.168.0.2 office1Router=192.168.2.129 office1Server=192.168.2.130 office2Router=192.168.1.1 office2Server=192.168.1.2"
ansible all -b -m shell -a "for t in $TARGETS; do n=\${t%%=*}; ip=\${t#*=}; if ping -c1 -W2 \$ip >/dev/null; then r=OK; else r=FAIL; fi; printf '%-14s %-15s %s\n' \$n \$ip \$r; done" | sed 's/ | CHANGED | rc=0 >>/  ->/'
