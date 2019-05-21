# github_rate_limit.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import pprint
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

pp = pprint.PrettyPrinter(indent=4)
pp.pprint(result)
timestamp = result['resources']['core']['reset']
print("Core reset time (local): " + localtime_from_timestamp(timestamp))
