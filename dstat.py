import subprocess
import time


class SSHClient:

    def __init__(self, ssh_key, ssh_user, endpoint_ip):
        self.ssh_key = ssh_key
        self.ssh_user = ssh_user
        self.endpoint = endpoint_ip

    def run_command(self, cmd, wait=True):
        cmd = f'ssh -i {self.ssh_key} {self.ssh_user}@{self.endpoint} "{cmd}"'
        if wait:
            subprocess.Popen(cmd, shell=True).wait()
        else:
            subprocess.Popen(cmd, shell=True)

    def install_dstat(self):
        self.run_command("sudo yum install -y dstat")

    def prepare_dstat_dir(self, dstat_output_dir):
        self.output_dir = dstat_output_dir
        self.run_command(f"rm -rf {self.output_dir}; mkdir -p {self.output_dir}")

    def run_dstat(self, device, dstat_output_file):
        self.run_command(f"dstat --disk-tps -d -t --noheaders -o {self.output_dir}/{dstat_output_file} -D {device} > /dev/null", wait=False)

    def kill_dstat(self):
        self.run_command("pkill -9 dstat > /dev/null")

    def get_dstat_out(self, path):
        scp_cmd = f'scp -r -i {self.ssh_key} {self.ssh_user}@{self.endpoint}:{self.output_dir} {path}'
        subprocess.Popen(scp_cmd, shell=True).wait()
