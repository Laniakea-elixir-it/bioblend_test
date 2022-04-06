#! /usr/bin/env python3

# Import dependencies
import argparse
import bioblend.galaxy
import json
import subprocess
import time
from pathlib import Path
import traceback
from dstat import DstatClient

################################################################################
# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy URL upload and FastQC test')
    parser.add_argument('--endpoint', dest='endpoint', default='http://localhost', help='Galaxy server URL')
    parser.add_argument('--api-key', dest='api_key', default='not_very_secret_api_key', help='Galaxy user API key')
    parser.add_argument('--history-name', default='wf-test', dest='history_name', help='New history name')
    parser.add_argument('--clean-histories', default=False, dest='clean_histories', action='store_true', help='If set, all histories will be deleted before running the workflow')
    parser.add_argument('-i', dest='wf_inputs_path', default='./input_files.json', help="JSON file containing input files URLs")
    parser.add_argument('--wf-path', default='./test_workflow.ga', dest='wf_path', help='Workflow path')
    parser.add_argument('--disk-metrics', default=False, dest='log_disk_metrics', action='store_true', help='If set, disk metrics are logged with dstat')
    parser.add_argument('--ssh-user', default='Pietro', dest='ssh_user', help='Galaxy vm ssh user')
    parser.add_argument('--ssh-key', default='~/.ssh/laniakea-robot.key', dest='ssh_key', help='Galaxy vm ssh key')
    parser.add_argument('--dstat-output-dir', default='~/dstat_out', dest='dstat_output_dir', help='dstat output dir')
    parser.add_argument('--dstat-device', default='vdb1', dest='dstat_device', help='dstat device to monitor')
    parser.add_argument('--metrics-output-dir', default='.', dest='metrics_output_dir', help="Path in which jobs metrics are written")
    return parser.parse_args()


def upload_and_build_data_input(inputs_path, galaxy_instance, history_id, workflow_id):
    with open(inputs_path, 'r') as f:
        inputs_dict = json.load(f)
    data = dict()
    for file_name, file_options in inputs_dict.items():
        file_url = file_options['url']
        file_type = file_options['file_type']
        upload = galaxy_instance.tools.put_url(file_url, history_id=history_id, file_name=file_name, file_type=file_type)
        upload_id = upload['outputs'][0]['id']
        wf_input = galaxy_instance.workflows.get_workflow_inputs(workflow_id, label=file_name)[0]
        data[wf_input] = {'id':upload_id, 'src':'hda'}

    # Wait for dataset
    wait_for_dataset(galaxy_instance, history_id)

    return data


def wait_for_dataset(galaxy_instance, history_id):
    dataset_client = bioblend.galaxy.datasets.DatasetClient(galaxy_instance)
    all_datasets = dataset_client.get_datasets(history_id=history_id)
    for dataset in all_datasets:
        dataset_client.wait_for_dataset(dataset['id'])


def get_job_metrics(galaxy_instance, history_id, invocation_id):
    job_client = bioblend.galaxy.jobs.JobsClient(galaxy_instance)
    wf_jobs = job_client.get_jobs(history_id=history_id)

    # Define filter for jobs
    if invocation_id is not None:
        invocation_client = bioblend.galaxy.invocations.InvocationClient(galaxy_instance)
        invocation_steps = invocation_client.show_invocation(invocation_id)['steps']
        jobs_filter = [step['job_id'] for step in invocation_steps]
    else:
        jobs_filter = [job['id'] for job in wf_jobs]

    jobs_metrics = dict()

    for job in wf_jobs:
        job_id = job['id']
        if job_id in jobs_filter:
            # Wait for the job to be finished
            job_client.wait_for_job(job_id)

            # Get raw job metrics
            raw_job_metrics = job_client.get_metrics(job_id)

            # Take useful job metrics
            job_metrics = {
                'tool_id':job['tool_id'],
                'runtime_value':raw_job_metrics[0]['value'],
                'runtime_raw_value':raw_job_metrics[0]['raw_value'],
                'start':raw_job_metrics[2]['value'],
                'end':raw_job_metrics[1]['value']
            }

            # Build dictionary with metrics for each job
            jobs_metrics[job_id] = job_metrics

    return jobs_metrics


def write_jobs_metrics(galaxy_instance, history_id, output_file, invocation_id=None):
    # Get upload jobs metrics
    upload_jobs_metrics = get_job_metrics(galaxy_instance, history_id, invocation_id)

    # Write upload job metrics to file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(f'{output_dir}/{output_file}','w', encoding='utf-8') as f:
        json.dump(upload_jobs_metrics, f, ensure_ascii=False, indent=4)


def create_history(galaxy_instance, history_name, clean_histories=False):
    # Delete all histories to ensure there's enough free space
    if clean_histories:
        history_client = bioblend.galaxy.histories.HistoryClient(galaxy_instance)
        for history in history_client.get_histories():
            history_client.delete_history(history['id'], purge=True)

    new_hist = galaxy_instance.histories.create_history(name=history_name)

    return new_hist['id']


def run_workflow(galaxy_instance, history_id, wf_path, wf_inputs_path, log_disk_metrics=False,
                 metrics_output_dir=None, dstat_output_dir=None, device=None, ssh_key=None, ssh_user=None):
    
    # Prepare endpoint to log disk metrics with dstat
    if log_disk_metrics:
        endpoint_ip = galaxy_instance.url.lstrip("http://").rstrip("/api")
        dstat_ssh_client = DstatClient(ssh_key, ssh_user, endpoint_ip)
        dstat_ssh_client.install_dstat()
        dstat_ssh_client.kill_dstat()
        prepare_dstat_dir(dstat_output_dir)
    
    # Import workflow from file
    wf = galaxy_instance.workflows.import_workflow_from_local_path(wf_path)
    workflow_id = wf['id']
    
    # Start logging disk metrics for upload
    if log_disk_metrics:
        dstat_ssh_client.run_dstat(dstat_output_dir, device, dstat_output_file='dstat_out_upload.csv')

    # Upload input data and build dictionary for workflow
    workflow_data = upload_and_build_data_input(wf_inputs_path, galaxy_instance, history_id, workflow_id)

    # Stop dstat, write upload jobs metrics and restart dstat for wf disk monitoring
    if log_disk_metrics:
        dstat_ssh_client.kill_dstat()
        write_jobs_metrics(galaxy_instance, history_id, output_file=f'{metrics_output_dir}/upload_jobs_metrics.json')
        dstat_ssh_client.run_dstat(device, dstat_output_file='dstat_out_wf.csv')
    
    # Invoke workflow
    wf_invocation = galaxy_instance.workflows.invoke_workflow(workflow_id, workflow_data, history_id=history_id)
    wf_invocation_id = wf_invocation['id']
    invocation_client = bioblend.galaxy.invocations.InvocationClient(galaxy_instance)
    invocation_client.wait_for_invocation(wf_invocation_id)

    # Stop dstat and write wf jobs metrics
    if log_disk_metrics:
        dstat_ssh_client.kill_dstat()
        write_jobs_metrics(galaxy_instance, history_id, metrics_output_dir,
                           metrics_output_file='wf_jobs_metrics.json', invocation_id=wf_invocation_id)
        dstat_ssh_client.get_dstat_out(metrics_output_dir)


def run_galaxy_tools(endpoint, api_key, history_name, wf_path, wf_inputs_path, clean_histories=False,
                     log_disk_metrics=False, metrics_output_dir=None, dstat_output_dir=None,
                     device=None, ssh_key=None, ssh_user=None):

    galaxy_instance = bioblend.galaxy.GalaxyInstance(url=endpoint, key=api_key)

    history_id = create_history(galaxy_instance, history_name, clean_histories)

    run_workflow(galaxy_instance, history_id, wf_path, wf_inputs_path, log_disk_metrics,
                 metrics_output_dir, dstat_output_dir, device, ssh_key, ssh_user)


if __name__ == '__main__':

    options = cli_options()

    run_galaxy_tools(options.endpoint, options.api_key, options.history_name, options.wf_path, options.wf_inputs_path, options.clean_histories,
                     options.log_disk_metrics, options.metrics_output_dir, options.dstat_output_dir, options.dstat_device, options.ssh_key, options.ssh_user)