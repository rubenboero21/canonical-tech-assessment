#!/usr/bin/env python3

"""
Simple script to gather some data about a disk to verify it's seen by the OS
and is properly represented. Defaults to 'sda' if no disk is specified.
"""

import os
import sys
import time
import subprocess

DISK = "sda"
STATUS = 0


def check_return_code(retval, message, *output):
    """
    Check the return code of a command and handle errors.
    If the return code is non-zero, print an error message and update the STATUS.
    
    Parameters:
    retval (int): The return code of the command.
    message (str): The error message to print if retval is non-zero.
    output (tuple): Additional output to print in case of an error.
    """
    global STATUS
    if retval != 0:
        print(f"ERROR: retval {retval} : {message}", file=sys.stderr)
        if STATUS == 0:
            STATUS = retval
        for item in output:
            print(f"output: {item}")


def main(disk):
    global STATUS

    nvdimm = "pmem"
    if nvdimm in disk:
        print(f"Disk {disk} appears to be an NVDIMM, skipping")
        sys.exit(STATUS)

    # Check /proc/partitions, exit with fail if disk isn't found
    retval = subprocess.call(['grep', '-w', '-q', disk, '/proc/partitions'])
    check_return_code(retval, f"Disk {disk} not found in /proc/partitions")

    # Next, check /proc/diskstats
    retval = subprocess.call(['grep', '-w', '-q', '-m', '1', disk, '/proc/diskstats'])
    check_return_code(retval, f"Disk {disk} not found in /proc/diskstats")

    # Verify the disk shows up in /sys/block/
    retval = subprocess.call(['ls', f'/sys/block/*{disk}*'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    check_return_code(retval, f"Disk {disk} not found in /sys/block")

    # Verify there are stats in /sys/block/$DISK/stat
    if not os.path.isfile(f'/sys/block/{disk}/stat') or os.path.getsize(f'/sys/block/{disk}/stat') == 0:
        check_return_code(1, f"stat is either empty or nonexistent in /sys/block/{disk}/")

    # Get some baseline stats for use later
    proc_stat_begin = subprocess.getoutput(f'grep -w -m 1 {disk} /proc/diskstats')
    sys_stat_begin = open(f'/sys/block/{disk}/stat').read()

    # Generate some disk activity using hdparm -t
    subprocess.call(['hdparm', '-t', f'/dev/{disk}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Sleep 5 to let the stats files catch up
    time.sleep(5)

    # Make sure the stats have changed:
    proc_stat_end = subprocess.getoutput(f'grep -w -m 1 {disk} /proc/diskstats')
    sys_stat_end = open(f'/sys/block/{disk}/stat').read()

    if proc_stat_begin != proc_stat_end:
        check_return_code(0, f"Stats in /proc/diskstats did not change", proc_stat_begin, proc_stat_end)
    else:
        check_return_code(1, f"Stats in /proc/diskstats did not change", proc_stat_begin, proc_stat_end)

    if sys_stat_begin != sys_stat_end:
        check_return_code(0, f"Stats in /sys/block/{disk}/stat did not change", sys_stat_begin, sys_stat_end)
    else:
        check_return_code(1, f"Stats in /sys/block/{disk}/stat did not change", sys_stat_begin, sys_stat_end)

    if STATUS == 0:
        print(f"PASS: Finished testing stats for {disk}")

    sys.exit(STATUS)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        DISK = sys.argv[1]

    main(DISK)
