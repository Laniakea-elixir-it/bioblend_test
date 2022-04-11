# bioblend-test
This repository contains two python scripts that use bioblend:

* [install_tools_from_wf.py](https://github.com/Laniakea-elixir-it/bioblend_test/blob/main/install_tools_from_wf.py) installs the tools required by a workflow;
* [run_workflow.py](https://github.com/Laniakea-elixir-it/bioblend_test/blob/main/run_workflow.py) runs the workflow in a Galaxy server. This script can also use [dstat](https://linux.die.net/man/1/dstat) to monitor disk I/O while the workflow is running.

Two files are needed:

* A Galaxy workflow file.
* A `.json` file containing information about the input data.

Clone this repository to run the scripts.


# install_tools_from_wf.py
To install the tools needed to run a workflow, a Galaxy workflow file is needed. Some examples can be found in the [workflows](https://github.com/Laniakea-elixir-it/bioblend_test/tree/main/workflows) directory.

## Script arguments

| Argument     | Description                  | Default                      |
| ------------ | ---------------------------- | ---------------------------- |
| `--endpoint` | Galaxy URL                   | http://localhost             |
| `--api-key`  | Galaxy admin API key         | not_very_secret_api_key      |
| `--wf-path`  | Path to the workflow.ga file | ./workflows/test_workflow.ga |

## Usage
To install tools and their dependencies, run:

```console
$ ./install_tools_from_wf.py --endpoint http://galaxy_url/ --api-key galaxy_api_key --wf-path /path/to/workflow.ga
```

# run_workflow.py
To run a workflow, a properly structured `.json` file containing information about the input data is needed.

## Input
Each input dataset is indicated by a key:value pair in the input `.json` file:

* The `key` corresponds to its respective input label in the galaxy workflow;
* The `value` is a dictionary containing the `file_url` and the `file_type`.

An example entry for the `.json` file is:
```json
{
    "1_reads": {
        "url":"https://raw.githubusercontent.com/Laniakea-elixir-it/general-reads-hg19/main/input_mate1.fastq",
        "file_type":"fastq"
    }
}
```

The [input_files.json](https://github.com/Laniakea-elixir-it/bioblend_test/blob/main/inputs/input_files.json) in this repository is an example of input file for a basic mapping workflow in Galaxy (e.g. [test_workflow.ga](https://github.com/Laniakea-elixir-it/bioblend_test/blob/main/workflows/test_workflow.ga)).

## Output
If the flag `--disk-metrics` is used, this script writes two json files: `upload_jobs_metrics.json` and `wf_jobs_metrics.json`, containing metrics about the upload and workflow jobs run repsectively. For each job run in Galaxy, a key:value pair is written in these file:

* The `key` corresponds to the job id;
* The `value` is a dictionary containing information about the respective job:
  * `tool_id`: id of the tool run by the job;
  * `runtime_value`: time used by the job;
  * `runtime_raw_value`: time in seconds used by the job;
  * `start`: job start time;
  * `end`: job end time.

An example of the `.json` file containing the jobs metrics is:
```json
{
    "fd1f25b49c9227b5": {
        "tool_id": "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.72+galaxy1",
        "runtime_value": "10 seconds",
        "runtime_raw_value": "10.0000000",
        "start": "2022-03-25 13:20:05",
        "end": "2022-03-25 13:20:15"
    }
}
```
These json files are written to the directory specified by the script argument `--metrics-output-dir`.
With the `--disk-metrics` flag, dstat is used in the Galaxy VM to log disk I/O metrics in the directory specified with the `--dstat-output-dir` argument. When the script ends, the output of dstat is copied to the same path specified in `--metrics-output-dir`.

## Script arguments

| Argument               | Description                                                        | Default                      |
| ------------           | ------------------------------------------------------------------ | ---------------------------- |
| `--endpoint`           | Galaxy URL                                                         | http://localhost             |
| `--api-key`            | Galaxy admin API key                                               | not_very_secret_api_key      |
| `--history-name`       | Name of the history where the workflow is run                      | wf-test                      |
| `--clean-histories`    | If specified, all histories will be purged before the workflow run | False                        |
| `-i`                   | `.json` input file                                                 | ./inputs/input_files.json    |
| `--wf-path`            | Path to the workflow.ga file                                       | ./workflows/test_workflow.ga |
| `--disk-metrics`       | If specified, disk metrics are measured with dstat                 | False                        |
| `--ssh-user`           | User name to run commands in the Galaxy VM via SSH                 | //                           |
| `--ssh-key`            | SSH key to run commands in the Galaxy VM                           | //                           |
| `--dstat-output-dir`   | Path in the Galaxy VM where dstat output is written                | ~/dstat_out                  |
| `--dstat-device`       | Device for which disk metrics are measured                         | vdb1                         |
| `--metrics-output-dir` | Local output directory where runtimes and disk metrics are written | ./                           |

## Usage
To upload files and run a workflow on a Galaxy instance, run:
```console
$ run_workflow.py --endpoint http://galaxy_url/ \
                  --api-key galaxy_api_key
                  -i /path/to/input_files.json \
                  --wf-path /path/to/workflow.ga
```

To measure runtimes and disk I/O while the workflow is running, more arguments are needed:
```console
$ run_workflow.py --endpoint http://galaxy_url/ \
                  --api-key galaxy_api_key
                  -i /path/to/input_files.json \
                  --wf-path /path/to/workflow.ga \
                  --disk-metrics \
                  --ssh-user galaxy_vm_ssh_user \
                  --ssh-key galaxy_vm_ssh_key \
                  --metrics-output-dir /path/to/metrics_output
```