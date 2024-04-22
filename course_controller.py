import json
import math
import time
import requests
import urllib
from bs4 import BeautifulSoup, Tag
from threading import Thread
import pprint, re
import degree_explorer

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

BASE_URL = "https://acorn.utoronto.ca"

class Acorn:
    def __init__(self, username, password):
        self.session = requests.session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
        self.username = username
        self.password = password
        self.registration_info = None
        self._start()

    def _start(self):
        self._authenticate()
        self._set_registration_info()

    def _authenticate(self):
        driver = webdriver.Chrome()
        driver.get(BASE_URL)

        username = driver.find_element(By.ID, "username")
        password = driver.find_element(By.ID, "password")
        username.send_keys(self.username)
        password.send_keys(self.password)
        driver.find_element(By.NAME, "_eventId_proceed").click()

        timeout = 15
        try:
            element_present = EC.presence_of_element_located((By.ID, 'acorn-nav-side-parent'))
            WebDriverWait(driver, timeout).until(element_present)
            print("Successfully logged into Acorn")
        except TimeoutException:
            print("Timed out loading Acorn")
            driver.quit()
            raise SystemExit

        cookies = driver.get_cookies()
        for cookie in cookies:
            if 'httpOnly' in cookie:
                http_only = cookie.pop('httpOnly')
                cookie['rest'] = {'httpOnly': http_only}
            if 'expiry' in cookie:
                cookie['expires'] = cookie.pop('expiry')
                
            self.session.cookies.set(**cookie)

        self.session.headers["X-XSRF-TOKEN"] = self.session.cookies["XSRF-TOKEN"]
        #print(session.headers)
        #print(session.cookies)

        driver.quit()

    def _set_registration_info(self):
        registrations = self.get_eligible_registrations()
        registration_d = {}
        for registration in registrations:
            session_code = registration["sessionCode"]
            registration_d[session_code] = registration
            
        self.registration_info = registration_d

    def get_student_registration_info(self):
        url = BASE_URL + "/sws/rest/profile/studentRegistrationInfo"
        r = self.session.get(url)
        response = r.json()
        return response

    def get_student_basic_info(self):
        url = BASE_URL + "/sws/rest/profile/studentBasicInfo"
        r = self.session.get(url)
        response = r.json()
        return response

    def get_eligible_registrations(self):
        url = BASE_URL + "/sws/rest/enrolment/eligible-registrations"
        r = self.session.get(url)
        response = r.json()
        return response

    def get_current_registrations(self):
        url = BASE_URL + "/sws/rest/enrolment/current-registrations"
        r = self.session.get(url)
        response = r.json()
        return response

    def get_posts(self):
        url = BASE_URL + "/sws/rest/subjectpost/subjectposts"
        payload = {"_ts":int(time.time() * 1000)}
        r = self.session.get(url, params=payload)
        response = r.json()
        return response

    def get_enrolled_courses(self, session_code):
        url = BASE_URL + "/sws/rest/enrolment/course/enrolled-courses"
        copy = self.registration_info[session_code]["registrationParams"].copy()
        r = self.session.get(url, params=self.registration_info[session_code]["registrationParams"])
        response = r.json()
        return response

    def get_enrolment_cart(self, session_code):
        url = BASE_URL + "/sws/rest/enrolment/plan"
        registration_info = self.registration_info[session_code]
        payload = {"candidacyPostCode":registration_info["candidacyPostCode"],
                   "candidacySessionCode":registration_info["candidacySessionCode"],
                   "courseSessionCode":registration_info["sessionCode"],
                   "sessionCode":registration_info["sessionCode"]}
        r = self.session.get(url, params=payload)
        response = r.json()
        return response

    def get_matching_courses(self, course_prefix, session_code):
        url = BASE_URL + "/sws/rest/enrolment/course/matching-courses"
        registration_info = self.registration_info[session_code]
        payload = registration_info["registrationParams"].copy()
        payload["coursePrefix"] = course_prefix
        payload["sessions"] = registration_info["registrationSessions"]
        payload["studentCampus"] = registration_info["studentCampusCode"]
        print(course_prefix)
        print(payload["sessions"])
        r = self.session.get(url, params=payload)
        response = r.json()
        return response

    def get_course_info(self, course_code, section_code, session_code):
        matching_courses = self.get_matching_courses(course_code, session_code)
        for course in matching_courses:
            if course["sectionCode"] == section_code:
                return course
            
        return {}

    def get_course_prereqs(self, course_code, section_code, session_code):
        url = BASE_URL + "/sws/rest/enrolment/course/get-course-prereqs"
        course_info = self.get_course_info(course_code, section_code, session_code)
        if not course_info:
            return {}
        
        payload = {"courseCode":course_info["activityCode"],
                   "sessionCode":course_info["sessionCode"]}
        r = self.session.get(url, params=payload)
        response = r.json()
        print(r.text)
        return response

    def get_full_course_info(self, course_code, section_code, session_code):
        url = BASE_URL + "/sws/rest/enrolment/course/view"
        registration_info = self.registration_info[session_code]
        course_info = self.get_course_info(course_code, section_code, session_code)
        if course_info:
            payload = registration_info["registrationParams"].copy()
            payload["activityApprovedInd"] = ""
            payload["activityApprovedOrg"] = ""
            payload["courseCode"] = course_info["activityCode"]
            payload["courseSessionCode"] = course_info["sessionCode"]
            payload["sectionCode"] = course_info["sectionCode"]
            r = self.session.get(url, params=payload)
            f = open("full_info_{}{}.txt".format(course_code, section_code), "w")
            f.write(r.text)
            f.close()
            response = r.json()
            return response

        return {}

    def enrol_course(self, course_code, section_code, session_code, lec_section_no=None, pra_section_no=None, tut_section_no=None):
        url = BASE_URL + "/sws/rest/enrolment/course/modify"
        registration_info = self.registration_info[session_code]
        course_resp = self.get_full_course_info(course_code, section_code, session_code)["responseObject"]
        course_d = {"code":course_resp["code"],
                    "enroled":course_resp["enroled"],
                    "primaryTeachMethod":course_resp["primaryTeachMethod"],
                    "sectionCode":course_resp["sectionCode"]}
        lecture_d = {}
        if lec_section_no:
            lecture_d["sectionNo"] = "LEC," + lec_section_no

        practical_d = {}
        if pra_section_no:
            practical_d["sectionNo"] = "PRA," + pra_section_no

        tutorial_d = {}
        if tut_section_no:
            tutorial_d["sectionNo"] = "TUT," + tut_section_no
        
        course_data = {"course":course_d,
                       "lecture":lecture_d,
                       "practical":practical_d,
                       "tutorial":tutorial_d}
        data = {"activeCourse":course_data,
                "eligRegParams":registration_info["registrationParams"]}
        #session.headers["Host"] = "acorn.utoronto.ca"
        #session.headers["Origin"] = "https://acorn.utoronto.ca"
        #session.headers["Referer"] = "https://acorn.utoronto.ca/sws/welcome.do?welcome.dispatch"
        r = self.session.post(url, json=data)
        print(r.status_code, r.text)
        response = r.json()
        #print(response)
        return response

    def drop_course(self, course_code, section_code, session_code):
        url = BASE_URL + "/sws/rest/enrolment/course/drop"
        registration_info = self.registration_info[session_code]
        enrolled_course_info = self.get_enrolled_courses(session_code)
        course_data = {"code":course_code,
                       "sectionCode":section_code,
                       "status":"APP"} # APP is applied; WAIT is waitlisted
        
        if "WAIT" in enrolled_course_info:
            for waitlisted in enrolled_course_info["WAIT"]:
                if waitlisted["code"] == course_code and waitlisted["sectionCode"] == section_code:
                    course_data["status"] = "WAIT"
             
        data = {"course":course_data,
                "eligRegParams":registration_info["registrationParams"]}
        r = self.session.post(url, json=data)
        print(r.status_code, r.text)
        response = r.json()
        #print(response)
        return response

    def waitlist_course(self, course_code, section_code, session_code, meetings):
        url = BASE_URL + "/sws/rest/enrolment/waitlist/wait"
        registration_info = self.registration_info[session_code]
        course_resp = self.get_full_course_info(course_code, section_code)["responseObject"]
        course_data = {"code":course_resp["code"],
                       "sectionCode":course_resp["sectionCode"],
                       "primaryTeachMethod":course_resp["primaryTeachMethod"]}
        meetings_l = []
        for teach_method, section_no in meetings:
            section_d = {"teachMethod":teach_method,
                         "sectionNo":section_no}
            meetings_l.append(section_d)
        
        waitlisted_d = {"course":course_data,
                        "meetingSections":meetings_l}
        original_d = {"code":course_resp["code"],
                      "enroled":course_resp["enroled"],
                      "primaryTeachMethod":course_resp["primaryTeachMethod"],
                      "sectionCode":course_resp["sectionCode"],
                      "waitlistMeetings":course_resp["waitlistMeetings"]}
        data = {"waitlistedCourse":waitlisted_d,
                "originalCourse":original_d,
                "eligRegParams":registration_info["registrationParams"]}
        r = self.session.post(url, json=data)
        print(r.status_code, r.text)
        response = r.json()
        return response

    def _create_messages(self, prereq_info):
        messages = []
        if prereq_info["prerequisites"]:
            info = ["Course(s) you need to take before you are eligible for this one:"]
            for prereq in prereq_info["prerequisites"]:
                info.append(prereq["description"])

            d = {"title":"Prerequisite",
                 "value":"<br/>".join(info)}
            messages.append(d)

        if prereq_info["corequisites"]:
            info = ["Course must be taken during the same term, unless previously passed:"]
            for coreq in prereq_info["corequisites"]:
                info.append(coreq["description"])

            d = {"title":"Corequisite",
                 "value":"<br/>".join(info)}
            messages.append(d)

        if prereq_info["orderedExclusions"]:
            info = ["Courses with content too similar to each other to be taken for credit:"]
            for exclusion in prereq_info["orderedExclusions"]:
                info.append(exclusion["description"])

            d = {"title":"Ordered Exclusions",
                 "value":"<br/>".join(info)}
            messages.append(d)
        
        return messages

    def _create_enrolment_cart_data(self, course_code, section_code, session_code, prereq_info, meetings):
        course_resp = self.get_full_course_info(course_code, section_code, session_code)["responseObject"]
        info_d = {"primaryActivities":[], #lec
                  "secondaryActivities":[], #tut
                  "thirdActivities":[]} #pra

        for meeting in course_resp["meetings"]:
            if (meeting["teachMethod"], meeting["sectionNo"]) in meetings:            
                days = []
                for meet_time in meeting["times"]:
                    day_info = {"roomLocation":meet_time["buildingCode"] + " " + meet_time["room"],
                                "startTime":meet_time["startTime"],
                                "endTime":meet_time["endTime"],
                                "dayOfWeek":meet_time["day"]["dayName"]}
                    days.append(day_info)
                
                meeting_info = {"sectionNo": meeting["sectionNo"],
                                "teachMethod": meeting["teachMethod"],
                                "activityId": meeting["displayName"],
                                "cancelled": meeting["cancelled"],
                                "closed": meeting["closed"],
                                "spaceTotal": meeting["totalSpace"],
                                "spaceLeft": meeting["enrollmentSpaceAvailable"],
                                "classTotal": meeting["enrollSpace"],
                                "note": "displayCourseInfo.js:getActivity",
                                "waitlistable": meeting["waitlistable"],
                                "waitlistableForAll": meeting["waitlistableForAll"],
                                "checkedStatus": True,
                                "enroled": False,
                                "waitlistRank": meeting["waitlistRank"],
                                "commaSeparatedInstructorNames": meeting["commaSeparatedInstructorNames"],
                                "subTitle": meeting["subTitle"],
                                "hasSubTitle": meeting["hasSubTitle"],
                                "days":days,
                                "enrolledInAllActivities": False,
                                "waitlistLookupMethod": meeting["waitlistLookupMethod"],
                                "formName": "primaryActivity",
                                "readOnlyMode": True}
                teach_type = meeting_info["teachMethod"]
                if teach_type == "LEC":
                    meeting_info["formName"] = "primaryActivity"
                    info_d["primaryActivities"].append(meeting_info)
                elif teach_type == "TUT":
                    meeting_info["formName"] = "secondaryActivity"
                    info_d["secondaryActivities"].append(meeting_info)
                elif teach_type == "PRA":
                    meeting_info["formName"] = "thirdActivity"
                    info_d["thirdActivities"].append(meeting_info)

        messages_l = self._create_messages(prereq_info)
        sessions_d = {}
        for reg_session in ["regSessionCode1", "regSessionCode2", "regSessionCode3"]:
            if course_resp[reg_session]:
                sessions_d[reg_session] = course_resp[reg_session]
                
        data = {"courseCode":course_resp["code"],
                "courseTitle":course_resp["title"],
                "sectionCode":course_resp["sectionCode"],
                "info":info_d,
                "messages":messages_l,
                "regSessions":sessions_d}
        
        return data

    def add_enrolment_cart(self, course_code, section_code, session_code, meetings):
        url = BASE_URL + "/sws/rest/enrolment/plan"
        course_resp = self.get_full_course_info(course_code, section_code, session_code)["responseObject"]
        prereq_info = self.get_course_prereqs(course_code, section_code, session_code)
        registration_info = self.registration_info[session_code]
        payload = {"candidacyPostCode":registration_info["candidacyPostCode"],
                   "candidacySessionCode":registration_info["candidacySessionCode"],
                   "courseSessionCode":course_resp["sessionCode"],
                   "sessionCode":registration_info["sessionCode"]}
        data = self._create_enrolment_cart_data(course_code, section_code, session_code, prereq_info, meetings)
        r = self.session.post(url, json=data, params=payload)
        print(r.status_code, r.text)
        response = r.json()
        #print(response)
        return response

    def update_enrolment_cart(self, course_code, section_code, session_code, plan_id):
        url = BASE_URL + "/sws/rest/enrolment/plan/update/course"
        course_resp = self.get_full_course_info(course_code, section_code, session_code)["responseObject"]
        registration_info = self.registration_info[session_code]
        payload = {"candidacyPostCode":registration_info["candidacyPostCode"],
                   "candidacySessionCode":registration_info["candidacySessionCode"],
                   "courseSessionCode":course_resp["sessionCode"],
                   "sessionCode":self.registration_info["sessionCode"]}
        data = self._create_enrolment_cart_data(course_code, section_code, session_code)
        data["planId"] = plan_id
        r = self.session.post(url, json=data, params=payload)
        print(r.status_code, r.text)
        response = r.json()
        #print(response)
        return response

    def delete_enrolment_cart(self, plan_id):
        url = BASE_URL + "/sws/rest/enrolment/plan"
        payload = {"planId":plan_id}
        r = self.session.delete(url, params=payload)
        print(r.status_code, r.text)
        return

    def enrol_change(self, course_code, section_code, session_code, meetings):
        # enrolled to waitlist
        url = BASE_URL + "/sws/rest/enrolment/waitlist/confirm-enrolled-change"
        registration_info = self.registration_info[session_code]
        course_resp = self.get_full_course_info(course_code, section_code, session_code)["responseObject"]
        course_data = {"code":course_resp["code"],
                       "sectionCode":course_resp["sectionCode"],
                       "primaryTeachMethod":course_resp["primaryTeachMethod"]}
        meetings_l = []
        for teach_method, section_no in meetings:
            section_d = {"teachMethod":teach_method,
                         "sectionNo":section_no}
            meetings_l.append(section_d)

        applied_info = {}
        applied_courses = self.get_enrolled_courses()["APP"]
        for applied_course_info in applied_courses:
            if applied_course_info["code"] == course_code and applied_course_info["sectionCode"] == section_code:
                applied_info = applied_course_info
        
        waitlisted_d = {"course":course_data,
                        "meetingSections":meetings_l}
        original_d = {"enroled":True,
                      "primaryTeachMethod":applied_info["primaryTeachMethod"],
                      "primarySectionNo":applied_info["primarySectionNo"]}
        data = {"waitlistedCourse":waitlisted_d,
                "originalCourse":original_d,
                "eligRegParams":registration_info["registrationParams"]}
        r = self.session.post(url, json=data)
        #print(data)
        print(r.status_code, r.text)
        response = r.json()
        #print(response)
        return response

    def get_full_transcript(self):
        url = BASE_URL + "/sws/transcript/academic/main.do?main.dispatch"
        payload = {"mode":"complete"}
        r = self.session.get(url, params=payload)
        #print(r.status_code, r.text)
        html = BeautifulSoup(r.text, "lxml")
        tags = html.find_all("div", attrs={"class":"courses blok pre-elem"})
        courses = []
        courses_data = []
        for tag in tags:
            courses.extend(tag.text.strip().split("\n"))

        return courses

    def _update_mark(self, course_code, grade, passed, curr_marks):
        if course_code in curr_marks:
            #update from ncr
            if curr_marks[course_code] == [-1, False]:
                curr_marks[course_code] = [grade, passed]
            #update from cr if now passed
            elif curr_marks[course_code] == [-1, True] and passed:
                curr_marks[course_code] = [grade, passed]
            #update from fail if now cr
            elif curr_marks[course_code][1] == False and grade == -1:
                curr_marks[course_code] = [grade, passed]
            #update mark if improved
            elif grade > curr_marks[course_code][0]:
                curr_marks[course_code] = [grade, passed]
        else:
            curr_marks[course_code] = [grade, passed]
        
        return

    def _get_course_marks(self):
        explorer = degree_explorer.DegreeExplorer(self.username, self.password)
        academic_history = explorer.get_academic_history()
        course_marks = {}
        for faculty in academic_history["facultyCourses"]:
            for session in faculty["studentSessions"]:
                for course_info in session["studentCourses"]:
                    course_code = course_info["courseCode"]
                    course_mark = course_info["enteredMark"]
                    passed = course_info["passIndicator"] == "Y"
                    grade = -1
                    if course_mark.isdigit():
                        grade = int(course_mark)

                    self._update_mark(course_code, grade, passed, course_marks)

        for course_info in academic_history["highSchoolCourses"]:
            course_code = course_info["courseCode"]
            course_mark = course_info["enteredMark"]
            passed = False
            grade = -1
            if course_mark.isdigit():
                grade = int(course_mark)
                passed = grade >= 50
            else:
                #special cases for high school marks
                pass

            self._update_mark(course_code, grade, passed, course_marks)
        
        return course_marks
    
        courses_data = {}
        full_transcript = self.get_full_transcript()
        for course in full_transcript:
            #print(course)
            m1 = re.search("(^[A-Z]{3}[A-Z0-9]{1}[0-9]{2}[HY]{1}[135]{1}).*[01]{1}\.[05]{2}\s+([0-9]{1,3})", course)
            m2 = re.search("(^[A-Z]{3}[A-Z0-9]{1}[0-9]{2}[HY]{1}[135]{1}).*[01]{1}\.[05]{2}\s+(NCR|CR)", course)
            if m1 or m2:
                if m1:
                    course_code = m1.group(1)
                    course_mark = int(m1.group(2))
                    if course_mark >= 50:
                        passed = True
                    else:
                        passed = False
                else:
                    course_code = m2.group(1)
                    course_grade = m2.group(2)
                    if course_grade == "CR":
                        passed = True
                    else:
                        passed = False

                    course_mark = -1

                if course_code in courses_data:
                    #update from ncr
                    if courses_data[course_code] == [-1, False]:
                        courses_data[course_code] = [course_mark, passed]
                    #update from cr if now passed
                    elif courses_data[course_code] == [-1, True] and passed:
                        courses_data[course_code] = [course_mark, passed]
                    #update from fail if now cr
                    elif courses_data[course_code][1] == False and course_mark == -1:
                        courses_data[course_code] = [course_mark, passed]
                    #update mark if improved
                    elif course_mark > courses_data[course_code][0]:
                        courses_data[course_code] = [course_mark, passed]
                else:
                    courses_data[course_code] = [course_mark, passed]

        return courses_data

    def _create_prereq_graph(self, prereq_descriptions):
        G = {}
        for description in prereq_descriptions:
            m = re.search("^\((P\d+)\)", description)
            node = m.group(1)
            neighbours = re.findall(" P\d+", description)
            G[node] = []
            for neighbour in neighbours:
                G[node].append(neighbour.strip())
        
        return G

    def _explore(self, graph, node, visited, order):
        for neighbour in graph[node]:
            if not visited[neighbour]:
                self._explore(graph, neighbour, visited, order)


        visited[node] = True
        order.append(node)

    def _topsort(self, graph):
        visited = {node:False for node in graph}
        order = []
        for node in graph:
            if not visited[node]:
                self._explore(graph, node, visited, order)

        order.reverse()                
        return order

    def _get_course_equivalents(self, course_code):
        equivalents = []
        if course_code[-2] == "Y":
            prereq_info = self.get_course_prereqs(course_code, "Y")
        else:
            prereq_info = self.get_course_prereqs(course_code, "F")
            if not prereq_info:
                prereq_info = self.get_course_prereqs(course_code, "S")

        if prereq_info:    
            for equiv_info in prereq_info["equivalents"]:
                for course in equiv_info["courses"]:
                    equivalents.append(course["code"])

        return equivalents
    
    def _prereq_match(self, course_marks, course_code):
        if course_code in course_marks:
            return (True, course_code)
        for equiv_code in self._get_course_equivalents(course_code):
            if equiv_code in course_marks:
                return (False, equiv_code)
            
        return (False, "")

    def _satisfied_prereqs_helper(self, course_marks, prereq, all_prereqs, satisfied):
        print(prereq)
        if prereq["values"] == []:
            if prereq["count"]:
                required_count = float(prereq["count"])
            else:
                required_count = 0
            if prereq["requisiteType"] == "ALL_OF":
                if prereq["countType"] == "COURSES":
                    pass
                else:
                    pass
            elif prereq["requisiteType"] == "MINIMUM":
                if prereq["countType"] == "COURSES":
                    completed_count = 0
                    for course in prereq["courses"]:
                        equiv_courses = self._get_course_equivalents(course["code"])
                        for course_code in equiv_courses:
                            if course_code in course_marks:
                                completed_count += 1
                                break

                    satisfied[prereq["key"]] = completed_count >= required_count
                elif prereq["countType"] == "CREDITS":
                    completed_count = 0
                    for course in prereq["courses"]:
                        equiv_courses = self._get_course_equivalents(course["code"])
                        for course_code in equiv_courses:
                            if course_code in course_marks and course_marks[course_code][1]:
                                if course_code[-2] == "H":
                                    completed_count += 0.5
                                else:
                                    completed_count += 1

                                break

                    satisfied[prereq["key"]] = completed_count >= required_count
                elif prereq["countType"] == "GRADE":
                    completed_count = 0
                    target = prereq["targetValue"]
                    for course in prereq["courses"]:
                        equiv_courses = self._get_course_equivalents(course["code"])
                        for course_code in equiv_courses:
                            if course_code in course_marks and course_marks[course_code][0] >= target:
                                completed_count += 1
                                break

                    satisfied[prereq["key"]] = completed_count >= required_count
                elif prereq["countType"] == "SUBJECT_POSTS":
                    completed_count = 0
                    post_info = self.get_posts()["ACT"]
                    post_codes = []
                    print(post_info)
                    for post in post_info:
                        post_codes.append(post["code"])
                        
                    for course in prereq["courses"]:
                        if course["code"] in post_codes:
                            completed_count += 1

                    satisfied[prereq["key"]] = completed_count >= required_count
                else:
                    satisfied[prereq["key"]] = True
            elif prereq["requisiteType"] == "MAXIMUM":
                if prereq["countType"] == "COURSES":
                    completed_count = 0
                    for course in prereq["courses"]:
                        equiv_courses = self._get_course_equivalents(course["code"])
                        for course_code in equiv_courses:
                            if course_code in course_marks:
                                completed_count += 1
                                break

                    satisfied[prereq["key"]] = completed_count <= required_count
                else:
                    satisfied[prereq["key"]] = True
            else:
                satisfied[prereq["key"]] = True
        else:
            completed_count = 0
            required_count = float(prereq["count"])
            for subreq in prereq["values"]:
                if subreq not in satisfied:
                    if self._satisfied_prereqs_helper(course_marks, all_prereqs[subreq], all_prereqs, satisfied):
                        completed_count += 1

                elif satisfied[subreq]:
                    completed_count += 1

            satisfied[prereq["key"]] = completed_count >= required_count

        return satisfied[prereq["key"]]

    def _satisfied_prereqs(self, course_code, section_code):
        satisfied = {}
        course_marks = self._get_course_marks()
        prereq_info = self.get_course_prereqs(course_code, section_code)
        descriptions = []
        for prereq in prereq_info["prerequisites"]:
            descriptions.append(prereq["description"])

        graph = self._create_prereq_graph(descriptions)
        order = self._topsort(graph)
        #pprint.pprint(descriptions)
        #pprint.pprint(graph)
        print(order)
        prereqs = prereq_info["prerequisites"][:]
        for i in range(len(prereqs)):
            node = "P{}".format(i+1)
            prereqs[i]["key"] = node
            prereqs[i]["values"] = graph[node]

        all_prereqs = {}
        for prereq in prereqs:
            all_prereqs[prereq["key"]] = prereq

        prereqs.sort(key=lambda x: order.index(x["key"]))
        for prereq in prereqs:
            if prereq["key"] not in satisfied:
                self._satisfied_prereqs_helper(course_marks, prereq, all_prereqs, satisfied)
                pass
        
        return satisfied

    def _time_to_index(self, class_time):
        if len(class_time) == 6:
            class_time = "0" + class_time

        index = 0
        if class_time[-2:] == "PM":
            index += 24
            
        hour = int(class_time[:2]) % 12
        index += hour * 2
        if class_time[3:5] == "30":
            index += 1
            
        return index   

    def _add_to_timetable(self, table, meeting):
        all_indexes = []
        for times in meeting["times"]:
            table_row = times["dayIndex"]
            start_index = self._time_to_index(times["startTime"])
            end_index = self._time_to_index(times["endTime"]) + 1
            all_indexes.append((table_row, start_index, end_index))
            if sum(table[table_row][start_index:end_index]) != 0:
                return False
        
        for table_row, start_index, end_index in all_indexes:
            for i in range(start_index, end_index):
                table[table_row][i] = 1
                
        return True

    def _remove_from_timetable(self, table, meeting):
        all_indexes = []
        for times in meeting["times"]:
            table_row = times["dayIndex"]
            start_index = self._time_to_index(times["startTime"])
            end_index = self._time_to_index(times["endTime"]) + 1
            all_indexes.append((table_row, start_index, end_index))

        for table_row, start_index, end_index in all_indexes:
            for i in range(start_index, end_index):
                table[table_row][i] = 0
                
        return

    def _get_all_schedules(self, all_meetings, curr_schedules):
        if not all_meetings:
            return curr_schedules

        new_schedules = []
        for curr_schedule in curr_schedules:
            for i in range(len(all_meetings[0])):
                schedule = curr_schedule + [i]
                new_schedules.append(schedule)
                
        return self._get_all_schedules(all_meetings[1:], new_schedules)

    def _get_possible_schedules(self, all_meetings):
        possible = []
        all_schedules = self._get_all_schedules(all_meetings, [[]])
        for schedule in all_schedules:
            timetable = [[0]*48 for _ in range(7)]
            valid = True
            for course_index, meeting_index in enumerate(schedule):
                course_meetings = all_meetings[course_index][meeting_index]
                for meeting in course_meetings:
                    if not self._add_to_timetable(timetable, meeting):
                        valid = False
                        break

            if valid:
                possible.append(schedule)
        
        return possible

    def _transform_meeting(self, course_code, section_code, meeting):
        new_meeting = {"code":course_code, "sectionCode":section_code}
        new_meeting["teachMethod"] = meeting["teachMethod"]
        new_meeting["sectionNo"] = meeting["sectionNo"]
        times = []
        for times_d in meeting["times"]:
            new_times_d = {"dayIndex":times_d["day"]["index"],
                           "startTime":times_d["startTime"],
                           "endTime":times_d["endTime"]}
            times.append(new_times_d)

        new_meeting["times"] = times
        return new_meeting

    def _schedule_courses(self, courses):
        all_meetings = []
        for course_code, section_code in courses:
            info = self.get_full_course_info(course_code, section_code)
            if info:
                lec_times = []
                tut_times = []
                pra_times = []
                code = info["responseObject"]["code"]
                section_code = info["responseObject"]["sectionCode"]
                meetings = info["responseObject"]["meetings"]
                for meeting in meetings:
                    # class has space, not restricted
                    if meeting["enrollmentSpaceAvailable"] > 0:
                        new_meeting = self._transform_meeting(code, section_code, meeting)
                        if meeting["teachMethod"] == "LEC":
                            lec_times.append(new_meeting)
                        elif meeting["teachMethod"] == "TUT":
                            tut_times.append(new_meeting)
                        else:
                            pra_times.append(new_meeting)

                course_meeting_combos = []
                # start adding lecture add times
                for lec_time in lec_times:
                    course_meeting_combos.append((lec_time,))

                # add tutorial times to current combos, if they exist
                if tut_times:
                    new_combos = []
                    for combo in course_meeting_combos:
                        for tut_time in tut_times:
                            new_combo = combo + (tut_time,)
                            new_combos.append(new_combo)

                    course_meeting_combos = new_combos[:]

                # add practical times to current combos, if they exist
                if pra_times:
                    new_combos = []
                    for combo in course_meeting_combos:
                        for pra_time in pra_times:
                            new_combo = combo + (pra_time,)
                            new_combos.append(new_combo)

                    course_meeting_combos = new_combos[:]

                all_meetings.append(course_meeting_combos)

        #pprint.pprint(all_meetings)
        schedules = self._get_possible_schedules(all_meetings)
        print(schedules)
        return

username = input("Username:").strip()
password = input("Password:").strip()
acorn = Acorn(username, password)
#pprint.pprint(acorn.get_posts())
#pprint.pprint(acorn._get_course_marks())
"""
session_code = "20209"
cart = acorn.get_enrolment_cart(session_code)
for course in cart:
    course_code = course["courseCode"]
    section_code = course["sectionCode"]
    course_info = course["info"]
    lec_section_no = None
    pra_section_no = None
    tut_section_no = None

    if course_info["primaryActivities"]:
        lec_section_no = course_info["primaryActivities"][0]["sectionNo"]
    if course_info["secondaryActivities"]:
        lec_section_no = course_info["secondaryActivities"][0]["sectionNo"]
    if course_info["thirdActivities"]:
        lec_section_no = course_info["thirdActivities"][0]["sectionNo"]
        
    acorn.enrol_course(course_code, section_code, session_code,
                       lec_section_no=lec_section_no,
                       pra_section_no=pra_section_no,
                       tut_section_no=tut_section_no)
"""
