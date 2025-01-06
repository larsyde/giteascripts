import requests
import json
import re

GITEA_URL = "https://gitea.xxx.net"  # Replace with your Gitea instance URL
TOKEN = "a61f2xxxxxxxxxxxxxxx40408496b7882f2"  # Replace with your personal access token
HEADERS = {"Authorization": f"token {TOKEN}"}

def get_users():
    users = []
    page = 1
    while True:
        response = requests.get(f"{GITEA_URL}/api/v1/admin/users", 
                                headers=HEADERS, 
                                params={"page": page, "limit": 50})
        if response.status_code == 200:
            current_page_users = response.json()
            if not current_page_users:
                break
            users.extend(current_page_users)
            page += 1
        else:
            print(f"Failed to fetch users: {response.status_code}")
            break
    return users

def get_orgs():
    orgs = []
    page = 1
    while True:
        response = requests.get(f"{GITEA_URL}/api/v1/orgs", 
                                headers=HEADERS, 
                                params={"page": page, "limit": 50})
        if response.status_code == 200:
            current_page_orgs = response.json()
            if not current_page_orgs:
                break
            orgs.extend(current_page_orgs)
            page += 1
        else:
            print(f"Failed to fetch organizations: {response.status_code}")
            break
    return orgs

def get_repos(owner_type, owner_name):
    repos = []
    page = 1
    while True:
        response = requests.get(f"{GITEA_URL}/api/v1/{owner_type}/{owner_name}/repos", 
                                headers=HEADERS, 
                                params={"page": page, "limit": 50})
        if response.status_code == 200:
            current_page_repos = response.json()
            if not current_page_repos:
                break
            repos.extend(current_page_repos)
            page += 1
        else:
            print(f"Failed to fetch repositories for {owner_name}: {response.status_code}")
            break
    return repos

def get_issues(owner, repo, state):
    issues = []
    page = 1
    while True:
        response = requests.get(f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/issues", 
                                headers=HEADERS, 
                                params={"state": state, "page": page, "limit": 50})
        if response.status_code != 200:
            print(f"Failed to fetch issues for {owner}/{repo}: {response.status_code}")
            break
        
        current_page_issues = response.json()
        if not current_page_issues:
            break

        issues.extend(current_page_issues)
        page += 1
    
    return issues

def filter_issue(issue, repo_name):
    return {
        "url": issue.get("html_url", ""),
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "created_at": issue.get("created_at", ""),
        "updated_at": issue.get("updated_at", ""),
        "repository": repo_name
    }

def clean_issue_body(body):
    if not body:
        return ""

    # Remove stack traces (assuming they start with "at " or "Traceback" and go until the end of the line)
    body = re.sub(r'(?m)^(at .+|Traceback.*|File .+|\t.*|\s+at .+|\s+File .+)+$', '', body)
    
    # Remove long sequences of non-alphabetic characters that are unlikely to be human-written (e.g., code, logs)
    body = re.sub(r'[^a-zA-Z\s]{10,}', '', body)
    
    # Remove multiple empty lines
    body = re.sub(r'\n\s*\n', '\n', body)
    
    # Strip leading/trailing whitespace
    return body.strip()

def save_filtered_issues_per_repo(owner_name, repo_name, filtered_issues):
    file_name = f"open_filtered_issues_{owner_name}_{repo_name}.json"
    with open(file_name, "w") as f:
        json.dump(filtered_issues, f, indent=4)
    print(f"Saved filtered open issues for {owner_name}/{repo_name} to {file_name}")

def main():
    open_issues = []
    closed_issues = []
    filtered_open_issues = []
    filtered_closed_issues = []
    cleaned_body_texts = []

    users = get_users()
    for user in users:
        user_name = user['username']
        print(f"Fetching repositories for user: {user_name}...")
        repos = get_repos('users', user_name)
        for repo in repos:
            repo_name = repo['name']
            print(f"Fetching issues for {user_name}/{repo_name}...")
            
            open_repo_issues = get_issues(user_name, repo_name, "open")
            closed_repo_issues = get_issues(user_name, repo_name, "closed")

            open_issues.extend(open_repo_issues)
            closed_issues.extend(closed_repo_issues)
            
            filtered_repo_open_issues = [filter_issue(issue, repo_name) for issue in open_repo_issues]
            filtered_open_issues.extend(filtered_repo_open_issues)

            filtered_closed_issues.extend([filter_issue(issue, repo_name) for issue in closed_repo_issues])

            save_filtered_issues_per_repo(user_name, repo_name, filtered_repo_open_issues)

            cleaned_body_texts.extend([clean_issue_body(issue.get("body", "")) for issue in open_repo_issues])

    orgs = get_orgs()
    for org in orgs:
        org_name = org['username']
        print(f"Fetching repositories for organization: {org_name}...")
        repos = get_repos('orgs', org_name)
        for repo in repos:
            repo_name = repo['name']
            print(f"Fetching issues for {org_name}/{repo_name}...")
            
            open_repo_issues = get_issues(org_name, repo_name, "open")
            closed_repo_issues = get_issues(org_name, repo_name, "closed")

            open_issues.extend(open_repo_issues)
            closed_issues.extend(closed_repo_issues)
            
            filtered_repo_open_issues = [filter_issue(issue, repo_name) for issue in open_repo_issues]
            filtered_open_issues.extend(filtered_repo_open_issues)

            filtered_closed_issues.extend([filter_issue(issue, repo_name) for issue in closed_repo_issues])

            save_filtered_issues_per_repo(org_name, repo_name, filtered_repo_open_issues)

            cleaned_body_texts.extend([clean_issue_body(issue.get("body", "")) for issue in open_repo_issues])

    with open("open_issues.json", "w") as f:
        json.dump(open_issues, f, indent=4)

    with open("closed_issues.json", "w") as f:
        json.dump(closed_issues, f, indent=4)

    with open("filtered_open_issues.json", "w") as f:
        json.dump(filtered_open_issues, f, indent=4)

    with open("filtered_closed_issues.json", "w") as f:
        json.dump(filtered_closed_issues, f, indent=4)

    with open("cleaned_issue_bodies.txt", "w", encoding="utf-8") as f:
        for body in cleaned_body_texts:
            f.write(f"{body}\n")

    print(f"Total number of open issues: {len(open_issues)}")
    print(f"Total number of closed issues: {len(closed_issues)}")
    print(f"Total number of filtered open issues: {len(filtered_open_issues)}")
    print(f"Total number of filtered closed issues: {len(filtered_closed_issues)}")
    print(f"Total number of cleaned issue bodies saved: {len(cleaned_body_texts)}")

if __name__ == "__main__":
    main()