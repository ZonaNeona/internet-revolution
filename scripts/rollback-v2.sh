#!/usr/bin/env bash
set -euo pipefail
archive=${1:?Pass the pre-v2 source archive printed by deploy-v2.py}
case "$archive" in /var/backups/product-hunter/pre-v2-*.tgz) ;; *) echo 'Unexpected archive'; exit 1;; esac
test -f "$archive"
pm2 stop demo-product-hunter-worker --silent
tar -xzf "$archive" -C /var/www/product-hunter
pm2 restart demo-product-hunter-api demo-product-hunter-worker --silent
echo 'Previous code restored; additive schema and saved research preserved.'
