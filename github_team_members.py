# github_org_teams.py
# Stephen Wong <swong@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
from github_config import *
from github_scanner import *
import requests

def main():
    """
    List all the teams in a GitHub organization and information about them  
    Arguments:
    
    --token XXX = GitHub Personal Access Token (default = defined in github_coinfig.py)
    --org XXX =  GitHub organization name, e.g. "Rice-COMP-310"
    --team XXX = team name slug (typically the team name with spaces replaced with dashes and no capital letters)
    
    Use github_org_teams.py to get the slugs for each team in an organization.
    
    Ref:  https://docs.github.com/en/rest/reference/teams#list-team-members
    """
    parser = argparse.ArgumentParser(description='Invites GitHub users to teams.')
    parser.add_argument('--token',
                        nargs=1,
                        default=[default_github_token],
                        help='GitHub API token')

    parser.add_argument('--org',
                        nargs=1,
                        help='GitHub Organization')
    
    parser.add_argument('--team',
                        nargs=1,
                        help='GitHub team slug')
    
    args = parser.parse_args()
    
    github_token = args.token[0]
    github_org = args.org[0]
    github_team = args.team[0]
    
    
    endpoint = "orgs/{org}/teams/{team_slug}/members".format(org=github_org, team_slug=github_team)
    result = get_github_endpoint(endpoint, github_token)
    print("result =", dict_to_pretty_json(result))        



if __name__ == "__main__":
    main()