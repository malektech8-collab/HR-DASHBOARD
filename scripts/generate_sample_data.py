import csv
import os
import random
from datetime import datetime, timedelta

def create_sample_data():
    os.makedirs("data/sample", exist_ok=True)
    
    # 1. Employees data
    # We will generate about 20 employees, including the required data quality issues:
    # - EMP001: Normal active Saudi employee
    # - EMP002: Normal active non-Saudi employee
    # - EMP003: Active Saudi but missing manager_id
    # - EMP004: Active non-Saudi but missing project
    # - EMP005: Duplicate Employee ID (we will output EMP005 twice with different names)
    # - EMP006: Inactive employee (Terminated) but we will give them a payroll record in payroll_sample.csv
    # - EMP007: Active employee but basic_salary = 0 (missing salary)
    # - EMP008: Active employee but negative housing allowance and basic_salary (abnormal payroll value)
    # - EMP009: Active employee but nationality is empty
    # - EMP010: Active employee but cost_center is empty
    # - Other employees (EMP011 to EMP020) will be normal to simulate realistic percentages.
    
    employees = [
        # employee_id, employee_name, nationality, is_saudi, company, department, project, job_title, job_family, grade, manager_id, cost_center, employment_type, contract_type, joining_date, termination_date, contract_end_date, status, basic_salary, housing_allowance, transport_allowance
        ["EMP001", "Ahmad Al-Sudairy", "Saudi", "True", "Company A", "HR", "PROJ-ALPHA", "HR Specialist", "HR", "G3", "EMP011", "CC-HR", "Full-time", "Unlimited", "2024-01-15", "", "", "Active", "12000", "3000", "1000"],
        ["EMP002", "John Doe", "British", "False", "Company A", "Engineering", "PROJ-BETA", "Software Engineer", "IT", "G4", "EMP012", "CC-ENG", "Full-time", "Limited", "2024-03-01", "", "2026-03-01", "Active", "15000", "3750", "1000"],
        # Issue 1: Missing manager_id
        ["EMP003", "Fahad Al-Otaibi", "Saudi", "True", "Company A", "Finance", "PROJ-ALPHA", "Financial Analyst", "Finance", "G3", "", "CC-FIN", "Full-time", "Unlimited", "2024-05-10", "", "", "Active", "11000", "2750", "1000"],
        # Issue 2: Missing project
        ["EMP004", "Jane Smith", "American", "False", "Company A", "Marketing", "", "Marketing Manager", "Marketing", "G5", "EMP013", "CC-MKT", "Full-time", "Limited", "2023-11-01", "", "2025-11-01", "Active", "18000", "4500", "1500"],
        # Issue 3: Duplicate employee ID
        ["EMP005", "Khalid Al-Ghamdi", "Saudi", "True", "Company B", "Operations", "PROJ-GAMMA", "Operations Supervisor", "Operations", "G4", "EMP014", "CC-OPS", "Full-time", "Unlimited", "2024-02-01", "", "", "Active", "14000", "3500", "1000"],
        ["EMP005", "Khalid Al-Ghamdi Duplicate", "Saudi", "True", "Company B", "Operations", "PROJ-GAMMA", "Operations Supervisor", "Operations", "G4", "EMP014", "CC-OPS", "Full-time", "Unlimited", "2024-02-01", "", "", "Active", "14000", "3500", "1000"],
        # Issue 4: Inactive/Terminated status (will have a payroll record)
        ["EMP006", "Youssef Mansour", "Egyptian", "False", "Company A", "Engineering", "PROJ-BETA", "QA Engineer", "IT", "G2", "EMP012", "CC-ENG", "Full-time", "Limited", "2023-01-01", "2026-05-31", "2025-01-01", "Terminated", "8000", "2000", "1000"],
        # Issue 5: Active with missing salary (0 basic salary)
        ["EMP007", "Sarah Jenkins", "Canadian", "False", "Company B", "HR", "PROJ-GAMMA", "Recruiter", "HR", "G2", "EMP011", "CC-HR", "Full-time", "Limited", "2025-02-15", "", "2027-02-15", "Active", "0", "2000", "1000"],
        # Issue 6: Negative/abnormal salary
        ["EMP008", "Mohammed Al-Qahtani", "Saudi", "True", "Company A", "Operations", "PROJ-ALPHA", "Operations Specialist", "Operations", "G3", "EMP014", "CC-OPS", "Full-time", "Unlimited", "2024-06-01", "", "", "Active", "-5000", "-1250", "1000"],
        # Issue 7: Missing nationality
        ["EMP009", "Ali Al-Harbi", "", "True", "Company A", "Finance", "PROJ-ALPHA", "Accountant", "Finance", "G2", "EMP003", "CC-FIN", "Full-time", "Unlimited", "2025-01-10", "", "", "Active", "9000", "2250", "1000"],
        # Issue 8: Missing cost center
        ["EMP010", "David Vance", "Australian", "False", "Company B", "Engineering", "PROJ-GAMMA", "Solutions Architect", "IT", "G6", "EMP012", "", "Full-time", "Limited", "2024-08-01", "", "2026-08-01", "Active", "25000", "6250", "2000"],
        # Normal reference managers / employees
        ["EMP011", "Sultan Al-Otaibi", "Saudi", "True", "Company A", "HR", "PROJ-ALPHA", "HR Manager", "HR", "G6", "EMP015", "CC-HR", "Full-time", "Unlimited", "2020-01-01", "", "", "Active", "25000", "6250", "2000"],
        ["EMP012", "Robert Martin", "American", "False", "Company A", "Engineering", "PROJ-BETA", "Engineering Director", "IT", "G7", "EMP015", "CC-ENG", "Full-time", "Limited", "2021-06-01", "", "2026-06-01", "Active", "35000", "8750", "2500"],
        ["EMP013", "Clara Oswald", "British", "False", "Company A", "Marketing", "PROJ-ALPHA", "Marketing Director", "Marketing", "G6", "EMP015", "CC-MKT", "Full-time", "Limited", "2022-03-15", "", "2026-03-15", "Active", "22000", "5500", "2000"],
        ["EMP014", "Faisal Al-Jabre", "Saudi", "True", "Company B", "Operations", "PROJ-GAMMA", "Operations Director", "Operations", "G7", "EMP015", "CC-OPS", "Full-time", "Unlimited", "2019-05-01", "", "", "Active", "32000", "8000", "2500"],
        ["EMP015", "CEO Office", "Saudi", "True", "Company A", "Executive", "PROJ-ALPHA", "CEO", "Executive", "G8", "", "CC-EXEC", "Full-time", "Unlimited", "2015-01-01", "", "", "Active", "60000", "15000", "3000"],
        ["EMP016", "Noura Al-Dosari", "Saudi", "True", "Company A", "HR", "PROJ-ALPHA", "HR Assistant", "HR", "G1", "EMP011", "CC-HR", "Full-time", "Unlimited", "2025-03-01", "", "", "Active", "6000", "1500", "500"],
        ["EMP017", "Thomas Miller", "German", "False", "Company A", "Engineering", "PROJ-BETA", "Backend Developer", "IT", "G3", "EMP012", "CC-ENG", "Full-time", "Limited", "2024-10-01", "", "2026-10-01", "Active", "13000", "3250", "1000"],
        ["EMP018", "Laila Hassan", "Jordanian", "False", "Company A", "Marketing", "PROJ-ALPHA", "Content Writer", "Marketing", "G2", "EMP013", "CC-MKT", "Full-time", "Limited", "2024-12-01", "", "2025-12-01", "Active", "8500", "2125", "1000"],
        ["EMP019", "Bandar Al-Harbi", "Saudi", "True", "Company B", "Operations", "PROJ-GAMMA", "Logistics Coordinator", "Operations", "G2", "EMP014", "CC-OPS", "Full-time", "Unlimited", "2025-01-15", "", "", "Active", "9500", "2375", "1000"],
        ["EMP020", "Omar Al-Masri", "Syrian", "False", "Company B", "Operations", "PROJ-GAMMA", "Operations Admin", "Operations", "G1", "EMP014", "CC-OPS", "Full-time", "Limited", "2025-04-01", "", "2026-04-01", "Active", "5500", "1375", "500"]
    ]

    with open("data/sample/employees_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "employee_id", "employee_name", "nationality", "is_saudi", "company", "department", "project", 
            "job_title", "job_family", "grade", "manager_id", "cost_center", "employment_type", 
            "contract_type", "joining_date", "termination_date", "contract_end_date", "status", 
            "basic_salary", "housing_allowance", "transport_allowance"
        ])
        writer.writerows(employees)

    # 2. Payroll data (Selected Month: 2026-06)
    # We will generate payroll records for 2026-06.
    # Note details of specific issues:
    # - EMP006: Inactive employee, but gets a payroll record
    # - EMP008: Has basic_salary = -5000, housing_allowance = -1250, other = 0, overtime = 0, deductions = 100, gross = -6250, net = -6350 (negative/abnormal values)
    # - EMP007: Active but salary is 0. Payroll gross_pay = 3000 (housing + transport + other) but basic_salary = 0.
    
    payroll_records = [
        # payroll_period, employee_id, basic_salary, housing_allowance, transport_allowance, other_allowances, overtime_amount, deductions, gross_pay, net_pay, project, cost_center, payroll_status
        ["2026-06", "EMP001", "12000", "3000", "1000", "500", "450", "200", "16950", "16750", "PROJ-ALPHA", "CC-HR", "Paid"],
        ["2026-06", "EMP002", "15000", "3750", "1000", "0", "600", "300", "20350", "20050", "PROJ-BETA", "CC-ENG", "Paid"],
        ["2026-06", "EMP003", "11000", "2750", "1000", "0", "0", "0", "14750", "14750", "PROJ-ALPHA", "CC-FIN", "Paid"],
        ["2026-06", "EMP004", "18000", "4500", "1500", "1000", "0", "500", "25000", "24500", "PROJ-ALPHA", "CC-MKT", "Paid"],
        ["2026-06", "EMP005", "14000", "3500", "1000", "200", "0", "150", "18700", "18550", "PROJ-GAMMA", "CC-OPS", "Paid"],
        # Issue 4: Inactive employee with payroll record
        ["2026-06", "EMP006", "8000", "2000", "1000", "0", "0", "0", "11000", "11000", "PROJ-BETA", "CC-ENG", "Paid"],
        # Issue 5: Active employee with missing salary (basic_salary = 0)
        ["2026-06", "EMP007", "0", "2000", "1000", "1000", "500", "0", "4000", "4000", "PROJ-GAMMA", "CC-HR", "Paid"],
        # Issue 6: Negative/abnormal payroll value
        ["2026-06", "EMP008", "-5000", "-1250", "1000", "0", "0", "100", "-5250", "-5350", "PROJ-ALPHA", "CC-OPS", "Paid"],
        ["2026-06", "EMP009", "9000", "2250", "1000", "0", "300", "100", "12550", "12450", "PROJ-ALPHA", "CC-FIN", "Paid"],
        ["2026-06", "EMP010", "25000", "6250", "2000", "2000", "0", "1000", "35250", "34250", "PROJ-GAMMA", "CC-ENG", "Paid"],
        ["2026-06", "EMP011", "25000", "6250", "2000", "0", "0", "500", "33250", "32750", "CC-HR", "CC-HR", "Paid"],
        ["2026-06", "EMP012", "35000", "8750", "2500", "0", "0", "1000", "46250", "45250", "PROJ-BETA", "CC-ENG", "Paid"],
        ["2026-06", "EMP013", "22000", "5500", "2000", "0", "0", "800", "29500", "28700", "PROJ-ALPHA", "CC-MKT", "Paid"],
        ["2026-06", "EMP014", "32000", "8000", "2500", "0", "0", "1200", "42500", "41300", "PROJ-GAMMA", "CC-OPS", "Paid"],
        ["2026-06", "EMP015", "60000", "15000", "3000", "5000", "0", "2500", "83000", "80500", "PROJ-ALPHA", "CC-EXEC", "Paid"],
        ["2026-06", "EMP016", "6000", "1500", "500", "0", "150", "0", "8150", "8150", "PROJ-ALPHA", "CC-HR", "Paid"],
        ["2026-06", "EMP017", "13000", "3250", "1000", "0", "500", "150", "17750", "17600", "PROJ-BETA", "CC-ENG", "Paid"],
        ["2026-06", "EMP018", "8500", "2125", "1000", "0", "0", "100", "11625", "11525", "PROJ-ALPHA", "CC-MKT", "Paid"],
        ["2026-06", "EMP019", "9500", "2375", "1000", "200", "400", "100", "13475", "13375", "PROJ-GAMMA", "CC-OPS", "Paid"],
        ["2026-06", "EMP020", "5500", "1375", "500", "0", "0", "0", "7375", "7375", "PROJ-GAMMA", "CC-OPS", "Paid"]
    ]
    
    # Also write a couple of previous periods to demonstrate trend charts
    historical_records = []
    for month in ["2026-04", "2026-05"]:
        for record in payroll_records:
            # Skip the terminated guy for older months, or generate normally. Let's make it simpler:
            # We'll just generate identical payroll records with slightly modified values for 2026-04 and 2026-05.
            # (In reality, basic salaries are similar, but we can alter overtime/other allowances slightly).
            if record[1] == "EMP006" and month == "2026-04":
                # Let's say he was active in April
                continue
            
            p_rec = record.copy()
            p_rec[0] = month
            # modify gross/net slightly for variance
            if p_rec[1] != "EMP008": # don't double count negative issue in history or let's keep it simple
                p_rec[6] = str(float(p_rec[6]) * 0.9) if p_rec[6] != "0" else "0"
                p_rec[8] = str(float(p_rec[2]) + float(p_rec[3]) + float(p_rec[4]) + float(p_rec[5]) + float(p_rec[6]))
                p_rec[9] = str(float(p_rec[8]) - float(p_rec[7]))
            
            historical_records.append(p_rec)
            
    payroll_records.extend(historical_records)

    with open("data/sample/payroll_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "payroll_period", "employee_id", "basic_salary", "housing_allowance", "transport_allowance", 
            "other_allowances", "overtime_amount", "deductions", "gross_pay", "net_pay", 
            "project", "cost_center", "payroll_status"
        ])
        writer.writerows(payroll_records)

    # 3. Attendance data (2026-06)
    # We will generate daily attendance logs for active employees.
    # We need:
    # - Attendance record with missing punch (scheduled check-in/out exists, actual check-in is there but actual check-out is empty, missing_punch_count = 1)
    
    attendance = []
    start_date = datetime(2026, 6, 1)
    end_date = datetime(2026, 6, 5) # Just 5 days to keep it reasonable size, but enough to calculate metrics
    
    # We'll populate attendance for employees
    emp_ids = ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005", "EMP007", "EMP008", "EMP009", "EMP010", "EMP011", "EMP012", "EMP013", "EMP014", "EMP015", "EMP016", "EMP017", "EMP018", "EMP019", "EMP020"]
    
    curr = start_date
    while curr <= end_date:
        for emp in emp_ids:
            # Skip weekends (Friday/Saturday) for Saudi context or Saturday/Sunday.
            # Let's say Friday (4) and Saturday (5) are weekend days.
            if curr.weekday() in [4, 5]:
                continue
                
            att_date = curr.strftime("%Y-%m-%d")
            scheduled_start = f"{att_date} 08:00:00"
            scheduled_end = f"{att_date} 17:00:00"
            
            # Normal day
            actual_in = f"{att_date} 07:55:00"
            actual_out = f"{att_date} 17:05:00"
            late = 0
            excused = 0
            net_late = 0
            absence = 0
            ot_hours = 0
            ot_approved = "False"
            missing_punches = 0
            proj = "PROJ-ALPHA"
            
            # Introduce Issue 9: Missing Punch (EMP002 on June 2nd has check-in but no check-out)
            if emp == "EMP002" and curr.day == 2:
                actual_out = ""
                missing_punches = 1
            
            # Let's give some real absences and late minutes
            elif emp == "EMP003" and curr.day == 3:
                # Late by 45 minutes, 15 excused, net late 30
                actual_in = f"{att_date} 08:45:00"
                late = 45
                excused = 15
                net_late = 30
            
            elif emp == "EMP004" and curr.day == 4:
                # Absent
                actual_in = ""
                actual_out = ""
                absence = 1.0
                
            elif emp == "EMP005" and curr.day == 1:
                # Overtime
                actual_out = f"{att_date} 19:30:00"
                ot_hours = 2.5
                ot_approved = "True"
                
            attendance.append([
                att_date, emp, "Day Shift", scheduled_start, scheduled_end, 
                actual_in, actual_out, str(late), str(excused), str(net_late), 
                str(absence), str(ot_hours), ot_approved, str(missing_punches), proj
            ])
            
        curr += timedelta(days=1)

    with open("data/sample/attendance_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "attendance_date", "employee_id", "shift_name", "scheduled_start", "scheduled_end", 
            "actual_check_in", "actual_check_out", "late_minutes", "excused_late_minutes", 
            "net_late_minutes", "absence_days", "overtime_hours", "overtime_approved", 
            "missing_punch_count", "project"
        ])
        writer.writerows(attendance)

    # 4. HR requests data
    # We need:
    # - HR request breaching SLA (actual_hours > sla_hours and sla_breached = True)
    
    hr_requests = [
        # request_id, employee_id, request_type, request_status, created_at, closed_at, owner, sla_hours, actual_hours, sla_breached, project
        ["REQ001", "EMP001", "Employment Certificate", "Closed", "2026-06-01 09:00:00", "2026-06-01 11:30:00", "HR Operations", "24", "2", "False", "PROJ-ALPHA"],
        ["REQ002", "EMP002", "Salary Transfer Letter", "Closed", "2026-06-02 10:00:00", "2026-06-04 15:00:00", "HR Payroll", "24", "53", "True", "PROJ-BETA"], # Issue 10: SLA Breached
        ["REQ003", "EMP003", "Leave Request", "Closed", "2026-06-03 08:30:00", "2026-06-03 14:00:00", "HR Shared Services", "48", "5", "False", "PROJ-ALPHA"],
        ["REQ004", "EMP004", "Business Card Request", "Open", "2026-06-05 13:00:00", "", "HR Operations", "72", "12", "False", "PROJ-ALPHA"]
    ]

    with open("data/sample/hr_requests_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "request_id", "employee_id", "request_type", "request_status", "created_at", "closed_at", 
            "owner", "sla_hours", "actual_hours", "sla_breached", "project"
        ])
        writer.writerows(hr_requests)

    # 5. Compliance data
    # We will generate compliance logs for active employees.
    
    compliance = [
        # employee_id, period, qiwa_status, gosi_status, mudad_status, contract_authenticated, gosi_salary, payroll_basic_salary, occupation_code, occupation_match_status, work_permit_expiry, iqama_expiry, insurance_status
        ["EMP001", "2026-06", "Active", "Registered", "Compliant", "True", "12000", "12000", "123456", "Matched", "2027-06-01", "", "Active"],
        ["EMP002", "2026-06", "Active", "Registered", "Compliant", "True", "15000", "15000", "234567", "Matched", "2026-12-31", "2026-12-31", "Active"],
        ["EMP003", "2026-06", "Active", "Registered", "Compliant", "True", "11000", "11000", "345678", "Matched", "2027-05-01", "", "Active"],
        ["EMP004", "2026-06", "Active", "Registered", "Compliant", "False", "18000", "18000", "456789", "Mismatch", "2026-11-01", "2026-11-01", "Active"]
    ]

    with open("data/sample/compliance_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "employee_id", "period", "qiwa_status", "gosi_status", "mudad_status", 
            "contract_authenticated", "gosi_salary", "payroll_basic_salary", 
            "occupation_code", "occupation_match_status", "work_permit_expiry", 
            "iqama_expiry", "insurance_status"
        ])
        writer.writerows(compliance)

    # 6. Employee Relations & Labor Cases data
    er_cases = [
        # case_id, employee_id, case_type, case_status, priority, created_date, target_due_date, closed_date, owner_id, escalated, escalation_reason, legal_reference, case_number, description
        ["ER001", "EMP001", "Disciplinary", "Closed", "High", "2026-06-01", "2026-06-15", "2026-06-10", "EMP003", "False", "", "", "", "Workplace dispute resolved"],
        ["ER002", "EMP002", "Grievance", "Open", "Medium", "2026-06-02", "2026-06-12", "", "EMP003", "False", "", "", "", "Salary review request"],
        ["ER002", "EMP002", "Grievance", "Open", "Medium", "2026-06-02", "2026-06-12", "", "EMP003", "False", "", "", "", "Salary review duplicate log entry"],
        ["ER003", "EMP003", "Labor Case", "Open", "High", "2026-05-15", "2026-06-15", "", "EMP001", "True", "Escalated to legal department", "LR-8877", "CASE-123", "Contract dispute in court"],
        ["ER004", "EMP004", "Disciplinary", "Open", "Low", "2026-06-10", "", "", "EMP001", "False", "", "", "", "Unexcused absence check"],
        ["ER005", "EMP005", "Labor Case", "Open", "High", "2026-05-01", "2026-06-01", "", "EMP003", "True", "", "", "", "Severance pay dispute"],
        ["ER006", "EMP007", "Grievance", "Closed", "Low", "2026-06-05", "2026-06-15", "", "EMP003", "False", "", "", "", "Equipment escalation"],
        ["ER007", "EMP010", "Disciplinary", "Closed", "Medium", "2026-06-10", "2026-06-24", "2026-06-05", "EMP003", "False", "", "", "", "Policy breach"],
        ["ER008", "EMP006", "Disciplinary", "Open", "Low", "2026-06-01", "2026-06-15", "", "EMP003", "False", "", "", "", "Exit checklist disciplinary log"],
        ["ER009", "EMP001", "Grievance", "Open", "Low", "2026-06-02", "2026-06-12", "", "EMP006", "False", "", "", "", "Grievance assigned to exited investigator"],
        ["ER010", "EMP999", "Grievance", "Open", "Medium", "2026-06-02", "2026-06-12", "", "EMP003", "False", "", "", "", "Unknown employee grievance log entry"]
    ]

    with open("data/sample/employee_relations_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id", "employee_id", "case_type", "case_status", "priority", 
            "created_date", "target_due_date", "closed_date", "owner_id", 
            "escalated", "escalation_reason", "legal_reference", "case_number", 
            "description"
        ])
        writer.writerows(er_cases)

    # 7. Recruitment & Workforce Planning data
    requisitions = [
        # requisition_id, job_title, department, project, cost_center, owner_id, approval_date, target_hire_date, closed_date, status
        ["REQ001", "Software Engineer", "Engineering", "PROJ-BETA", "CC-ENG", "EMP011", "2026-06-01", "2026-06-25", "2026-06-20", "Closed"],
        ["REQ002", "HR Specialist", "HR", "PROJ-ALPHA", "CC-HR", "EMP011", "2026-06-02", "2026-07-15", "", "Open"],
        ["REQ002", "HR Specialist duplicate log", "HR", "PROJ-ALPHA", "CC-HR", "EMP011", "2026-06-02", "2026-07-15", "", "Open"],
        ["REQ003", "Financial Analyst", "Finance", "PROJ-ALPHA", "CC-FIN", "", "2026-06-05", "2026-07-20", "", "Open"],
        ["REQ004", "Operations Supervisor", "Operations", "PROJ-GAMMA", "CC-OPS", "EMP011", "2026-05-01", "2026-06-15", "", "Open"],
        ["REQ005", "Marketing Manager", "Marketing", "PROJ-ALPHA", "CC-MKT", "EMP011", "2026-06-10", "", "", "Open"],
        ["REQ006", "QA Engineer", "Engineering", "PROJ-BETA", "CC-ENG", "EMP011", "2026-06-01", "2026-06-15", "2026-06-10", "Closed"]
    ]

    with open("data/sample/recruitment_requisitions_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["requisition_id", "job_title", "department", "project", "cost_center", "owner_id", "approval_date", "target_hire_date", "closed_date", "status"])
        writer.writerows(requisitions)

    candidates = [
        # candidate_id, candidate_name, source, pipeline_stage, requisition_id, applied_date
        ["CAN001", "Alice Smith", "LinkedIn", "Hired", "REQ001", "2026-06-02"],
        ["CAN002", "Bob Jones", "Indeed", "Interview", "REQ004", "2026-06-05"],
        ["CAN002", "Bob Jones duplicate log", "Indeed", "Interview", "REQ004", "2026-06-05"],
        ["CAN003", "Charlie Brown", "Referral", "", "REQ004", "2026-06-06"],
        ["CAN004", "Diana Prince", "Direct", "Applied", "REQ999", "2026-06-07"],
        ["CAN005", "Evan Wright", "Agency", "Offer Extended", "REQ004", "2026-06-08"],
        ["CAN006", "Fiona Gallagher", "Twitter", "Applied", "REQ005", "2026-06-09"],
        ["CAN007", "George Costanza", "LinkedIn", "Offer Accepted", "REQ006", "2026-06-02"]
    ]

    with open("data/sample/candidates_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "candidate_name", "source", "pipeline_stage", "requisition_id", "applied_date"])
        writer.writerows(candidates)

    interviews = [
        # interview_id, candidate_id, interview_date, recruiter_id, rating, outcome
        ["INT001", "CAN001", "2026-06-10 10:00:00", "EMP001", "5", "Pass"],
        ["INT002", "CAN002", "2026-06-12 14:00:00", "", "3", "Pass"],
        ["INT003", "CAN005", "", "EMP001", "", "Pending"]
    ]

    with open("data/sample/interviews_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["interview_id", "candidate_id", "interview_date", "recruiter_id", "rating", "outcome"])
        writer.writerows(interviews)

    offers = [
        # offer_id, candidate_id, offer_date, salary, outcome_status, outcome_date
        ["OFF001", "CAN001", "2026-06-15", "15000", "Accepted", "2026-06-18"],
        ["OFF002", "CAN005", "2026-06-20", "", "Sent", ""],
        ["OFF003", "CAN007", "2026-06-05", "12000", "Accepted", "2026-06-08"]
    ]

    with open("data/sample/offers_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["offer_id", "candidate_id", "offer_date", "salary", "outcome_status", "outcome_date"])
        writer.writerows(offers)

    onboarding = [
        # onboarding_id, candidate_id, start_date, status, employee_id
        ["ONB001", "CAN001", "2026-06-20", "Completed", "EMP002"],
        ["ONB002", "CAN002", "2026-07-01", "In Progress", "EMP999"]
    ]

    with open("data/sample/onboarding_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["onboarding_id", "candidate_id", "start_date", "status", "employee_id"])
        writer.writerows(onboarding)

    workforce_plan = [
        # period, project, department, planned_headcount
        ["2026-06", "PROJ-ALPHA", "HR", "4"],
        ["2026-06", "PROJ-ALPHA", "Finance", "3"],
        ["2026-06", "PROJ-BETA", "Engineering", "5"],
        ["2026-06", "PROJ-GAMMA", "Operations", "4"],
        ["2026-06", "", "Finance", "2"],
        ["2026-06", "PROJ-ALPHA", "Marketing", "0"]
    ]

    with open("data/sample/workforce_plan_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["period", "project", "department", "planned_headcount"])
        writer.writerows(workforce_plan)

    vacancy_requests = [
        # request_id, department, project, job_title, quantity, status, approved_date
        ["VAC001", "HR", "PROJ-ALPHA", "HR Specialist", "1", "Approved", "2026-06-01"],
        ["VAC002", "Engineering", "PROJ-BETA", "Software Engineer", "2", "Approved", "2026-06-02"],
        ["VAC003", "Operations", "PROJ-GAMMA", "Operations Coordinator", "-1", "Approved", "2026-06-03"]
    ]

    with open("data/sample/vacancy_requests_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["request_id", "department", "project", "job_title", "quantity", "status", "approved_date"])
        writer.writerows(vacancy_requests)

    # 1. Performance Reviews
    perf_reviews = [
        # review_id, employee_id, reviewer_id, review_period, rating, status, completed_date
        ["REV001", "EMP001", "EMP011", "2026-06", "5.0", "Completed", "2026-06-15"],
        ["REV001", "EMP001", "EMP011", "2026-06", "5.0", "Completed", "2026-06-15"], # Duplicate Review ID
        ["REV002", "EMP002", "EMP012", "2026-06", "4.0", "Completed", "2026-06-18"],
        ["REV003", "EMP004", "EMP013", "2026-06", "", "Completed", "2026-06-12"], # Review completed without rating
        ["REV004", "EMP005", "EMP014", "2026-06", "3.0", "Completed", "2026-06-14"],
        ["REV005", "EMP007", "EMP011", "2026-06", "6.0", "Completed", "2026-06-10"], # Rating outside range (6.0)
        ["REV006", "EMP008", "", "2026-06", "2.0", "Completed", "2026-06-11"], # Review missing reviewer
        ["REV007", "EMP009", "EMP003", "2026-06", "3.5", "Completed", "2026-06-16"],
        ["REV008", "EMP010", "EMP012", "2026-06", "4.2", "Completed", "2026-06-17"],
        ["REV009", "EMP011", "EMP015", "2026-06", "4.8", "Completed", "2026-06-20"],
        ["REV010", "EMP012", "EMP015", "2026-06", "3.8", "Completed", "2026-06-22"],
        ["REV011", "EMP013", "EMP015", "2026-06", "3.2", "Completed", "2026-06-21"],
        ["REV012", "EMP014", "EMP015", "2026-06", "3.0", "Completed", "2026-06-23"],
        ["REV013", "EMP015", "EMP015", "2026-06", "4.5", "Completed", "2026-06-25"],
        ["REV014", "EMP016", "EMP011", "2026-06", "2.2", "Completed", "2026-06-13"],
        ["REV015", "EMP017", "EMP012", "2026-06", "3.9", "Completed", "2026-06-19"],
        ["REV016", "EMP018", "EMP013", "2026-06", "3.1", "Completed", "2026-06-20"],
        ["REV017", "EMP019", "EMP014", "2026-06", "2.8", "Completed", "2026-06-24"],
        ["REV018", "EMP020", "EMP014", "2026-06", "1.2", "Completed", "2026-06-26"],
        ["REV099", "EMP999", "EMP011", "2026-06", "3.0", "Completed", "2026-06-15"] # Linked to unknown employee
    ]
    with open("data/sample/performance_reviews_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["review_id", "employee_id", "reviewer_id", "review_period", "rating", "status", "completed_date"])
        writer.writerows(perf_reviews)

    # 2. Performance Goals
    perf_goals = [
        # goal_id, employee_id, title, status, due_date, completed_date
        ["GOL001", "EMP001", "Deliver dashboard", "Completed", "2026-06-15", "2026-06-14"],
        ["GOL002", "EMP002", "Refactor api", "In Progress", "2026-06-30", ""],
        ["GOL003", "EMP003", "Complete audit", "Cancelled", "2026-06-20", ""],
        ["GOL004", "EMP004", "Run campaign", "Overdue", "2026-06-10", ""], # Goal overdue
        ["GOL005", "EMP999", "Unknown goal", "Completed", "2026-06-15", "2026-06-15"], # Goal linked to unknown employee
        ["GOL006", "EMP005", "No status goal", "", "2026-06-25", ""] # Goal missing status
    ]
    with open("data/sample/performance_goals_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["goal_id", "employee_id", "title", "status", "due_date", "completed_date"])
        writer.writerows(perf_goals)

    # 3. Competency Assessments
    competencies = [
        # assessment_id, employee_id, competency_name, required_score, actual_score, assessed_date
        ["COM001", "EMP001", "SQL Fundamentals", "4.0", "4.5", "2026-06-10"],
        ["COM002", "EMP002", "Python Coding", "4.0", "3.0", "2026-06-11"], # Gap of 1.0 (4 - 3)
        ["COM003", "EMP999", "Unknown competency", "3.0", "3.0", "2026-06-12"], # Linked to unknown employee
        ["COM004", "EMP004", "Marketing Strategy", "4.0", "6.0", "2026-06-13"] # Score outside range (6.0)
    ]
    with open("data/sample/competency_assessments_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["assessment_id", "employee_id", "competency_name", "required_score", "actual_score", "assessed_date"])
        writer.writerows(competencies)

    # 4. Learning Enrollments
    learning_enrollments = [
        # enrollment_id, employee_id, course_id, status, enrollment_date, completion_date
        ["ENR001", "EMP001", "CRS001", "Completed", "2026-06-01", "2026-06-10"],
        ["ENR002", "EMP002", "CRS002", "Completed", "2026-06-02", ""], # Completed without completion date
        ["ENR003", "EMP999", "CRS001", "Completed", "2026-06-05", "2026-06-12"], # Unknown employee
        ["ENR004", "EMP004", "CRS003", "In Progress", "2026-06-05", ""],
        ["ENR005", "EMP005", "CRS004", "Cancelled", "2026-06-01", ""]
    ]
    with open("data/sample/learning_enrollments_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["enrollment_id", "employee_id", "course_id", "status", "enrollment_date", "completion_date"])
        writer.writerows(learning_enrollments)

    # 5. Training Catalog
    training_catalog = [
        # course_id, course_name, category, duration_hours
        ["CRS001", "DuckDB Advanced Analytics", "Data Engineering", "12.0"],
        ["CRS002", "React Performance Optimization", "", "8.0"], # Missing category
        ["CRS003", "Strategic Marketing 101", "Marketing", "0.0"], # Invalid hours
        ["CRS004", "Effective HR Management", "Management", "10.0"]
    ]
    with open("data/sample/training_catalog_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["course_id", "course_name", "category", "duration_hours"])
        writer.writerows(training_catalog)

    # 6. Succession Plans
    succession_plans = [
        # plan_id, critical_role_id, role_title, current_employee_id, successor_employee_id, readiness, flight_risk, is_critical
        ["PLN001", "ROLE001", "HR Manager", "EMP011", "EMP001", "Ready Now", "Low", "True"],
        ["PLN002", "ROLE002", "Engineering Director", "EMP012", "EMP002", "Ready in 1 Year", "Medium", "True"],
        ["PLN003", "ROLE003", "Finance Director", "EMP003", "", "", "", "True"], # Critical role missing successor (or empty successor)
        ["PLN004", "ROLE001", "HR Manager", "EMP011", "EMP888", "Ready Now", "Low", "True"], # Unknown successor
        ["PLN005", "ROLE001", "HR Manager", "EMP011", "EMP006", "Ready in 2+ Years", "Low", "True"], # Successor assigned to inactive employee
        ["PLN006", "ROLE002", "Engineering Director", "EMP012", "EMP017", "", "Low", "True"] # Successor readiness missing
    ]
    with open("data/sample/succession_plans_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["plan_id", "critical_role_id", "role_title", "current_employee_id", "successor_employee_id", "readiness", "flight_risk", "is_critical"])
        writer.writerows(succession_plans)

    # 7. Talent Reviews
    talent_reviews = [
        # review_id, employee_id, performance_rating, potential_rating, flight_risk, retention_risk
        ["TLR001", "EMP001", "5.0", "High", "High", "Low"], # High performer with high flight risk exception
        ["TLR002", "EMP002", "4.0", "Medium", "Medium", "Medium"],
        ["TLR003", "EMP004", "3.0", "", "Low", "High"], # Talent review missing potential rating
        ["TLR004", "EMP011", "4.8", "High", "Low", "Low"],
        ["TLR005", "EMP012", "3.8", "Medium", "Low", "Low"]
    ]
    with open("data/sample/talent_reviews_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["review_id", "employee_id", "performance_rating", "potential_rating", "flight_risk", "retention_risk"])
        writer.writerows(talent_reviews)

    # 8. Employee Skills
    employee_skills = [
        # skill_id, employee_id, skill_name, proficiency
        ["SKL001", "EMP001", "SQL", "Expert"],
        ["SKL001", "EMP001", "SQL", "Expert"], # Duplicate skill record
        ["SKL002", "EMP002", "React", "Intermediate"]
    ]
    with open("data/sample/employee_skills_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["skill_id", "employee_id", "skill_name", "proficiency"])
        writer.writerows(employee_skills)

    # 9. Career Paths
    career_paths = [
        # path_id, employee_id, current_role, next_role, readiness_months
        ["PTH001", "EMP001", "HR Specialist", "HR Specialist Senior", "12"],
        ["PTH002", "EMP002", "Software Engineer", "", "24"] # Career path missing next role
    ]
    with open("data/sample/career_paths_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path_id", "employee_id", "current_role", "next_role", "readiness_months"])
        writer.writerows(career_paths)

    print("Successfully generated sample files in data/sample/.")

if __name__ == "__main__":
    create_sample_data()

