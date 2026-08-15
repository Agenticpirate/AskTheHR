#!/bin/bash
set -u
RAW=/workspace/jobs/raw
NORM=/workspace/jobs/normalized
LOG=$RAW/himalayas_country_log.txt
JSONL=$NORM/himalayas.jsonl
UA="Mozilla/5.0 (compatible; JobCollector/1.0)"
BASE="https://himalayas.app/jobs/api/search"

log() {
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$ts $*" | tee -a "$LOG"
}

sleep_polite() {
  # 120–250ms
  python3 - <<'PY' 2>/dev/null || sleep 0.15
import random, time
time.sleep(random.uniform(0.12, 0.25))
PY
}

fetch_page() {
  local url="$1"
  local out="$2"
  local tmp="${out}.tmp"
  local code
  code=$(curl -sS -A "$UA" -H "Accept: application/json" -o "$tmp" -w "%{http_code}" --max-time 45 "$url" || echo "000")
  if [ "$code" = "429" ]; then
    log "429 $url wait 60s then retry"
    sleep 60
    code=$(curl -sS -A "$UA" -H "Accept: application/json" -o "$tmp" -w "%{http_code}" --max-time 45 "$url" || echo "000")
    if [ "$code" = "429" ]; then
      log "429-again $url"
      rm -f "$tmp"
      echo "$code"
      return 1
    fi
  fi
  if [ "$code" != "200" ]; then
    log "ERR status=$code url=$url"
    rm -f "$tmp"
    echo "$code"
    return 1
  fi
  mv "$tmp" "$out"
  echo "$code"
  return 0
}

page_country() {
  local cc="$1"
  local extra_qs="${2:-}"
  local suffix="${3:-}"
  local page=1
  local total=""
  local jobs_sum=0
  local pages=0
  local empty=0
  local prefix="himalayas_${cc,,}"
  if [ -n "$suffix" ]; then
    prefix="himalayas_${cc,,}_${suffix}"
  fi

  # resume: find next missing page
  while [ -f "$RAW/${prefix}_p${page}.json" ] && [ "$(stat -c%s "$RAW/${prefix}_p${page}.json" 2>/dev/null || echo 0)" -gt 20 ]; do
    local n tc
    n=$(jq -r '.jobs | length' "$RAW/${prefix}_p${page}.json" 2>/dev/null || echo 0)
    tc=$(jq -r '.totalCount // 0' "$RAW/${prefix}_p${page}.json" 2>/dev/null || echo 0)
    [ -z "$total" ] && total=$tc
    jobs_sum=$((jobs_sum + n))
    pages=$((pages + 1))
    if [ "$n" = "0" ]; then
      empty=$((empty + 1))
      if [ "$empty" -ge 2 ]; then
        echo "$total $pages $jobs_sum"
        return 0
      fi
    else
      empty=0
    fi
    if [ -n "$total" ] && [ "$total" != "0" ] && [ $((page * 20)) -ge "$total" ]; then
      echo "$total $pages $jobs_sum"
      return 0
    fi
    page=$((page + 1))
  done

  while true; do
    local out="$RAW/${prefix}_p${page}.json"
    local url="${BASE}?country=${cc}&sort=recent&page=${page}"
    if [ -n "$extra_qs" ]; then
      url="${url}&${extra_qs}"
    fi
    if [ -f "$out" ] && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" -gt 20 ]; then
      :
    else
      if ! fetch_page "$url" "$out" >/dev/null; then
        echo "$total $pages $jobs_sum"
        return 1
      fi
    fi
    local n tc
    n=$(jq -r '.jobs | length' "$out" 2>/dev/null || echo 0)
    tc=$(jq -r '.totalCount // 0' "$out" 2>/dev/null || echo 0)
    [ -z "$total" ] && total=$tc
    jobs_sum=$((jobs_sum + n))
    pages=$((pages + 1))
    log "OK ${cc} ${suffix:-country} page=${page} jobs=${n} totalCount=${tc} saved=$(basename "$out")"
    if [ "$n" = "0" ]; then
      empty=$((empty + 1))
      if [ "$empty" -ge 2 ]; then
        break
      fi
    else
      empty=0
    fi
    if [ -n "$total" ] && [ "$total" != "0" ] && [ $((page * 20)) -ge "$total" ]; then
      break
    fi
    if [ "$n" -lt 20 ]; then
      break
    fi
    page=$((page + 1))
    sleep_polite
  done
  echo "$total $pages $jobs_sum"
  return 0
}

probe_city_param() {
  local cc="$1"
  local city="$2"
  local param tc n
  for param in location city q query; do
    local tmp="$RAW/_probe_${cc}_${param}.json"
    local url="${BASE}?country=${cc}&sort=recent&page=1&${param}=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$city" 2>/dev/null || echo "$city")"
    if ! fetch_page "$url" "$tmp" >/dev/null; then
      log "PROBE city ${cc} ${city} param=${param} FAIL"
      continue
    fi
    tc=$(jq -r '.totalCount // 0' "$tmp")
    n=$(jq -r '.jobs | length' "$tmp")
    log "PROBE city ${cc} ${city} param=${param} totalCount=${tc} njobs=${n}"
    echo "$param $tc"
    return 0
  done
  echo "none 0"
  return 1
}

log "START bash collector using /jobs/api/search page= 1-based"
log "NOTE browse /jobs/api?country= ignores filter (100k). search IN totalCount=7068 confirmed"

# ---------- INDIA (must complete) ----------
log "==== COUNTRY IN India ===="
IN_RES=$(page_country IN)
log "DONE IN $IN_RES"

# merge + combine after India is done by the parent python merge later
# continue countries
for spec in "NL" "FR" "AU" "SG" "IE" "GB" "CA" "DE"; do
  log "==== COUNTRY $spec ===="
  RES=$(page_country "$spec")
  log "DONE $spec $RES"
done

log "FINISH paging"
