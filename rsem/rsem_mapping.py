#! /usr/bin/env python3

# Import dependencies
import argparse
import bioblend.galaxy
import json
import subprocess
import requests
import time

################################################################################
# COMMAND LINE OPTIONS
def cli_options():
    parser = argparse.ArgumentParser(description='Galaxy URL upload and FastQC test')
    parser.add_argument('--galaxy-server', dest='galaxy_server', default='http://localhost', help='Galaxy server URL')
    parser.add_argument('--key', dest='api_key', default='not_very_secret_api_key', help='Galaxy user API key')
    parser.add_argument('--history-name', default='mapping-test', dest='hist_name', help='New history name')
    parser.add_argument('--ref-wf-inputs', dest='ref_wf_inputs', default='./ref_wf_inputs.json', help='JSON file containing input files URLs to build ref')
    parser.add_argument('--rsem-wf-inputs', dest='rsem_wf_inputs', default='./rsem_wf_inputs.json', help='JSON file containing input files URLs to map')
    parser.add_argument('--ref-wf', default='./build_rsem_reference.ga', dest='ref_wf_path', help='Reference building workflow path')
    parser.add_argument('--rsem-wf', default='./rsem-bowtie_quality_and_mapping', dest='rsem_wf_path', help='RSEM mapping workflow path')
    parser.add_argument('--job-conf-path', default='/home/galaxy/galaxy/config/job_conf.xml', dest='job_conf_path', help='Galaxy job conf path')
    parser.add_argument('--ssh-user', default='Pietro', dest='ssh_user', help='Galaxy vm ssh user')
    parser.add_argument('--ssh-key', default='~/.ssh/laniakea-robot.key', dest='ssh_key', help='Galaxy vm ssh key')
    parser.add_argument('--threads', nargs='+', default=[1,2,4,8], dest='threads', help='Threads for mapping')
    parser.add_argument('--dstat-output-dir', default='~/dstat_out', dest='dstat_output_dir', help='dstat output dir')
    parser.add_argument('--dstat-device', default='vdb1', dest='dstat_device', help='dstat device to monitor')
    parser.add_argument('--output-dir', default='.', dest='output_dir', help="Path in which jobs metrics are written")
    return parser.parse_args()


def upload_and_build_data_input(inputs_path, gi, hist_id, wf_id):
    with open(inputs_path, 'r') as f:
        inputs_dict = json.load(f)
    data = dict()
    for file_name, file_options in inputs_dict.items():
        file_url = file_options['url']
        file_type = file_options['file_type']
        upload = gi.tools.put_url(content=file_url, history_id=hist_id, file_name=file_name, file_type=file_type)
        upload_id = upload['outputs'][0]['id']
        wf_input = gi.workflows.get_workflow_inputs(wf_id, label=file_name)[0]
        data[wf_input] = {'id':upload_id, 'src':'hda'}
    return data 


def wait_for_dataset(gi, hist_id):
    dataset_client = bioblend.galaxy.datasets.DatasetClient(gi)
    all_datasets = dataset_client.get_datasets(history_id=hist_id)
    for dataset in all_datasets:
        dataset_client.wait_for_dataset(dataset['id'])


def get_job_metrics(gi, hist_id, invocation_id=None):
    job_client = bioblend.galaxy.jobs.JobsClient(gi)
    wf_jobs = job_client.get_jobs(history_id=hist_id)
    #print(wf_jobs)

    # Define filter for jobs
    if invocation_id is not None:
        invocation_client = bioblend.galaxy.invocations.InvocationClient(gi)
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
                'start':raw_job_metrics[1]['value'],
                'end':raw_job_metrics[2]['value']
            }

            # Build dictionary with metrics for each job
            jobs_metrics[job_id] = job_metrics
 
    return jobs_metrics


def update_job_conf(ssh_user, ssh_key, galaxy_server, job_conf_path, thread):
    galaxy_ip = galaxy_server.lstrip("http://").rstrip("/")
    sed_command = f"""sed -i '/local_slots/ s/[0-9]\+/{thread}/' {job_conf_path}"""
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "sudo {sed_command}"'
    subprocess.Popen(command, shell=True)

def dstat(ssh_user, ssh_key, galaxy_server, output_file, device):
    galaxy_ip = galaxy_server.lstrip("http://").rstrip("/")
    dstat_command = f"dstat --disk-tps -d -t --noheaders -o {output_file} -D {device} > /dev/null"
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "{dstat_command}"'
    subprocess.Popen(command, shell=True)

def kill_dstat(ssh_user, ssh_key, galaxy_server):
    galaxy_ip = galaxy_server.lstrip("http://").rstrip("/")
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "pkill -9 dstat > /dev/null"'
    subprocess.Popen(command, shell=True)
    time.sleep(5)

def get_dstat_out(ssh_user, ssh_key, galaxy_server, dstat_output_dir, output_dir):
    galaxy_ip = galaxy_server.lstrip("http://").rstrip("/")
    scp_command = f'scp -r -i {ssh_key} {ssh_user}@{galaxy_ip}:{dstat_output_dir} {output_dir}'
    subprocess.Popen(scp_command, shell=True)


if __name__ == '__main__':
    
    options = cli_options()

    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=options.galaxy_server, key=options.api_key)

    # Create new history
    new_hist = gi.histories.create_history(name=options.hist_name)
    hist_id = new_hist['id']

    # Import workflows
    ref_wf = gi.workflows.import_workflow_from_local_path(options.ref_wf_path)
    ref_wf_id = ref_wf['id']
    ref_wf_steps = ref_wf['number_of_steps']
    rsem_wf = gi.workflows.import_workflow_from_local_path(options.rsem_wf_path)
    rsem_wf_id = rsem_wf['id']
    rsem_wf_steps = rsem_wf['number_of_steps']

    # Make dstat output dir
    galaxy_ip = options.galaxy_server.lstrip("http://").rstrip("/")
    subprocess.Popen(f'ssh -i {options.ssh_key} {options.ssh_user}@{galaxy_ip} "mkdir -p {options.dstat_output_dir}"', shell=True)

    # Start dstat monitoring
    kill_dstat(options.ssh_user, options.ssh_key, options.galaxy_server)
    dstat_output_file = f'{options.dstat_output_dir}/dstat_out_upload.csv'
    dstat(options.ssh_user, options.ssh_key, options.galaxy_server, dstat_output_file, options.dstat_device)

    # Upload reference build input data and build dictionary for workflows
    ref_wf_data = upload_and_build_data_input(inputs_path=options.ref_wf_inputs, gi=gi, hist_id=hist_id, wf_id=ref_wf_id)
    rsem_wf_data = upload_and_build_data_input(inputs_path=options.rsem_wf_inputs, gi=gi, hist_id=hist_id, wf_id=rsem_wf_id)

    # Wait for datasets to be uploaded
    wait_for_dataset(gi, hist_id)

    # Get upload jobs metrics
    upload_jobs_metrics = get_job_metrics(gi, hist_id)

    # Write upload job metrics to file
    with open(f'{options.output_dir}/upload_jobs_metrics.json','w', encoding='utf-8') as f:
        json.dump(upload_jobs_metrics, f, ensure_ascii=False, indent=4)

    # Kill running dstat process and start new dstat process
    kill_dstat(options.ssh_user, options.ssh_key, options.galaxy_server)
    dstat_output_file = f'{options.dstat_output_dir}/dstat_out_reference.csv'
    dstat(options.ssh_user, options.ssh_key, options.galaxy_server, dstat_output_file, options.dstat_device)

    # Invoke reference workflow
    ref_wf_invocation = gi.workflows.invoke_workflow(ref_wf_id, inputs=ref_wf_data, history_id=hist_id)
    ref_wf_invocation_id = ref_wf_invocation['id']
    invocation_client = bioblend.galaxy.invocations.InvocationClient(gi)
    invocation_client.wait_for_invocation(ref_wf_invocation_id)

    # Get reference workflow job metrics
    ref_wf_jobs_metrics = get_job_metrics(gi=gi, hist_id=hist_id, invocation_id=ref_wf_invocation_id)

    # Write reference workflow job metrics to file    
    with open(f'{options.output_dir}/reference_jobs_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(ref_wf_jobs_metrics, f, ensure_ascii=False, indent=4)

    # Kill dstat process
    kill_dstat(options.ssh_user, options.ssh_key, options.galaxy_server)

    # Get job id of the job that built the reference
    ref_job_id = list(ref_wf_jobs_metrics.keys())[0]

    # Get output id of the built reference
    job_client = bioblend.galaxy.jobs.JobsClient(gi)
    ref_job_output_id = job_client.get_outputs(ref_job_id)[0]['dataset']['id']

    # Add reference to RSEM workflow inputs
    rsem_ref_wf_input = gi.workflows.get_workflow_inputs(rsem_wf_id, label='rsem_ref')[0]
    rsem_wf_data[rsem_ref_wf_input] = {'id':ref_job_output_id, 'src':'hda'}

    for thread in options.threads:
        # Update job_conf.xml
        update_job_conf(options.ssh_user, options.ssh_key, options.galaxy_server, options.job_conf_path, thread)

        # Restart galaxy
        galaxy_ip = options.galaxy_server.lstrip("http://").rstrip("/")
        restart_command = f'ssh -i {options.ssh_key} {options.ssh_user}@{galaxy_ip} "sudo systemctl restart galaxy"'
        subprocess.Popen(restart_command, shell=True)

        # Check that galaxy is available
        status_code = 502
        while status_code != 200:
            r = requests.get(options.galaxy_server)
            status_code = r.status_code
        time.sleep(120)

        # Kill running dstat and start new dstat process
        dstat_output_file = f'{options.dstat_output_dir}/dstat_out_rsem_{thread}thread.csv'
        dstat(options.ssh_user, options.ssh_key, options.galaxy_server, dstat_output_file, options.dstat_device)

        # Invoke rsem workflow
        rsem_wf_invocation = gi.workflows.invoke_workflow(rsem_wf_id, inputs=rsem_wf_data, history_id=hist_id)
        rsem_wf_invocation_id = rsem_wf_invocation['id']
        invocation_client.wait_for_invocation(rsem_wf_invocation_id)

        # Get rsem workflow metrics
        rsem_wf_jobs_metrics = get_job_metrics(gi, hist_id, invocation_id=rsem_wf_invocation_id)

        # Write rsem workflow job metrics to file
        with open(f'{options.output_dir}/rsem_jobs_metrics_{thread}thread.json','w', encoding='utf-8') as f:
            json.dump(rsem_wf_jobs_metrics, f, ensure_ascii=False, indent=4)
        
        # Kill last dstat process
        kill_dstat(options.ssh_user, options.ssh_key, options.galaxy_server)

    get_dstat_out(options.ssh_user, options.ssh_key, options.galaxy_server, options.dstat_output_dir, options.output_dir)
