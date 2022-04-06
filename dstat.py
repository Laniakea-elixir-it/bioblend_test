import subprocess
import time


class DstatClient:

    def __init__(self, ssh_key, ssh_user, endpoint_ip):
        self.ssh_key = ssh_key
        self.ssh_user = ssh_user
        self.endpoint = endpoint_ip

    def build_command(self, cmd):
        return command = f'ssh -i {self.ssh_key} {self.ssh_user}@{self.endpoint} "{cmd}"'

    def install_dstat(self):
        cmd = self.build_command("sudo yum install -y dstat")
        subprocess.Popen(cmd, shell=True)

    def prepare_dstat_dir(self, dstat_output_dir):
        self.output_dir = dstat_output_dir
        cmd = self.build_command("rm -rf {self.output_dir}; mkdir -p {self.output_dir}")
        subprocess.Popen(cmd, shell=True)

    def run_dstat(self, device, dstat_output_file):
        cmd = self.build_command(f"dstat --disk-tps -d -t --noheaders -o {self.output_dir}/{dstat_output_file} -D {device} > /dev/null")
        subprocess.Popen(cmd, shell=True)

    def kill_dstat(self):
        cmd = self.build_command("pkill -9 dstat > /dev/null")
        subprocess.Popen(cmd, shell=True)
        time.sleep(5)

    def get_dstat_out(self, path):
        scp_cmd = f'scp -r -i {self.ssh_key} {self.ssh_user}@{self.endpoint}:{self.output_dir} {path}'
        subprocess.Popen(scp_cmd, shell=True)
