# github_private_all.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
from github_config import *
from github_scanner import *

parser = argparse.ArgumentParser(description='Set matching GitHub repos to be private.')
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

filtered_repo_list = fetch_matching_repos(github_organization, github_prefix, github_token)
print("%d repos found for %s/%s" % (len(filtered_repo_list), github_organization, github_prefix))

for repo in filtered_repo_list:
    make_repo_private(repo, github_token)
    sys.stderr.write(".")

sys.stderr.write("\n")
