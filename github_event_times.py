# github_event_times.py
# Dan Wallach <dwallach@rice.edu>
# Available subject to the Apache 2.0 License
# https://www.apache.org/licenses/LICENSE-2.0

import argparse
import pprint
from github_config import *
from github_scanner import *


# https://stackoverflow.com/questions/16259923/how-can-i-escape-latex-special-characters-inside-django-templates
def tex_escape(text: str) -> str:
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key=lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)


parser = argparse.ArgumentParser(description='Get event timestamps from a GitHub repo.')
parser.add_argument('--tiny',
                    default=False,
                    action="store_true",
                    help='Uses LaTeX footnotesize to make the table smaller')
parser.add_argument('--longtable',
                    default=False,
                    action="store_true",
                    help='Generates a table with the LaTeX longtable package')
parser.add_argument('--token',
                    nargs=1,
                    default=[default_github_token],
                    help='GitHub API token')
parser.add_argument('--org',
                    nargs=1,
                    default=[default_github_organization],
                    help='GitHub organization to scan, default: ' + default_github_organization)
parser.add_argument('repo',
                    nargs='+',
                    default="",
                    help='repo to query, no default')

args = parser.parse_args()

github_repos = args.repo
github_organization = args.org[0]
github_token = args.token[0]
use_longtable = args.longtable
use_footnotesize = args.tiny

pp = pprint.PrettyPrinter(indent=2)


for repo in github_repos:
    response = parallel_get_github_endpoint_paged_list("repos/%s/%s/events" % (github_organization, repo), github_token)
    event_list = [x for x in response if x['type'] == 'PushEvent']

    if use_longtable:
        if use_footnotesize:
            print("{\\footnotesize")
        print("\\begin{longtable}{llp{3in}l}")
        print("{\\bf GitHub ID} & {\\bf Commit ID} & {\\bf Comment} & {\\bf GitHub push time} \\\\")
        print("\\hline")
        print("\\endhead")
        print("\\hline")
        if use_footnotesize:
            print("\\caption{Events for " + repo + " \\label{events-" + repo + "}}")
        else:
            print("\\caption{Events for " + repo + " \\label{events-" + repo + "}}")
        print("\\endlastfoot")
        print("\\hline")
        print("\\\\")
        print("\\caption{Events for " + repo + "}")
        print("\\endfoot")
    else:
        print("\\begin{table}")
        if use_footnotesize:
            print("{\\footnotesize")
        print("\\begin{tabular}{llp{3in}l}")
        print("{\\bf GitHub ID} & {\\bf Commit ID} & {\\bf Comment} & {\\bf GitHub push time} \\\\")
        print("\\hline")
    for event in event_list:
        try:
            github_id = event['actor']['login']
            date = localtime_from_iso_datestr(event['created_at'])
            commits = event['payload']['commits']
            for commit in commits:
                commit_message = tex_escape(commit['message'].splitlines()[0])  # only the first line if multiline
                commit_hash = commit['sha'][0:7]  # only the first 7 characters: how GitHub reports commitIDs on the web
                print("%s & {\\tt %s} & %s & {\\tt %s} \\\\" % (github_id, commit_hash, commit_message, date))
        except KeyError:
            print("Error: malformed event!")
            pp.pprint(event)

    if use_longtable:
        print("\\end{longtable}")
        if use_footnotesize:
            print("} % end of footnotesize")
    else:
        print("\\hline")
        print("\\end{tabular}")
        if use_footnotesize:
            print("} % end of footnotesize")
        print("\\caption{Events for " + repo + " \\label{events-" + repo + "}}")
        print("\\end{table}")
    print()
