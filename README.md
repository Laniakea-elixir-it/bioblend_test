# bioblend-test
This script uploads a fastq file from URL and run FastQC in a Galaxy server. In order to run, it needs the `test_worflow.ga` file in this repository.\
Git clone this repo to run the script.

# Usage
From the command line, run:
```bash
upload_and_fastqc.py --galaxy-server server \
                     --key api_key \
                     --history-name history_name \
                     --file-url URL \
                     --file-name filename.fastq \
                     --workflow-path /path/to/test_workflow.ga 
```