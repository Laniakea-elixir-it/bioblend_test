#! /usr/bin/env python3

from pprint import pprint
import bioblend.galaxy
import bioblend.galaxy.objects

# Create GalaxyInstance object
server = "https://usegalaxy.eu"
api_key = "..."
gi = bioblend.galaxy.objects.GalaxyInstance(url=server, api_key=api_key)

# Create galaxy history
new_history = gi.histories.create(name="Prova Mapping")

# Upload fastq files
hist_mate1 = new_history.upload_file("data/input_mate1.fastq.gz")
hist_mate2 = new_history.upload_file("data/input_mate2.fastq.gz")

# Gest fastqc and bowtie2
fastqc_id = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.72+galaxy1"
bowtie2_id = "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2/2.4.2+galaxy0"

tools = bioblend.galaxy.objects.client.ObjToolClient(gi)

fastqc = tools.get(fastqc_id, io_details=True)
bowtie2 = tools.get(bowtie2_id, io_details=True)

# Run fastqc
fastqc.run(inputs={"format":"fastq.gz","name":"input_mate1.fastq.gz"}, history=new_history)
fastqc.run(inputs={"format":"fastq.gz","name":"input_mate2.fastq.gz"}, history=new_history)

# Run bowtie2
inputs = {'value': 'paired', 'inputs': [{'name':'input_mate1.fastq.gz'},{'name':'input_mate2.fastq.gz'}], 'reference_genome':'hg19'}
bowtie2.run(inputs=inputs,history=new_history)


