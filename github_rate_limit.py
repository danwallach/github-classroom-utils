# github_rate_limit.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
from github_config import *
from github_scanner import *

parser = argparse.ArgumentParser(description='Prints your GitHub API rate limit stats.')
parser.add_argument('--token',
                    nargs=1,
                    default=[default_github_token],
                    help='GitHub API token')

args = parser.parse_args()
github_token = args.token[0]

result = get_endpoint("rate_limit", github_token)

if result == {}:
    exit(1)

formatted_result = json.dumps(result, sort_keys=True, indent=2)
print(formatted_result)
print("")

timestamp = result['resources']['core']['reset']
print("Core reset time (local timezone): " + localtime_from_timestamp(timestamp))
print("Core remaining / limit: %d / %d" % (result['resources']['core']['remaining'],
                                           result['resources']['core']['limit']))
