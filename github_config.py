# github_config.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

# see installation and usage instructions in README.md

default_github_token = "[Your token here]"
default_github_organization = "RiceComp215-Fall2018"
default_prefix = ""

# for use with github_graders:
# - a list of the GitHub IDs of your grading staff
default_grader_list = ["alice", "bob", "charlie"]

# for use with github_graders:
# - a list of the GitHub IDs of any other non-students (professors, etc.)
default_grader_ignore_list = []

# for use with github_graders:
# - CSV list of students with a header row specifying the names of all
#   the columns. Ours looks like: "NetID","Name","Email","SID","GitHubID".
#   This is used to map from GitHubIDs to real names and emails.
default_student_csv_name = "student-data.csv"
