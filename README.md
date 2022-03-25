# bioblend-test
This python script uses bioblend to run a workflow in a Galaxy server. It needs two files:

* A Galaxy workflow file.
* A `.json` file containing information about the input data.

## Input
Each input dataset is indicated by a key:value pair in the dataset:

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

The [input_files.json](https://github.com/Laniakea-elixir-it/bioblend-test/blob/main/input_files.json) in this repository is an example of input file for a basic mapping workflow in Galaxy (e.g. [bwa_quality_and_mapping.ga](https://github.com/Laniakea-elixir-it/bioblend-test/blob/main/bwa_quality_and_mapping.ga) in this same repository).

## Output
This script outputs a `.json` file containing metrics about the jobs run. For each job run in Galaxy, a key:value pair is written in this file:

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
        "start": "2022-03-25 13:20:15",
        "end": "2022-03-25 13:20:05"
    }
}
```

# Usage
Clone this repo to run the script.

From the command line, run:
```bash
upload_and_fastqc.py --galaxy-server server \
                     --key api_key \
                     --history-name history_name \
                     -i input_files.json \
                     --workflow-path /path/to/workflow.ga \
                     -o jobs_metrics.json
```
