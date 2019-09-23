# github_config.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

# see installation and usage instructions in README.md

# your GitHub API token here, inside the quotation marks
# https://github.com/blog/1509-personal-api-tokens
default_github_token = ""

# your GitHub organization (https://github.com/Organization/Repository/...)
default_github_organization = ""

# your default prefix on the Repository name for queries
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

# for use with github_completion_times:
# - Your local timezone, in string format. Here's a worldwide list of
#   all timezones that Python understands:
#   https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
default_timezone = "US/Central"
