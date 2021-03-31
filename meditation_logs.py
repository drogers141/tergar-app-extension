#!/usr/bin/env python

"""
Parse downloaded meditation logs from Tergar meditation app.

This script is customized for various regular expressions I use to add more
classifications to meditation sessions than are available in the Tergar app.
It is intended to be modified as new meditation session types or other salient
features are added in the meditation logs.

Set DOWNLOAD_DIR and TERGAR_DATA_DIR for your system.

Contact me if you like:
Dave Rogers
dave@drogers.us
"""
import json
import os
import sys
import glob
import re
import argparse

# default download directory for your system - the json file downloaded by the extension will go in this dir
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

# directory where the json files will be stored
TERGAR_DATA_DIR = os.path.expanduser("~/Dropbox/data/tergar")

def stored_meditation_log_files():
    return glob.glob(os.path.join(TERGAR_DATA_DIR, "tergar-meditation-logs-20*.json"))

def move_downloaded_log_files_to_storage():
    log_files = glob.glob(os.path.join(DOWNLOAD_DIR, "tergar-meditation-logs-20*.json"))
    for f in log_files:
        new_name = f.replace(DOWNLOAD_DIR, TERGAR_DATA_DIR)
        print(f"moving file from {f} to {new_name}")
        os.rename(f, new_name)



def hours_minutes_seconds(seconds):
    (mins, secs) = divmod(seconds, 60)
    (hours, minutes) = divmod(mins, 60)
    return (hours, minutes, secs)


def format_time(seconds):
    h, m, s = hours_minutes_seconds(seconds)
    if h > 0:
        return "{:d}:{:02d}:{:02d}".format(h, m, s)
    else:
        return "{:d}:{:02d}".format(m, s)


class MeditationLogs:
    def __init__(self, log_file):
        entries = json.load(open(log_file)).get("valor")
        if entries:
            self.all_entries = sorted(entries, key=lambda e: e["date"])
        else:
            raise Exception("No entries")
        self.buckets = {}
        self.bucket_entries()

    def bucket_entries(self):
        # jol3 and not-jol3 should partition the complete set of logs
        self.buckets["jol3"] = [e for e in self.all_entries if e["course"]["code"] == "JOL3"]
        self.buckets["not-jol3"] = [e for e in self.all_entries if e["course"]["code"] != "JOL3"]
        self.buckets["custom"] = [e for e in self.all_entries if e["course"]["code"] == "CUSTOM"]
        # these buckets are based on my convention of putting W1 through W6 for the week of the course
        # and therefore the different meditations since each week introduced a new method
        self.buckets["jol3-by-week"] = {}
        for bucket in ("W1", "W2", "W3", "W4", "W5", "W6"):
            self.buckets["jol3-by-week"][bucket] = [e for e in self.buckets["jol3"] if e.get("notes") and bucket in e["notes"]]
        # Dying Every Day Course
        self.buckets["ded"] = [e for e in self.all_entries if e.get("notes") and "DED" in e["notes"]]
        # Awakening in Daily Life Course
        self.buckets["adl"] = [e for e in self.all_entries if e.get("notes") and "ADL" in e["notes"]]
        # Dying and Awakening Course - DOA nickname
        self.buckets["doa"] = [e for e in self.all_entries if e.get("notes") and "DOA" in e["notes"]]

        self.buckets["not-any-course"] = [entry for entry in self.all_entries
                                          if entry in self.buckets["custom"] and not
                                          entry in self.buckets["ded"] + self.buckets["adl"] + self.buckets["doa"]]
        # Nectar of the Path
        self.buckets["nop"] = [e for e in self.all_entries if e["course"]["code"] == "NECTAR_PATH"]

    def search_notes(self, regexp, return_full_entries=False):
        """Return notes matching regex search (case insensitive, multiline)
        return_full_entries - if True return the full log entries
        Default - returns a list of the "notes" key value of the entry dicts
        """
        regex = re.compile(regexp, re.I | re.DOTALL)
        if return_full_entries:
            return [e for e in self.all_entries if e.get("notes") and regex.search(e.get("notes"))]
        return [e.get("notes") for e in self.all_entries if e.get("notes") and regex.search(e.get("notes"))]

    def search_notes_in_bucket(self, regexp, bucket_name, return_full_entries=False):
        regex = re.compile(regexp, re.I | re.DOTALL)
        if return_full_entries:
            return [e for e in self.buckets[bucket_name] if e.get("notes") and regex.search(e.get("notes"))]
        return [e.get("notes") for e in self.buckets[bucket_name]
                if e.get("notes") and regex.search(e.get("notes"))]


    @classmethod
    def total_duration_seconds(cls, bucket):
        elapsed_list = [e.get("elapsed") for e in bucket]
        seconds = sum(int(x) for x in elapsed_list)
        return seconds

    @classmethod
    def most_recent(cls, bucket):
        if len(bucket) > 0:
            return bucket[-1]

    @classmethod
    def format_log(cls, entry):
        """Return pretty string of log entry"""
        course = entry.get("course", {}).get("code", "n/a")
        str_list = [
            "{:<21}{:>7}{:>10}{:>10}".format(entry.get("dateString"), format_time(entry.get("elapsed", 0)), course, entry.get("id")),
            "{}".format(entry.get("notes")),
            # "id: {}  duration: {}  course: {}".format(entry.get("id"), format_time(entry.get("elapsed", 0)), course),
            # "date: {}".format(entry.get("dateString")),
            # "duration: {}".format(format_time(entry.get("elapsed", 0))),
            # "course: {}".format(course),
            # "notes: {}".format(entry.get("notes")),
            ""
        ]
        return '\n'.join(str_list)

    # returns (week name, number of entries, total seconds of meditation for that week) for each week
    def jol3_by_week_totals(self):
        returns = []
        for week in self.buckets['jol3-by-week']:
            returns.append((week,
                           len(self.buckets['jol3-by-week'][week]),
                           MeditationLogs.total_duration_seconds(self.buckets['jol3-by-week'][week])))
        return returns

    def jol3_stats_string(self):
        header = "JOL 3 Meditation"
        overall = "Total sessions: {}, Total Time: {}".format(
            len(self.buckets["jol3"]),
            format_time(MeditationLogs.total_duration_seconds(self.buckets["jol3"])))
        weeks_header = "By Weeks:\n{:6}{:12}{}".format("Week", "Sessions", "Time")
        weeks = "\n".join(["{:>3}{:>8}{:>13}".format(t[0], t[1], format_time(t[2])) for t in self.jol3_by_week_totals()])
        return "\n".join((header, overall, weeks_header, weeks))

    def overall_stats_string(self):
        header = "Overall Meditation"
        overall = "Total sessions: {}, Total Time: {}".format(
            len(self.all_entries),
            format_time(MeditationLogs.total_duration_seconds(self.all_entries)))
        return "\n".join([header, overall])

    def other_bucketed_entries_stats_string(self, header, bucket):
        overall = "Total sessions: {}, Total Time: {}".format(
            len(bucket),
            format_time(MeditationLogs.total_duration_seconds(bucket)))
        return "\n".join([header, overall])

    def ded_stats_string(self):
        return self.other_bucketed_entries_stats_string(header="DED Meditation", bucket=self.buckets["ded"])

    def adl_stats_string(self):
        return self.other_bucketed_entries_stats_string(header="ADL Meditation", bucket=self.buckets["adl"])

    def doa_stats_string(self):
        return self.other_bucketed_entries_stats_string(header="DOA Meditation", bucket=self.buckets["doa"])

    def nop_stats_string(self):
        return self.other_bucketed_entries_stats_string(header="NOP Meditation", bucket=self.buckets["nop"])



def clean_up_old_files():
    """Save 2 most recent meditation log files"""
    log_files = stored_meditation_log_files()
    if len(log_files) > 2:
        for i, f in enumerate(sorted(log_files)[:-2]):
            os.remove(f)
        print("removed old files: {}".format(i+1))


def latest_log():
    log_files = stored_meditation_log_files()
    if log_files:
        return sorted(log_files)[-1]


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", help='search log notes for case-insensitive regex')
    parser.add_argument("-f", "--full-logs", help='with -s, --search - print full logs rather than just notes',
                        action="store_true")
    parser.add_argument("-b", "--search-bucket", help="search a single bucket of logs with case-insensitive regex." +
                        " SEARCH_BUCKET is a bucket name")
    parser.add_argument("-l", "--list-buckets", help="list available bucket names to search",
                        action="store_true")
    args = parser.parse_args()

    move_downloaded_log_files_to_storage()
    log_file = latest_log()
    if not log_file:
        print("No downloaded logs in ~/Downloads")
        exit(0)
    clean_up_old_files()
    print("meditation log file: {}\n".format(log_file))

    ml = MeditationLogs(log_file)
    if args.search_bucket:
        print(f"search_bucket: {args.search_bucket}")
        if args.full_logs:
            logs = ml.search_notes_in_bucket(args.search, args.search_bucket, True)
            print("Bucket: {}\n{} logs found\n".format(args.search_bucket, len(logs)))
            print("{:^21}{:7}{:>9}{:>8}\n{}\n".format("Date", "Duration", "Course", "ID", "-" * 50))
            for log in logs:
                print(MeditationLogs.format_log(log))
            total_duration = sum(e.get("elapsed", 0) for e in logs)
            print("Total Duration:  {}\n".format(format_time(total_duration)))
        else:
            notes = ml.search_notes_in_bucket(args.search, args.search_bucket)
            print("Bucket: {}\n{} logs found\n".format(args.search_bucket, len(notes)))
            print('\n'.join(notes))
        exit(0)
    elif args.search:
        if args.full_logs:
            logs = ml.search_notes(args.search, True)
            print("{} logs found\n".format(len(logs)))
            print("{:^21}{:7}{:>9}{:>8}\n{}\n".format("Date", "Duration", "Course", "ID", "-" * 50))
            for log in logs:
                print(MeditationLogs.format_log(log))
            total_duration = sum(e.get("elapsed", 0) for e in logs)
            print("Total Duration:  {}\n".format(format_time(total_duration)))
        else:
            notes = ml.search_notes(args.search)
            print("{} logs found\n".format(len(notes)))
            print('\n'.join(notes))
        exit(0)
    elif args.list_buckets:
        print(", ".join(ml.buckets.keys()))
        exit(0)
    else:
        print("{}\n\n{}\n\n{}\n\n{}\n\n{}\n".format(ml.jol3_stats_string(),
                                                    ml.ded_stats_string(),
                                                    ml.adl_stats_string(),
                                                    ml.doa_stats_string(),
                                                    ml.overall_stats_string()))

    print("Other stats:\n")
    non_jol3_stats = ml.other_bucketed_entries_stats_string("Non-JOL3", ml.buckets["not-jol3"])
    bardo_courses_stats = ml.other_bucketed_entries_stats_string("Bardo Courses Total",
                                                                 ml.buckets["ded"] + ml.buckets["adl"] +
                                                                 ml.buckets["doa"])
    custom_stats = ml.other_bucketed_entries_stats_string("CUSTOM", ml.buckets["custom"])
    custom_not_any_course_stats = ml.other_bucketed_entries_stats_string("CUSTOM and not in any course",
                                                                         ml.buckets["not-any-course"])
    print("{}\n\n{}\n\n{}\n\n{}\n".format(bardo_courses_stats, non_jol3_stats, custom_stats,
                                          custom_not_any_course_stats))
    print(f"{ml.nop_stats_string()}\n")



