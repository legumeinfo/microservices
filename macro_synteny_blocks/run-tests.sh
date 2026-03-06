#!/bin/bash
#
# This script uses the base compose configuration from gcv-docker-compose and overlays
# test-specific configuration.
#
# The GCV_DOCKER_COMPOSE environment variable should point to the gcv-docker-compose
# directory (defaults to ../ - the parent directory).
#
# Usage:
#   ./run-tests.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compose file paths
# Use gcv-docker-compose directory for base configuration
GCV_DOCKER_COMPOSE="${GCV_DOCKER_COMPOSE:-../}"
COMPOSE_BASE="$GCV_DOCKER_COMPOSE/compose.yml"
COMPOSE_DEV="$GCV_DOCKER_COMPOSE/compose.dev.yml"
COMPOSE_TEST="compose.test.yml"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running macro_synteny_blocks tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify compose files exist
if [ ! -f "$COMPOSE_BASE" ]; then
    echo -e "${RED}Error: $COMPOSE_BASE not found${NC}"
    echo -e "${YELLOW}Set GCV_DOCKER_COMPOSE environment variable to the gcv-docker-compose directory${NC}"
    echo -e "${YELLOW}Default: ../ (parent directory)${NC}"
    exit 1
fi

if [ ! -f "$COMPOSE_DEV" ]; then
    echo -e "${RED}Error: $COMPOSE_DEV not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Using compose files from: ${GCV_DOCKER_COMPOSE}${NC}"

# Save current directory
ORIGINAL_DIR=$(pwd)

# Export paths for use in compose.test.yml
export MACRO_SYNTENY_BLOCKS_DIR="$ORIGINAL_DIR"
export TEST_DATA_DIR="$(dirname "$ORIGINAL_DIR")"  # Parent of macro_synteny_blocks

# Change to GCV docker compose directory for running compose
cd "$GCV_DOCKER_COMPOSE"

# Make compose.test.yml path absolute
COMPOSE_TEST_ABS="$ORIGINAL_DIR/compose.test.yml"

# Clean up any existing containers
echo -e "${YELLOW}Cleaning up existing containers...${NC}"
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" -f "$COMPOSE_TEST_ABS" --profile services down -v 2>/dev/null || true

# Build and run tests
echo -e "${YELLOW}Building and starting services...${NC}"
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" -f "$COMPOSE_TEST_ABS" --profile services up --build --abort-on-container-exit --exit-code-from macro_synteny_blocks_test

# Capture exit code
TEST_EXIT_CODE=$?

# Clean up
echo ""
echo -e "${YELLOW}Cleaning up...${NC}"
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" -f "$COMPOSE_TEST_ABS" --profile services down -v

# Return to original directory
cd "$ORIGINAL_DIR"

# Report results
echo ""
echo -e "${GREEN}========================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Tests passed!${NC}"
else
    echo -e "${RED}✗ Tests failed with exit code $TEST_EXIT_CODE${NC}"
fi
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Coverage report available in: ${YELLOW}./htmlcov/index.html${NC}"

exit $TEST_EXIT_CODE
