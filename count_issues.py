import json

def load_issues(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def count_unique_issues(issues):
    unique_issues = set()
    for issue in issues:
        # Assuming each issue has a unique URL which can be used as a unique identifier
        unique_issues.add(issue['url'])
    return len(unique_issues)

def main():
    issues = load_issues('all_issues.json')
    unique_count = count_unique_issues(issues)
    print(f"Total unique issues: {unique_count}")

if __name__ == "__main__":
    main()