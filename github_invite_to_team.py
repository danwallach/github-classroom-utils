# github_invite_to_teampy
# Stephen Wong <swong@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
from github_config import *
from github_scanner import *
import requests


ALLOWED_TEAM_ROLES = ["member", "maintainer"]

def main():
    """
    Read a JSON file with a dictionary mapping team slugs to lists of members usernames.
    If the member is not part of the organization, they will receive an email inviting them to the organization, 
    acceptance of which will automatically also put them on the specified team.
    
    IMPORTANT: If the member was not already part of the organization, they will automatically be added as a "member", 
    NOT as an "owner"!   Course staff needs to be owners of the organization in order for them to accept the invitation 
    to the classroom.
    
    Arguments:
    
    --token XXX = GitHub Personal Access Token (default = defined in github_coinfig.py)
    --file XXX =  JSON file with format:  { team_slug:[username, ...] }   A team slug is generally the team name 
    with spaces replaced with dashes and no capital letters, e.g. "current-comp310-students"
    --org XXX =  GitHub organization name, e.g. "Rice-COMP-310"
    
    Ref:  https://docs.github.com/en/rest/reference/teams#add-or-update-team-membership-for-a-user
    """
    parser = argparse.ArgumentParser(description='Invites GitHub users to teams.')
    parser.add_argument('--token',
                        nargs=1,
                        default=[default_github_token],
                        help='GitHub API token')
    
    parser.add_argument('--file',
                        nargs=1,
                        help='JSON file with data')
    
    parser.add_argument('--org',
                        nargs=1,
                        help='GitHub Organization')
    
    parser.add_argument('--role',
                        nargs=1,
                        default=["member"],
                        help='Team role for ALL invitations.  Allowed values: "member" (default), "maintainer"')
    
    args = parser.parse_args()
    
    github_token = args.token[0]
    data_filename = args.file[0]
    github_org = args.org[0]
    team_role = args.role[0]
    
    if team_role not in ALLOWED_TEAM_ROLES:
        print("ERROR:  Invalid team role specified: ", team_role, " not in ", ALLOWED_TEAM_ROLES)
        return
    
    request_data = {
        "role": team_role
        }       
         
    print("data_filename = ", data_filename)
    
    with open(data_filename, "r") as data_file:
        data_str = data_file.read()
    
    data_dict = json.loads(data_str)
    
    print("data_dict = ", data_dict)
    

    
    # endpoint = "orgs/{}/teams".format(github_org)
    # result = get_github_endpoint(endpoint, github_token)
    
    endpoint_fmt = "orgs/{org}/teams/{team_slug}/memberships/{username}"


    for team, members in data_dict.items():
        print("team = ", team,": ", members)
        for member in members:
            print("inviting "+request_data["role"]+": ", member)
            endpoint = endpoint_fmt.format(org= github_org, team_slug=team, username=member)
            # print("endpoint = ", endpoint)
            result = put_github_endpoint(endpoint, github_token, data_dict=request_data)
            print("result =", dict_to_pretty_json(result))        






if __name__ == "__main__":
    main()