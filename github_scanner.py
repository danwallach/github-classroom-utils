# github_scanner.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

# This file has all the shared logic for interacting with the GitHub service, including keeping
# a local cache to speed things up.

import iso8601
import requests
import sys
import os
import json
from typing import List
from datetime import datetime, timezone

scanner_cache = {}


def load_cache(github_organization: str, verbose: bool = True):
    if github_organization in scanner_cache:
        return

    cache_name = ".github-classroom-utils." + github_organization + ".json"
    try:
        if os.path.isfile(cache_name) and os.access(cache_name, os.R_OK):
            with open(cache_name, 'r') as file:
                data = json.loads(file.read())
                scanner_cache[github_organization] = data
                if verbose:
                    print("Restored cache for: " + github_organization)

    except Exception as e:
        if verbose:
            print("Unexpected error loading cache: " + cache_name)
            print(e)
            exit(1)


def store_cache(github_organization: str, verbose: bool = True):
    if github_organization not in scanner_cache:
        if verbose:
            print("Warning: nothing in cache for " + github_organization + ". Nothing to persist to disk.")
        return

    cache_name = ".github-classroom-utils." + github_organization + ".json"
    try:
        with open(cache_name, 'w') as file:
            # Pretty-printing the results, even though they're larger. Human-legibility may come in handy.
            data = json.dumps(scanner_cache[github_organization], sort_keys=True, indent=2)
            file.write(data)

            if verbose:
                print("Wrote cache for " + github_organization)

    except Exception as e:
        if verbose:
            print("Unexpected error writing cache: " + cache_name)
            print(e)


def github_headers(github_token: str) -> dict:
    return {
        "User-Agent": "GitHubClassroomUtils/1.0",
        "Authorization": "token " + github_token
    }


def query_github(github_organization: str, github_token: str, verbose: bool = True) -> List[dict]:
    load_cache(github_organization, verbose)

    # How we can tell if our cache is valid: we do a HEAD request to GitHub, which doesn't consume any
    # of our API limit. The result will include an ETag header, which is just an opaque string. Assuming
    # this string is the same as it was last time, then we'll reuse our cached data. If it's different,
    # then something changed, so we'll rescan everything.

    # Ideally, we'd instead use the GitHub v4 GraphQL APIs, which are much, much more efficient than
    # the v3 REST API we're using, but unfortunately, we found some really nasty bugs in the v4
    # GraphQL API (wherein *sometimes* the results we get back are missing entries). This same
    # bug also applies to the v3 "search" endpoint. So fine, we need to page through all of the
    # repos, but at least we can avoid doing it multiple times if nothing's changed.

    # More on how ETag works:
    # https://gist.github.com/6a68/4971859
    # https://developer.github.com/v3/#conditional-requests

    request_headers = github_headers(github_token)

    previous_etag = scanner_cache[github_organization]["ETag"] if github_organization in scanner_cache else ""
    head_status = requests.head('https://api.github.com/orgs/' + github_organization + '/repos',
                                headers=request_headers)

    if head_status.status_code != 200:
        print('Error connecting to GitHub API: ' + head_status.content)
        exit(1)

    current_etag = head_status.headers["ETag"]

    if previous_etag == current_etag:
        if verbose:
            print('Cached result for ' + github_organization + ' is current')
        return scanner_cache[github_organization]["Contents"]
    else:
        if verbose:
            print('Cached result for ' + github_organization + ' is missing or outdated')

    if verbose:
        sys.stdout.write('Getting repo list from GitHub')

    all_repos_list = []
    page_number = 1

    while True:
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
    
        repos_page = requests.get('https://api.github.com/orgs/' + github_organization + '/repos',
                                  headers=request_headers,
                                  params={'page': page_number})
        page_number = page_number + 1

        if repos_page.status_code != 200:
            if verbose:
                print('Error connecting to GitHub API: ' + repos_page.content)
            exit(1)

        repos = repos_page.json()
    
        if len(repos) == 0:
            if verbose:
                print(" Done.")
            break

        all_repos_list = all_repos_list + repos

    scanner_cache[github_organization] = {}  # force it to exist before we create sub-keys
    scanner_cache[github_organization]['ETag'] = current_etag
    scanner_cache[github_organization]['Contents'] = all_repos_list

    store_cache(github_organization, verbose)
    return all_repos_list


def fetch_matching_repos(github_organization: str,
                         github_repo_prefix: str,
                         github_token: str,
                         verbose: bool = True) -> List[dict]:
    """
    This is the function we expect most of our GitHub Classroom utilities to use. Every GitHub repository has
    a URL of the form https://github.com/Organization/Repository/contents, so the arguments given specify
    which organization is being queried and a string prefix for the repositories being matched. The results
    will be cached to dot-files in the current working directory, such that subsequent queries will run
    more quickly, assuming that there are no new repositories in the given organization.

    The results of this call are a list of Python dict objects. The fields that you might find useful
    include:

    clone_url: https link to the repository
        (e.g., 'https://github.com/RiceComp215/comp215-week01-intro-2017-dwallach.git')

    ssh_url: git@github.com link to the repository
        (e.g., 'git@github.com:RiceComp215/comp215-week01-intro-2017-dwallach.git')

    name: the name of the repo itself (e.g., 'comp215-week01-intro-2017-dwallach')

    full_name: the organization and repo (e.g., 'RiceComp215/comp215-week01-intro-2017-dwallach')

    :param github_organization: GitHub Organization being queried.
    :param github_repo_prefix: String prefix to match GitHub Repositories.
    :param github_token: Token for the GitHub API.
    :param verbose: Specifies whether anything should be printed to show the user status updates.
    :return: A list of Python dicts containing the results of the query.
    """
    result = query_github(github_organization, github_token, verbose)
    return [x for x in result if x['name'].startswith(github_repo_prefix)]


def make_repo_private(repo: dict, github_token: str):
    requests.patch('https://api.github.com/repos/' + repo['full_name'],
                   headers=github_headers(github_token),
                   json={'private': True})


def get_endpoint(endpoint: str, github_token: str, verbose: bool = True) -> dict:
    result = requests.get('https://api.github.com/' + endpoint, headers=github_headers(github_token))

    if result.status_code != 200:
        if verbose:
            print("Failed to load %s from GitHub: %s" % (endpoint, result.content))
        return {}

    return result.json()


# And now for a bunch of code to handle times and timezones. This is probably going to
# require Python 3.7 or later.

LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo


def datetime_to_local_timezone(dt: datetime) -> str:
    return localtime_from_timestamp(dt.timestamp())


def localtime_from_timestamp(timestamp: float) -> str:
    return str(datetime.fromtimestamp(timestamp, LOCAL_TIMEZONE))


def localtime_from_datestr(date_str: str) -> str:
    return datetime_to_local_timezone(iso8601.parse_date(date_str))
