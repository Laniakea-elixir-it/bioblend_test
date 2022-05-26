# Disk I/O comparison with and without encryption
This repository contains the scripts used to run a workflow multiple times on a Galaxy instance, collecting data
about the workflow runtime and the disk read/write speed during the execution of the workflow.

## Example usage
In our usecase, two instances of the `wf_disk_test.sh` script were run at the same time targetting two Galaxy
instances, one with and one without disk encryption.
Once the two scripts ended, the collected metrics were then preprocessed and visualized through the `plots.py`
script, which produces a plot illustrating the difference between runtimes and disk read/write speed between the
two virtual machines.


## Collect disk metrics
The bash script `wf_disk_test.sh` uses the [run_workflow.py](https://github.com/Laniakea-elixir-it/bioblend_test/blob/main/run_workflow.py)
script to run a workflow multiple times on a Galaxy instance, retrieving runtimes and disk metrics when the
workflow is ended.

To organize data correctly for subsequent usage, a main directory containing metrics for both the VMs should be
created, with two sub-directories (one for each VM):
```console
$ mkdir metrics_data                      # main directory
$ mkdir metrics_data/metrics              # directory for metrics of non encrypted VM
$ mkdir metrics_data/metrics_encrypted    # directory for metrics of encrypted VM
```
The two sub-directories must be named `metrics` and `metrics_encrytped` for the script `plots.py` to work.

Once main directory tree is created, the script can be run specifying the required arguments. For example,
to run the workflow 50 times on the encrypted VM using the provided `input_files.json` and the workflow mapping
the input files to the hg38 reference genome with bowtie2:
```console
$ cd /path/to/this/repository/tests
$ nohup ./wf_disk_test.sh --endpoint http://encrypted_galaxy_instance_url \
                          --api-key galaxy_api_key \
                          -i ./input_files.json \
                          --wf-path ../workflows/bowtie2_mapping.ga \
                          --ssh-user galaxy_vm_ssh_user \
                          --ssh-key galaxy_vm_ssh_key \
                          --device monitored_device \
                          -o /path/to/metrics_data/metrics_encrypted \
                          --iterations 50 > /path/to/metrics_data/metrics_encrypted/test.log
```

To run the test also on the non encrypted VM, change the script arguments accordingly, specifing
`-o /path/to/metrics_data/metrics` as the output directory argument.

Once the tests are finished, the resulting directory tree should be like this:
```console
$ tree /path/to/metrics_data
metrics_data/
├── metrics
│   ├── metrics1
│   │   ├── dstat_out1
│   │   │   ├── dstat_out_upload.csv
│   │   │   └── dstat_out_wf.csv
│   │   ├── upload_jobs_metrics.json
│   │   └── wf_jobs_metrics.json
│   ├── metrics2
│   │   ├── dstat_out2
...
└── metrics_encrypted
    ├── metrics1
    │   ├── dstat_out1
    │   │   ├── dstat_out_upload.csv
    │   │   └── dstat_out_wf.csv
    │   ├── upload_jobs_metrics.json
    │   └── wf_jobs_metrics.json
    ├── metrics2
    │   ├── dstat_out2
```


## Plot disk metrics
Once the data has been collected for both machines, two types of figures can be produced with the `plots.py` script.

1. A figure containing 5 plots comparing distributions between the two VMs:
    a. A boxplot comparing runtimes during the workflow.
    b. An histogram comparing read speed during the workflow.
    c. An histogram comparing write speed during the workflow.
    d. A boxplot comparing average read speed during the workflow.
    e. A boxplot comparing average write speed during the workflow.
2. A figure containing 3 plots, namely plot `a`,`d` and `e` described in the previous figure.

To save this figure to a file, run the `plots.py` script specifying the main directory containing the metrics:
```console
$ ./plots.py -i /path/to/metrics_data/ --title 'Test plot' -o test_plot.png
```