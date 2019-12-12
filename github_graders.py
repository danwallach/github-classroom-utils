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
parser.add_argument('--teams',
                    action="store_true",
                    default=False,
                    help="reads GitHub team information, use on group assignments")
parser.add_argument('--students',
                    nargs=1,
                    default=[default_student_csv_name],
                    help="CSV file name with student information (default: student-data.csv)")
parser.add_argument('--ignore',
                    nargs=1,
                    default=[""],
                    help="string pattern in group names to ignore, e.g., STAFF (no default)")

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]
student_file_name = args.students[0]
use_teams = args.teams
ignore_str = args.ignore[0]

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
    # force lower-case of GitHub IDs
    df_students.GitHubID = df_students.GitHubID.astype(str).str.lower()  # force lower-case of GitHub IDs
    df_students_success = True
    sys.stdout.write("Found %d students in file %s\n" % (len(df_students), student_file_name))
except FileNotFoundError:
    sys.stdout.write("Cannot file student info file: %s\n" % student_file_name)
    sys.stdout.flush()
    pass


def student_info(github_ids: List[str]) -> str:
    """
    Given a list of GitHub IDs, returns a suitably human-readable string based on
    the student-data CSV file with the students' name, email, etc.
    """
    results = []
    for github_id in github_ids:
        if df_students_success:
            matches = df_students[df_students['GitHubID'] == github_id.lower()]
            if len(matches) == 1:
                student = matches.iloc[0].to_dict()
            elif len(matches) == 0:
                sys.stdout.write("Warning: github-id (%s) not found in student info!\n" % github_id)
                sys.stdout.flush()
                student = {'NetID': '', 'Name': '', 'Email': '', 'GitHubID': github_id}
            else:
                sys.stdout.write("Warning: two or more rows found for github-id (%s) in student info!\n" % github_id)
                sys.stdout.flush()
                student = matches.iloc[0].to_dict()
            if 'NetID' in student and student['Email'].startswith(student['NetID']):
                results.append("%s <%s>" % (student['Name'], student['Email']))
            else:
                results.append("%s <%s> (%s)" % (student['Name'], student['Email'], student['NetID']))
        else:
            results.append(github_id)

    return ", ".join(results)


# First things first, if we have no graders, we can't divide up the work.
if not grader_list:
    print("Error: grader_list is empty, cannot assign grades")
    exit(1)

ids_seen = {}
submissions = {}
all_ignore_list = ignore_list + grader_list

filtered_repo_list = [x for x in query_matching_repos(github_organization, github_prefix, github_token)
                      if desired_user(github_prefix, all_ignore_list, x['name'], ignore_str)]

if use_teams:
    team_info = fetch_team_infos(filtered_repo_list, github_token, True)
else:
    team_info = {}

url_to_gids = {}
url_to_short = {}
# Let's do a duplicate check, and also sort out the URL we want to use
# print("%d repos in the initial search\n" % len(filtered_repo_list))
for repo in filtered_repo_list:
    if 'html_url' in repo:
        repo['final_url'] = repo['html_url']
    else:
        repo['final_url'] = repo['url']

    if use_teams:
        gids = team_info[repo['final_url']]['team_members']
    else:
        gids = [student_name_from(github_prefix, repo['name'])]
    url_to_gids[repo['final_url']] = gids
    url_to_short[repo['final_url']] = repo['name']

    for gid in gids:
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

# now, detect the unique vs. duplicated repos
unique = {}
duplicates = {}
exemplar = {}
for gid in submissions.keys():
    if len(submissions[gid]) == 1:
        url = submissions[gid][0]['final_url']
        unique[url] = True
    else:
        all_urls = [x['final_url'] for x in submissions[gid]]
        for url in all_urls:
            unique[url] = False
            duplicates[url] = all_urls
            exemplar[url] = all_urls[0]

# one more round of filtering when dealing with teams
if use_teams:
    old_filtered_repo_list = filtered_repo_list
    filtered_repo_list = []
    for repo in old_filtered_repo_list:
        gids = [x.lower() for x in team_info[repo['final_url']]['team_members']]
        desired_gids = functools.reduce(lambda a, b: a and b, [x not in all_ignore_list for x in gids], True)
        if desired_gids:
            filtered_repo_list.append(repo)

# sanity check
for repo in filtered_repo_list:
    url = repo['final_url']
    if url not in url_to_gids:
        print("WARNING: %s missing from url_to_gids db" % url)
    if url not in url_to_short:
        print("WARNING: %s missing from url_to_short db" % url)
    if url not in unique:
        print("WARNING: %s missing from unique db (perhaps a student repo without a team?)" % url)
    elif not unique[url]:
        if not url in duplicates:
            print("WARNING: %s missing from duplicates db" % url)
        if not url in exemplar:
            print("WARNING: %s missing from exemplar db" % url)
        
    
              
# note: we're shuffling the graders, so different graders get lucky each week when the load isn't evenly divisible
# and, of course, we're shuffling the repos.
all_urls = [repo['final_url']
            for repo in filtered_repo_list
            if (repo['final_url'] in unique and unique[repo['final_url']]) or \
                (repo['final_url'] in exemplar and exemplar[repo['final_url']] == repo['final_url'])]
repo_db = {repo['final_url']: repo for repo in filtered_repo_list}

random.shuffle(all_urls)
random.shuffle(grader_list)

# inefficient, but correct
grading_groups = [[entry[i] for entry
                   in group_list_by_n(all_urls, len(grader_list))
                   if i < len(entry)]
                  for i in range(len(grader_list))]

grader_map = dict(zip(grader_list, grading_groups))

print("# Grade assignments for %s" % github_prefix)
print("%d repos are ready to grade\n" % len(all_urls))
for grader in sorted(grader_map.keys(), key=str.lower):
    print("## %s (%d total)" % (grader, len(grader_map[grader])))
    for url in sorted(grader_map[grader]):
        gids = url_to_gids[url]
        if url in duplicates:
            print("- **Possible repo duplicates**")
            for u in duplicates:
                print("  - [%s](%s) - %s" % (url_to_short[u], u, student_info(gids)))
        else:
            print("- [%s](%s) - %s" % (url_to_short[url], url, student_info(gids)))
