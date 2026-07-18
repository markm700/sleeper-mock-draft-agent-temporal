#!/usr/bin/env bash
# ==============================================================================
# Sleeper Mock Draft Agent — API Script
# Executes the full workflow pipeline via FastAPI (localhost:8002)
# ==============================================================================
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8002}"
USERNAME="${SLEEPER_USERNAME:-markm700}"
LEAGUE_NAME="${SLEEPER_LEAGUE_NAME:-DTA Jehovahs}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─── Helpers ──────────────────────────────────────────────────────────────────

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }
info()  { echo -e "${CYAN}[→]${NC} $1"; }

api_call() {
    local method="$1"
    local endpoint="$2"
    shift 2
    local url="${BASE_URL}${endpoint}"

    info "${method} ${url}"
    local response
    response=$(curl -s -w "\n%{http_code}" -X "${method}" "${url}" \
        -H "Content-Type: application/json" "$@")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        log "HTTP ${http_code}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        err "HTTP ${http_code}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
    echo ""
}

usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  health              Health check
  status              Worker service status

  --- Data Collection ---
  collect-all         Run full data collection (team owners + league + drafts + players)
  collect-players     Run player data collection only
  collect-team-owner  Run team owner data collection

  --- Model Training ---
  train-league        Train models for all owners in a league
  train-owner         Train model for a single owner

  --- Model Management ---
  models              List all models
  model-status        Get model status
  model-build         Build a model scaffold
  model-rebuild       Force rebuild a model
  model-delete        Delete a model
  model-manage        Generic model management action

  --- Prediction ---
  predict             Run a draft pick prediction
  simulate-draft      Run a full mock draft simulation using trained models

  --- Full Pipeline ---
  pipeline            Run the full pipeline: collect → train → verify

Environment:
  API_BASE_URL         Base URL (default: http://localhost:8002)
  SLEEPER_USERNAME     Sleeper username (default: markm700)
  SLEEPER_LEAGUE_NAME  Sleeper league name (default: DTA Jehovahs)

EOF
}

# ─── Commands ─────────────────────────────────────────────────────────────────

cmd_health() {
    api_call GET "/healthz"
}

cmd_status() {
    api_call GET "/healthz/data-collection-worker-service/status"
}

cmd_collect_all() {
    local user="${1:-$USERNAME}"
    local league="${2:-$LEAGUE_NAME}"
    warn "Running full data collection (this may take a few minutes)..."
    api_call POST "/full-data-collection/run?username=$(urlencode "$user")&league_name=$(urlencode "$league")"
}

cmd_collect_players() {
    api_call POST "/player-data-collection/run"
}

cmd_collect_team_owner() {
    local user="${1:-$USERNAME}"
    local league="${2:-$LEAGUE_NAME}"
    api_call POST "/team-owner-data-collection/run?username=$(urlencode "$user")&league_name=$(urlencode "$league")"
}

cmd_train_league() {
    local league_id="${1:?Error: league_id required. Usage: $0 train-league <league_id> [season]}"
    local season="${2:-}"
    local url="/league-model-training/run?league_id=${league_id}"
    [[ -n "$season" ]] && url="${url}&season=${season}"
    warn "Training models for all owners in league ${league_id}..."
    api_call POST "$url"
}

cmd_train_owner() {
    local league_id="${1:?Error: league_id required. Usage: $0 train-owner <league_id> <user_id> [model_name]}"
    local user_id="${2:?Error: user_id required. Usage: $0 train-owner <league_id> <user_id> [model_name]}"
    local model_name="${3:-}"
    local url="/model-training/run?league_id=${league_id}&user_id=${user_id}"
    [[ -n "$model_name" ]] && url="${url}&model_name=${model_name}"
    api_call POST "$url"
}

cmd_models() {
    api_call GET "/models"
}

cmd_model_status() {
    local model_name="${1:?Error: model_name required. Usage: $0 model-status <model_name>}"
    api_call GET "/models/${model_name}/status"
}

cmd_model_build() {
    local model_name="${1:?Error: model_name required. Usage: $0 model-build <model_name>}"
    api_call POST "/models/${model_name}/build"
}

cmd_model_rebuild() {
    local model_name="${1:?Error: model_name required. Usage: $0 model-rebuild <model_name>}"
    api_call POST "/models/${model_name}/rebuild"
}

cmd_model_delete() {
    local model_name="${1:?Error: model_name required. Usage: $0 model-delete <model_name>}"
    api_call DELETE "/models/${model_name}"
}

cmd_model_manage() {
    local model_name="${1:?Error: model_name required. Usage: $0 model-manage <model_name> <action>}"
    local action="${2:?Error: action required (build|rebuild|status|list|delete)}"
    api_call POST "/model-management/run?model_name=${model_name}&action=${action}"
}

cmd_predict() {
    local model_name="${1:?Error: model_name required. Usage: $0 predict <model_name> <user_id> <json_body_file>}"
    local user_id="${2:?Error: user_id required}"
    local body_file="${3:?Error: JSON body file required (with player_ids, draft_context, owner_profile)}"

    if [[ ! -f "$body_file" ]]; then
        err "File not found: $body_file"
        return 1
    fi

    api_call POST "/model-prediction/run?model_name=${model_name}&user_id=${user_id}" \
        -d @"$body_file"
}

cmd_simulate_draft() {
    local league_id="${1:?Error: league_id required. Usage: $0 simulate-draft <league_id> [additional_league_ids...]}"
    shift

    local url="/mock-draft-simulation/run?league_id=${league_id}"

    # Remaining args are additional league IDs
    for lid in "$@"; do
        url="${url}&additional_league_ids=${lid}"
    done

    warn "Running full mock draft simulation (this may take several minutes)..."
    info "League: ${league_id}"
    [[ $# -gt 0 ]] && info "Historical leagues: $*"

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}${url}" \
        -H "Content-Type: application/json")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        log "HTTP ${http_code} — Mock draft simulation complete!"
        echo ""

        # Pretty-print the draft board
        echo "$body" | python3 -c "
import sys, json

data = json.load(sys.stdin)
result = data.get('result', data)
board = result.get('draft_board', [])
summary = result.get('summary_by_owner', {})

if not board:
    print('No draft picks generated.')
    sys.exit(0)

print(f\"{'='*70}\")
print(f\"  MOCK DRAFT RESULTS — {result.get('num_picks', 0)} picks, {result.get('num_rounds', 0)} rounds\")
print(f\"  Draft Type: {result.get('draft_type', 'snake')} | Teams: {result.get('num_teams', 0)}\")
print(f\"{'='*70}\")
print()
print(f\"{'Pick':<5} {'Round':<6} {'Owner':<18} {'Player':<28} {'Pos':<5} {'Team':<5} {'ADP':<6}\")
print(f\"{'-'*70}\")

for pick in board:
    name = (pick.get('player_name') or 'Unknown')[:27]
    owner = (pick.get('display_name') or 'Unknown')[:17]
    print(f\"{pick['pick_no']:<5} {pick['round']:<6} {owner:<18} {name:<28} {pick.get('position',''):<5} {pick.get('team',''):<5} {pick.get('adp', 999):<6.1f}\")

print()
print(f\"{'='*70}\")
print('  TEAM SUMMARIES')
print(f\"{'='*70}\")
for uid, info in summary.items():
    positions = info.get('positions_drafted', [])
    pos_counts = {}
    for p in positions:
        pos_counts[p] = pos_counts.get(p, 0) + 1
    pos_str = ', '.join(f'{k}:{v}' for k, v in sorted(pos_counts.items()))
    print(f\"  {info['display_name']:<18} (slot {info['draft_slot']}) — {pos_str}\")
print()
" 2>/dev/null || echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        err "HTTP ${http_code}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
    echo ""
}

cmd_pipeline() {
    local user="${1:-$USERNAME}"
    local league="${2:-$LEAGUE_NAME}"

    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "  FULL PIPELINE: collect → train → verify"
    echo "  User: ${user} | League: ${league}"
    echo "════════════════════════════════════════════════════════"
    echo ""

    # Step 0: Health check
    info "Step 0: Health check"
    api_call GET "/healthz" || { err "API not reachable at ${BASE_URL}"; exit 1; }

    # Step 1: Full data collection
    info "Step 1: Full data collection"
    warn "This collects team owners, leagues, drafts, and players..."
    local collect_result
    collect_result=$(curl -s -X POST "${BASE_URL}/full-data-collection/run?username=$(urlencode "$user")&league_name=$(urlencode "$league")" \
        -H "Content-Type: application/json")
    log "Data collection complete"
    echo "$collect_result" | python3 -m json.tool 2>/dev/null || echo "$collect_result"
    echo ""

    # Extract league_id and all_league_ids from result
    local league_id
    local additional_league_ids
    league_id=$(echo "$collect_result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
# Primary: use top-level league_id
if 'league_id' in result:
    print(result['league_id'])
else:
    print('')
" 2>/dev/null)

    additional_league_ids=$(echo "$collect_result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
all_ids = result.get('all_league_ids', [])
primary = result.get('league_id', '')
# Exclude the primary league_id — these are the historical ones
others = [lid for lid in all_ids if lid != primary]
if others:
    # Format as query params: &additional_league_ids=X&additional_league_ids=Y
    print('&'.join(f'additional_league_ids={lid}' for lid in others))
else:
    print('')
" 2>/dev/null)

    if [[ -z "$league_id" ]]; then
        warn "Could not auto-extract league_id from response."
        echo "Please provide league_id manually:"
        read -r league_id
    fi

    if [[ -z "$league_id" ]]; then
        err "No league_id — cannot continue to training."
        exit 1
    fi

    log "Using league_id: ${league_id}"
    if [[ -n "$additional_league_ids" ]]; then
        log "Including historical leagues for training data"
    fi
    echo ""

    # Step 2: Train all owner models (with historical league data)
    info "Step 2: Training models for all owners in league (including historical seasons)..."
    local train_url="/league-model-training/run?league_id=${league_id}"
    [[ -n "$additional_league_ids" ]] && train_url="${train_url}&${additional_league_ids}"
    api_call POST "$train_url" || {
        err "Training failed"; exit 1
    }

    # Step 3: Verify models
    info "Step 3: Listing trained models"
    api_call GET "/models"

    # Step 4: Run mock draft simulation
    info "Step 4: Running mock draft simulation..."
    local sim_url="/mock-draft-simulation/run?league_id=${league_id}"
    [[ -n "$additional_league_ids" ]] && sim_url="${sim_url}&${additional_league_ids}"
    cmd_simulate_draft "${league_id}" $(echo "$collect_result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
all_ids = result.get('all_league_ids', [])
primary = result.get('league_id', '')
others = [lid for lid in all_ids if lid != primary]
print(' '.join(others))
" 2>/dev/null)

    echo ""
    log "Pipeline complete! Mock draft simulation finished."
    echo ""
    echo "  To re-run simulation: $0 simulate-draft ${league_id} <historical_ids...>"
    echo ""
}

# ─── URL Encoding Helper ─────────────────────────────────────────────────────

urlencode() {
    python3 -c "import urllib.parse; print(urllib.parse.quote('$1', safe=''))"
}

# ─── Main ─────────────────────────────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

command="$1"
shift

case "$command" in
    health)             cmd_health "$@" ;;
    status)             cmd_status "$@" ;;
    collect-all)        cmd_collect_all "$@" ;;
    collect-players)    cmd_collect_players "$@" ;;
    collect-team-owner) cmd_collect_team_owner "$@" ;;
    train-league)       cmd_train_league "$@" ;;
    train-owner)        cmd_train_owner "$@" ;;
    models)             cmd_models "$@" ;;
    model-status)       cmd_model_status "$@" ;;
    model-build)        cmd_model_build "$@" ;;
    model-rebuild)      cmd_model_rebuild "$@" ;;
    model-delete)       cmd_model_delete "$@" ;;
    model-manage)       cmd_model_manage "$@" ;;
    predict)            cmd_predict "$@" ;;
    simulate-draft|sim)     cmd_simulate_draft "$@" ;;
    pipeline|-p)           cmd_pipeline "$@" ;;
    help|--help|-h)     usage ;;
    *)
        err "Unknown command: ${command}"
        usage
        exit 1
        ;;
esac
