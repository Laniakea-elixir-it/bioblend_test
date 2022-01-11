#! /usr/bin/env python3

# Import dependencies
import argparse
import bioblend.galaxy

################################################################################
# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy URL upload and FastQC test')
    parser.add_argument('--galaxy-server', dest='galaxy_server', help='Galaxy server URL')
    parser.add_argument('--key', dest='api_key', help='Galaxy user API key')
    parser.add_argument('--history-name', default='Test history', dest='hist_name', help='New history name')
    parser.add_argument('--file-url', dest='file_url', help='Input file URL')
    parser.add_argument('--file-name', default='test_file.fastq', dest='file_name', help='File name for Galaxy history')
    parser.add_argument('--workflow-path', default='./test_workflow.ga', dest='wf_path', help='Workflow path')
    return parser.parse_args()



if __name__ == '__main__':
    
    options = cli_options()

    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=options.galaxy_server, key=options.api_key)

    # Create new history
    new_hist = gi.histories.create_history(name=options.hist_name)

    # Upload file to history
    upload = gi.tools.put_url(content=options.file_url, history_id=new_hist['id'], file_name=options.file_name)
    upload_info = upload['outputs'][0]
    upload_id = upload_info['id']

    # Import workflow from file
    wf = gi.workflows.import_workflow_from_local_path(options.wf_path)

    # Define workflow input
    inputs = {0:{'id':upload_id, 'src':'hda'}}
    wf_return = gi.workflows.invoke_workflow(wf['id'], inputs=inputs, history_id=new_hist['id'])
    