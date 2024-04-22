import math
import time
import requests
import urllib
from bs4 import BeautifulSoup, Tag
from threading import Thread
import db

BASE_URL = "http://coursefinder.utoronto.ca/course-search/search/"
BURST_SIZE = 40

def get_span_text(html, span_id):
    span = html.find("span", id=span_id)
    if span is None:
        return ""
    
    return span.text.strip()

def get_breadth(html, campus):
    if campus == "Mississauga":
        return ""
    elif campus == "St. George":
        return get_span_text(html, "u122")
    elif campus == "Scarborough":
        return get_span_text(html, "u104")
    
    return ""

def get_distribution(html, campus):
    if campus == "Mississauga":
        return get_span_text(html, "u113")
    elif campus == "St. George":
        return get_span_text(html, "u131")
    elif campus == "Scarborough":
        return ""
    
    return ""

def get_session():
    s = requests.session()
    url = BASE_URL + "courseSearch/course/search"
    payload = {"queryText":"", "requirements":"", "campusParam":""}
    s.get(url, params=payload)
    return s

def get_campuses():
    r = requests.get(BASE_URL)
    if r.status_code != requests.codes.ok:
        return []

    response = r.text
    html = BeautifulSoup(response, "lxml")
    parent_tag = html.find(id="u49_fieldset")
    campuses = []
    for child in parent_tag.find_all("input"):
        if child.get("type") == "checkbox":
            campuses.append(child.get("value"))

    return campuses

def get_requirements():
    r = requests.get(BASE_URL)
    if r.status_code != requests.codes.ok:
        return []

    response = r.text
    html = BeautifulSoup(response, "lxml")
    parent_tag = html.find(id="textArea_control")
    requirements = []
    for child in parent_tag.find_all("option"):
        if child.get("value") != " ":
            requirements.append(child.get("value"))

    return requirements

def get_all_courses(campuses, requirements, session):
    url = BASE_URL + "courseSearch/course/search"
    courses = []
    for requirement in requirements:
        payload = {"queryText":"", "requirements":requirement, "campusParam":campuses}
        r = session.get(url, params=payload)
        if r.status_code != requests.codes.ok:
            print(r.text)
            continue

        response = r.json()
        for data in response["aaData"]:
            tag = BeautifulSoup(data[1], "lxml")
            course_url = tag.a.get("href")
            courses.append(course_url)

    return list(set(courses))

def get_course_info(session, url_path, info):
    url = BASE_URL + url_path
    r = session.get(url)
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        return {}

    response = r.text
    html = BeautifulSoup(response, "lxml")
    title = html.find(id="pageTitle").get("value").strip()
    code = title.split(":")[0]
    division = get_span_text(html, "u23")
    description = get_span_text(html, "u32")
    department = get_span_text(html, "u41")
    prerequisites = get_span_text(html, "u50")
    exclusions = get_span_text(html, "u68")
    level = get_span_text(html, "u86")
    campus = get_span_text(html, "u149")
    breadth = get_breadth(html, campus)
    distribution = get_distribution(html, campus)
    elective = get_span_text(html, "u140")
    term = get_span_text(html, "u158")
    sections = html.find("table", id="u172")
    meetings = []
    if sections:
        rows = sections.tbody.find_all("tr")      
        for row in rows:
            meeting_info = []
            spans = row.find_all("span")
            for i in range(0, len(spans), 3):
                meeting_info.append(spans[i].text.strip())

            meetings.append(meeting_info)

        meetings.sort()
        
    #print(meetings)
    d = {"code":code,
         "title":title,
         "division":division,
         "description":description,
         "department":department,
         "prerequisites":prerequisites,
         "exclusions":exclusions,
         "level":level,
         "campus":campus,
         "breadth":breadth,
         "distribution":distribution,
         "elective":elective,
         "term":term,
         "meetings":meetings}

    #import pprint
    #pprint.pprint(d)
    info.append(d)
    return d

def get_all_info(session, url_paths):
    info = []
    count = 0
    for i in range(int(math.ceil(len(url_paths) / BURST_SIZE))):
        print(i)
        threads = []
        for j in range(BURST_SIZE):
            if count == len(url_paths):
                break

            url_path = url_paths[i*BURST_SIZE + j]
            t = Thread(target=get_course_info, args=(session, url_path, info))
            t.start()
            threads.append(t)
            count += 1

        for thread in threads:
            thread.join()

        time.sleep(4)
        
    return info

def insert_info(courses_info):
    return
    
session = get_session()
campuses = get_campuses()
print(campuses)
requirements = get_requirements()
print(requirements)
courses = get_all_courses(campuses, requirements, session)
print(len(courses))
#get_course_info(session, courses[0], [])
#get_all_info(session, ["courseSearch/coursedetails/CSC108H5F20199"])
info = get_all_info(session, courses[:100])

test = db.CourseDB("localhost", "user", "password")
for course_info in info:
    test.insert_course(course_info)
