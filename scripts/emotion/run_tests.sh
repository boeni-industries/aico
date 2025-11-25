#!/bin/bash
# Quick test runner for emotion simulation tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BASE_URL="http://localhost:8771"
OUTPUT_DIR="./test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Help message
show_help() {
    cat << EOF
Emotion Simulation Test Runner

Usage: ./run_tests.sh <user_uuid> <pin> [options]

Arguments:
    user_uuid       User UUID for authentication
    pin             User PIN for authentication

Options:
    -u, --url       Backend URL (default: http://localhost:8771)
    -o, --output    Output directory (default: ./test_results)
    -s, --scenario  Scenario to run (default: default)
    -h, --help      Show this help message

Examples:
    ./run_tests.sh user_123 1234
    ./run_tests.sh user_123 1234 --url http://localhost:8771
    ./run_tests.sh user_123 1234 --output ./results --scenario default

EOF
}

# Parse arguments
if [ $# -lt 2 ]; then
    show_help
    exit 1
fi

USER_UUID=$1
PIN=$2
shift 2

SCENARIO="default"

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

OUTPUT_FILE="$OUTPUT_DIR/emotion_test_${TIMESTAMP}.json"

echo -e "${GREEN}Starting Emotion Simulation Tests${NC}"
echo "=================================="
echo "User UUID:  $USER_UUID"
echo "Backend:    $BASE_URL"
echo "Scenario:   $SCENARIO"
echo "Output:     $OUTPUT_FILE"
echo ""

# Check if backend is running
echo -e "${YELLOW}Checking backend availability...${NC}"
if ! curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Backend not reachable at $BASE_URL${NC}"
    echo "Please ensure the backend is running."
    exit 1
fi
echo -e "${GREEN}✓ Backend is running${NC}"
echo ""

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python3 scripts/emotion/test_emotion_simulation.py \
    "$USER_UUID" \
    "$PIN" \
    --base-url "$BASE_URL" \
    --scenario "$SCENARIO" \
    --output "$OUTPUT_FILE"

TEST_EXIT_CODE=$?

echo ""
echo "=================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Tests completed successfully${NC}"
    echo -e "Results saved to: ${GREEN}$OUTPUT_FILE${NC}"
    exit 0
else
    echo -e "${RED}✗ Tests failed${NC}"
    echo -e "Results saved to: ${YELLOW}$OUTPUT_FILE${NC}"
    exit 1
fi
