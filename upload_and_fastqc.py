#! /usr/bin/env python3

# Import dependencies
import argparse
import bioblend.galaxy
import json

################################################################################
# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy URL upload and FastQC test')
    parser.add_argument('--galaxy-server', dest='galaxy_server', default='http://localhost', help='Galaxy server URL')
    parser.add_argument('--key', dest='api_key', default='not_very_secret_api_key', help='Galaxy user API key')
    parser.add_argument('--history-name', default='mapping-test', dest='hist_name', help='New history name')
    parser.add_argument('-i', dest='inputs_path', default='./input_files.json', help="JSON file containing input files URLs")
    parser.add_argument('--workflow-path', default='./quality_and_mapping.ga', dest='wf_path', help='Workflow path')
    parser.add_argument('-o', default='./jobs_metrics.json', dest='output_file', help="Path in which jobs metrics are written")
    return parser.parse_args()


if __name__ == '__main__':
    
    options = cli_options()

    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=options.galaxy_server, key=options.api_key)

    # Create new history
    new_hist = gi.histories.create_history(name=options.hist_name)

    # Import workflow from file
    wf = gi.workflows.import_workflow_from_local_path(options.wf_path)
    workflow_id = wf['id']

    # Get input files url from inputs_path
    with open(options.inputs_path, 'r') as f:
        inputs_dict = json.load(f)
    
    # Initialize dictionary for wf input data
    data = dict()

    # Upload each file in history and put its id in the data dictionary
    for file_name, file_url in inputs_dict.items():
        upload = gi.tools.put_url(content=file_url, history_id=new_hist['id'], file_name=file_name)
        upload_id = upload['outputs'][0]['id']
        wf_input = gi.workflows.get_workflow_inputs(workflow_id, label=file_name)[0]
        data[wf_input] = {'id':upload_id, 'src':'hda'}
    

    wf_return = gi.workflows.invoke_workflow(wf['id'], inputs=data, history_id=new_hist['id'])
    print(wf_return)

    dataset_client = bioblend.galaxy.datasets.DatasetClient(gi)
    all_datasets = dataset_client.get_datasets(history_id=new_hist['id'])
    for dataset in all_datasets:
        dataset_client.wait_for_dataset(dataset['id'])

    job_client = bioblend.galaxy.jobs.JobsClient(gi)
    all_jobs = job_client.get_jobs(history_id=new_hist['id'])
    jobs_metrics = dict()

    for job in reversed(all_jobs):
        # Wait for the job to be finished
        job_client.wait_for_job(job['id'])

        # Get raw job metrics
        raw_job_metrics = job_client.get_metrics(job['id'])

        # Take useful job metrics
        job_metrics = {
            'runtime_value':raw_job_metrics[0]['value'],
            'runtime_raw_value':raw_job_metrics[0]['raw_value'],
            'start':raw_job_metrics[1]['value'],
            'end':raw_job_metrics[2]['value']
        }

        # Build dictionary with metrics for each job
        jobs_metrics[job['id']] = job_metrics
    
    with open(options.output_file, 'w', encoding='utf-8') as f:
        json.dump(jobs_metrics, f, ensure_ascii=False, indent=4)
