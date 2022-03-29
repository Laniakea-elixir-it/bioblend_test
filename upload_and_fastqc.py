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
    parser.add_argument('-i', dest='wf_inputs', default='./input_files.json', help="JSON file containing input files URLs")
    parser.add_argument('--workflow-path', default='./quality_and_mapping.ga', dest='wf_path', help='Workflow path')
    parser.add_argument('--ssh-user', default='Pietro', dest='ssh_user', help='Galaxy vm ssh user')
    parser.add_argument('--ssh-key', default='~/.ssh/laniakea-robot.key', dest='ssh_key', help='Galaxy vm ssh key')
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
        upload = gi.tools.put_url(path=file_url, history_id=hist_id, file_name=file_name, file_type=file_type)
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
                'start':raw_job_metrics[2]['value'],
                'end':raw_job_metrics[1]['value']
            }

            # Build dictionary with metrics for each job
            jobs_metrics[job_id] = job_metrics

    return jobs_metrics


def install_dstat(ssh_user, ssh_key, galaxy_ip):
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "sudo yum install -y dstat"'
    subprocess.Popen(command, shell=True)


def dstat(ssh_user, ssh_key, galaxy_ip, output_file, device):
    dstat_command = f"dstat --disk-tps -d -t --noheaders -o {output_file} -D {device} > /dev/null"
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "{dstat_command}"'
    subprocess.Popen(command, shell=True)


def kill_dstat(ssh_user, ssh_key, galaxy_ip):
    command = f'ssh -i {ssh_key} {ssh_user}@{galaxy_ip} "pkill -9 dstat > /dev/null"'
    subprocess.Popen(command, shell=True)
    time.sleep(5)


def get_dstat_out(ssh_user, ssh_key, galaxy_ip, dstat_output_dir, output_dir):
    scp_command = f'scp -r -i {ssh_key} {ssh_user}@{galaxy_ip}:{dstat_output_dir} {output_dir}'
    subprocess.Popen(scp_command, shell=True)



if __name__ == '__main__':
    
    options = cli_options()

    # Define Galaxy instance
    gi = bioblend.galaxy.GalaxyInstance(url=options.galaxy_server, key=options.api_key)

    # Delete all histories to ensure there's enough free space
    history_client = bioblend.galaxy.histories.HistoryClient(gi)
    for history in history_client.get_histories():
        history_client.delete_history(history['id'], purge=True)

    # Create new history
    new_hist = gi.histories.create_history(name=options.hist_name)
    hist_id = new_hist['id']

    # Import workflow from file
    wf = gi.workflows.import_workflow_from_local_path(options.wf_path)
    wf_id = wf['id']

    # Remove dstat output dir if present and make a new one
    galaxy_ip = options.galaxy_server.lstrip("http://").rstrip("/")
    subprocess.Popen(f'ssh -i {options.ssh_key} {options.ssh_user}@{glaxy_ip} "rm -rf {options.dstat_output_dir}"', shell=True)
    subprocess.Popen(f'ssh -i {options.ssh_key} {options.ssh_user}@{galaxy_ip} "mkdir -p {options.dstat_output_dir}"', shell=True)

    # Install dstat
    install_dstat(options.ssh_user, options.ssh_key, galaxy_ip)

    # Start dstat monitoring
    kill_dstat(options.ssh_user, options.ssh_key, galaxy_ip)
    dstat_output_file = f'{options.dstat_output_dir}/dstat_out_upload.csv'
    dstat(options.ssh_user, options.ssh_key, galaxy_ip, dstat_output_file, options.dstat_device)

    # Upload input data and build dictionary for workflow
    wf_data = upload_and_build_data_input(inputs_path=options.wf_inputs, gi=gi, hist_id=hist_id, wf_id=wf_id)

    # Wait for dataset
    wait_for_dataset(gi, hist_id)

    # Get upload jobs metrics
    upload_jobs_metrics = get_job_metrics(gi, hist_id)

    # Write upload job metrics to file
    Path(options.output_dir).mkdir(parents=True, exist_ok=True)
    with open(f'{options.output_dir}/upload_jobs_metrics.json','w', encoding='utf-8') as f:
        json.dump(upload_jobs_metrics, f, ensure_ascii=False, indent=4)

    # Kill running dstat process and start new dstat process
    kill_dstat(options.ssh_user, options.ssh_key, galaxy_ip)
    dstat_output_file = f'{options.dstat_output_dir}/dstat_out_reference.csv'
    dstat(options.ssh_user, options.ssh_key, galaxy_ip, dstat_output_file, options.dstat_device)

    # Invoke reference workflow
    wf_invocation = gi.workflows.invoke_workflow(wf_id, inputs=wf_data, history_id=hist_id)
    wf_invocation_id = wf_invocation['id']
    invocation_client = bioblend.galaxy.invocations.InvocationClient(gi)
    invocation_client.wait_for_invocation(wf_invocation_id)

    # Get reference workflow job metrics
    wf_jobs_metrics = get_job_metrics(gi=gi, hist_id=hist_id, invocation_id=wf_invocation_id)

    # Write reference workflow job metrics to file
    with open(f'{options.output_dir}/wf_jobs_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(ref_wf_jobs_metrics, f, ensure_ascii=False, indent=4)

    # Kill dstat process
    kill_dstat(options.ssh_user, options.ssh_key, galaxy_ip)
