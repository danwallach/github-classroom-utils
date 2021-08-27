# github_invite_to_teampy
# Stephen Wong <swong@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
from github_config import *
from github_scanner import *
import requests


ALLOWED_ORG_ROLES = ["member", "admin"]

def main():
    """
    Read a JSON file with a dictionary mapping organization roles to lists of members usernames.
    
    Arguments:
    
    --token XXX = GitHub Personal Access Token (default = defined in github_coinfig.py)
    --file XXX =  JSON file with format:  { role:[username, ...] }   where role = "member" or "admin" (owner)
    --org XXX =  GitHub organization name, e.g. "Rice-COMP-310"
    
    Ref:  https://docs.github.com/en/rest/reference/orgs#set-organization-membership-for-a-user
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
                        default=[default_github_organization],
                        help='GitHub Organization')
    
    
    args = parser.parse_args()
    
    github_token = args.token[0]
    data_filename = args.file[0]
    github_org = args.org[0] 
         
    print("data_filename = ", data_filename)
    
    with open(data_filename, "r") as data_file:
        data_str = data_file.read()
    
    data_dict = json.loads(data_str)
    
    print("data_dict = ", data_dict)
    
    endpoint_fmt = "orgs/{org}/memberships/{username}"


    for org_role, members in data_dict.items():
        print("role = ", org_role,": ", members)
        if team_role not in ALLOWED_ORG_ROLES:
            print("ERROR:  Invalid organization role specified: ", org_role, " not in ", ALLOWED_ORG_ROLES, " Skipping these role assignments!")
            continue
        request_data = {
            "role": org_role
        }      
        for member in members:
            print("inviting "+request_data["role"]+": ", member)
            endpoint = endpoint_fmt.format(org= github_org, username=member)
            # print("endpoint = ", endpoint)
            result = put_github_endpoint(endpoint, github_token, data_dict=request_data)
            print("result =", dict_to_pretty_json(result))        





if __name__ == "__main__":
    main()