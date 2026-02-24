#!/usr/bin/env python3
import sys
import yaml
import os
from databricks import sql
from typing import Dict, List, Set
from collections import defaultdict

def parse_yaml_file(file_path: str) -> Dict:
    """Parse a YAML check definition file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def extract_checks_from_yaml(yaml_data: Dict) -> List[Dict]:
    """Extract table and check information from YAML."""
    checks = []
    
    table_name = yaml_data.get('table-name', '')
    definition = yaml_data.get('definition', '')
    
    if not table_name:
        return checks
    
    # Parse check definitions (simplified - adjust based on your YAML structure)
    if isinstance(definition, str):
        # Parse string-based definitions
        for line in definition.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                checks.append({
                    'table': table_name,
                    'check_type': line.split(':')[0].strip('- '),
                    'definition': line
                })
    
    return checks

def query_existing_checks(connection, table_names: Set[str]) -> Dict[str, List[str]]:
    """Query all_scan_results for existing checks on these tables."""
    if not table_names:
        return {}
    
    table_list = "', '".join(table_names)
    
    query = f"""
    SELECT DISTINCT
        dataset_name,
        check_name,
        check_type,
        COUNT(*) as execution_count,
        MAX(scan_time) as last_execution
    FROM all_scan_results
    WHERE dataset_name IN ('{table_list}')
    GROUP BY dataset_name, check_name, check_type
    ORDER BY dataset_name, check_name
    """
    
    cursor = connection.cursor()
    cursor.execute(query)
    
    results = defaultdict(list)
    for row in cursor.fetchall():
        results[row[0]].append({
            'check_name': row[1],
            'check_type': row[2],
            'execution_count': row[3],
            'last_execution': row[4]
        })
    
    cursor.close()
    return dict(results)

def check_for_duplicates(new_checks: List[Dict], existing_checks: Dict) -> List[Dict]:
    """Compare new checks against existing ones."""
    duplicates = []
    
    for check in new_checks:
        table = check['table']
        check_type = check['check_type']
        
        if table in existing_checks:
            for existing in existing_checks[table]:
                # Check if similar check already exists
                if check_type.lower() in existing['check_name'].lower() or \
                   check_type.lower() in existing['check_type'].lower():
                    duplicates.append({
                        'new_check': check,
                        'existing_check': existing,
                        'severity': 'warning'
                    })
    
    return duplicates

def generate_report(duplicates: List[Dict], output_file: str = 'duplicate_report.md'):
    """Generate markdown report for PR comment."""
    if not duplicates:
        with open(output_file, 'w') as f:
            f.write("✅ **No duplicate checks detected!**\n")
        return False
    
    report = ["## ⚠️ Duplicate Quality Checks Detected\n"]
    report.append(f"Found **{len(duplicates)}** potential duplicate(s):\n")
    
    for dup in duplicates:
        new = dup['new_check']
        existing = dup['existing_check']
        
        report.append(f"### 🔄 Table: `{new['table']}`\n")
        report.append(f"**New Check:** `{new['check_type']}`\n")
        report.append(f"```yaml\n{new['definition']}\n```\n")
        report.append(f"**Existing Check:** `{existing['check_name']}`\n")
        report.append(f"- Type: `{existing['check_type']}`\n")
        report.append(f"- Executions: {existing['execution_count']}\n")
        report.append(f"- Last run: {existing['last_execution']}\n")
        report.append("---\n")
    
    report.append("\n**Action Required:** Please review if these checks are truly duplicates. ")
    report.append("If intentional, add a comment explaining why.\n")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: check_duplicate_checks.py <changed_files_list>")
        sys.exit(1)
    
    # Read changed files
    with open(sys.argv[1], 'r') as f:
        changed_files = [line.strip() for line in f if line.strip()]
    
    if not changed_files:
        print("No YAML files changed")
        sys.exit(0)
    
    # Parse new checks from changed files
    all_new_checks = []
    table_names = set()
    
    for file_path in changed_files:
        if os.path.exists(file_path):
            yaml_data = parse_yaml_file(file_path)
            checks = extract_checks_from_yaml(yaml_data)
            all_new_checks.extend(checks)
            if yaml_data.get('table-name'):
                table_names.add(yaml_data['table-name'])
    
    print(f"Found {len(all_new_checks)} new checks for {len(table_names)} tables")
    
    # Query Databricks for existing checks
    connection = sql.connect(
        server_hostname=os.environ['DATABRICKS_HOST'],
        http_path=os.environ['DATABRICKS_HTTP_PATH'],
        access_token=os.environ['DATABRICKS_TOKEN']
    )
    
    existing_checks = query_existing_checks(connection, table_names)
    connection.close()
    
    print(f"Found existing checks for {len(existing_checks)} tables")
    
    # Check for duplicates
    duplicates = check_for_duplicates(all_new_checks, existing_checks)
    
    # Generate report
    has_duplicates = generate_report(duplicates)
    
    # Set GitHub Actions outputs
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"has_duplicates={'true' if has_duplicates else 'false'}\n")

    print(f"Duplicate check complete: {len(duplicates)} potential duplicates found")

if __name__ == '__main__':
    main()

