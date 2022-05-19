# github_delete_all.py
# Usage:  python3 github_delete.py --prefix SOMEPREFIX
# Requires: gh CLI
# Modified by See-Mong Tan <see-mong.tan@wwu.edu>
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import subprocess
from github_config import *
from github_scanner import *

parser = argparse.ArgumentParser(description='Clone matching GitHub repos all at once.')
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
parser.add_argument('--safe',
                    action="store_true",
                    default=False,
                    help="Creates cloned repos without the API token embedded. Pushing may not work," +
                         " but repos are safer to share (default: API token is embedded)")
parser.add_argument('--out',
                    nargs=1,
                    default=["."],
                    help='Destination directory for GitHub clones (default: current directory)')

args = parser.parse_args()

github_prefix = args.prefix[0]
github_organization = args.org[0]
github_token = args.token[0]
out_dir = args.out[0]
use_safe_clone = args.safe

filtered_repo_list = query_matching_repos(github_organization, github_prefix, github_token)
print("%d repos found for %s/%s" % (len(filtered_repo_list), github_organization, github_prefix))

# before we start getting any repos, we need a directory to put them
if out_dir != ".":
    try:
        os.makedirs(out_dir)
    except OSError:
        pass  # directory already exists

    os.chdir(out_dir)

# specific clone instructions here:
# https://github.com/blog/1270-easier-builds-and-deployments-using-git-over-https-and-oauth

for repo in filtered_repo_list:
    clone_url = 'https://%s@github.com/%s.git' % (github_token, repo['full_name'])
    print("Deleting %s" % clone_url)
    args = [
        "gh", "api", "--method", "DELETE",
        "-H", "Accept: application/vnd.github.v3+json",
        "repos/" + repo['full_name']
    ]
    subprocess.call(args)
