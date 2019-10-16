# github_scanner.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

# This file has all the shared logic for interacting with the GitHub service, including keeping
# a local cache to speed things up.

import iso8601
import sys
import os
import json
import re
import functools
from typing import List
from datetime import datetime, timezone
from requests.models import Response
import requests
import asyncio
from aiohttp import ClientSession, ClientResponse


scanner_cache = {}


def dict_to_pretty_json(d: dict) -> str:
    return json.dumps(d, sort_keys=True, indent=2)


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
                    print("Restored cache: " + github_organization)

    except Exception as e:
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
            file.write(dict_to_pretty_json(scanner_cache[github_organization]))

            if verbose:
                print("Wrote cache for " + github_organization)

    except Exception as e:
        if verbose:
            print("Unexpected error writing cache: " + cache_name)
            print(e)


def github_headers(github_token: str) -> dict:
    """
    Given a GitHub access token, produces a Python dict suitable for passing to requests' headers field.
    If github_token is an empty string, this prints an error message and crashes the program.
    """
    if github_token == "":
        print("\nError: github_token isn't defined, use the --token argument or edit github_config.py to set it")
        exit(1)

    return {
        "User-Agent": "GitHubClassroomUtils/1.0",
        "Authorization": "token " + github_token,
        "Accept": "application/vnd.github.antiope-preview+json,application/vnd.github.hellcat-preview+json"
    }


def fail_on_github_errors(response: Response):
    if response.status_code != 200:
        print("\nRequest failed, status code: %d" % response.status_code)
        print("Headers: %s\n" % dict_to_pretty_json(dict(response.headers)))
        print("Body: %s\n" % dict_to_pretty_json(response.json()))
        exit(1)


async def fail_on_github_errors_async(response: ClientResponse):
    if response.status != 200:
        print("\nRequest failed, status code: %d" % response.status)
        print("Headers: %s\n" % dict_to_pretty_json(dict(response.headers)))
        print("Body: %s\n" % dict_to_pretty_json(await response.json()))
        exit(1)


def fetch_team_infos(repo_info_list: List[dict], github_token: str, verbose: bool = True) -> dict:
    if verbose:
        print("Fetching team_urls...")

    team_url_results = parallel_get_github_endpoint(
        [{'key': repo['html_url'], 'url': repo['teams_url']}
         for repo in repo_info_list],
        github_token)

    if verbose:
        print("Fetching team_data...")

    # we're assuming there's zero or one teams, and filtering out the zeroes
    member_data_results = parallel_get_github_endpoint(
        [{'key': k, 'url': re.sub('{/member}', '', team_url_results[k]['body'][0]['members_url'])}
         for k in team_url_results.keys()
         if team_url_results[k]['body']], github_token, verbose)

    for member in member_data_results.keys():
        member_data_results[member]['team_members'] = [x['login'] for x in member_data_results[member]['body']]

    return member_data_results


def query_repos_cached(github_organization: str, github_token: str, verbose: bool = True) -> List[dict]:
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
    fail_on_github_errors(head_status)

    current_etag = head_status.headers["ETag"]

    if previous_etag == current_etag:
        if verbose:
            print('Cached result for ' + github_organization + ' is current')
        return scanner_cache[github_organization]["Contents"]
    else:
        if verbose:
            print('Cached result for ' + github_organization + ' is missing or outdated')

    all_repos_list = parallel_get_github_endpoint_paged_list('orgs/' + github_organization + '/repos',
                                                             github_token, verbose)

    # if verbose:
    #     sys.stdout.write('Getting team information from GitHub')
    # team_info_repos(all_repos_list, github_token, verbose)

    scanner_cache[github_organization] = {}  # force it to exist before we create sub-keys
    scanner_cache[github_organization]['ETag'] = current_etag
    scanner_cache[github_organization]['Contents'] = all_repos_list

    num_repos = len(all_repos_list)
    if verbose:
        print("Found %d repos in %s" % (num_repos, github_organization))

    if num_repos != 0:
        # if we got an empty list, then something went wrong so don't write it to the cache
        store_cache(github_organization, verbose)

    return all_repos_list


def query_matching_repos(github_organization: str,
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
    result = query_repos_cached(github_organization, github_token, verbose)
    return [x for x in result if x['name'].startswith(github_repo_prefix)]


def make_repo_private(repo: dict, github_token: str):
    requests.patch('https://api.github.com/repos/' + repo['full_name'],
                   headers=github_headers(github_token),
                   json={'private': True})


def get_github_endpoint(endpoint: str, github_token: str, verbose: bool = True) -> dict:
    if not endpoint.startswith('https:'):
        endpoint = 'https://api.github.com/' + endpoint

    result = requests.get(endpoint, headers=github_headers(github_token))
    fail_on_github_errors(result)

    return result.json()


# inspiration for this parallel / asynchronous code:
# https://pawelmhm.github.io/asyncio/python/aiohttp/2016/04/22/asyncio-aiohttp.html
async def _fetch(key: str, url: str, session: ClientSession, github_token: str, verbose: bool = True) -> dict:
    async with session.get(url, headers=github_headers(github_token)) as response:
        result = await response.read()
        await fail_on_github_errors_async(response)
        return {'key': key, 'url': url, 'body': json.loads(result)}


async def _parallel_get_github_endpoint(endpoint_list: List[dict], github_token: str, verbose: bool = True) -> dict:
    tasks = []
    async with ClientSession() as session:
        for endpoint in endpoint_list:
            key = endpoint['key']
            url = endpoint['url']
            if not url.startswith('https:'):
                url = 'https://api.github.com/' + url
            task = asyncio.ensure_future(_fetch(key, url, session, github_token, verbose))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return {x['key']: x for x in responses}


def parallel_get_github_endpoint(endpoint_list: List[dict], github_token: str, verbose: bool = True) -> dict:
    """
    Similar to get_github_endpoint, but launches requests in parallel, returning a dictionary where
    the keys are the original endpoint URLs, and the values are the same dictionaries that get_github_endpoint
    would have returned. The endpoint_list is actually a list of dictionaries, which every entry must
    have two fields: 'key', which is an arbitrary string, and 'url', which is what will be fetched.
    The resulting dictionary will preserve these two fields and add a third one, 'body', with the result.
    """
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(_parallel_get_github_endpoint(endpoint_list, github_token, verbose))
    return loop.run_until_complete(future)


def get_github_endpoint_paged_list(endpoint: str, github_token: str, verbose: bool = True) -> List[dict]:
    if not endpoint.startswith('https:'):
        endpoint = 'https://api.github.com/' + endpoint

    page_number = 1
    result_list = []

    while True:
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()

        headers = github_headers(github_token)

        result = requests.get(endpoint,
                              headers=headers,
                              params={'page': page_number} if page_number > 1 else {})
        fail_on_github_errors(result)
        page_number = page_number + 1

        result_l = result.json()

        if len(result_l) == 0:
            if verbose:
                print(" Done.")
            break

        result_list = result_list + result_l

    if verbose:
        print("Total %d results found over %d pages" % (len(result_list), page_number - 1))

    return result_list


def parallel_get_github_endpoint_paged_list(endpoint: str, github_token: str, verbose: bool = True) -> List[dict]:
    if not endpoint.startswith('https:'):
        endpoint = 'https://api.github.com/' + endpoint

    headers = github_headers(github_token)

    page1_result = requests.get(endpoint, headers=headers)
    fail_on_github_errors(page1_result)

    link_header = page1_result.headers["Link"]
    p = re.compile('page=(\\d+)>; rel="last"')
    m = p.findall(link_header)
    if len(m) != 1:
        if verbose:
            print("Malformed header, didn't have pagination!")
        return page1_result.json()

    num_pages = int(m[0])
    if verbose:
        print("Fetching %d pages in parallel" % num_pages)

    urls = ["%s?page=%d" % (endpoint, n) for n in range(1, num_pages + 1)]
    all_pages = parallel_get_github_endpoint([{"key": url, "url": url} for url in urls], github_token, verbose)
    ordered_pages = [all_pages[url]['body'] for url in urls]
    joined_pages = functools.reduce(lambda a, b: a + b, ordered_pages, [])

    if verbose:
        print("Total %d results found over %d pages" % (len(joined_pages), num_pages))

    return joined_pages


# And now for a bunch of code to handle times and timezones. This is probably going to
# require Python 3.7 or later.

LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo


def datetime_to_local_timezone(dt: datetime) -> str:
    return localtime_from_timestamp(dt.timestamp())


def localtime_from_timestamp(timestamp: float) -> str:
    return str(datetime.fromtimestamp(timestamp, LOCAL_TIMEZONE))


def localtime_from_iso_datestr(date_str: str) -> str:
    return datetime_to_local_timezone(iso8601.parse_date(date_str))


def student_name_from(github_prefix: str, repo_name: str) -> str:
    """
    Given a GitHub repo "name" (e.g., "comp215-week01-intro-danwallach") return the username suffix at the
    end ("danwallach"). If it's not there, the result is an empty string ("").
    """
    m = re.search(github_prefix + "-(.*)$", repo_name)
    if not m:
        return ""  # something funny in the name, so therefore not matching
    else:
        # there might be a trailing dash and digits if the student did the clone thing multiple times
        # also, we're converting everything to lower-case
        return re.sub("-\\d+$", "", m.group(1)).lower()


def desired_user(github_prefix: str, ignore_list: List[str], name: str) -> bool:
    """
    Given a GitHub repo "name" (e.g., "comp215-week01-intro-2017-danwallach"), returns true or false if that
    project is something we're trying to grade now, based on the specified prefix as well as the list of graders
    (to be ignored). Since we might be dealing with student groups, which can give themselves their own group names,
    this function defaults to True, unless it finds a reason to say False.
    """

    # This is inefficient, since we're not caching the
    # result, but performance doesn't really matter here.
    lower_case_ignore_list = [x.lower() for x in ignore_list]

    m = student_name_from(github_prefix, name).lower()
    return m != "" and name.startswith(github_prefix) and name != github_prefix and \
        m not in lower_case_ignore_list
