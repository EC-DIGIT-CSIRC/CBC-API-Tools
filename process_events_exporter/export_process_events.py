#!/usr/bin/env python3

# *********************************************************************
# Copyright (EC DIGIT CSIRC 2022). Licensed under the EUPL-1.2 or later
# *********************************************************************

"""Script to export the Events related to a process.

Based on Carbon Black Cloud API SDK it searches the Events within a defined timeframe related to a process
to export them to a CSV file for latter processing.
"""

import logging
import argparse
import os
import sys
from events.exporter import CBCProcessEventsExporter
from tqdm.contrib.logging import logging_redirect_tqdm

log = logging.getLogger(__name__)

def build_arg_parser():
    """Creates an Argument parser

    Creates an Argument parser with the following arguments:
    - profile: Carbon Black file profile to use. https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication/
    - guid: Process GUID.
    - start: When to start the result search. ISO 8601 timestamp, e.g. YYYY-MM-DDTHH:mm:ssZ
    - end: When to end the result search. ISO 8601 timestamp, e.g. YYYY-MM-DDTHH:mm:ssZ
    - follow_childprocs: Number of nesting levels to follow children processes to build and the process tree.
    - summary: Path to the JSON file that contains the attributes of the different event types to be included in the summary column.
    - outfile: Path to the CSV file where to export the events.
    - verbose: Flag to enable debug logging.
    """

    parser = argparse.ArgumentParser(description='Process Event Exporter')

    parser.add_argument("--profile", help="profile to connect", default="dev")
    parser.add_argument("--guid", help="Process GUID", required=True)
    parser.add_argument("--start", help="When to start the result search. ISO 8601 timestamp, e.g. YYYY-MM-DDTHH:mm:ssZ", required=True)
    parser.add_argument("--end", help="When to end the result search. ISO 8601 timestamp, e.g. YYYY-MM-DDTHH:mm:ssZ", required=True)
    parser.add_argument("--follow_childprocs", help="Number of nesting levels to follow children processes to build and the process tree", default=0)
    parser.add_argument("--summary", help="Path to the file that contains the attributes of the different event types to be included in the summary", required=True)
    parser.add_argument("--outfile", help="Path to the out file where to write", required=True)
    parser.add_argument("--verbose", help="enable debug logging", default=False, action='store_true')

    return parser

def export_events_from_process(profile, summary_file, outfile, guid, start, end):
    """Exports the events related to a process within a defined timeframe to a CSV file.

    Uses the Carbon Black Cloud API SDK to search for Events related to a given Process GUID in a defined timeframe, and
    exports the results to a CSV file. The CSV file has the following columns:
    - event_timestamp: ISO 8601 timestamp of the event in the CBC platform.
    - event_type: modload, childproc, etc.
    - event_description: Event description (if it exists)
    - summary: highlighted attributes of the event.
    - details: full Event details.

    Args:
        - profile (str): CBC profile to use. See more: https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication
        - summary_file (str): Path to the summary file (JSON) that contains the fields and transforms to apply when exporting events to file.
        - outfile (str): Path to CSV file to write to
        - guid (str): CBC Process GUID
        - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
        - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
    """
    exporter = CBCProcessEventsExporter(profile, summary_file)
    exporter.export_process_events(guid, start, end, outfile)


def export_events_from_process_tree(profile, summary_file, outpath, guid, start, end, depth_max):
    """Exports the events related to each process (childproc) in the process tree as well as the process tree itself.

    The process events are exported into CSV file similarly to the method "export_events_from_process", while the process tree is exported
    in JSON format.

    Args:
        - profile (str): CBC profile to use. See more: https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication
        - summary_file (str): Path to the summary file (JSON) that contains the fields and transforms to apply when exporting events to file.
        - outpath (str): Path where to write the export files.
        - guid (str): CBC Process GUID
        - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
        - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
        - depth_max (int): Maximum depth level to traverse in the process tree.
    """
    exporter = CBCProcessEventsExporter(profile, summary_file)
    exporter.export_process_tree_events(guid, start, end, outpath, depth_max)

if __name__ == "__main__":
    # Parse arguments
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.verbose:
       # https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/logging/
       logging.basicConfig(level=logging.DEBUG)

    # Are we sure?
    depth = int(args.follow_childprocs)
    if depth > 2:
        log.warning("Following more than 2 nesting levels of children processes may last quite long")
        user_input = input("Following more than 2 levels of children processes may last quite long. Are you sure to continue? [yes/no] ")
        if not user_input.lower() in ('y', 'yes'):
            sys.exit()

    with logging_redirect_tqdm():
        if depth > 0:
            outpath = os.path.dirname(args.outfile)
            export_events_from_process_tree(args.profile, args.summary_file, outpath, args.guid, args.start, args.end, depth)
        else:
            export_events_from_process(args.profile, args.summary, args.outfile, args.guid, args.start, args.end)
    