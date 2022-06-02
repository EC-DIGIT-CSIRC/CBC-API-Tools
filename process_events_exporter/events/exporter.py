# *********************************************************************
# Copyright (EC DIGIT CSIRC 2022). Licensed under the EUPL-1.2 or later
# *********************************************************************

"""Module that contains the classes needed to export events and process tree given a process.
"""

# CBC API SDK
from cbc_sdk import CBCloudAPI
# https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/porting-guide/#enterprise-edr
from cbc_sdk.platform import Event
# General
import os
import logging
import json
import csv
from queue import Queue
# External dependencies
from tqdm import tqdm
from anytree import AnyNode
from anytree.exporter import JsonExporter
# Project
from . import transforms

log = logging.getLogger(__name__)

class CBCProcessEventsReader(object):
    """Retrieves events and/or children processes from a process.

    This class makes use of the CBC API to retrieve process events.
    """

    def __init__(self, profile):
        """Initialises the class with the CBC profile.

        Args:
            profile (str): CBC profile to use. See more: https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication
        """
        self._cb = CBCloudAPI(profile=profile)
    
    def get_events(self, process_guid, start=None, end=None, window=None):
        """Returns the events associated to a given process in a defined timeframe.

        This method uses the CBC API for search events: 
            - https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/platform-search-api-processes/#get-events-associated-with-a-given-process-v2
            - https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/cbc_sdk.platform/#module-cbc_sdk.platform.events
            - https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/platform-search-fields/

        Args:
            - process_guid (str): CBC Process GUID
            - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
            - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
            - window (str): Time window to execute the result search, ending on the current time. Should be in the form “-2w”, where y=year, w=week, d=day, h=hour, m=minute, s=second.
                It takes precedence to start/end timestamps.

        Returns:
            events (list of cbc_sdk.platform.Event): List of events.
        """
        # https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/concepts/#refine-queries-with-where-and-and-or
        query = self._cb.select(Event).where(process_guid=process_guid).set_rows(10000)
        if window:
            query.set_time_range(window=window)
        elif start and end:
            query.set_time_range(start=start, end=end)
        
        return query.sort_by('event_timestamp', 'DESC')
    
    def get_children(self, process_guid, start=None, end=None, window=None):
        """Returns the childproc events associated to a process.

        It does not use the Process.Tree CBC API implementation, because we might face hitting limits and be unable to retrieve the process tree.

        Args:
            - process_guid (str): CBC Process GUID
            - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
            - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
            - window (str): Time window to execute the result search, ending on the current time. Should be in the form “-2w”, where y=year, w=week, d=day, h=hour, m=minute, s=second.
                It takes precedence to start/end timestamps.

        Returns:
            events (list of cbc_sdk.platform.Event): List of childproc events with only the following fields: "process_guid", "childproc_process_guid", "childproc_pid", "childproc_name".
        """
        # try:
        #     process_tree = self._cb.select(Process.Tree, process_guid)
        # except Exception as ex:
        #     log.warning(ex)

        childprocs = self._cb.select(Event).where(process_guid=process_guid).and_(event_type="childproc").set_rows(1000)
        if window:
            childprocs.set_time_range(window=window)
        elif start and end:
            childprocs.set_time_range(start=start, end=end)
        childprocs.set_fields(["process_guid", "childproc_process_guid", "childproc_pid", "childproc_name"])
        
        return childprocs

class CBCProcessEventsWriter(object):
    """This class writes events or process trees into files.
    """

    def __init__(self, summary_file):
        """Initialises the writer with the summary file to use when writing events.

        Args:
            - summary_file (str): Path to the summary file (JSON) that contains the fields and transforms to apply when exporting events to file.
        """
        # Reads the summary attributes.            
        with open(summary_file) as f:
            self._attributes = json.load(f)
        self._summary_file = summary_file
    
    def write_events_to_csv(self, guid, events, outfile):
        """Write the list of events into a CSV file.

        Args:
            - guid (str): Process GUID.
            - events (list of cbc_sdk.platform.Event): List of events to export
            - outfile (str): Path to CSV file to write to
        """
        
        # Export them to a CSV file
        with open(outfile, 'w', newline='', encoding='utf-8') as csv_file:
            wr = csv.writer(csv_file, delimiter=",")
            # Header
            wr.writerow(["event_timestamp","event_type","event_description", "summary", "details"])
            # Loop on the events
            for event in tqdm(events, desc=f"Exporting events from process: {guid}"):
                # Summary attributes
                summary = ''
                try:
                    for k in self._attributes['types'][event.event_type]:
                        try:
                            val = event.get(k)
                            # Apply transform?
                            if k in self._attributes['transforms']:
                                # https://docs.python.org/3/faq/programming.html#how-do-i-use-strings-to-call-functions-methods
                                func = getattr(transforms, self._attributes['transforms'][k])
                                val = func(val)

                            summary += f" {k}: {val}"
                        except:
                            log.warning(f"The attribute {k} does not exist for this event type {event.event_type}. Review the summary JSON file {self._summary_file}")
                except:
                    log.warning(f"The event type {event.event_type} does not exist. Review the summary JSON file {self._summary_file} if you want it to be included in the summary column")
                # Export event            
                wr.writerow([event.event_timestamp, event.event_type, event.get('event_description'), summary, json.dumps(event.original_document)])

    def write_process_tree_to_json(self, root, outfile):
        """Write process tree into a JSON file.
        
        Args:
            - root (AnyNode): Root now from which to get the process tree
            - outfile (str): Path to JSON file where to write the process tree.
        """
        exporter = JsonExporter(ensure_ascii=False, indent=4)
        with open(outfile, 'w', encoding='utf-8') as fd:
            exporter.write(root, fd)

class CBCProcessEventsExporter(object):
    """Class responsible for exporting process events and process trees

    This class uses CBCProcessEventsReader to query for events and/or children processes and CBCProcessEventsWriter to export them to files.
    """

    def __init__(self, profile, summary_file):
        """Initialises the exporter.

        Args:
            - profile (str): CBC profile to use. See more: https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication
            - summary_file (str): Path to the summary file (JSON) that contains the fields and transforms to apply when exporting events to file.
        """
        self._reader = CBCProcessEventsReader(profile)
        self._writer = CBCProcessEventsWriter(summary_file)
    
    def export_process_events(self, process_guid, start, end, outfile):
        """Export into CSV file the events associated to the given process within the given timeframe.

        Args:
            - process_guid (str): CBC Process GUID
            - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
            - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
            - outfile (str): Path to CSV file to write to
        """
        events = self._reader.get_events(process_guid, start=start, end=end)
        if len(events) > 0:
            self._writer.write_events_to_csv(process_guid, events, outfile)
        else:
            log.info(f"No events to export from this process {process_guid}")
    
    def export_process_tree_events(self, process_guid, start, end, outpath, depth_max=1):
        """Export into CSV file the events associated to the given process within the given timeframe as well as the events associated
        to the children processes limited to given depth.

        It will generate a CSV file per process with the corresponding events and a JSON file with the process tree (or parent-child relationship) 
        using the given process GUID as starting point (root)

        Args:
            - process_guid (str): CBC Process GUID to start (root node)
            - start (str): ISO 8601 timestamp from where to start to search for. It is used in combination with end.
            - end (str): ISO 8601 timestamp to limit the result search. It is used in combination with start.
            - outpath (str): Path where to save the export files.
            - depth_max (int): Maximum depth
        """

        # Using FIFO queue to avoid recursion in favour of performance
        nodes = Queue()
        depth = 0
        # Creates the process tree root node
        # https://anytree.readthedocs.io/en/latest/api/anytree.node.html
        root = AnyNode(guid=process_guid, name='', pid='', level=depth)
        # Adds the first node to process
        nodes.put(root)
        while not nodes.empty() and depth < depth_max:
            # Get the next node to process
            parent = nodes.get()
            # Export the events to its dedicated file
            outfile = os.path.join(outpath, f"{parent.level}_{parent.guid}.csv")
            self.export_process_events(parent.guid, start, end, outfile)
            # Get children nodes
            depth += 1
            children = self._reader.get_children(parent.guid, start=start, end=end)
            for child in tqdm(children, desc=f"(Depth: {depth}) Querying childprocs from {parent.guid}"):
                # Add child node to the process tree
                node = AnyNode(guid=child.childproc_process_guid, name=child.childproc_name, pid=child.childproc_pid, level=depth, parent=parent)
                # Add childe node to the queue for next iteration
                nodes.put(node)

        # Exports the events of the remaining nodes
        while not nodes.empty():
            node = nodes.get()
            # Export the events to its dedicated file
            outfile = os.path.join(outpath, f"{node.level}_{node.guid}.csv")
            self.export_process_events(node.guid, start, end, outfile)

        # Exports the process tree
        outfile = os.path.join(outpath, f"{root.level}_{root.guid}-process_tree.json")
        self._writer.write_process_tree_to_json(root, outfile)
        tqdm.write(f"Process tree exported to {outfile}")

