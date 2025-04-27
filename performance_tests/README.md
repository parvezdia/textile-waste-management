# Performance Testing Documentation

This directory contains performance testing scripts for the Textile Fabric Waste Management System using [Locust](https://locust.io/) - an open-source load testing tool.

## Overview

These tests are designed to evaluate the system's performance under various load conditions, specifically:

1. **Test 1:** Simulating 50 users submitting orders simultaneously
2. **Test 2:** Simulating 100 users viewing the transaction list

## Prerequisites

- Python 3.6+
- Locust 2.15.1+
- Faker library (for generating test data)

## Setup

Ensure you have installed all required packages:

```bash
pip install locust faker
```

## Running the Tests

### Web UI Mode

1. Start the Locust web interface by running:

```bash
cd performance_tests
locust
```

2. Open your browser and go to `http://localhost:8089/`
3. Configure your test:
   - **Number of users**: Set to 50 for Test 1 or 100 for Test 2
   - **Spawn rate**: How quickly users should be spawned (e.g., 5-10 users per second)
   - **Host**: The base URL of your application (e.g., `http://localhost:8000`)
4. Click "Start swarming" to begin the test

### Command-line Mode

Run specific test scenarios directly from the command line:

#### Test 1: 50 Users Submitting Orders

```bash
lcoust --host=http://localhost:8000 --tags order_submission --users 50 --spawn-rate 10 --run-time 5m --headless --csv=results_orders
```

#### Test 2: 100 Users Viewing Transaction List

```bash
locust --host=http://localhost:8000 --tags view_transactions --users 100 --spawn-rate 10 --run-time 5m --headless --csv=results_transactions
```

## Interpreting Results

After running the tests, Locust will provide detailed statistics:

- **Request Count**: Total number of requests made
- **Response Time**: Min, max, median, average, and percentiles
- **Requests Per Second**: The throughput of your system
- **Failure Rate**: Percentage of failed requests

### Key Metrics to Monitor

1. **Response Time**: 
   - < 200ms: Excellent
   - 200-500ms: Good
   - 500ms-1s: Acceptable
   - > 1s: Poor performance

2. **Error Rate**: 
   - Should be less than 1% in normal conditions
   - Any error rate above 5% indicates a serious issue

3. **Throughput**: 
   - Measure of how many requests your system can handle per second
   - Should align with your expected production load

## CSV Reports

When running in headless mode with the `--csv` flag, Locust will generate CSV files with detailed statistics that can be further analyzed or visualized.

## Performance Improvement Tips

If the tests reveal performance issues, consider these improvements:

1. **Database Optimization**:
   - Add indexes to frequently queried fields
   - Optimize complex queries

2. **Caching**:
   - Implement Redis or Memcached for frequently accessed data
   - Cache rendered templates and expensive computations

3. **Code Optimization**:
   - Profile your code to identify bottlenecks
   - Optimize database access patterns

4. **Infrastructure Scaling**:
   - Add more application servers
   - Increase database resources
   - Consider using load balancers