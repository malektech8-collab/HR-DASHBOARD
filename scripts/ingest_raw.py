import os
import polars as pl

def ingest():
    os.makedirs("data/bronze", exist_ok=True)
    os.makedirs("data/silver", exist_ok=True)
    
    print("Starting data ingestion...")

    # Define paths
    files = {
        "employees": "data/sample/employees_sample.csv",
        "payroll": "data/sample/payroll_sample.csv",
        "attendance": "data/sample/attendance_sample.csv",
        "hr_requests": "data/sample/hr_requests_sample.csv",
        "compliance": "data/sample/compliance_sample.csv",
        "employee_relations": "data/sample/employee_relations_sample.csv",
        "recruitment_requisitions": "data/sample/recruitment_requisitions_sample.csv",
        "candidates": "data/sample/candidates_sample.csv",
        "interviews": "data/sample/interviews_sample.csv",
        "offers": "data/sample/offers_sample.csv",
        "onboarding": "data/sample/onboarding_sample.csv",
        "workforce_plan": "data/sample/workforce_plan_sample.csv",
        "vacancy_requests": "data/sample/vacancy_requests_sample.csv",
        "performance_reviews": "data/sample/performance_reviews_sample.csv",
        "performance_goals": "data/sample/performance_goals_sample.csv",
        "competency_assessments": "data/sample/competency_assessments_sample.csv",
        "learning_enrollments": "data/sample/learning_enrollments_sample.csv",
        "training_catalog": "data/sample/training_catalog_sample.csv",
        "succession_plans": "data/sample/succession_plans_sample.csv",
        "talent_reviews": "data/sample/talent_reviews_sample.csv",
        "employee_skills": "data/sample/employee_skills_sample.csv",
        "career_paths": "data/sample/career_paths_sample.csv"
    }

    # 1. Employees
    if os.path.exists(files["employees"]):
        # Save raw to bronze
        df_raw = pl.read_csv(files["employees"])
        df_raw.write_parquet("data/bronze/employees.parquet")
        
        # Clean and type cast for silver
        df = pl.read_csv(files["employees"], null_values=[""])
        df = df.with_columns([
            pl.col("is_saudi").cast(pl.Boolean, strict=False),
            pl.col("joining_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("termination_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("contract_end_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("basic_salary").cast(pl.Float64, strict=False),
            pl.col("housing_allowance").cast(pl.Float64, strict=False),
            pl.col("transport_allowance").cast(pl.Float64, strict=False),
        ])
        df.write_parquet("data/silver/employees.parquet")
        print("Ingested employees to bronze/silver.")

    # 2. Payroll
    if os.path.exists(files["payroll"]):
        df_raw = pl.read_csv(files["payroll"])
        df_raw.write_parquet("data/bronze/payroll.parquet")
        
        df = pl.read_csv(files["payroll"], null_values=[""])
        numeric_cols = [
            "basic_salary", "housing_allowance", "transport_allowance", 
            "other_allowances", "overtime_amount", "deductions", 
            "gross_pay", "net_pay"
        ]
        df = df.with_columns([
            pl.col(c).cast(pl.Float64, strict=False) for c in numeric_cols
        ])
        df.write_parquet("data/silver/payroll.parquet")
        print("Ingested payroll to bronze/silver.")

    # 3. Attendance
    if os.path.exists(files["attendance"]):
        df_raw = pl.read_csv(files["attendance"])
        df_raw.write_parquet("data/bronze/attendance.parquet")
        
        df = pl.read_csv(files["attendance"], null_values=[""])
        df = df.with_columns([
            pl.col("attendance_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("scheduled_start").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("scheduled_end").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("actual_check_in").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("actual_check_out").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("late_minutes").cast(pl.Int64, strict=False),
            pl.col("excused_late_minutes").cast(pl.Int64, strict=False),
            pl.col("net_late_minutes").cast(pl.Int64, strict=False),
            pl.col("absence_days").cast(pl.Float64, strict=False),
            pl.col("overtime_hours").cast(pl.Float64, strict=False),
            pl.col("overtime_approved").cast(pl.Boolean, strict=False),
            pl.col("missing_punch_count").cast(pl.Int64, strict=False),
        ])
        df.write_parquet("data/silver/attendance.parquet")
        print("Ingested attendance to bronze/silver.")

    # 4. HR Requests
    if os.path.exists(files["hr_requests"]):
        df_raw = pl.read_csv(files["hr_requests"])
        df_raw.write_parquet("data/bronze/hr_requests.parquet")
        
        df = pl.read_csv(files["hr_requests"], null_values=[""])
        df = df.with_columns([
            pl.col("created_at").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("closed_at").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("sla_hours").cast(pl.Int64, strict=False),
            pl.col("actual_hours").cast(pl.Int64, strict=False),
            pl.col("sla_breached").cast(pl.Boolean, strict=False),
        ])
        df.write_parquet("data/silver/hr_requests.parquet")
        print("Ingested hr_requests to bronze/silver.")

    # 5. Compliance
    if os.path.exists(files["compliance"]):
        df_raw = pl.read_csv(files["compliance"])
        df_raw.write_parquet("data/bronze/compliance.parquet")
        
        df = pl.read_csv(files["compliance"], null_values=[""])
        df = df.with_columns([
            pl.col("contract_authenticated").cast(pl.Boolean, strict=False),
            pl.col("gosi_salary").cast(pl.Float64, strict=False),
            pl.col("payroll_basic_salary").cast(pl.Float64, strict=False),
            pl.col("work_permit_expiry").str.to_date("%Y-%m-%d", strict=False),
            pl.col("iqama_expiry").str.to_date("%Y-%m-%d", strict=False),
        ])
        df.write_parquet("data/silver/compliance.parquet")
        print("Ingested compliance to bronze/silver.")
        
    # 6. Employee Relations
    if "employee_relations" in files and os.path.exists(files["employee_relations"]):
        df_raw = pl.read_csv(files["employee_relations"])
        df_raw.write_parquet("data/bronze/employee_relations.parquet")
        
        df = pl.read_csv(files["employee_relations"], null_values=[""])
        df = df.with_columns([
            pl.col("created_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("target_due_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("closed_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("escalated").cast(pl.Boolean, strict=False),
        ])
        df.write_parquet("data/silver/employee_relations.parquet")
        print("Ingested employee_relations to bronze/silver.")

    # 7. Production mode source check
    import yaml
    production_mode = False
    try:
        if os.path.exists("config/business_rules.yml"):
            with open("config/business_rules.yml", "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
                recruitment_rules = rules.get("recruitment_rules", {})
                production_mode = recruitment_rules.get("production_mode", False)
    except Exception as e:
        print(f"Error loading business rules: {e}")

    recruitment_tables = [
        "recruitment_requisitions", "candidates", "interviews", "offers", 
        "onboarding", "workforce_plan", "vacancy_requests"
    ]
    for table in recruitment_tables:
        path = files.get(table)
        if production_mode:
            if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
                raise ValueError(f"PRODUCTION EXCEPTION: Core recruitment source table '{table}' is empty or unavailable.")

    # 8. Ingest Recruitment tables
    # Requisitions
    if os.path.exists(files["recruitment_requisitions"]):
        df_raw = pl.read_csv(files["recruitment_requisitions"])
        df_raw.write_parquet("data/bronze/recruitment_requisitions.parquet")
        df = pl.read_csv(files["recruitment_requisitions"], null_values=[""])
        df = df.with_columns([
            pl.col("approval_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("target_hire_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("closed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/recruitment_requisitions.parquet")
        print("Ingested recruitment_requisitions to bronze/silver.")

    # Candidates
    if os.path.exists(files["candidates"]):
        df_raw = pl.read_csv(files["candidates"])
        df_raw.write_parquet("data/bronze/candidates.parquet")
        df = pl.read_csv(files["candidates"], null_values=[""])
        df = df.with_columns([
            pl.col("applied_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/candidates.parquet")
        print("Ingested candidates to bronze/silver.")

    # Interviews
    if os.path.exists(files["interviews"]):
        df_raw = pl.read_csv(files["interviews"])
        df_raw.write_parquet("data/bronze/interviews.parquet")
        df = pl.read_csv(files["interviews"], null_values=[""])
        df = df.with_columns([
            pl.col("interview_date").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
        ])
        df.write_parquet("data/silver/interviews.parquet")
        print("Ingested interviews to bronze/silver.")

    # Offers
    if os.path.exists(files["offers"]):
        df_raw = pl.read_csv(files["offers"])
        df_raw.write_parquet("data/bronze/offers.parquet")
        df = pl.read_csv(files["offers"], null_values=[""])
        df = df.with_columns([
            pl.col("offer_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("salary").cast(pl.Float64, strict=False),
            pl.col("outcome_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/offers.parquet")
        print("Ingested offers to bronze/silver.")

    # Onboarding
    if os.path.exists(files["onboarding"]):
        df_raw = pl.read_csv(files["onboarding"])
        df_raw.write_parquet("data/bronze/onboarding.parquet")
        df = pl.read_csv(files["onboarding"], null_values=[""])
        df = df.with_columns([
            pl.col("start_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/onboarding.parquet")
        print("Ingested onboarding to bronze/silver.")

    # Workforce Plan
    if os.path.exists(files["workforce_plan"]):
        df_raw = pl.read_csv(files["workforce_plan"])
        df_raw.write_parquet("data/bronze/workforce_plan.parquet")
        df = pl.read_csv(files["workforce_plan"], null_values=[""])
        df = df.with_columns([
            pl.col("planned_headcount").cast(pl.Int64, strict=False)
        ])
        df.write_parquet("data/silver/workforce_plan.parquet")
        print("Ingested workforce_plan to bronze/silver.")

    # Vacancy Requests
    if os.path.exists(files["vacancy_requests"]):
        df_raw = pl.read_csv(files["vacancy_requests"])
        df_raw.write_parquet("data/bronze/vacancy_requests.parquet")
        df = pl.read_csv(files["vacancy_requests"], null_values=[""])
        df = df.with_columns([
            pl.col("quantity").cast(pl.Int64, strict=False),
            pl.col("approved_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/vacancy_requests.parquet")
        print("Ingested vacancy_requests to bronze/silver.")

    # Ingest Talent tables
    # Performance Reviews
    if os.path.exists(files["performance_reviews"]):
        df_raw = pl.read_csv(files["performance_reviews"])
        df_raw.write_parquet("data/bronze/performance_reviews.parquet")
        df = pl.read_csv(files["performance_reviews"], null_values=[""])
        df = df.with_columns([
            pl.col("rating").cast(pl.Float64, strict=False),
            pl.col("completed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/performance_reviews.parquet")
        print("Ingested performance_reviews to bronze/silver.")

    # Performance Goals
    if os.path.exists(files["performance_goals"]):
        df_raw = pl.read_csv(files["performance_goals"])
        df_raw.write_parquet("data/bronze/performance_goals.parquet")
        df = pl.read_csv(files["performance_goals"], null_values=[""])
        df = df.with_columns([
            pl.col("due_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("completed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/performance_goals.parquet")
        print("Ingested performance_goals to bronze/silver.")

    # Competency Assessments
    if os.path.exists(files["competency_assessments"]):
        df_raw = pl.read_csv(files["competency_assessments"])
        df_raw.write_parquet("data/bronze/competency_assessments.parquet")
        df = pl.read_csv(files["competency_assessments"], null_values=[""])
        df = df.with_columns([
            pl.col("required_score").cast(pl.Float64, strict=False),
            pl.col("actual_score").cast(pl.Float64, strict=False),
            pl.col("assessed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/competency_assessments.parquet")
        print("Ingested competency_assessments to bronze/silver.")

    # Learning Enrollments
    if os.path.exists(files["learning_enrollments"]):
        df_raw = pl.read_csv(files["learning_enrollments"])
        df_raw.write_parquet("data/bronze/learning_enrollments.parquet")
        df = pl.read_csv(files["learning_enrollments"], null_values=[""])
        df = df.with_columns([
            pl.col("enrollment_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("completion_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/learning_enrollments.parquet")
        print("Ingested learning_enrollments to bronze/silver.")

    # Training Catalog
    if os.path.exists(files["training_catalog"]):
        df_raw = pl.read_csv(files["training_catalog"])
        df_raw.write_parquet("data/bronze/training_catalog.parquet")
        df = pl.read_csv(files["training_catalog"], null_values=[""])
        df = df.with_columns([
            pl.col("duration_hours").cast(pl.Float64, strict=False)
        ])
        df.write_parquet("data/silver/training_catalog.parquet")
        print("Ingested training_catalog to bronze/silver.")

    # Succession Plans
    if os.path.exists(files["succession_plans"]):
        df_raw = pl.read_csv(files["succession_plans"])
        df_raw.write_parquet("data/bronze/succession_plans.parquet")
        df = pl.read_csv(files["succession_plans"], null_values=[""])
        df = df.with_columns([
            pl.col("is_critical").cast(pl.Boolean, strict=False)
        ])
        df.write_parquet("data/silver/succession_plans.parquet")
        print("Ingested succession_plans to bronze/silver.")

    # Talent Reviews
    if os.path.exists(files["talent_reviews"]):
        df_raw = pl.read_csv(files["talent_reviews"])
        df_raw.write_parquet("data/bronze/talent_reviews.parquet")
        df = pl.read_csv(files["talent_reviews"], null_values=[""])
        df = df.with_columns([
            pl.col("performance_rating").cast(pl.Float64, strict=False)
        ])
        df.write_parquet("data/silver/talent_reviews.parquet")
        print("Ingested talent_reviews to bronze/silver.")

    # Employee Skills
    if os.path.exists(files["employee_skills"]):
        df_raw = pl.read_csv(files["employee_skills"])
        df_raw.write_parquet("data/bronze/employee_skills.parquet")
        df = pl.read_csv(files["employee_skills"], null_values=[""])
        df.write_parquet("data/silver/employee_skills.parquet")
        print("Ingested employee_skills to bronze/silver.")

    # Career Paths
    if os.path.exists(files["career_paths"]):
        df_raw = pl.read_csv(files["career_paths"])
        df_raw.write_parquet("data/bronze/career_paths.parquet")
        df = pl.read_csv(files["career_paths"], null_values=[""])
        df = df.with_columns([
            pl.col("readiness_months").cast(pl.Int64, strict=False)
        ])
        df.write_parquet("data/silver/career_paths.parquet")
        print("Ingested career_paths to bronze/silver.")

    print("Ingestion complete.")

if __name__ == "__main__":
    ingest()
