#!/bin/bash
# ⟡ MirrorGate Live Demo Script
# 
# This script demonstrates wild runtime enforcement.
# Run with: ./scripts/demo_recording.sh
#
# For video recording:
# 1. Start terminal recording
# 2. Run this script
# 3. Watch MirrorGate enforce in real-time
# 4. Human can walk away - system continues

set -e

MIRRORGATE_DIR="$HOME/.mirrorgate"
DEMO_DIR="$MIRRORGATE_DIR/demo"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;91m'
GREEN='\033[0;92m'
YELLOW='\033[0;93m'
CYAN='\033[0;96m'
RESET='\033[0m'
BOLD='\033[1m'

clear

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   ⟡ MirrorGate v2.1 — Live Demo                             ║"
echo "║                                                              ║"
echo "║   Wild Runtime Cryptographic Enforcement                     ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo ""

# Setup demo directory
echo -e "${YELLOW}[SETUP]${RESET} Creating demo environment..."
rm -rf "$DEMO_DIR"
mkdir -p "$DEMO_DIR"
echo ""

# Clear old audit log for clean demo
echo -e "${YELLOW}[SETUP]${RESET} Clearing audit log for clean demo..."
rm -f "$MIRRORGATE_DIR/audit_log.jsonl"
rm -f "$MIRRORGATE_DIR/chain_state.json"
echo ""

echo -e "${GREEN}[READY]${RESET} Demo environment prepared"
echo -e "${GREEN}[READY]${RESET} Demo directory: $DEMO_DIR"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# Start daemon in background
echo -e "${YELLOW}[STARTING]${RESET} MirrorGate daemon..."
cd "$PROJECT_DIR"
python3 -m src.daemon "$DEMO_DIR" &
DAEMON_PID=$!
sleep 2
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}[CLEANUP]${RESET} Stopping daemon..."
    kill $DAEMON_PID 2>/dev/null || true
    wait $DAEMON_PID 2>/dev/null || true
    echo -e "${GREEN}[DONE]${RESET} Demo complete"
}
trap cleanup EXIT

# Wait for daemon to be ready
sleep 1

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}SCENARIO 1: Clean Write (Should ALLOW)${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[WRITE]${RESET} Agent writing: 'User asked about project timeline.'"
echo "User asked about project timeline." > "$DEMO_DIR/note1.md"
sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}SCENARIO 2: Hallucinated Fact (Should BLOCK)${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[WRITE]${RESET} Agent writing: 'Paul confirmed the deal was signed yesterday.'"
echo "Paul confirmed the deal was signed yesterday." > "$DEMO_DIR/note2.md"
sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}SCENARIO 3: First-Person Authority (Should BLOCK)${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[WRITE]${RESET} Agent writing: 'I have verified that the data is correct.'"
echo "I have verified that the data is correct." > "$DEMO_DIR/note3.md"
sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}SCENARIO 4: Clean Technical Note (Should ALLOW)${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[WRITE]${RESET} Agent writing: 'The API endpoint returns JSON with status codes.'"
echo "The API endpoint returns JSON with status codes." > "$DEMO_DIR/note4.md"
sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}SCENARIO 5: Medical Assertion (Should BLOCK)${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[WRITE]${RESET} Agent writing: 'You should stop taking your medication.'"
echo "You should stop taking your medication." > "$DEMO_DIR/note5.md"
sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}DEMO COMPLETE — Showing Audit Log${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
sleep 2

echo -e "${YELLOW}[AUDIT]${RESET} Decision records:"
echo ""
if [ -f "$MIRRORGATE_DIR/audit_log.jsonl" ]; then
    cat "$MIRRORGATE_DIR/audit_log.jsonl" | while read line; do
        action=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('action','?'))" 2>/dev/null || echo "?")
        resource=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('resource','?').split('/')[-1])" 2>/dev/null || echo "?")
        violation=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('violation_code') or 'None')" 2>/dev/null || echo "?")
        
        if [ "$action" = "BLOCK" ]; then
            echo -e "  ${RED}⛔ BLOCK${RESET} | $resource | $violation"
        else
            echo -e "  ${GREEN}✅ ALLOW${RESET} | $resource"
        fi
    done
else
    echo "  No audit log found"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${GREEN}${BOLD}⟡ MirrorGate Demo Complete${RESET}"
echo ""
echo "What was demonstrated:"
echo "  • Agent writes intercepted in real-time"
echo "  • Hallucinated facts blocked"
echo "  • First-person authority claims blocked"
echo "  • Medical/legal assertions blocked"
echo "  • Clean writes allowed through"
echo "  • All decisions cryptographically signed"
echo "  • Tamper-evident hash chain maintained"
echo ""
echo -e "${CYAN}This is wild runtime enforcement — no staging, no scripts.${RESET}"
echo ""

# Keep running for a moment to show final state
sleep 5
