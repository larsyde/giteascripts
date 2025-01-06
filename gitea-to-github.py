import subprocess
import os
import sys
import shutil
import time

def run_command(command, cwd=None, check=True):
    """Run a shell command in a specified directory."""
    result = subprocess.run(command, shell=True, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        print(f"Error running command: {command}\n{result.stderr}")
        sys.exit(result.returncode)
    return result.stdout.strip()

def clean_up(local_dir, retries=5, delay=2):
    """Remove the temporary local directory, with retries."""
    for i in range(retries):
        try:
            if os.path.exists(local_dir):
                shutil.rmtree(local_dir)
                print(f"Cleaned up temporary directory {local_dir}.")
            return
        except PermissionError as e:
            print(f"Attempt {i+1}: Failed to clean up {local_dir} - {e}")
            time.sleep(delay)  # Wait before retrying
    print(f"Failed to clean up {local_dir} after {retries} attempts.")

def clone_repo(gitea_repo_url, local_dir):
    """Clone the Gitea repository as a mirror."""
    print(f"Cloning Gitea repository {gitea_repo_url} into {local_dir}...")
    run_command(f"git clone --mirror {gitea_repo_url} {local_dir}")

def ref_exists(local_dir, ref):
    """Check if a specific ref exists in the repository."""
    result = run_command(f"git show-ref {ref}", cwd=local_dir, check=False)
    return ref in result

def lfs_fetch_and_checkout(local_dir):
    """Fetch and checkout all LFS objects in the repository."""
    print(f"Fetching all LFS objects in {local_dir}...")
    run_command("git lfs fetch --all", cwd=local_dir)
    print(f"Checking out all LFS objects in {local_dir}...")
    run_command("git lfs checkout", cwd=local_dir)

def push_to_github(local_dir, github_repo_url):
    """Push all branches, tags, and content to GitHub repository, excluding certain refs."""
    print(f"Pushing content from {local_dir} to GitHub repository {github_repo_url}...")

    # Push all branches
    run_command(f"git push {github_repo_url} refs/heads/*:refs/heads/*", cwd=local_dir)
    
    # Push all tags
    run_command(f"git push {github_repo_url} refs/tags/*:refs/tags/*", cwd=local_dir)
    
    # Push other refs if they exist (e.g., refs/notes/*, refs/stash)
    if ref_exists(local_dir, "refs/notes/*"):
        run_command(f"git push {github_repo_url} refs/notes/*:refs/notes/*", cwd=local_dir)
    
    if ref_exists(local_dir, "refs/stash"):
        run_command(f"git push {github_repo_url} refs/stash:refs/stash", cwd=local_dir)
    
    # Push LFS objects
    run_command(f"git lfs push --all {github_repo_url}", cwd=local_dir)

def main(gitea_repo_url, github_repo_url):
    local_dir = "temp_repo.git"  # .git indicates a bare repository
    
    # Clean up any previous temporary directory
    clean_up(local_dir)

    try:
        clone_repo(gitea_repo_url, local_dir)
        lfs_fetch_and_checkout(local_dir)  # Ensure LFS objects are fetched and checked out
        push_to_github(local_dir, github_repo_url)
    finally:
        clean_up(local_dir)

    print("All branches, tags, and content have been pushed to the GitHub repository, excluding hidden refs.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clone_and_push.py <GiteaRepoURL> <GitHubRepoURL>")
        sys.exit(1)

    gitea_repo_url = sys.argv[1]
    github_repo_url = sys.argv[2]

    main(gitea_repo_url, github_repo_url)
