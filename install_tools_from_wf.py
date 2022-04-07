#! /usr/bin/env python3

# Import dependencies
import argparse
import bioblend.galaxy
import json

# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy install all workflows tools using bioblend')
    parser.add_argument('--galaxy-server', dest='galaxy_server', default='http://localhost', help='Galaxy server URL')
    parser.add_argument('--key', dest='api_key', default='not_very_secret_api_key', help='Galaxy user API key')
    parser.add_argument('--workflow-path', default='./quality_and_mapping.ga', dest='wf_path', help='Workflow path')
    return parser.parse_args()

def wf_tools_repo(wf_path):

    tool_list = list()
    with open(wf_path, 'r') as f:
        wf_dict = json.load(f)
    for i,o in wf_dict['steps'].items():
        try:
            install_info = o['tool_shed_repository']
            if install_info not in tool_list:
                tool_list.append(install_info)
        except:
            pass
    return tool_list

def install_tools(galaxy_server,api_key,wf_path):


    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=galaxy_server, key=api_key)
    
    #install galaxy tools
    install_tools = bioblend.galaxy.toolshed.ToolShedClient(gi)
    wf_repos = wf_tools_repo(wf_path)
    for i in wf_repos:
        tool_name = i['name']
        changeset_revision = i['changeset_revision']
        try:
            install_tools.install_repository_revision('https://'+i['tool_shed'],tool_name,i['owner'],changeset_revision,True,True,True,True,None)
        except bioblend.ConnectionError:
            pass
        print(f'Installing tool {tool_name} and its dependencies...')
        status = ''
        while status != 'Installed':
            installed_repos = install_tools.get_repositories()
            status = [repo['status'] for repo in installed_repos if repo['name']==tool_name and repo['changeset_revision']==changeset_revision][0]
        print(f'Tool {tool_name} installed successfully.')

if __name__ == '__main__':
    options = cli_options()
    install_tools(options.galaxy_server,options.api_key,options.wf_path)

