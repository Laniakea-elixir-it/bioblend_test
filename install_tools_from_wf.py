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
    repos = wf_tools_repo(wf_path)
    for i in repos: 
        install_tools.install_repository_revision('https://'+i['tool_shed'],i['name'],i['owner'],i['changeset_revision'],True,True,True,True,None)

if __name__ == '__main__':
    options = cli_options()
    install_tools(options.galaxy_server,options.api_key,options.wf_path)

