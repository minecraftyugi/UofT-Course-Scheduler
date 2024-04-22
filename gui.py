from threading import Thread
import tkinter as tk
import json

root = tk.Tk()
root.title("UofT Acorn Planner")
root.state("zoomed")
root.resizable(0, 0)

def create_scroll_text(root_widget):
    root_widget.update()
    scroll = tk.Scrollbar(root_widget)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    text = tk.Text(root_widget)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.config(command=text.yview) 
    text.config(yscrollcommand=scroll.set)
    for i in range(100):
        text.insert(tk.END, "a\n")
        
    return text

def display_plan(root_widget, plan):
    root_widget.update()
    
    return

def insert_meetings(root_widget, meetings, curr_sections):
    curr_row = root_widget.grid_size()[1]
    activity_title = tk.Label(root_widget, text="Activity")
    activity_title.grid(row=curr_row, column=1)
    time_title = tk.Label(root_widget, text="Times")
    time_title.grid(row=curr_row, column=2)
    space_title = tk.Label(root_widget, text="Space Available")
    space_title.grid(row=curr_row, column=3)
    radio_var = tk.IntVar(master=root_widget)
    curr_row += 1
    print(curr_sections)
    for i, meeting in enumerate(meetings):
        teach_method = meeting["teachMethod"]
        section_num = meeting["sectionNo"]
        print(teach_method, section_num)
        if teach_method in curr_sections and curr_sections[teach_method] == section_num:
            radio_var.set(i)
        print(radio_var.get())
        radio = tk.Radiobutton(root_widget, value=i, var=radio_var)
        radio.grid(row=curr_row, column=0)
        
            
        activity_label = tk.Label(root_widget, text=meeting["displayName"])
        activity_label.grid(row=curr_row, column=1)
        time_label = tk.Label(root_widget, text=meeting["displayTime"])
        time_label.grid(row=curr_row, column=2)
        avail = meeting["enrollmentSpaceAvailable"]
        total = meeting["enrollSpace"]
        space = "{} of {}".format(avail, total)
        space_label = tk.Label(root_widget, text=space)
        space_label.grid(row=curr_row, column=3)
        curr_row += 1
    
    return radio_var

def insert_waitlist(root_widget, meetings, curr_sections):
    curr_row = root_widget.grid_size()[1]
    activity_title = tk.Label(root_widget, text="Activity")
    activity_title.grid(row=curr_row, column=1)
    time_title = tk.Label(root_widget, text="Times")
    time_title.grid(row=curr_row, column=2)
    space_title = tk.Label(root_widget, text="Waitlist Size")
    space_title.grid(row=curr_row, column=3)
    check_vars = []
    curr_row += 1
    for i, meeting in enumerate(meetings):
        check_var = tk.BooleanVar()
        check_vars.append(check_var)
        check = tk.Checkbutton(root_widget, var=check_var)
        check.grid(row=curr_row, column=0)
        activity_label = tk.Label(root_widget, text=meeting["displayName"])
        activity_label.grid(row=curr_row, column=1)
        time_label = tk.Label(root_widget, text=meeting["displayTime"])
        time_label.grid(row=curr_row, column=2)
        wait_size = meeting["waitlistRank"]
        total = meeting["enrollSpace"]
        space = "{} (Class size: {})".format(wait_size, total)
        space_label = tk.Label(root_widget, text=space)
        space_label.grid(row=curr_row, column=3)
        curr_row += 1
    
    return check_vars

def display_course(root_widget, course_info):
    root_widget.update()
    resp = course_info["responseObject"]
    course_code = resp["code"]
    section_code = resp["sectionCode"]
    course_title = resp["title"]
    curr_sections = {resp["primaryTeachMethod"]:resp["primarySectionNo"],
                     resp["secondaryTeachMethod1"]:resp["secondarySectionNo1"],
                     resp["secondaryTeachMethod2"]:resp["secondarySectionNo2"]}
    
    full_title = " ".join([course_code, section_code, course_title])
    title_label = tk.Label(root_widget, text=full_title, fg="red")
    title_label.grid(row=0, columnspan=4)
    
    lec_meetings = []
    tut_meetings = []
    pra_meetings = []
    waitlist_meetings = []
    for meeting in resp["meetings"]:
        if meeting["waitlistable"]:
            waitlist_meetings.append(meeting)
        elif meeting["teachMethod"] == "LEC":
            lec_meetings.append(meeting)
        elif meeting["teachMethod"] == "TUT":
            tut_meetings.append(meeting)
        else:
            pra_meetings.append(meeting)

    lec_meetings.sort(key=lambda x:x["displayName"])
    tut_meetings.sort(key=lambda x:x["displayName"])
    pra_meetings.sort(key=lambda x:x["displayName"])
    waitlist_meetings.sort(key=lambda x:x["displayName"])
    if lec_meetings:
        lec_var = insert_meetings(root_widget, lec_meetings, curr_sections)

    if tut_meetings:
        tut_var = insert_meetings(root_widget, tut_meetings, curr_sections)

    if pra_meetings:
        pra_var = insert_meetings(root_widget, pra_meetings, curr_sections)

    if waitlist_meetings:
        wait_var = insert_waitlist(root_widget, waitlist_meetings, curr_sections)
    
    return

frame = tk.Frame(root)
frame.place(x=100, y=100, width=500, height=500)
#print(dir(frame))
#f = open("full_info_JRE300H1S.txt")
f = open("full_info_CSC373H5F.txt")
info = json.loads(f.read())
f.close()
display_course(frame, info)
##text = create_scroll_text(frame)
##text.config(state=tk.DISABLED)
##text.config(state=tk.NORMAL)

if __name__ == "__main__":
    root.mainloop()

