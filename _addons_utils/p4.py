import subprocess
import codecs


def is_process_success(process):
    if process is None:
        return False

    if process.returncode == 0:
        return True
    # process.stderr can be None or "" on success
    if process.stderr is not None and process.stderr:
        return False

    return False

class P4LogOutput:
    def __init__(self):
        self.logs = []

    def add_process_result(self, process: subprocess.CompletedProcess):
        def decode_output(output):
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            return codecs.unicode_escape_decode(output.encode("unicode_escape"))[0]

        if process.stdout:
            self.logs.append(decode_output(process.stdout))
        if process.stderr:
            self.logs.append(decode_output(process.stderr))

    def add_log(self, message: str):
        self.logs.append(message)
 
    def __str__(self):
        return "".join(self.logs)


def p4_edit(filepath: str, 
            changelist_name:str="default", 
            p4_output: P4LogOutput | None = None):
    # Check file status first
    result = subprocess.run(
        ["p4", "fstat", filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )
    
    if not is_process_success(result):
        if p4_output is not None:
            p4_output.add_process_result(result)
        return False

    # Check if file is synced to latest revision
    check_synced = subprocess.run(
        ["p4", "sync", "-n", filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    if check_synced.stdout: 
        if p4_output is not None:
            p4_output.add_log(f"Not synced to the latest revision!\n{filepath}")
        return False

    process = None
    if result.stdout:  
        # stdout is an empty string if not in depot
        process = subprocess.run(
            ["p4", "edit", "-c", changelist_name, filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
    else:
        process = subprocess.run(
            ["p4", "add", "-c", changelist_name, filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )

    if not is_process_success(process):
        if p4_output is not None:
            p4_output.add_process_result(result)
        return False

    return True


def p4_add(filepath: str, 
           changelist_name:str="default",
           p4_output: P4LogOutput | None = None):
    cmd = f"p4 add -c {changelist_name} -v {filepath}"
    process = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        check=False
    )
    if p4_output is not None:
        p4_output.add_process_result(process)

    if not is_process_success(process):
        return False

    return True

def use_p4():
    cmd = "p4 info"
    try:
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False
        )
        exit_code = process.returncode
        if exit_code == 0:
            return True
    except:  # in case p4 is not installed
        return False

    return False
