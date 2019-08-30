# github_project_status.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import subprocess
from github_config import *
from github_scanner import *

parser = argparse.ArgumentParser(description='Scan all student projects, returns their CI status')
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

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]

filtered_repo_list = query_matching_repos(github_organization, github_prefix, github_token)
print("%d matching repos found for %s/%s" % (len(filtered_repo_list), github_organization, github_prefix))

# GET /repos/:owner/:repo/commits/:ref/statuses

conclusions = {}
conclusions['MISSING'] = 0
num_repos = 0
num_missing = 0
all_ignore_list = default_grader_list + default_grader_ignore_list

for repo in sorted(filtered_repo_list, key=lambda d: str.lower(d['full_name'])):
    repo_name = repo['full_name']
    short_name = repo['name']
    if not desired_user(github_prefix, all_ignore_list, short_name):
        continue

    num_repos = num_repos + 1
    # print("repo: %s" % repo_name)

    # The GitHub API for getting the check status requires us to know
    # the SHA1 hash for the commit we're checking.

    # TODO: find a way to just name the HEAD of the master branch.
    ref_response = get_github_endpoint("repos/%s/git/refs" % repo_name, github_token)
    head_sha = ref_response[0]['object']['sha'][0:7]

    # print("repo: %s (%s)" % (repo_name, head_sha))

    tmp_response = get_github_endpoint("repos/%s/commits/%s/check-suites" % (repo_name, head_sha), github_token)

    if 'check_suites' in tmp_response and len(tmp_response['check_suites']) > 0:
        check_suites_response = tmp_response['check_suites'][0]
        conclusion = check_suites_response['conclusion']
        response_sha = check_suites_response['head_sha'][0:7]
        timestamp = localtime_from_iso_datestr(check_suites_response['created_at'])

        print("%s: %s (%s, %s)" % (short_name, conclusion, timestamp, response_sha))

        if conclusion in conclusions:
            conclusions[conclusion] = conclusions[conclusion] + 1
        else:
            conclusions[conclusion] = 1
    else:
        print("MISSING CHECKS: " + repo_name)
        conclusions['MISSING'] = conclusions['MISSING'] + 1

print("Total repos scanned: %d" % num_repos)
for key in conclusions.keys():
    print("%s: %4d" % (key, conclusions[key]))
