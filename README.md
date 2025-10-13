# Data Quality Duplicate Check Action

This repository contains a GitHub Action that automatically detects duplicate data quality checks when creating pull requests.

## Overview

The action prevents users from creating duplicate quality checks by:
- Parsing YAML check definitions in PRs
- Querying historical execution data from `all_scan_results`
- Comparing new checks against existing ones
- Posting warnings as PR comments

## Setup

### 1. Configure Secrets

Add these secrets to your GitHub repository:
- `DATABRICKS_HOST`: Your Databricks workspace URL
- `DATABRICKS_TOKEN`: Personal access token for Databricks
- `DATABRICKS_HTTP_PATH`: SQL warehouse HTTP path

### 2. How It Works

When a PR is created with YAML file changes:
1. GitHub Action triggers automatically
2. Python script parses new check definitions
3. Queries Databricks for existing checks on the same tables
4. Generates a report of potential duplicates
5. Posts report as PR comment (if duplicates found)

### 3. Usage

Simply create a PR with your YAML check definitions. The action will:
- ✅ Automatically detect duplicates
- 💬 Comment on the PR with findings
- ⚠️ Optionally block merging if critical duplicates found

## Files

- `.github/workflows/check-duplicates.yml`: GitHub Action workflow
- `.github/scripts/check_duplicate_checks.py`: Duplicate detection logic

## Example Output

When duplicates are found, you'll see a PR comment like:

```markdown
## ⚠️ Duplicate Quality Checks Detected

Found **2** potential duplicate(s):

### 🔄 Table: `customer_transactions`
**New Check:** `row_count`
... existing check details ...
```

## Contributing

Contributions welcome! Please test locally before submitting PRs.

