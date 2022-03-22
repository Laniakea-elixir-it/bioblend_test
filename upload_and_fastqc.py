#! /usr/bin/env python3

# Import dependencies
import pathlib
import argparse
import bioblend.galaxy
from pathlib import Path

################################################################################
# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy URL upload and FastQC test')
    parser.add_argument('--galaxy-server', dest='galaxy_server', default='http://localhost', help='Galaxy server URL')
    parser.add_argument('--key', dest='api_key', default='not_very_secret_api_key', help='Galaxy user API key')
    parser.add_argument('--history-name', default='mapping-test', dest='hist_name', help='New history name')
    parser.add_argument('-f1', dest='file_url_1', default='https://raw.githubusercontent.com/Laniakea-elixir-it/general-reads-hg19/main/input_mate1.fastq', help='Input file URL')
    parser.add_argument('-f2', dest='file_url_2', default='https://raw.githubusercontent.com/Laniakea-elixir-it/general-reads-hg19/main/input_mate2.fastq',help='Input file URL')
    parser.add_argument('--workflow-path', default='./quality_and_mapping.ga', dest='wf_path', help='Workflow path')
    return parser.parse_args()


if __name__ == '__main__':
    
    options = cli_options()

#    print(options.dir_input)
#    files = 
    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=options.galaxy_server, key=options.api_key)

    # Create new history
    new_hist = gi.histories.create_history(name=options.hist_name)

    filenames = {}
    # Upload file to history
    upload_1 = gi.tools.put_url(content=options.file_url_1, history_id=new_hist['id'], file_name="reads_1")
    upload_2 = gi.tools.put_url(content=options.file_url_2, history_id=new_hist['id'], file_name="reads_2")
    upload_1_info = upload_1['outputs'][0]
    upload_2_info = upload_2['outputs'][0]
    upload_id_1 = upload_1_info['id']
    upload_id_2 = upload_2_info['id']
    # Import workflow from file
    wf = gi.workflows.import_workflow_from_local_path(options.wf_path)
    workflow_id = wf['id']

    input_1 = gi.workflows.get_workflow_inputs(workflow_id, label='1_reads')[0]
    input_2 = gi.workflows.get_workflow_inputs(workflow_id, label='2_reads')[0]
    # Define workflow input
    data = {
            input_1: {'id':upload_id_1, 'src':'hda'},
            input_2: {'id':upload_id_2, 'src':'hda'}
    }

    wf_return = gi.workflows.invoke_workflow(wf['id'], inputs=data, history_id=new_hist['id'])
    print(wf_return)

    wf_details = bioblend.galaxy.invocations.InvocationClient(gi)
    jobs_details = bioblend.galaxy.jobs.JobsClient(gi)
    wf_details_output = wf_details.wait_for_invocation(wf_return['id']) 
    print(wf_details_output)
    ## get all history jobs
    all_jobs = jobs_details.get_jobs(history_id=new_hist['id'])
    print('------------------------------------ALL_JOBS---------------------------')
    print(all_jobs)
    for i in reversed(all_jobs):
        print(i['tool_id'])
        print(jobs_details.wait_for_job(i['id']))
        print(jobs_details.get_metrics(i['id']))
        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print('------------------------------------------------------------------------')
 #   job_infos = jobs_details.wait_for_job(wf_details_output['steps'][2]['job_id']) 
 #   
 #   jobs_metrics = jobs_details.get_metrics(wf_details_output['steps'][2]['job_id'])
    
 #   print(job_infos)
    
    print("-----------------------------------------------------------------------------------------------------------------")
    
 #   print(jobs_metrics)
