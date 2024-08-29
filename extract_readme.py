import os
import subprocess

import pandas as pd

# Define the repository path
repo_path = "/Users/praveenzirali/active_projects/crcsim"


# Function to execute git commands
def git_command(cmd):
    result = subprocess.run(
        cmd, shell=True, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.stdout.decode("utf-8").strip()


# Function to get a list of all branches
def get_branches():
    branches = git_command("git branch -r")
    return [branch.strip().replace("origin/", "") for branch in branches.split("\n")]


# Function to get the first line of README.txt from a branch
def get_readme_first_line(branch):
    git_command(f"git checkout {branch}")  # Switch to the branch
    try:
        with open(os.path.join(repo_path, "README.md"), "r") as file:
            first_line = file.readline().strip()
    except FileNotFoundError:
        first_line = "README.md not found"
    return first_line


# Main function
def main():
    branches = get_branches()
    data = []

    for branch in branches:
        print(f"Processing branch: {branch}")
        first_line = get_readme_first_line(branch)
        data.append({"Branch": branch, "README First Line": first_line})

        # Switch back to the main branch (or any default branch)
        git_command("git checkout main")

    # Save the results to a CSV file
    df = pd.DataFrame(data)
    df.to_csv("branch_readme_summary.csv", index=False)


if __name__ == "__main__":
    main()
