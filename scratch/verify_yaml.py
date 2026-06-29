import yaml
import os

files_to_check = [
    "config/access_roles.yml",
    "config/business_rules.yml",
    "config/masking_rules.yml",
    "config/metrics_dictionary.yml",
    "config/privacy_classification.yml",
    "config/real_data_intake_gates.yml",
    "config/real_data_mapping.yml",
    "config/real_data_validation_rules.yml",
    "config/source_systems.yml",
    "config/source_owner_matrix.yml",
    "config/gate_1_signoff_status.yml",
    "config/source_mapping_validation.yml",
    "config/source_readiness_risks.yml",
    "config/gate_2_mapping_approval_status.yml",
    "config/synthetic_test_file_contracts.yml",
    "config/source_control_totals.yml",
    "config/file_naming_standards.yml",
    "config/mapping_exception_register.yml",
    "config/gate_2_signoff_status.yml",
    "config/mapping_exception_resolution.yml",
    "config/gate_3_privacy_security_status.yml",
    "config/field_level_access_matrix.yml",
    "config/export_control_rules.yml",
    "config/audit_logging_requirements.yml",
    "config/data_retention_rules.yml",
    "config/privacy_security_risks.yml",
    "config/gate_3_signoff_status.yml",
    "config/gate_4_dry_run_status.yml",
    "config/synthetic_dry_run_manifest.yml",
    "config/synthetic_dry_run_validation_rules.yml",
    "config/synthetic_dry_run_control_totals.yml",
    "config/synthetic_dry_run_quarantine_rules.yml",
    "config/gate_4_signoff_status.yml",
    "config/gate_5_controlled_load_status.yml",
    "config/controlled_load_authorization.yml",
    "config/first_load_scope.yml",
    "config/authorized_real_data_sources.yml",
    "config/real_data_storage_controls.yml",
    "config/real_data_access_signoff.yml",
    "config/controlled_load_rollback_plan.yml",
    "config/controlled_load_incident_response.yml",
    "config/post_load_validation_checks.yml",
    "config/gate_5_signoff_status.yml",
    "config/gate_5_execution_readiness_decision.yml",
    "config/controlled_load_decision_status.yml",
    "config/pre_execution_readiness_checks.yml",
    "config/controlled_load_scheduling_requirements.yml",
    "config/final_authorization_requirements.yml",
    "config/pre_execution_risk_assessment.yml",
    "config/final_written_authorization_status.yml",
    "config/authorization_evidence_register.yml",
    "config/controlled_load_scheduling_package.yml",
    "config/load_window_owner_availability.yml",
    "config/execution_stop_criteria.yml",
    "config/controlled_load_command_model.yml",
    "config/pre_post_load_communication_checks.yml",
    "config/milestone_3h_status.yml"
]

success = True
for f in files_to_check:
    path = os.path.join(os.path.dirname(__file__), "..", f)
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
            print(f"PASS: {f} parsed successfully.")
    except Exception as e:
        print(f"FAIL: {f} failed to parse. Error: {e}")
        success = False

if not success:
    exit(1)
print("All YAML files validated successfully.")
