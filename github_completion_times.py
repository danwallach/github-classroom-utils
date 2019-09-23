# github_completion_times.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt

from github_config import *
from github_scanner import *

default_output_filename = "out.pdf"

# change this to get a different timezone for your plot
matplotlib.rcParams['timezone'] = 'US/Central'

parser = argparse.ArgumentParser(description='Generate a graph of how many students are passing at any given time')
parser.add_argument('--token',
                    nargs=1,
                    default=[default_github_token],
                    help='GitHub API token')
parser.add_argument('--org',
                    nargs=1,
                    default=[default_github_organization],
                    help='GitHub organization to scan, default: ' + default_github_organization)
parser.add_argument('--output',
                    nargs=1,
                    default=[default_output_filename],
                    help='Output filename, default: ' + default_output_filename +
                         ', with the file format based on the suffix given')
parser.add_argument('--prefix',
                    nargs=1,
                    default=[default_prefix],
                    help='Prefix on projects to match (default: match all projects)')

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]

output_filename = args.output[0]

matplotlib.rcParams['timezone'] = default_timezone

filtered_repo_list = query_matching_repos(github_organization, github_prefix, github_token)
print("%d matching repos found for %s/%s" % (len(filtered_repo_list), github_organization, github_prefix))

num_repos = 0
num_check_suites = 0
num_missing = 0
all_ignore_list = default_grader_list + default_grader_ignore_list
sha_seen = {}
repo_seen = {}

results = []

sys.stdout.write("Loading")
sys.stdout.flush()
for repo in sorted(filtered_repo_list, key=lambda d: str.lower(d['full_name'])):
    repo_name = repo['full_name']
    short_name = repo['name']
    if not desired_user(github_prefix, all_ignore_list, short_name):
        continue

    num_repos = num_repos + 1

    # The GitHub API for getting the check status requires us to know
    # the SHA1 hash for the commit we're checking.

    # TODO: find a way to just name the HEAD of the master branch.
    ref_responses = get_github_endpoint_paged_list("repos/%s/git/refs" % repo_name, github_token, verbose=False)
    sys.stdout.write(":")
    sys.stdout.flush()

    for ref_response in ref_responses:
        branch = ref_response['ref']
        head_sha = ref_response['object']['sha']
        if branch == "refs/heads/master" and head_sha not in sha_seen:
            # print("repo: %s (%s)" % (repo_name, head_sha))

            tmp_response = get_github_endpoint("repos/%s/commits/%s/check-suites" % (repo_name, head_sha),
                                               github_token, verbose=False)
            sys.stdout.write(".")
            sys.stdout.flush()
            num_check_suites = num_check_suites + 1

            if 'check_suites' in tmp_response and len(tmp_response['check_suites']) > 0:
                check_suites_response = tmp_response['check_suites'][0]
                conclusion = check_suites_response['conclusion']
                response_sha = check_suites_response['head_sha']
                if response_sha not in sha_seen:
                    sha_seen[response_sha] = True
                    repo_seen[short_name] = True
                    timestamp = iso8601.parse_date(check_suites_response['created_at'])

                    # print("%s: %s (%s, %s)" % (short_name, conclusion, timestamp, response_sha))

                    result = {
                        'name': short_name,
                        'conclusion': conclusion,
                        'timestamp': timestamp,
                        'sha': response_sha
                    }

                    results.append(result)

print("Done.")
print("Total repos scanned: %d" % num_repos)
print("Total check-suites recorded / scanned: %d / %d" % (len(results), num_check_suites))

sorted_results = sorted(results, key=lambda x: x['timestamp'])
processed_results = []

passing = {}
for repo in repo_seen.keys():
    passing[repo] = False

# Useful hints for handling datetime and matplotlib here:
# https://stackoverflow.com/questions/9627686/plotting-dates-on-the-x-axis-with-pythons-matplotlib

x_timestamps = []
y_passing = []

for r in sorted_results:
    passing[r['name']] = (r['conclusion'] == 'success')
    num_passing = len([p for p in passing.keys() if passing[p]])
    x_timestamps.append(r['timestamp'])
    y_passing.append(num_passing)

print("Writing %s" % output_filename)
fig = plt.figure()
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())
plt.plot(x_timestamps, y_passing)
plt.gcf().autofmt_xdate()
fig.savefig(output_filename, dpi=fig.dpi)
