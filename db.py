import mysql.connector as mysql

db = mysql.connect(host = "localhost", user = "user", passwd = "password")

cursor = db.cursor()

class CourseDB:
    def __init__(self, host, username, password):
        self._db = mysql.connect(host=host, user=username, passwd=password)
        self._db.get_warnings = True
        self._dbname = "course_test"
        self.create_courses_table()
        self.create_prerequisites_table()
        self.create_exclusions_table()
        self.create_meetings_table()
        return

    def create_courses_table(self):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        cursor.execute("""
        create table if not exists courses(
        code varchar(10) not null,
        title varchar(100) not null,
        division varchar(100) not null,
        description varchar(1000) not null,
        department varchar(100) not null,
        level varchar(10) not null,
        campus varchar(20) not null,
        breadth varchar(100) not null,
        distribution varchar(100) not null,
        elective varchar(100) not null,
        term varchar(20) not null,
        primary key (code, term)
        );
        """)
        return

    def create_prerequisites_table(self):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        cursor.execute("""
        create table if not exists prerequisites(
        code varchar(10) not null,
        term varchar(20) not null,
        prereq varchar(100) not null,
        primary key (code, term, prereq),
        foreign key (code, term) references courses(code, term)
        );
        """)
        return

    def create_exclusions_table(self):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        cursor.execute("""
        create table if not exists exclusions(
        code varchar(10) not null,
        term varchar(20) not null,
        exclusion varchar(100) not null,
        primary key (code, term, exclusion),
        foreign key (code, term) references courses(code, term)
        );
        """)
        return

    def create_meetings_table(self):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        cursor.execute("""
        create table if not exists meetings(
        code varchar(10) not null,
        term varchar(20) not null,
        activity varchar(10) not null,
        day varchar(10) not null,
        start int not null,
        end int not null,
        instructor varchar(100) not null,
        location varchar(10) not null,
        size int not null,
        enrolled int not null,
        delivery varchar(10) not null,
        primary key (code, term, activity),
        foreign key (code, term) references courses(code, term)
        );
        """)
        return

    def insert_course(self, course_info):
        self._insert_course_general(course_info)
        self._insert_course_prerequisites(course_info)
        self._insert_course_exclusions(course_info)
        self._insert_course_meetings(course_info)
        return

    def _insert_course_general(self, course_info):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        query = """
        insert into courses values (
        %(code)s, %(title)s, %(division)s, %(description)s, %(department)s,
        %(level)s, %(campus)s, %(breadth)s, %(distribution)s, %(elective)s,
        %(term)s
        );"""
        d = {}
        for k, v in course_info.items():
            if k != "meetings":
                d[k] = v
        cursor.execute(query, d)
        #print(cursor.fetchwarnings())
        self._db.commit()
        return

    def _insert_course_prerequisites(self, course_info):
        return

    def _insert_course_exclusions(self, course_info):
        return

    def _insert_course_meetings(self, course_info):
        cursor = self._db.cursor()
        cursor.execute("use {}".format(self._dbname))
        meetings = course_info["meetings"]
        for activity, times, prof, location, size, enrolment, delivery in meetings:
            if size:
                size = int(size)
            else:
                size = 0

            if enrolment:
                enrolment = int(enrolment)
            else:
                enrolment = 0

            day_times = times.split()
            for i in range(0, len(day_times), 2):
                day = day_times[i]
                time = day_times[i+1]
        return
    
class UserDB:
    def __init__(self, host, username, password):
        self._db = mysql.connect(host=host, user=username, passwd=password)
        self._dbname = "user_test"
        return
