#!/usr/bin/python3

from urllib.request import urlretrieve, urlopen
from time import time, sleep

import os
import sys
import tarfile
import subprocess


TAR_URL = "https://s3.eu-central-1.amazonaws.com/devops-exercise/pandapics.tar.gz"
TAR_DEPLOYMENT_DIR = "/public/images"
DOCKER_COMPOSE_EXE = "/usr/local/bin/docker-compose"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
HEALTH_URL = "http://localhost:3000/health"
TIMEOUT_FOR_DEPLOYMENT = 15 # in seconds


def main():
    print("##### Deploying Ops Task @BigPanda Web Application #####")
    check_requirements(DOCKER_COMPOSE_EXE, DOCKER_COMPOSE_FILE)
    halt_old_deployment(DOCKER_COMPOSE_EXE)
    os.makedirs(TAR_DEPLOYMENT_DIR, exist_ok=True)
    download_and_extract_tar(TAR_URL, TAR_DEPLOYMENT_DIR)
    build_application(DOCKER_COMPOSE_EXE)
    run_deployment(DOCKER_COMPOSE_EXE)
    check_health(HEALTH_URL, timeout=TIMEOUT_FOR_DEPLOYMENT)


def write_without_newline(msg):
    """Writing to stdout without printing new line."""
    sys.stdout.write(msg)
    sys.stdout.flush()
    

def exit_if_failed(func):
    """Halt application if there is an exception or a func returned False."""
    def wrapper(*args, **kwargs):
        try:
            if not func(*args, **kwargs):
                sys.exit(1)
        except Exception:
            sys.exit(2)
    return wrapper


def print_task(msg, status=True):
    """Warp function with a task message and an ending status by default."""
    def run_task(func):
        def wrapper(*args, **kwargs):
            if status:
                write_without_newline(msg)
                try:
                    result = func(*args, **kwargs)
                    print("OK") if result else print("FAILED")
                    return result
                except Exception:
                    print("FAILED")
                    raise
            else:
                print(msg)
                return func(*args, **kwargs)
        return wrapper
    return run_task


@exit_if_failed
@print_task("Checking Requirements...")
def check_requirements(docker_compose_exe, docker_compose_file):
    if not os.path.isfile(docker_compose_exe):
        raise Exception("Please install docker-compose first!")
    if docker_compose_file not in os.listdir():
        raise Exception("{} wasn't found in the current directory!".format(DOCKER_COMPOSE_FILE))
    return True


@exit_if_failed
@print_task("Downloading Image Resources...")
def download_and_extract_tar(url, path):
    """Downloading a tar file and extract it on the giving path."""
    filename = os.path.basename(url)
    path_to_tar = os.path.join(path, filename)
    urlretrieve(url, filename=path_to_tar)
    tar = tarfile.open(path_to_tar)
    tar.extractall(path)
    os.remove(path_to_tar)
    return True


def run_docker_compose(exe, command, hide_stdout=False, hide_stderr=False, *args):
    """Run docker-compose with the giving command.
    You can set stdout/stderr in quit mode by setting them to True accordingly.
    You may add additional flags to the command via args.
    """
    with open(os.devnull, "w") as fnull:
        stdout = fnull if hide_stdout else None
        stderr = fnull if hide_stderr else None
        docker_compose_command = [exe, command]
        docker_compose_command.extend(args)
        return 0 == subprocess.run(docker_compose_command, stdout=stdout, stderr=stderr).returncode


@exit_if_failed
@print_task("Stopping Old Deployments If Exists...")
def halt_old_deployment(exe):
    """Stop docker-compose"""
    return run_docker_compose(exe, "down", True, True)


@exit_if_failed
@print_task("Building Application...", status=False)
def build_application(exe):
    """Build and pull latest tags for the application using docker compose in the foreground"""
    return run_docker_compose(exe, "build", False, False, "--pull")
    

@exit_if_failed
@print_task("Deploying Application Using Docker Compose...")
def run_deployment(exe):
    """Deploy application in the background using docker compose"""
    return run_docker_compose(exe, "up", True, True, "-d")
    

@exit_if_failed
@print_task("Checking Health Condition...")
def check_health(url, timeout=1):
    """Waiting for the application to be deployed and return True/False in response to it's status.
    If the application has yet been deployed when the timeout elapsed, assumes the deployment has failed.
    """
    timeout = time() + timeout
    while(timeout > time()):
        try:
            if urlopen(HEALTH_URL).status == 200:
                return True
            return False
        except Exception:
            sleep(0.5)
    return False


if __name__ == "__main__":
    main()
