"""
Parse downloaded meditation logs from Tergar meditation app.

This script is customized for various regular expressions I use to add more
classifications to meditation sessions than are available in the Tergar app.
It is intended to be modified as new meditation session types or other salient
features are added in the meditation logs.

If you use this extension for downloading the Tergar app logs and would
like to customize this script, you can:

Set DOWNLOAD_DIR and TERGAR_DATA_DIR for your system.

Customize the MeditationLogs class following the patterns to create tables
Customize main() to print your tables.

you need to install tabulate:
pip install tabulate

Contact me if you like:
Dave Rogers
dave@drogers.us
"""
import datetime
import json
import os
import glob
import re
import argparse
import shutil
from datetime import datetime, date, timedelta
import tracemalloc

from dateutil.parser import parse as parse_date
from tabulate import tabulate
import psutil

# default download directory for your system - the json file downloaded by the extension will go in this dir
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

# directory where the json files are stored
TERGAR_DATA_DIR = os.path.expanduser("~/Dropbox/data/tergar/tergar-meditation-app")

# backup meditation logs file if the last backup is older than this many days
BACKUP_AFTER_NUM_DAYS = 30


def _parse_date_element(e):
    try:
        return (datetime.today() - timedelta(days=int(e))).date()
    except ValueError:
        return parse_date(e).date()


def parse_date_range(date_range_string):
    """Parse a comma-delimited string into a datetime.date tuple

    date_range_string - comma-delimited string representing date range
      - "a, b" date range string is interpreted as follows
        a, b -> duration from a to b inclusive
        a, b can be anything dateutil can parse
        a, b can also be an int indicating the number of days ago
        if a is the empty string or None, then the range is from beginning_of_history (or the Epoch) to b
        if b is the empty string or None, then the range is from a to now()
        Examples:
        "3," -> from 3 days ago until now
        ",3" -> beginning_of_history until 3 days ago
        "7, 3" -> between 7 and 3 days ago - inclusive
        "2019-01-01 00:00:00," -> Jan 1 2019 until now
    beginning_of_history - datetime.date - defaults to 1970-01-01
    Returns (datetime.date, datetime.date)
    """
    strvals = date_range_string.split(",")
    if not strvals[0]:
        date_range = (date(1970, 1, 1), _parse_date_element(strvals[1]))
    elif not strvals[1]:
        date_range = (_parse_date_element(strvals[0]), date.today())
    else:
        date_range = (_parse_date_element(strvals[0]), _parse_date_element(strvals[1]))
    return date_range


def stored_meditation_log_files():
    return glob.glob(os.path.join(TERGAR_DATA_DIR, "tergar-meditation-logs-20*.json"))


def backed_up_log_files():
    return glob.glob(os.path.join(TERGAR_DATA_DIR, "tergar-meditation-logs-backup-*"))


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


def format_time(seconds, hours_width=1):
    """
    :param seconds: total seconds
    :param hours_width: total width of hours column - will be padded with spaces
        only if there is an hours column
    :return:
    """
    h, m, s = hours_minutes_seconds(seconds)
    if h > 0:
        return "{1:{0}d}:{2:02d}:{3:02d}".format(hours_width, h, m, s)
    else:
        return "{:d}:{:02d}".format(m, s)


# TODO - clean this up
# performance - hasn't been a problem because the data is small, but bucketing/tagging
# should be done in one pass where possible
# So far each time I needed something I just added new dicts, but at this point perhaps
# using class attributes might be easier to understand.
# Perhaps a little more OO design might not be terrible
# It would be interesting to compare performance while changing from just dealing with
# dictionaries to using attributes.  Not sure whether I need to change smaller dicts into
# objects.
class MeditationLogs:
    def __init__(self, log_file):
        entries = json.load(open(log_file))
        if entries:
            self.all_entries = sorted(entries, key=lambda e: e["date"])
        else:
            raise Exception("No entries")
        self.buckets = {}
        self.bucket_entries()

    def bucket_entries(self):
        # jol3 and not-jol3 should partition the complete set of logs
        self.buckets["jol3"] = [e for e in self.all_entries if e["course"].get("code") == "JOL3"]
        self.buckets["not-jol3"] = [e for e in self.all_entries if e["course"].get("code") != "JOL3"]
        # breaking change to json format on Mar 21, 2022
        # see file ./tergar-breaking-changes
        # old 'Custom' course entries still have a 'code' field
        # but the new ones don't, so add them
        self.buckets["custom"] = [e for e in self.all_entries if e["course"].get("code") == "CUSTOM"]
        for e in self.all_entries:
            if ('code' not in e['course']) and e['course'].get('name') == 'Custom':
                self.buckets['custom'].append(e)
        # these buckets are based on my convention of putting W1 through W6 for the week of the course
        # and therefore the different meditations since each week introduced a new method
        self.buckets["jol3-by-week"] = {}
        for bucket in ("W1", "W2", "W3", "W4", "W5", "W6"):
            self.buckets["jol3-by-week"][bucket] = [e for e in self.buckets["jol3"] if
                                                    e.get("notes") and bucket in e["notes"]]
        # Dying Every Day Course
        self.buckets["ded"] = [e for e in self.all_entries if e.get("notes") and "DED" in e["notes"]]
        # Awakening in Daily Life Course
        self.buckets["adl"] = [e for e in self.all_entries if e.get("notes") and "ADL" in e["notes"]]
        # Dying and Awakening Course - DOA nickname
        self.buckets["doa"] = [e for e in self.all_entries if e.get("notes") and "DOA" in e["notes"]]
        # Nectar of the Path
        self.buckets["nop"] = [e for e in self.all_entries if e["course"].get("code") == "NECTAR_PATH"]
        # Tsoknyi Rinpoche - Fully Being - v1 - the original course
        self.buckets["fully-being-v1"] = [e for e in self.all_entries
                                       if e.get("notes") and re.search(r"TR[- ]+FB[,\- ]", e["notes"], re.I)]
        self.buckets["fb-sections"] = {}
        for section in ("dropping", "four modes", "handshake", "essence love",
                        "subtle body", "calm abiding", "insight", "qualities"):
            self.buckets["fb-sections"][section] = [e for e in self.buckets["fully-being-v1"]
                                                    if re.search(section, e["notes"].replace('\n', ' '), re.I)]
        # Tsoknyi Rinpoche - Fully Being - v2 - Oct 2021
        self.buckets["fully-being-v2"] = [e for e in self.all_entries
                                          if e.get("notes") and re.search(r"TR[- ]+FB2[,\- ]", e["notes"], re.I)]
        self.buckets["fb2-sections"] = {}
        for section in ("dropping", "handshake", "essence love", "four ways",
                        "subtle body", "shinay", "insight", "qualities"):
            self.buckets["fb2-sections"][section] = [e for e in self.buckets["fully-being-v2"]
                                                    if re.search(section, e["notes"].replace('\n', ' '), re.I)]

        _custom_course_combined = (self.buckets["ded"] + self.buckets["adl"] + self.buckets["doa"] + self.buckets["nop"]
                                    + self.buckets["fully-being-v1"] + self.buckets["fully-being-v1"])
        self.buckets["not-any-course"] = [entry for entry in self.all_entries
                                          if entry in self.buckets["custom"]
                                          and entry not in _custom_course_combined]
        self.buckets['pol1'] = {}
        bucket_regex_dict = {
            'Four Thoughts 1': r'four[- ]+thoughts[- ]+1',
            'Four Thoughts 2': r'four[- ]+thoughts[- ]+2',
            'Four Thoughts 3': r'four[- ]+thoughts[- ]+3',
            'Four Thoughts 4': r'four[- ]+thoughts[- ]+4',
            'SMA': 'sma',
            'APCFM': 'apcfm',
        }
        for section in bucket_regex_dict:
            self.buckets['pol1'][section] = [
                e for e in self.buckets['nop']
                if e['notes'] and re.search(bucket_regex_dict[section], e['notes'].replace('\n', ' '), re.I)
            ]

    def search_notes(self, regexp, return_full_entries=False, date_range=None):
        """Return notes matching regex search (case insensitive, multiline)
        return_full_entries - if True return the full log entries
        date_range - sequence (date, date) which represent and inclusive date range to limit data to
        Default - returns a list of the "notes" key value of the entry dicts
        """
        regex = re.compile(regexp, re.I | re.DOTALL)
        if date_range:
            beginning, ending = date_range
            # note we need to use the dateString as the 'date' timestamp is not accurate probably
            # due to adding a timezone - this could be checked more rigorously, but a short
            # check of the data for 'id': 1566145 on 'dateString': '2021-12-25 00:00:00'
            # shows this error
            entries = [e for e in self.all_entries
                       if e.get('notes') and parse_date(e['dateString']).date() >= beginning
                       and parse_date(e['dateString']).date() <= ending]
        else:
            entries = [e for e in self.all_entries if e.get("notes")]
        if return_full_entries:
            return [e for e in entries if regex.search(e.get("notes"))]
        return [e.get("notes") for e in entries if regex.search(e.get("notes"))]

    def search_notes_in_bucket(self, regexp, bucket_name, return_full_entries=False, date_range=None):
        regex = re.compile(regexp, re.I | re.DOTALL)
        if date_range:
            beginning, ending = date_range
            entries = [e for e in self.buckets[bucket_name]
                       if e.get('notes') and parse_date(e['dateString']).date() >= beginning
                       and parse_date(e['dateString']).date <= ending]
        else:
            entries = [e for e in self.buckets[bucket_name] if e.get("notes")]
        if return_full_entries:
            return [e for e in entries if regex.search(e.get("notes"))]
        return [e.get("notes") for e in entries if regex.search(e.get("notes"))]

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
        try:
            str_list = [
                "{:<21}{:>7}{:>14}{:>10}".format(entry.get("dateString"), format_time(entry.get("elapsed", 0)), course,
                                                 entry.get("id")),
                "{}".format(entry.get("notes")),
                ""
            ]
        except TypeError as error:
            print(f"Error with entry: {entry}")
            raise
        return '\n'.join(str_list)

    # returns (week name, number of entries, total seconds of meditation for that week) for each week
    def jol3_by_week_totals(self):
        returns = []
        for week in self.buckets['jol3-by-week']:
            returns.append((week,
                            len(self.buckets['jol3-by-week'][week]),
                            format_time(MeditationLogs.total_duration_seconds(self.buckets['jol3-by-week'][week]),
                                        hours_width=2)))
        return returns

    def jol3_stats_string(self):
        header = "JOL 3 Meditation"
        overall = "Total sessions: {}, Total Time: {}".format(
            len(self.buckets["jol3"]),
            format_time(MeditationLogs.total_duration_seconds(self.buckets["jol3"])))
        weeks_header = "By Weeks:\n{:6}{:12}{}".format("Week", "Sessions", "Time")
        weeks = "\n".join(["{:>3}{:>8}{:>13}".format(t[0], t[1], t[2]) for t in self.jol3_by_week_totals()])
        return "\n".join((header, overall, weeks_header, weeks))

    def jol3_table(self):
        title = "Joy of Living 3    (add 20-30 hours before tracking)"
        headers = ["Week", "Sessions", "Total Time"]
        table = self.jol3_by_week_totals()
        table.append(("Total", len(self.buckets["jol3"]),
                      format_time(MeditationLogs.total_duration_seconds(self.buckets["jol3"]))))
        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"

    def _number_of_sessions_and_duration(self, bucket_name):
        return (len(self.buckets[bucket_name]),
                format_time(MeditationLogs.total_duration_seconds(self.buckets[bucket_name])))

    def bardo_courses_table(self):
        """Returns string table"""
        title = "Bardo Courses"
        headers = ["Course", "Sessions", "Total Time"]
        # headers = ["DED", "ADL", "DOA", "Bardo Total"]
        table = [["DED", *self._number_of_sessions_and_duration("ded")],
                 ["ADL", *self._number_of_sessions_and_duration("adl")],
                 ["DOA", *self._number_of_sessions_and_duration("doa")],
                 ["Total", len(self.buckets["ded"] + self.buckets["adl"] + self.buckets["doa"]),
                  format_time(MeditationLogs.total_duration_seconds(
                      self.buckets["ded"] + self.buckets["adl"] + self.buckets["doa"]
                  ))],
                 ]

        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"

    def general_table(self):
        """General stats, also NOP"""
        title = "General"
        headers = ["", "Sessions", "Total Time"]
        table = [["NOP", *self._number_of_sessions_and_duration("nop")],
                 ["Not In Any Course", *self._number_of_sessions_and_duration("not-any-course")],
                 ["Overall Meditation", len(self.all_entries),
                  format_time(MeditationLogs.total_duration_seconds(self.all_entries))]]

        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"

    def fully_being_v1_table(self):
        """Tsoknyi Rinpoche's Fully Being - version 1 of the course"""
        title = "Fully Being V1 Course  (combined section times are greater than total due to overlap)"
        headers = ["Section", "Sessions", "Total Time"]
        table = []
        for section in ("Dropping", "Four Modes", "Handshake", "Essence Love",
                        "Subtle Body", "Calm Abiding", "Insight", "Qualities"):
            section_bucket = section.lower()
            if section_bucket in self.buckets["fb-sections"] and len(self.buckets["fb-sections"][section_bucket]) > 0:
                table.append([section,
                              len(self.buckets["fb-sections"][section_bucket]),
                              format_time(MeditationLogs.total_duration_seconds(
                                  self.buckets["fb-sections"][section_bucket]))])
        table.append(["Total", *self._number_of_sessions_and_duration("fully-being-v1")])

        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"

    def fully_being_v2_table(self):
        """Tsoknyi Rinpoche's Fully Being - version 2 of the course - Oct 2021
        In this version, there are 3 courses - or levels of courses
        - Essentials Course
        - Immersion Level 1
        - Immersion Level 2

        I'll be going through Immersion Level 1 then 2, probably.  The levels both have sections like the v1,
        but in the order:
        - Dropping, Handshake, Essence Love, Subtle Body, 4 Ways of Seeing, Settling the Mind, Insight

        I will keep these names for the regular expressions except '4 Ways of Seeing' will be 'Four Ways', and
        'Settling the Mind' will be 'Shinay'.

        Each section has a number of pages each with a unit of teaching - video, notes, daily instruction, etc.
        These all are named with no numbers, but for ease I will refer to a section by its number in a 1-based
        sequence.

        All told, this means Immersion Level 1, Handshake "Feeling Awareness", the 8th topic, will be referred
        to in the meditation log as Handshake 1.8.  Immersion Level 2 Handshake will be Handshake 2.x, etc.
        To distinguish between Fully Being Course versions, I'll use:
        TR - FB2 - ...
        This is backwards compatible so the previous counts will stand.
        For now, I won't worry about displaying the counts per topic in course sections (as I haven't with v1).
        They can be picked up with a search.
        """
        title = "Fully Being V2 Course  (combined section times are greater than total due to overlap)"
        headers = ["Section", "Sessions", "Total Time"]
        table = []
        for section in ("Dropping", "Handshake", "Essence Love", "Four Ways",
                        "Subtle Body", "Shinay", "Insight", "Qualities"):
            section_bucket = section.lower()
            if section_bucket in self.buckets["fb2-sections"] and len(self.buckets["fb2-sections"][section_bucket]) > 0:
                table.append([section,
                              len(self.buckets["fb2-sections"][section_bucket]),
                              format_time(MeditationLogs.total_duration_seconds(
                                  self.buckets["fb2-sections"][section_bucket]))])
        table.append(["Total", *self._number_of_sessions_and_duration("fully-being-v2")])

        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"

    def path_of_liberation_table(self):
        title = "POL 1 - NOP"
        headers = ["Section", "Sessions", "Total Time"]
        table = []
        all_pol1_nop_sessions = []
        for section in ("Four Thoughts 1", "Four Thoughts 2", "Four Thoughts 3", "Four Thoughts 4",
                        "SMA", "APCFM"):
            if section in self.buckets["pol1"] and len(self.buckets["pol1"][section]) > 0:
                if re.search('thoughts', section, re.I):
                    all_pol1_nop_sessions.extend(self.buckets['pol1'][section])
                table.append([section,
                              len(self.buckets["pol1"][section]),
                              format_time(MeditationLogs.total_duration_seconds(
                                  self.buckets["pol1"][section]))])
        table.append(["Total", len(all_pol1_nop_sessions),
                      format_time(MeditationLogs.total_duration_seconds(all_pol1_nop_sessions))])

        return f"{title}\n\n{tabulate(table, headers=headers, tablefmt='presto', colalign=('left', 'right', 'right'))}"


def clean_up_old_files():
    """Save 2 most recent meditation log files"""
    log_files = stored_meditation_log_files()
    if len(log_files) > 2:
        for i, f in enumerate(sorted(log_files)[:-2]):
            os.remove(f)
        print("removed old files: {}".format(i + 1))


def latest_log():
    log_files = stored_meditation_log_files()
    if log_files:
        return sorted(log_files)[-1]


def datetime_from_filename(filename):
    """Returns datetime with no tz"""
    datetime_str = re.search(r'(\d{4}.*)-\d\d\.\d\d.json', filename).groups()[0]
    return datetime.strptime(datetime_str, '%Y-%m-%dT%H.%M.%S')


def backup_logs():
    """Backup logs every month.

    Later we can add logic to check backups and remove them as necessary.
    :raise IndexError if there are no existing backups
    """
    latest_backup = sorted(backed_up_log_files())[-1]
    latest_backup_date = datetime_from_filename(latest_backup)
    if datetime.now() - latest_backup_date >= timedelta(days=BACKUP_AFTER_NUM_DAYS):
        backup_filename = latest_log().replace('tergar-meditation-logs', 'tergar-meditation-logs-backup')
        shutil.copy(latest_log(), backup_filename)
        print(f"last backup older than {BACKUP_AFTER_NUM_DAYS} days, backing up:")
        print(f"{latest_log()} ->\n{backup_filename}\n")


def main():

    tracemalloc.start()

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", help='search log notes for case-insensitive regex')
    parser.add_argument("-f", "--full-logs", help='with -s, --search - print full logs rather than just notes',
                        action="store_true")
    parser.add_argument("-b", "--search-bucket", help="with -s, --search - search a single bucket of logs with " +
                                                      "case-insensitive regex. SEARCH_BUCKET is a bucket name")
    parser.add_argument("-l", "--list-buckets", help="list available bucket names to search",
                        action="store_true")
    parser.add_argument('-d', '--date-range', help='search by date range. DATE_RANGE is a comma-delimited inclusive ' +
                        'range, which can be open-ended - so each element is optional.  Each element can be any ' +
                        'string parseable by dateutil as a date, or an integer representing days ago.  See ' +
                        'parse_date_range for examples.')
    args = parser.parse_args()

    move_downloaded_log_files_to_storage()
    log_file = latest_log()
    if not log_file:
        print(f"No downloaded meditation logs in {TERGAR_DATA_DIR} or {DOWNLOAD_DIR}")
        return
    clean_up_old_files()
    backup_logs()
    print("meditation log file: {}\n".format(log_file))


    date_range = parse_date_range(args.date_range) if args.date_range else None
    ml = MeditationLogs(log_file)

    print('Memory stats:')
    memory_mb = psutil.Process().memory_info().rss / (1024 **2)
    print(f'Process resident memory:  {memory_mb:.3f} MiB')

    ## example of displaying lines of source code that allocate the largest
    ## amount of memory
    # snapshot = tracemalloc.take_snapshot()
    # top_stats = snapshot.statistics('lineno')
    # n = 20
    # print(f'Top {n} lines using memory')
    # for stat in top_stats[:n]:
    #     print(stat)

    current_KiB, peak_KiB = [int(x/1024) for x in tracemalloc.get_traced_memory()]
    print(f'tracemalloc: current: {current_KiB} KiB  peak: {peak_KiB} KiB')
    print()

    tracemalloc.stop()

    if args.search_bucket:
        print(f"search_bucket: {args.search_bucket}")
        if args.full_logs:
            logs = ml.search_notes_in_bucket(args.search,
                                             args.search_bucket,
                                             return_full_entries=True,
                                             date_range=date_range)
            print("Bucket: {}\n{} logs found\n".format(args.search_bucket, len(logs)))
            print("{:^21}{:7}{:>9}{:>8}\n{}\n".format("Date", "Duration", "Course", "ID", "-" * 50))
            for log in logs:
                print(MeditationLogs.format_log(log))
            total_duration = sum(e.get("elapsed", 0) for e in logs)
            print("Total Duration:  {}\n".format(format_time(total_duration)))
        else:
            notes = ml.search_notes_in_bucket(args.search,
                                              args.search_bucket,
                                              return_full_entries=False,
                                              date_range=date_range)
            print("Bucket: {}\n{} logs found\n".format(args.search_bucket, len(notes)))
            print('\n'.join(notes))
        return

    elif args.search:
        if args.full_logs:
            logs = ml.search_notes(args.search, return_full_entries=True, date_range=date_range)
            print("{} logs found\n".format(len(logs)))
            print("{:^21}{:7}{:>14}{:>10}\n{}\n".format("Date", "Duration", "Course", "ID", "-" * 50))
            for log in logs:
                print(MeditationLogs.format_log(log))
            total_duration = sum(e.get("elapsed", 0) for e in logs)
            print("Sessions:  Total Duration:\n{:>8}{:>17}".format(len(logs), format_time(total_duration)))
        else:
            notes = ml.search_notes(args.search, return_full_entries=False, date_range=date_range)
            print("{} logs found\n".format(len(notes)))
            print('\n'.join(notes))
        return

    elif args.list_buckets:
        print(", ".join(ml.buckets.keys()))
        return

    print("Started tracking: May 5, 2019\n")
    print(ml.jol3_table() + "\n")
    print(ml.bardo_courses_table() + "\n")
    print(ml.fully_being_v1_table() + "\n")
    print(ml.fully_being_v2_table() + '\n')
    print(ml.path_of_liberation_table() + "\n")
    print(ml.general_table() + "\n")


if __name__ == "__main__":
    exit(main())
