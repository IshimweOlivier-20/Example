#!/bin/bash
# Automated security scanning and testing script
# Run: ./run_security_tests.sh

set -e

echo "=========================================="
echo "IshemaLink Security & Testing Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Dependency Security Check
echo -e "${YELLOW}[1/6] Checking dependencies for known vulnerabilities...${NC}"
safety check --json || echo -e "${RED}Warning: Vulnerabilities found in dependencies${NC}"
echo ""

# 2. Python Security Linting
echo -e "${YELLOW}[2/6] Running Bandit security linter...${NC}"
bandit -r . -c .bandit -f txt || echo -e "${RED}Warning: Security issues found${NC}"
echo ""

# 3. SQL Injection Testing
echo -e "${YELLOW}[3/6] Checking for SQL injection vulnerabilities...${NC}"
python manage.py check --deploy
echo ""

# 4. Unit Tests with Coverage
echo -e "${YELLOW}[4/6] Running unit tests with coverage...${NC}"
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=85
echo ""

# 5. Integration Tests
echo -e "${YELLOW}[5/6] Running integration tests...${NC}"
python manage.py test --parallel --keepdb
echo ""

# 6. Load Testing (Optional - requires running server)
echo -e "${YELLOW}[6/6] Load testing (skipped - run manually with Locust)${NC}"
echo "To run load test: locust -f tests/locustfile.py --host=http://localhost:8000"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Security & Testing Suite Complete${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review coverage report: open htmlcov/index.html"
echo "2. Fix any security warnings from Bandit"
echo "3. Update vulnerable dependencies"
echo "4. Run load test before production deployment"
echo ""
