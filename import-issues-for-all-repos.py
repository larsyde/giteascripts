import requests
import json
import time
import sys
from difflib import get_close_matches
import argparse
import re
from datetime import datetime

# Add your Gitea and GitHub credentials
GITEA_URL = "https://gitea.xxxxx.net"  # Replace with your Gitea URL
GITEA_TOKEN = "a61f24f3efcc3xxxxxxxxxxxxxx6b7882f2"
GITHUB_TOKEN = "gitxxxxxx_11BJJ5JGA096otOmy6ZeOy_3SiShoTxxxxxxxxxxxxxxxxxxxxxxxxFVSZGo67OOqrU"      # Replace with your GitHub token
GITEA_HEADERS = {"Authorization": f"token {GITEA_TOKEN} "}  # Replace with your Gitea token
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Define the GitHub owner and repo where issues should be created
GITHUB_OWNER = "xxxx"  # Replace with the GitHub owner (user/org)

# Define the Gitea owner
GITEA_OWNER = "xxxxxx"  # Replace with the actual Gitea owner name

GRAPHQL_URL = "https://api.github.com/graphql"

import argparse


def get_issue_id(issue_number, repo):
    query = """
    query($owner: String!, $repo: String!, $issueNumber: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $issueNumber) {
          id
        }
      }
    }
    """
    variables = {
        "owner": GITHUB_OWNER,
        "repo": repo,
        "issueNumber": issue_number
    }
    
    response = requests.post(GRAPHQL_URL, headers=GITHUB_HEADERS, json={"query": query, "variables": variables})

    if response.status_code == 200:
        data = response.json()
        issue_id = data.get("data", {}).get("repository", {}).get("issue", {}).get("id")
        if issue_id:
            return issue_id
        else:
            print(f"Error: Could not find issue ID for issue #{issue_number}.")
            print(f"Response Text: {response.text}")
    else:
        print(f"Failed to fetch issue ID. Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")

    return None

def delete_github_issue(issue_number, repo):
    issue_id = get_issue_id(issue_number, repo)
    if not issue_id:
        return

    mutation = """
    mutation($input: DeleteIssueInput!) {
      deleteIssue(input: $input) {
        clientMutationId
      }
    }
    """
    variables = {
        "input": {
            "issueId": issue_id
        }
    }
    
    response = requests.post(GRAPHQL_URL, headers=GITHUB_HEADERS, json={"query": mutation, "variables": variables})

    print(f"Attempting to delete issue #{issue_number} at: {GRAPHQL_URL}")
    print(f"Request Method: POST")
    print(f"Request URL: {GRAPHQL_URL}")
    print(f"Request Payload: {json.dumps({'query': mutation, 'variables': variables}, indent=2)}")

    if response.status_code == 200:
        data = response.json()
        if data.get("data") and data["data"].get("deleteIssue"):
            print(f"Issue {issue_number} deleted successfully.")
        else:
            print(f"Error: Failed to delete issue {issue_number}.")
            print(f"Response Text: {response.text}")
    else:
        print(f"Failed to delete issue {issue_number}. Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")

    # Additional debugging info
    print(f"Response Headers: {response.headers}")

def delete_all_issues(owner, repo):
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {"state": "all", "per_page": 100, "page": page}
        response = requests.get(url, headers=GITHUB_HEADERS, params=params)

        print(f"Fetching issues for deletion from: {url} with params: {params}")
        if response.status_code == 200:
            issues = response.json()
            if not issues:
                break

            for issue in issues:
                if 'pull_request' not in issue:  # Skip pull requests
                    delete_github_issue(issue['number'], repo)
            
            page += 1
        else:
            print(f"Failed to fetch issues for deletion: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

def get_gitea_repos():
    repos = []
    page = 1
    while True:
        url = f"{GITEA_URL}/api/v1/user/repos"
        params = {"page": page, "limit": 100, "archived": True}
        response = requests.get(url, headers=GITEA_HEADERS, params=params)

        print(f"Fetching repositories from: {url} with params: {params}")
        if response.status_code != 200:
            print(f"Failed to fetch repositories: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

        current_page_repos = response.json()
        if not current_page_repos:
            break

        repos.extend(current_page_repos)
        page += 1

    # Extract and print the names of the repositories
    repo_names = [repo['name'] for repo in repos]
    print("List of repository names (including archived):")
    for name in repo_names:
        print(name)

    return repos

def get_github_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/user/repos"
        params = {"page": page, "per_page": 100}
        response = requests.get(url, headers=GITHUB_HEADERS, params=params)

        print(f"Fetching GitHub repositories from: {url} with params: {params}")
        if response.status_code != 200:
            print(f"Failed to fetch GitHub repositories: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

        current_page_repos = response.json()
        if not current_page_repos:
            break

        repos.extend(current_page_repos)
        page += 1

    return repos

def get_issues(owner, repo, state="open"):
    issues = []
    page = 1
    while True:
        url = f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/issues"
        params = {"state": state, "page": page, "limit": 50, "type": "issues"}
        response = requests.get(url, headers=GITEA_HEADERS, params=params)

        print(f"Fetching issues from: {url} with params: {params}")
        if response.status_code != 200:
            print(f"Failed to fetch issues for {owner}/{repo}: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

        current_page_issues = response.json()
        if not current_page_issues:
            break

        issues.extend(current_page_issues)
        page += 1

    return issues


def find_closest_github_repo(repo_name, github_repos):
    # First, check for an exact match
    for repo in github_repos:
        if repo['name'] == repo_name:
            print(f"Found exact match for Gitea repo '{repo_name}' with GitHub repo '{repo['name']}'")
            return repo
    
    # If no exact match, find the closest match
    repo_names = [repo['name'] for repo in github_repos]
    closest_match = get_close_matches(repo_name, repo_names, n=1)
    return next((repo for repo in github_repos if repo['name'] == closest_match[0]), None) if closest_match else None

def issue_exists(title, github_repo):
    page = 1
    per_page = 100
    while True:
        search_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{github_repo}/issues"
        params = {
            "state": "all",  # Include both open and closed issues
            "per_page": per_page,
            "page": page
        }
        response = requests.get(search_url, headers=GITHUB_HEADERS, params=params)

        print(f"Searching for existing issues at: {search_url} with params: {params}")
        if response.status_code == 200:
            existing_issues = response.json()
            if not existing_issues:
                # No more issues to check, we've reached the end of the list
                break

            # Normalize the title by stripping whitespace and converting to lowercase
            normalized_title = title.strip().lower()

            for issue in existing_issues:
                # Normalize the existing issue title
                existing_title = issue['title'].strip().lower()
             # for debugging only:   print(f"Comparing: '{existing_title}' with '{normalized_title}'")
                if existing_title == normalized_title:
                    print(f"Found existing issue with matching title: #{issue['number']} - '{issue['title']}' in GitHub repo {github_repo}")
                    return issue  # Return the full issue object for reference

            # Move to the next page
            page += 1
        else:
            print(f"Failed to search for existing issues: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

    return None


def fetch_collaborators_and_team_members(owner, repo, org, team_slug):
    collaborators_url = f"https://api.github.com/repos/{owner}/{repo}/collaborators"
    response = requests.get(collaborators_url, headers=GITHUB_HEADERS)

    print(f"Fetching collaborators from: {collaborators_url}")
    if response.status_code == 200:
        collaborators = [collab['login'] for collab in response.json()]
    else:
        print(f"Failed to fetch collaborators: {response.status_code}")
        print(f"Response Text: {response.text}")
        collaborators = []

    # Fetch team members
    team_members = fetch_team_members(org, team_slug)

    # Combine collaborators and team members
    return list(set(collaborators + team_members))


def normalize_username(username):
    # Normalize by converting to lowercase and removing non-alphanumeric characters
    return re.sub(r'\W+', '', username.lower())

def find_closest_github_user(username, valid_users):
    # Normalize the username
    normalized_username = normalize_username(username)
    normalized_valid_users = [(user, normalize_username(user)) for user in valid_users]
    
    # Find the closest match
    closest_user = get_close_matches(normalized_username, [user[1] for user in normalized_valid_users], n=1)
    if closest_user:
        closest_user_index = [user[1] for user in normalized_valid_users].index(closest_user[0])
        return normalized_valid_users[closest_user_index][0]
    return None

def create_or_update_github_issue(owner, repo, issue_data, github_repo, always_prompt, org, team_slug):
    github_url = f"https://api.github.com/repos/{owner}/{github_repo}/issues"

    # Assignee mapping between Gitea and GitHub usernames
    assignee_mapping = {
        'aa': 'Anders-And_XXX',
        'bb': 'Boerge-Baghaand_XXX',
        'cc': 'Casper-Cool_XXX',
        'dd': 'Dennis-Dynamite_XXX',
        'ee': 'Eben-Ezer_XXX',
        'ff': 'Frodo-Faggins_XXX',
        'gg': 'Gertrude-Gaggins_XXX'
    }

    # Get Gitea assignees (if any)
    gitea_assignees = [assignee['login'] for assignee in issue_data.get('assignees', [])] if issue_data.get('assignees') else []
    github_assignees = [assignee_mapping.get(assignee.lower(), assignee) for assignee in gitea_assignees]

    # Get the issue creator's username
    creator_username = issue_data['user']['login_name']
    github_creator = assignee_mapping.get(creator_username.lower(), creator_username)

    labels = [label['name'] for label in issue_data.get('labels', [])]

    # Fetch valid assignees list for the GitHub repository
    valid_assignees_list = fetch_collaborators_and_team_members(owner, github_repo, org, team_slug)
    valid_assignees_set = set(name.lower() for name in valid_assignees_list)

    # Default to normalized GitHub assignees based on Gitea's assignees and collaborators
    normalized_assignees = [assignee for assignee in github_assignees if assignee.lower() in valid_assignees_set]

    # Special case: If the creator is 'Yyyy-Zzz_xxx', enforce specific assignee rules
    if github_creator == 'Yyyy-Zzz_xxx':
        print(f"Issue was created by 'Yyyy-Zzz_xxx', ensuring assignee matches Gitea.")

        # If the Gitea issue is unassigned, ensure the GitHub issue is unassigned too
        if not gitea_assignees:
            print(f"No assignees in Gitea for issue '{issue_data['title']}', unassigning in GitHub.")
            normalized_assignees = []
        else:
            # Otherwise, ensure only valid assignees from Gitea are mapped to GitHub
            normalized_assignees = [assignee for assignee in github_assignees if assignee.lower() in valid_assignees_set]

    # Print warning if no valid assignees found
    if not normalized_assignees:
        print(f"Warning: None of the assignees are valid collaborators or team members for repo '{github_repo}'.")

    issue_body = (
        f"**Original Gitea Issue by**: {issue_data['user']['login_name']} ({issue_data['user']['full_name']})\n\n"
        f"{issue_data['body']}\n\n"
        f"---\n"
        f"_This issue was migrated from Gitea. Originally created on {issue_data['created_at']}._"
    )

    # Check if the issue already exists in GitHub
    existing_issue = issue_exists(issue_data['title'], github_repo)
    if existing_issue:
        # Prompt for confirmation if the titles are the same, but only if --prompt-always is enabled
        print(f"An issue with the same title exists: #{existing_issue['number']} - '{existing_issue['title']}'")
        if always_prompt:
            confirmation = input(f"Do you want to update the existing issue '{existing_issue['title']}' in GitHub repo '{github_repo}'? (yes/no): ").strip().lower()
            if confirmation != 'yes':
                print(f"Skipping update for issue '{issue_data['title']}'")
                return
        else:
            print(f"Updating existing issue without prompt as --prompt-always is not set.")
        # Update the existing GitHub issue
        update_github_issue(owner, github_repo, existing_issue['number'], issue_body, normalized_assignees, labels)
    else:
        print(f"Creating new issue '{issue_data['title']}' in GitHub repo '{github_repo}'.")
        if always_prompt:
            confirmation = input(f"Do you want to create this issue: '{issue_data['title']}' from {GITEA_URL}/repos/{GITEA_OWNER}/{repo}/issues/{issue_data['number']}? (yes/no): ").strip().lower()
            if confirmation != 'yes':
                print(f"Skipping issue '{issue_data['title']}'")
                return
        else:
            print(f"Creating issue without prompt as --prompt-always is not set.")

        # Prepare the payload for creating the GitHub issue
        payload = {
            "title": issue_data['title'],
            "body": issue_body,
            "assignees": normalized_assignees,
            "labels": labels,
        }

        # Retry up to 5 times to handle rate limits or transient errors
        for attempt in range(5):
            print(f"Attempting to create GitHub issue: {payload}")
            print(f"Target GitHub URL: {github_url}")
            response = requests.post(github_url, headers=GITHUB_HEADERS, json=payload)

            if response.status_code == 201:
                created_issue = response.json()
                print(f"Issue created successfully in {owner}/{github_repo}: {issue_data['title']}")
                # If the Gitea issue is closed, close the GitHub issue as well
                if issue_data['state'] == 'closed':
                    close_url = f"{github_url}/{created_issue['number']}"
                    close_payload = {"state": "closed"}
                    close_response = requests.patch(close_url, headers=GITHUB_HEADERS, json=close_payload)
                    if close_response.status_code == 200:
                        print(f"Closed issue #{created_issue['number']} in {owner}/{github_repo}")
                    else:
                        print(f"Failed to close issue #{created_issue['number']} in {owner}/{github_repo}. Status Code: {close_response.status_code}")
                        print(f"Response Text: {close_response.text}")
                return
            elif response.status_code == 403:
                if "Retry-After" in response.headers:
                    retry_after = int(response.headers["Retry-After"])
                    print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    print(f"Rate limit exceeded. Retrying in 60 seconds.")
                    time.sleep(60)
            else:
                print(f"Failed to create issue in {owner}/{github_repo}. Status Code: {response.status_code}")
                print(f"Response Text: {response.text}")
                break



def update_github_issue(owner, github_repo, issue_number, body, assignees, labels):
    url = f"https://api.github.com/repos/{owner}/{github_repo}/issues/{issue_number}"
    payload = {
        "body": body,
        "assignees": assignees,
        "labels": labels,
    }

    for attempt in range(5):  # Retry up to 5 times
        print(f"Attempting to update GitHub issue #{issue_number} with payload: {payload}")
        print(f"Target GitHub URL: {url}")

        response = requests.patch(url, headers=GITHUB_HEADERS, json=payload)

        if response.status_code == 200:
            updated_issue = response.json()
            print(f"Issue #{issue_number} updated successfully in {owner}/{github_repo}.")
            return

        elif response.status_code == 403:
            if "Retry-After" in response.headers:
                retry_after = int(response.headers["Retry-After"])
                print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                time.sleep(retry_after)
            else:
                print(f"Rate limit exceeded. Retrying in 60 seconds.")
                time.sleep(60)
        else:
            print(f"Failed to update issue #{issue_number} in {owner}/{github_repo}. Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            break




def process_repo_issues(gitea_repo, github_repo, include_closed=False, always_prompt=False):
    print(f"Fetching open issues for Gitea repo {gitea_repo}...")
    open_repo_issues = get_issues(GITEA_OWNER, gitea_repo, "open")

    closed_repo_issues = []
    if include_closed:
        print(f"Fetching closed issues for Gitea repo {gitea_repo}...")
        closed_repo_issues = get_issues(GITEA_OWNER, gitea_repo, "closed")

    all_issues = open_repo_issues + closed_repo_issues

    if all_issues:
        print(f"Found {len(all_issues)} total issues (open + closed) in Gitea repo '{gitea_repo}'.")
        for issue in all_issues:
            create_or_update_github_issue(GITHUB_OWNER, github_repo, issue, gitea_repo, always_prompt, "xxx", "engineering")
    else:
        print("No issues found in the Gitea repo.")


def fetch_team_members(org, team_slug):
    team_members_url = f"https://api.github.com/orgs/{org}/teams/{team_slug}/members"
    response = requests.get(team_members_url, headers=GITHUB_HEADERS)
    
    print(f"Fetching team members from: {team_members_url}")
    if response.status_code == 200:
        return [member['login'] for member in response.json()]
    else:
        print(f"Failed to fetch team members: {response.status_code}")
        print(f"Response Text: {response.text}")
        return []

def delete_intraday_issues(repo):
    """Delete all issues created on the current day in the specified repo."""
    owner = GITHUB_OWNER
    today = datetime.now().strftime('%Y-%m-%d')
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {"state": "all", "per_page": 100, "page": page}
        response = requests.get(url, headers=GITHUB_HEADERS, params=params)

        print(f"Fetching issues for deletion from: {url} with params: {params}")
        if response.status_code == 200:
            issues = response.json()
            if not issues:
                break

            for issue in issues:
                if 'pull_request' not in issue:  # Skip pull requests
                    issue_created_at = issue['created_at'][:10]  # Get YYYY-MM-DD part of the timestamp
                    if issue_created_at == today:
                        print(f"Issue #{issue['number']} created on {issue_created_at}, which is today. Deleting...")
                        delete_github_issue(issue['number'], repo)
            
            page += 1
        else:
            print(f"Failed to fetch issues for deletion: {response.status_code}")
            print(f"Response Text: {response.text}")
            break

def compare_issue_counts(gitea_repo, github_repo):
    # Fetch open and closed issues for Gitea repo
    gitea_open_issues = get_issues(GITEA_OWNER, gitea_repo, state="open")
    gitea_closed_issues = get_issues(GITEA_OWNER, gitea_repo, state="closed")
    
    gitea_open_count = len(gitea_open_issues)
    gitea_closed_count = len(gitea_closed_issues)

    # Fetch open and closed issues for GitHub repo
    github_open_issues = get_issues(GITHUB_OWNER, github_repo, state="open")
    github_closed_issues = get_issues(GITHUB_OWNER, github_repo, state="closed")
    
    github_open_count = len(github_open_issues)
    github_closed_count = len(github_closed_issues)

    # Print counts and differences
    print(f"Gitea Repo '{gitea_repo}': Open issues = {gitea_open_count}, Closed issues = {gitea_closed_count}")
    print(f"GitHub Repo '{github_repo}': Open issues = {github_open_count}, Closed issues = {github_closed_count}")

    open_diff = abs(gitea_open_count - github_open_count)
    closed_diff = abs(gitea_closed_count - github_closed_count)

    print(f"Difference in open issues: {open_diff}")
    print(f"Difference in closed issues: {closed_diff}")


def main():
    parser = argparse.ArgumentParser(description="Migrate issues from Gitea to GitHub.")
    parser.add_argument('--include-closed', action='store_true', help="Include closed issues in the migration.")
    parser.add_argument('--always-prompt', action='store_true', help="Prompt for confirmation before creating each issue.")
    parser.add_argument('--delete-all-issues', metavar='REPO', help="Delete all issues in the specified GitHub repository.")
    parser.add_argument('--delete-intraday', metavar='REPO', help="Delete all issues created today in the specified GitHub repository.")
    parser.add_argument('--repo', help="Specify a single repository to process")
    parser.add_argument('--check-count', action='store_true', help="Compare issue counts between Gitea and GitHub repositories.")
    args = parser.parse_args()

    # Handle deletion options
    if args.delete_all_issues:
        confirmation = input(f"Are you sure you want to delete ALL issues from {GITHUB_OWNER}/{args.delete_all_issues}? This action cannot be undone. (yes/no): ").strip().lower()
        if confirmation == 'yes':
            delete_all_issues(GITHUB_OWNER, args.delete_all_issues)
        else:
            print("Operation cancelled.")
        return

    if args.delete_intraday:
        confirmation = input(f"Are you sure you want to delete all issues created today from {GITHUB_OWNER}/{args.delete_intraday}? This action cannot be undone. (yes/no): ").strip().lower()
        if confirmation == 'yes':
            delete_intraday_issues(args.delete_intraday)
        else:
            print("Operation cancelled.")
        return

    # Fetch Gitea and GitHub repos
    gitea_repos = get_gitea_repos()
    github_repos = get_github_repos()

    # Handle issue count comparison
    if args.check_count:
        for gitea_repo in gitea_repos:
            gitea_repo_name = gitea_repo['name']
            closest_github_repo = find_closest_github_repo(gitea_repo_name, github_repos)

            if closest_github_repo:
                compare_issue_counts(gitea_repo_name, closest_github_repo['name'])
            else:
                print(f"No matching GitHub repo found for Gitea repo '{gitea_repo_name}'")
        return

    # Process specific repository or all repos if no specific repo is provided
    if args.repo:
        gitea_repo = next((repo for repo in gitea_repos if repo['name'] == args.repo), None)
        if not gitea_repo:
            print(f"Error: Specified Gitea repository '{args.repo}' not found.")
            return
        process_single_repo(args.repo, github_repos, args.include_closed, args.always_prompt)
    else:
        for gitea_repo in gitea_repos:
            gitea_repo_name = gitea_repo['name']
            process_single_repo(gitea_repo_name, github_repos, args.include_closed, args.always_prompt)



def process_single_repo(gitea_repo_name, github_repos, include_closed, always_prompt):
    github_repo = find_closest_github_repo(gitea_repo_name, github_repos)

    if github_repo:
        github_repo_name = github_repo['name']
        if github_repo_name == gitea_repo_name:
            print(f"Exact match: Migrating issues from Gitea repo '{gitea_repo_name}' to GitHub repo '{github_repo_name}'.")
            process_repo_issues(gitea_repo_name, github_repo_name, include_closed=include_closed, always_prompt=always_prompt)
        else:
            # Ask for confirmation before proceeding with a closest match
            confirmation = input(f"Closest GitHub repo match for '{gitea_repo_name}' is '{github_repo_name}'. Proceed? (yes/no): ").strip().lower()
            if confirmation == 'yes':
                process_repo_issues(gitea_repo_name, github_repo_name, include_closed=include_closed, always_prompt=always_prompt)
            else:
                print(f"Skipping migration for {gitea_repo_name}")
    else:
        print(f"No matching GitHub repository found for Gitea repo '{gitea_repo_name}'.")

if __name__ == "__main__":
    main()