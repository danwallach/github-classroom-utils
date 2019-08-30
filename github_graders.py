# github_graders.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import random
import pandas as pd
from github_config import *
from github_scanner import *

from typing import List, TypeVar

# your graders, preferably their GitHub IDs (we'll ignore them if they've also checked out a copy of the assignment)
grader_list = default_grader_list

# your own GitHub ID and/or anybody else who you wish to exclude from being graded
ignore_list = default_grader_ignore_list

# command-line argument processing

parser = argparse.ArgumentParser(description='Random assignment of graders to students')
parser.add_argument('--token',
                    nargs=1,
                    default=[default_github_token],
                    help='GitHub API token')
parser.add_argument('--org',
                    nargs=1,
                    default=[default_github_organization],
                    help='GitHub organization to scan, default: ' + default_github_organization)
parser.add_argument('--prefix',
                    nargs=1,
                    default=[default_prefix],
                    help='Prefix on projects to match (default: match all projects)')
parser.add_argument('--students',
                    nargs=1,
                    default=[default_student_csv_name],
                    help="CSV file name with student information (default: student-info.csv)")

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]
student_file_name = args.students[0]

# Python3's parametric type hints are ... a thing.
T = TypeVar('T')


def group_list_by_n(l: List[T], n: int) -> List[List[T]]:
    """
    Given a list of whatever type, divides it into a list of lists, each of which is n elements long,
    until the last one, having whatever is left.
    """
    if len(l) == 0:
        return []
    elif len(l) <= n:
        return [l]
    else:
        return [l[0:n]] + group_list_by_n(l[n:], n)


df_students = {}  # will replace below
df_students_success = False
try:
    df_students = pd.read_csv(student_file_name)
    df_students.GitHubID = df_students.GitHubID.astype(str).str.lower()  # force lower-case of GitHub IDs
    df_students_success = True
except FileNotFoundError:
    #    sys.stdout.write("Cannot file student info file: %s\n" % student_file_name)
    #    sys.stdout.flush()
    pass


def student_info(github_id: str) -> str:
    """
    Given a GitHub ID, returns a suitably human-readable string based on
    the student-data CSV file with the student's name, email, etc.
    """
    if df_students_success:
        matches = df_students[df_students['GitHubID'] == github_id]
        if len(matches) == 1:
            student = matches.iloc[0].to_dict()
        elif len(matches) == 0:
            sys.stdout.write("Warning: github-id (%s) not found in student info!\n" % github_id)
            sys.stdout.flush()
            student = {'NetID': '', 'Name': '', 'Email': '', 'SID': '', 'GitHubID': github_id}
        else:
            sys.stdout.write("Warning: two or more rows found for github-id (%s) in student info!\n" % github_id)
            sys.stdout.flush()
            student = matches.iloc[0].to_dict()
        if 'NetID' in student and student['Email'].startswith(student['NetID']):
            return "%s <%s>" % (student['Name'], student['Email'])
        else:
            return "%s <%s> (%s)" % (student['Name'], student['Email'], student['NetID'])
    else:
        return github_id


# First things first, if we have no graders, we can't divide up the work.
if not grader_list:
    print("Error: grader_list is empty, cannot assign grades")
    exit(1)

ids_seen = {}
submissions = {}
all_ignore_list = ignore_list + grader_list

filtered_repo_list = [x for x in query_matching_repos(github_organization, github_prefix, github_token)
                      if desired_user(github_prefix, all_ignore_list, x['name'])]

# Let's do a duplicate check, and also sort out the URL we want to use
print("%d repos in the initial search\n" % len(filtered_repo_list))
for repo in filtered_repo_list:
    if 'html_url' in repo:
        repo['final_url'] = repo['html_url']
    else:
        repo['final_url'] = repo['url']

    gid = student_name_from(github_prefix, repo['name'])
    if gid in ids_seen:
        # check if we have an exact duplicate or not ... this shouldn't happen, but ... does.
        submission_urls = [x['final_url'] for x in submissions[gid]]
        if repo['final_url'] in submission_urls:
            sys.stdout.write('Warning: exact url for GitHub ID <%s> seen more than once!\n' % gid)
            sys.stdout.flush()
        else:
            sys.stdout.write('Warning: GitHub ID <%s> with different URLs seen!\n' % gid)
            sys.stdout.flush()
            ids_seen[gid] = ids_seen[gid] + 1
            submissions[gid].append(repo)
    else:
        ids_seen[gid] = 1
        submissions[gid] = [repo]


# note: we're shuffling the graders, so different graders get lucky each week when the load isn't evenly divisible
# and, of course, we're shuffling the repos.
all_gids = list(submissions.keys())
print("%d unique GitHub IDs found" % len(all_gids))
random.seed()
random.shuffle(all_gids)
random.shuffle(grader_list)

# inefficient, but correct
grading_groups = [[entry[i] for entry
                   in group_list_by_n(all_gids, len(grader_list))
                   if i < len(entry)]
                  for i in range(len(grader_list))]

grader_map = dict(zip(grader_list, grading_groups))

print("# Grade assignments for %s" % github_prefix)
print("%d repos are ready to grade\n" % len(all_gids))
for grader in sorted(grader_map.keys(), key=str.lower):
    print("## %s (%d total)" % (grader, len(grader_map[grader])))
    for gid in sorted(grader_map[grader]):
        repos = submissions[gid]
        if len(repos) == 1:
            if df_students_success:
                print("- [%s](%s) - %s" % (gid, repos[0]['final_url'], student_info(gid)))
            else:
                print("- [%s](%s)" % (gid, repos[0]['final_url']))
        else:
            print("- **Multiple repos for %s** - %s" % (gid, student_info(gid)))
            for repo in repos:
                print("  - [%s](%s)" % (repo['name'], repo['final_url']))
