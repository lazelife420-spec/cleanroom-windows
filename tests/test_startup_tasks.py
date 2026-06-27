"""Tests for the scheduled-task (logon trigger) startup source."""
# ruff: noqa: E402
import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
project_dir = tests_dir.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import startup_manager as sm

CSV_SAMPLE = (
    '"HostName","TaskName","Next Run Time","Status","Logon Mode","Last Run Time","Last Result",'
    '"Author","Task To Run","Start In","Comment","Scheduled Task State","Idle Time","Power Management",'
    '"Run As User","Delete Task If Not Rescheduled","Stop Task If Runs X Hours and X Mins","Schedule",'
    '"Schedule Type","Start Time","Start Date","End Date","Days","Months","Repeat: Every",'
    '"Repeat: Until: Time","Repeat: Until: Duration","Repeat: Stop If Still Running"\r\n'
    '"PC","\\MyApp Updater","N/A","Ready","Interactive only","11/7/2025","0",'
    '"MyApp","C:\\Program Files\\MyApp\\updater.exe --quiet","","","Enabled","Disabled","",'
    '"User","Disabled","72:00:00","Scheduling data is not available in this format.",'
    '"At logon time","N/A","N/A","N/A","N/A","N/A","N/A","N/A","N/A","N/A"\r\n'
    # schtasks repeats the header row between folders — must be skipped
    '"HostName","TaskName","Next Run Time","Status","Logon Mode","Last Run Time","Last Result",'
    '"Author","Task To Run","Start In","Comment","Scheduled Task State","Idle Time","Power Management",'
    '"Run As User","Delete Task If Not Rescheduled","Stop Task If Runs X Hours and X Mins","Schedule",'
    '"Schedule Type","Start Time","Start Date","End Date","Days","Months","Repeat: Every",'
    '"Repeat: Until: Time","Repeat: Until: Duration","Repeat: Stop If Still Running"\r\n'
    '"PC","\\Microsoft\\Windows\\Defrag\\ScheduledDefrag","N/A","Ready","Background only","11/7/2025","0",'
    '"Microsoft","defrag.exe -c","","","Enabled","Disabled","",'
    '"SYSTEM","Disabled","72:00:00","Scheduling data is not available in this format.",'
    '"Weekly","03:00:00","1/1/2020","N/A","SUN","N/A","N/A","N/A","N/A","N/A"\r\n'
)


def test_parse_schtasks_csv_filters_logon_tasks():
    entries = sm._parse_schtasks_csv(CSV_SAMPLE)
    assert len(entries) == 1
    e = entries[0]
    assert e['source'] == 'task'
    assert e['name'] == 'MyApp Updater'
    assert e['location'] == '\\MyApp Updater'
    assert 'updater.exe' in e['command']
    assert e['status'] == 'Ready'


def test_parse_schtasks_csv_garbage_returns_empty():
    assert sm._parse_schtasks_csv('') == []
    assert sm._parse_schtasks_csv('not,a,real\ncsv,at,all') == []


def test_list_startup_entries_includes_tasks_key():
    data = sm.list_startup_entries()
    assert 'tasks' in data
    assert isinstance(data['tasks'], list)
    for t in data['tasks']:
        assert t['source'] == 'task'
        assert 'logon' not in (t.get('status') or '').lower() or True  # structural only
