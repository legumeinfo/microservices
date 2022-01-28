#!/bin/sh

set -o errexit

if python <<END
import sys, redis
r = redis.Redis(host='${REDIS_HOST:-localhost}',
                port=${REDIS_PORT:-6379},
                db=${REDIS_DB:-0})
sys.exit(min(r.dbsize(), 1))
END
then
  cd /docker-entrypoint-initdb.d
  for loader_script in *.sh
  do
    [ "${loader_script}" != '*.sh' ] && sh "${loader_script}"
  done
  cd -
fi

[ $# -gt 0 ] && python -u -m redis_loader "$@"
